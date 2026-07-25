# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import atexit
import logging
import os
import time
from collections import defaultdict, deque
from collections.abc import Generator
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass

from flask import current_app
from rdflib import RDF, Dataset, Graph, Literal, URIRef
from rdflib.plugins.sparql.algebra import translateUpdate
from rdflib.plugins.sparql.parser import parseUpdate
from rdflib.term import Node
from rdflib.util import from_n3
from SPARQLWrapper import JSON
from SPARQLWrapper.SPARQLExceptions import SPARQLWrapperException
from time_agnostic_library.agnostic_entity import AgnosticEntity

from heritrace.editor import Editor
from heritrace.extensions import (
    get_change_tracking_config,
    get_classes_with_multiple_shapes,
    get_custom_filter,
    get_dataset_is_quadstore,
    get_display_rules,
    get_display_rules_use_inverse_relations,
    get_provenance_sparql,
    get_shacl_graph,
    get_sparql,
)
from heritrace.sparql import get_sparql_bindings
from heritrace.utils.converters import convert_to_datetime
from heritrace.utils.display_rules_utils import (
    find_matching_rule,
    get_highest_priority_class,
    get_sortable_properties,
    is_entity_type_visible,
)
from heritrace.utils.shacl_utils import (
    determine_shape_for_classes,
    determine_shape_for_entity_triples,
)
from heritrace.utils.virtuoso_utils import VIRTUOSO_EXCLUDED_GRAPHS, is_virtuoso

_cache: dict[str, tuple[list[dict[str, str | int]], float] | None] = {
    "available_classes": None
}
AVAILABLE_CLASSES_TTL_SECONDS = 60


def _parse_n3(value: str) -> Node:
    result = from_n3(value)
    if not isinstance(result, Node):
        msg = f"Cannot parse N3 value: {value}"
        raise TypeError(msg)
    return result


def n3_set_to_graph(
    n3_set: set[tuple[str, ...]],
    *,
    is_quadstore: bool,
) -> Graph | Dataset:
    if is_quadstore:
        g = Dataset(default_union=True)
        for tup in n3_set:
            quad = (
                _parse_n3(tup[0]),
                _parse_n3(tup[1]),
                _parse_n3(tup[2]),
                _parse_n3(tup[3]),
            )
            g.add(quad)  # type: ignore[arg-type]
    else:
        g = Graph()
        for tup in n3_set:
            g.add((_parse_n3(tup[0]), _parse_n3(tup[1]), _parse_n3(tup[2])))
    return g


def convert_to_rdflib_graphs(snapshots: dict, *, is_quadstore: bool) -> dict:
    converted = {}
    for entity_uri, timestamps in snapshots.items():
        converted[entity_uri] = {}
        for ts, n3_set in timestamps.items():
            converted[entity_uri][ts] = n3_set_to_graph(
                n3_set, is_quadstore=is_quadstore
            )
    return converted


def get_triples_from_graph(
    graph_or_dataset: Graph | Dataset,
    pattern: tuple[URIRef | None, URIRef | None, Node | None],
) -> Generator[tuple[Node, Node, Node]]:
    """
    Get triples from a Graph or Dataset, handling both cases correctly.

    For Dataset (quadstore), converts quads to triples by extracting (s, p, o).
    For Graph (triplestore), uses triples() directly.

    Args:
        graph_or_dataset: Graph or Dataset instance
        pattern: Triple pattern tuple (s, p, o) where each can be None

    Returns:
        Generator of triples (s, p, o)
    """
    if isinstance(graph_or_dataset, Dataset):
        # For Dataset, use quads() and extract only (s, p, o)
        for s, p, o, _g in graph_or_dataset.quads(pattern):
            yield (s, p, o)
    else:
        # For Graph, use triples() directly
        yield from graph_or_dataset.triples(pattern)


COUNT_LIMIT = int(os.getenv("COUNT_LIMIT", "10000"))


@dataclass(slots=True)
class _WorkerPool:
    executor: ProcessPoolExecutor | None = None


_worker_pool = _WorkerPool()


def configure_worker_pool(max_workers: int, gunicorn_workers: int) -> None:
    if max_workers < 1:
        msg = "MAX_WORKERS must be at least 1"
        raise ValueError(msg)
    if gunicorn_workers < 1:
        msg = "GUNICORN_WORKERS must be at least 1"
        raise ValueError(msg)

    if _worker_pool.executor is not None:
        _worker_pool.executor.shutdown()

    workers_per_server = max_workers // gunicorn_workers
    _worker_pool.executor = (
        ProcessPoolExecutor(max_workers=workers_per_server)
        if workers_per_server > 0
        else None
    )


def shutdown_worker_pool() -> None:
    if _worker_pool.executor is not None:
        _worker_pool.executor.shutdown()
        _worker_pool.executor = None


atexit.register(shutdown_worker_pool)


def _wrap_virtuoso_graph_pattern(pattern: str) -> str:
    """Wrap a SPARQL pattern with Virtuoso GRAPH clause if needed."""
    if is_virtuoso():
        return f"""
            GRAPH ?g {{
                {pattern}
            }}
            FILTER(?g NOT IN (<{">, <".join(VIRTUOSO_EXCLUDED_GRAPHS)}>))
        """
    return pattern


def _build_count_query_with_limit(class_uri: str, limit: int) -> str:
    """Build a COUNT query with LIMIT for a specific class."""

    return f"""
        SELECT (COUNT(?subject) as ?count)
        WHERE {{
            {{
                SELECT DISTINCT ?subject
                WHERE {{
                    ?subject a <{class_uri}> .
                }}
                LIMIT {limit}
            }}
        }}
    """


def _count_class_instances(class_uri: str, limit: int = COUNT_LIMIT) -> tuple:
    """
    Count instances of a class up to a limit.

    Returns:
        tuple: (display_count, numeric_count) where display_count may be "LIMIT+"
    """
    sparql = get_sparql()
    query = _build_count_query_with_limit(class_uri, limit + 1)

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    bindings = get_sparql_bindings(sparql.query().convert())

    count = int(bindings[0]["count"]["value"])

    if count > limit:
        return f"{limit}+", limit
    return str(count), count


def _get_entities_with_enhanced_shape_detection(
    class_uri: str, classes_with_multiple_shapes: set[str], limit: int = COUNT_LIMIT
) -> defaultdict[str, list[dict[str, str]]]:
    """
    Get entities for a class using enhanced shape detection
    for classes with multiple shapes.
    Uses LIMIT to avoid loading all entities.
    """
    # Early exit if no classes have multiple shapes
    if (
        not classes_with_multiple_shapes
        or class_uri not in classes_with_multiple_shapes
    ):
        return defaultdict(list)

    sparql = get_sparql()

    subjects_query = f"""
        SELECT DISTINCT ?subject
        WHERE {{
            ?subject a <{class_uri}> .
        }}
        LIMIT {limit}
    """

    sparql.setQuery(subjects_query)
    sparql.setReturnFormat(JSON)
    subjects_bindings = get_sparql_bindings(sparql.query().convert())

    subjects = [r["subject"]["value"] for r in subjects_bindings]

    if not subjects:
        return defaultdict(list)

    # Fetch triples only for these specific subjects
    subjects_filter = " ".join([f"(<{s}>)" for s in subjects])
    pattern_with_filter = (
        f"?subject a <{class_uri}> . ?subject ?p ?o"
        f" . VALUES (?subject) {{ {subjects_filter} }}"
    )

    triples_query = f"""
        SELECT ?subject ?p ?o
        WHERE {{
            {pattern_with_filter}
        }}
    """

    sparql.setQuery(triples_query)
    sparql.setReturnFormat(JSON)
    triples_bindings = get_sparql_bindings(sparql.query().convert())

    entities_triples = defaultdict(list)
    for binding in triples_bindings:
        subject = binding["subject"]["value"]
        predicate = binding["p"]["value"]
        obj = binding["o"]["value"]
        entities_triples[subject].append((subject, predicate, obj))

    shape_to_entities = defaultdict(list)
    for subject_uri, triples in entities_triples.items():
        shape_uri = determine_shape_for_entity_triples(triples)
        if shape_uri:
            entity_key = (class_uri, shape_uri)
            if is_entity_type_visible(entity_key):
                shape_to_entities[shape_uri].append(
                    {"uri": subject_uri, "class": class_uri, "shape": shape_uri}
                )

    return shape_to_entities


def get_classes_from_shacl_or_display_rules() -> list[str]:
    """Extract classes from SHACL shapes or display_rules configuration."""
    sh_target_class = URIRef("http://www.w3.org/ns/shacl#targetClass")
    classes = set()

    shacl_graph = get_shacl_graph()
    if shacl_graph:
        for shape in shacl_graph.subjects(sh_target_class, None, unique=True):
            for target_class in shacl_graph.objects(
                shape, sh_target_class, unique=True
            ):
                classes.add(str(target_class))

    if not classes:
        display_rules = get_display_rules()
        if display_rules:
            for rule in display_rules:
                if "target" in rule and "class" in rule["target"]:
                    classes.add(rule["target"]["class"])

    return list(classes)


def _get_classes_from_config() -> list[str]:
    classes_from_config = get_classes_from_shacl_or_display_rules()
    if classes_from_config:
        return classes_from_config

    return _get_classes_from_sparql()


def _get_classes_from_sparql() -> list[str]:
    sparql = get_sparql()
    pattern = "?subject a ?class ."
    wrapped_pattern = _wrap_virtuoso_graph_pattern(pattern)

    query = f"""
        SELECT DISTINCT ?class
        WHERE {{
            {wrapped_pattern}
        }}
    """

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    class_bindings = get_sparql_bindings(sparql.query().convert())
    return [r["class"]["value"] for r in class_bindings]


def get_available_classes() -> list[dict[str, str | int]]:
    cached = _cache["available_classes"]
    if cached is not None:
        available_classes, computed_at = cached
        if time.monotonic() - computed_at < AVAILABLE_CLASSES_TTL_SECONDS:
            return available_classes

    custom_filter = get_custom_filter()
    class_uris = _get_classes_from_config()

    classes_with_counts = []
    for class_uri in class_uris:
        display_count, numeric_count = _count_class_instances(class_uri)
        classes_with_counts.append(
            {
                "uri": class_uri,
                "display_count": display_count,
                "numeric_count": numeric_count,
            }
        )

    classes_with_counts.sort(key=lambda x: x["numeric_count"], reverse=True)

    available_classes = []
    classes_with_multiple_shapes = get_classes_with_multiple_shapes()

    for class_data in classes_with_counts:
        class_uri = class_data["uri"]

        if classes_with_multiple_shapes and class_uri in classes_with_multiple_shapes:
            shape_to_entities = _get_entities_with_enhanced_shape_detection(
                class_uri, classes_with_multiple_shapes, limit=COUNT_LIMIT
            )

            for shape_uri, entities in shape_to_entities.items():
                if entities:
                    entity_key = (class_uri, shape_uri)
                    available_classes.append(
                        {
                            "uri": class_uri,
                            "label": custom_filter.human_readable_class(entity_key),
                            "count": f"{len(entities)}+"
                            if len(entities) >= COUNT_LIMIT
                            else str(len(entities)),
                            "count_numeric": len(entities),
                            "shape": shape_uri,
                        }
                    )
        else:
            shape_uri = determine_shape_for_classes([class_uri])
            entity_key = (class_uri, shape_uri)

            if is_entity_type_visible(entity_key):
                available_classes.append(
                    {
                        "uri": class_uri,
                        "label": custom_filter.human_readable_class(entity_key),
                        "count": class_data["display_count"],
                        "count_numeric": class_data["numeric_count"],
                        "shape": shape_uri,
                    }
                )

    available_classes.sort(key=lambda x: x["label"].lower())
    _cache["available_classes"] = (available_classes, time.monotonic())
    return available_classes


def build_sort_clause(
    sort_property: str, entity_type: str, shape_uri: str | None = None
) -> str:
    """
    Build a SPARQL sort clause based on the sortableBy configuration.

    Args:
        sort_property: The property to sort by
        entity_type: The entity type URI
        shape_uri: Optional shape URI for more specific sorting rules

    Returns:
        SPARQL sort clause or empty string
    """
    if not sort_property or not entity_type:
        return ""

    rule = find_matching_rule(entity_type, shape_uri)

    if not rule or "sortableBy" not in rule:
        return ""

    sort_config = next(
        (s for s in rule["sortableBy"] if s.get("property") == sort_property), None
    )

    if not sort_config:
        return ""

    return f"OPTIONAL {{ ?subject <{sort_property}> ?sortValue }}"


@dataclass(frozen=True, slots=True)
class CatalogQuery:
    selected_class: str | None
    page: int
    per_page: int
    sort_property: str | None = None
    sort_direction: str = "ASC"
    selected_shape: str | None = None


def _fetch_entity_labels(
    subject_uris: list[str], entity_key: tuple[str | None, str | None]
) -> list[str]:
    if not subject_uris:
        return []

    if _worker_pool.executor is None:
        return [_fetch_entity_label(uri, entity_key) for uri in subject_uris]
    return list(
        _worker_pool.executor.map(
            _fetch_entity_label, subject_uris, [entity_key] * len(subject_uris)
        )
    )


def _fetch_entity_label(uri: str, entity_key: tuple[str | None, str | None]) -> str:
    return get_custom_filter().human_readable_entity(uri, entity_key, None)


def _get_entities_with_shape_filtering(
    query: CatalogQuery,
) -> tuple[list[dict[str, str]], int]:
    sparql = get_sparql()
    selected_class = query.selected_class
    selected_shape = query.selected_shape
    offset = (query.page - 1) * query.per_page
    fetch_limit = query.per_page * 5

    subjects_query = f"""
        SELECT DISTINCT ?subject
        WHERE {{
            ?subject a <{selected_class}> .
        }}
        LIMIT {fetch_limit}
        OFFSET {offset}
    """

    sparql.setQuery(subjects_query)
    sparql.setReturnFormat(JSON)
    subjects_bindings = get_sparql_bindings(sparql.query().convert())

    subjects = [r["subject"]["value"] for r in subjects_bindings]

    if not subjects:
        return [], 0

    subjects_filter = " ".join([f"(<{s}>)" for s in subjects])

    triples_query = f"""
        SELECT ?subject ?p ?o
        WHERE {{
            ?subject a <{selected_class}> . ?subject ?p ?o . VALUES (?subject) {{
            {subjects_filter} }}
        }}
    """

    sparql.setQuery(triples_query)
    sparql.setReturnFormat(JSON)
    triples_bindings = get_sparql_bindings(sparql.query().convert())

    entities_triples = defaultdict(list)
    for binding in triples_bindings:
        subject = binding["subject"]["value"]
        predicate = binding["p"]["value"]
        obj = binding["o"]["value"]
        entities_triples[subject].append((subject, predicate, obj))

    matching_uris = [
        subject_uri
        for subject_uri, triples in entities_triples.items()
        if determine_shape_for_entity_triples(list(triples)) == selected_shape
    ]
    labels = _fetch_entity_labels(matching_uris, (selected_class, selected_shape))
    filtered_entities = [
        {"uri": uri, "label": label}
        for uri, label in zip(matching_uris, labels, strict=True)
    ]

    if query.sort_property and query.sort_direction:
        reverse_sort = query.sort_direction.upper() == "DESC"
        filtered_entities.sort(key=lambda x: x["label"].lower(), reverse=reverse_sort)

    total_count = len(filtered_entities)
    return filtered_entities[: query.per_page], total_count


def get_entities_for_class(
    query: CatalogQuery,
    available_classes: list[dict[str, str | int]],
) -> tuple[list[dict[str, str]], int]:
    if query.selected_class is None:
        msg = "selected_class must not be None"
        raise ValueError(msg)
    sparql = get_sparql()
    classes_with_multiple_shapes = get_classes_with_multiple_shapes()

    selected_class: str = query.selected_class
    selected_shape = query.selected_shape
    page = query.page
    per_page = query.per_page
    sort_property = query.sort_property
    sort_direction = query.sort_direction

    use_shape_filtering = (
        selected_shape and selected_class in classes_with_multiple_shapes
    )

    if use_shape_filtering:
        return _get_entities_with_shape_filtering(query)

    offset = (page - 1) * per_page
    sort_clause = ""
    order_clause = ""

    if sort_property:
        sort_clause = build_sort_clause(sort_property, selected_class, selected_shape)
        if sort_clause:
            order_clause = f"ORDER BY {sort_direction}(?sortValue)"

    entities_query = f"""
        SELECT ?subject {"?sortValue" if sort_property else ""}
        WHERE {{
            ?subject a <{selected_class}> . {sort_clause}
        }}
        {order_clause}
        LIMIT {per_page}
        OFFSET {offset}
    """

    class_info = next(
        (
            c
            for c in available_classes
            if c["uri"] == selected_class and c.get("shape") == selected_shape
        ),
        None,
    )
    total_count = int(class_info["count_numeric"]) if class_info else 0

    sparql.setQuery(entities_query)
    sparql.setReturnFormat(JSON)
    entities_bindings = get_sparql_bindings(sparql.query().convert())

    shape = selected_shape or determine_shape_for_classes([selected_class])
    subject_uris = [result["subject"]["value"] for result in entities_bindings]
    labels = _fetch_entity_labels(subject_uris, (selected_class, shape))
    entities = [
        {"uri": uri, "label": label}
        for uri, label in zip(subject_uris, labels, strict=True)
    ]

    return entities, total_count


def get_catalog_data(
    query: CatalogQuery,
    available_classes: list[dict[str, str | int]],
) -> dict:
    entities = []
    total_count = 0
    sortable_properties = []
    sort_property = query.sort_property

    if query.selected_class:
        sortable_properties = get_sortable_properties(
            (query.selected_class, query.selected_shape)
        )

        if not sort_property and sortable_properties:
            sort_property = sortable_properties[0]["property"]

        inner_query = CatalogQuery(
            selected_class=query.selected_class,
            page=query.page,
            per_page=query.per_page,
            sort_property=sort_property,
            sort_direction=query.sort_direction,
            selected_shape=query.selected_shape,
        )
        entities, total_count = get_entities_for_class(inner_query, available_classes)

    return {
        "entities": entities,
        "total_pages": (
            (total_count + query.per_page - 1) // query.per_page
            if total_count > 0
            else 0
        ),
        "current_page": query.page,
        "per_page": query.per_page,
        "total_count": total_count,
        "sort_property": sort_property,
        "sort_direction": query.sort_direction,
        "sortable_properties": sortable_properties,
        "selected_class": query.selected_class,
        "selected_shape": query.selected_shape,
    }


def warm_catalogue(
    available_classes: list[dict[str, str | int]], per_page: int
) -> None:
    total_started_at = time.monotonic()

    for class_info in available_classes:
        if int(class_info["count_numeric"]) == 0:
            continue

        class_uri = str(class_info["uri"])
        shape_value = class_info["shape"]
        shape_uri = str(shape_value) if shape_value is not None else None
        category_started_at = time.monotonic()

        get_catalog_data(
            CatalogQuery(
                selected_class=class_uri,
                selected_shape=shape_uri,
                page=1,
                per_page=per_page,
            ),
            available_classes,
        )

        current_app.logger.info(
            "[STARTUP] Warmed catalogue category class=%s shape=%s in %.3f seconds",
            class_uri,
            shape_uri,
            time.monotonic() - category_started_at,
        )

    current_app.logger.info(
        "[STARTUP] Catalogue warm-up completed in %.3f seconds",
        time.monotonic() - total_started_at,
    )


def fetch_data_graph_for_subject(subject: URIRef) -> Graph | Dataset:
    g = Dataset() if get_dataset_is_quadstore() else Graph()
    sparql = get_sparql()

    if is_virtuoso():
        # For virtuoso we need to explicitly query the graph
        query = f"""
        SELECT ?predicate ?object ?g WHERE {{
            GRAPH ?g {{
                <{subject}> ?predicate ?object.
            }}
            FILTER(?g NOT IN (<{">, <".join(VIRTUOSO_EXCLUDED_GRAPHS)}>))
        }}
        """
    elif get_dataset_is_quadstore():
        # For non-virtuoso quadstore, we need to query all graphs
        query = f"""
            SELECT ?predicate ?object ?g WHERE {{
                GRAPH ?g {{
                    <{subject}> ?predicate ?object.
                }}
            }}
            """
    else:
        # For regular triplestore
        query = f"""
            SELECT ?predicate ?object WHERE {{
                <{subject}> ?predicate ?object.
            }}
            """

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    bindings = get_sparql_bindings(sparql.query().convert())

    for result in bindings:
        # Create the appropriate value (Literal or URIRef)
        obj_data = result["object"]
        if obj_data["type"] in {"literal", "typed-literal"}:
            if "datatype" in obj_data:
                value = Literal(
                    obj_data["value"], datatype=URIRef(obj_data["datatype"])
                )
            else:
                # Omit explicit datatype to match Reader's import behavior
                value = Literal(obj_data["value"])
        else:
            value = URIRef(obj_data["value"])

        # Add triple/quad based on store type
        if get_dataset_is_quadstore():
            graph_uri = URIRef(result["g"]["value"])
            g.add(
                (  # type: ignore[arg-type]
                    subject,
                    URIRef(result["predicate"]["value"]),
                    value,
                    graph_uri,
                )
            )
        else:
            g.add((subject, URIRef(result["predicate"]["value"]), value))

    return g


def parse_sparql_update(query: str) -> dict[str, list[tuple[Node, Node, Node]]]:
    parsed = parseUpdate(query)
    translated = translateUpdate(parsed).algebra
    modifications = {}

    def extract_quads(
        quads: defaultdict[Node, list[tuple[Node, Node, Node]]],
    ) -> list[tuple[Node, Node, Node]]:
        return [
            (triple[0], triple[1], triple[2])
            for triples in quads.values()
            for triple in triples
        ]

    for operation in translated:
        if operation.name == "DeleteData":
            if hasattr(operation, "quads") and operation.quads:
                deletions = extract_quads(operation.quads)
            else:
                deletions = operation.triples
            if deletions:
                modifications.setdefault("Deletions", []).extend(deletions)
        elif operation.name == "InsertData":
            if hasattr(operation, "quads") and operation.quads:
                additions = extract_quads(operation.quads)
            else:
                additions = operation.triples
            if additions:
                modifications.setdefault("Additions", []).extend(additions)

    return modifications


def fetch_current_state_with_related_entities(
    provenance: dict,
) -> Graph | Dataset:
    """
    Fetch the current state of an entity and all its related entities known from
    provenance.

    Args:
        provenance (dict): Dictionary containing provenance metadata for main entity and
        related entities

    Returns:
        Dataset: A graph containing the current state of all entities
    """
    combined_graph = Dataset() if get_dataset_is_quadstore() else Graph()

    # Fetch state for all entities mentioned in provenance
    for entity_uri in provenance:
        current_graph = fetch_data_graph_for_subject(URIRef(entity_uri))

        if get_dataset_is_quadstore():
            for quad in current_graph.quads():  # type: ignore[union-attr]
                combined_graph.add(quad)  # type: ignore[call-overload]
        else:
            for triple in current_graph:
                combined_graph.add(triple)  # type: ignore[call-overload]

    return combined_graph


@dataclass(frozen=True, slots=True)
class DeletedEntitiesQuery:
    page: int = 1
    per_page: int = 50
    sort_property: str = "deletionTime"
    sort_direction: str = "DESC"
    selected_class: str | None = None
    selected_shape: str | None = None


def _filter_and_paginate_deleted_entities(
    deleted_entities: list[dict],
    query: DeletedEntitiesQuery,
    sortable_properties: list[dict[str, str]],
) -> tuple[
    list[dict],
    str | None,
    str | None,
    list[dict[str, str]],
    int,
]:
    selected_class = query.selected_class
    selected_shape = query.selected_shape

    reverse_sort = query.sort_direction.upper() == "DESC"
    if query.sort_property == "deletionTime":
        deleted_entities.sort(key=lambda e: e["deletionTime"], reverse=reverse_sort)
    else:
        deleted_entities.sort(
            key=lambda e: e["sort_values"].get(query.sort_property, "").lower(),
            reverse=reverse_sort,
        )

    if selected_class:
        if selected_shape is None:
            selected_shape = determine_shape_for_classes([selected_class])
        entity_key = (selected_class, selected_shape)
        sortable_properties.extend(get_sortable_properties(entity_key))

    if selected_class:
        filtered_entities = [
            entity
            for entity in deleted_entities
            if selected_class in entity["entity_types"]
        ]
    else:
        filtered_entities = deleted_entities

    total_count = len(filtered_entities)
    offset = (query.page - 1) * query.per_page
    paginated_entities = filtered_entities[offset : offset + query.per_page]

    return (
        paginated_entities,
        selected_class,
        selected_shape,
        sortable_properties,
        total_count,
    )


def get_deleted_entities_with_filtering(
    query: DeletedEntitiesQuery,
) -> tuple[
    list[dict[str, str | list[str] | dict[str, str]]],
    list[dict[str, str | int]],
    str | None,
    str | None,
    list[dict[str, str]],
    int,
]:
    sortable_properties = [
        {"property": "deletionTime", "displayName": "Deletion Time", "sortType": "date"}
    ]
    provenance_sparql = get_provenance_sparql()
    custom_filter = get_custom_filter()

    prov_query = """
    SELECT DISTINCT ?entity ?lastSnapshot ?deletionTime ?agent ?lastValidSnapshotTime
    WHERE {
        ?lastSnapshot a <http://www.w3.org/ns/prov#Entity> ;
                     <http://www.w3.org/ns/prov#specializationOf> ?entity ;
                     <http://www.w3.org/ns/prov#generatedAtTime> ?deletionTime ;
                     <http://www.w3.org/ns/prov#invalidatedAtTime> ?invalidationTime ;
                     <http://www.w3.org/ns/prov#wasDerivedFrom> ?lastValidSnapshot.

        ?lastValidSnapshot <http://www.w3.org/ns/prov#generatedAtTime>
        ?lastValidSnapshotTime .

        OPTIONAL { ?lastSnapshot <http://www.w3.org/ns/prov#wasAttributedTo> ?agent . }

        FILTER NOT EXISTS {
            ?laterSnapshot <http://www.w3.org/ns/prov#wasDerivedFrom> ?lastSnapshot .
        }
    }
    """
    provenance_sparql.setQuery(prov_query)
    provenance_sparql.setReturnFormat(JSON)
    results_bindings = get_sparql_bindings(provenance_sparql.query().convert())
    if not results_bindings:
        return [], [], None, None, [], 0

    if _worker_pool.executor is None:
        processed_entities = [
            process_deleted_entity(result, sortable_properties)
            for result in results_bindings
        ]
    else:
        futures = [
            _worker_pool.executor.submit(
                process_deleted_entity, result, sortable_properties
            )
            for result in results_bindings
        ]
        processed_entities = [future.result() for future in as_completed(futures)]

    deleted_entities = [entity for entity in processed_entities if entity is not None]

    class_counts = {}
    for entity in deleted_entities:
        for type_uri in entity["entity_types"]:
            class_counts[type_uri] = class_counts.get(type_uri, 0) + 1

    available_classes = [
        {
            "uri": class_uri,
            "label": custom_filter.human_readable_class(
                (class_uri, determine_shape_for_classes([class_uri]))
            ),
            "count": count,
        }
        for class_uri, count in class_counts.items()
    ]

    available_classes.sort(key=lambda x: x["label"].lower())

    resolved_query = query
    if not query.selected_class and available_classes:
        resolved_query = DeletedEntitiesQuery(
            page=query.page,
            per_page=query.per_page,
            sort_property=query.sort_property,
            sort_direction=query.sort_direction,
            selected_class=available_classes[0]["uri"],
            selected_shape=query.selected_shape,
        )

    (
        paginated_entities,
        selected_class,
        selected_shape,
        sortable_properties,
        total_count,
    ) = _filter_and_paginate_deleted_entities(
        deleted_entities, resolved_query, sortable_properties
    )

    return (
        paginated_entities,
        available_classes,
        selected_class,
        selected_shape,
        sortable_properties,
        total_count,
    )


def process_deleted_entity(result: dict, sortable_properties: list) -> dict | None:
    """
    Process a single deleted entity, filtering by visible classes.
    """
    change_tracking_config = get_change_tracking_config()
    custom_filter = get_custom_filter()

    entity_uri = result["entity"]["value"]
    last_valid_snapshot_time = result["lastValidSnapshotTime"]["value"]

    agnostic_entity = AgnosticEntity(
        res=entity_uri,
        config=change_tracking_config,
        include_related_objects=True,
        include_merged_entities=True,
        include_reverse_relations=get_display_rules_use_inverse_relations(),
    )
    state, _, _ = agnostic_entity.get_state_at_time(
        (last_valid_snapshot_time, last_valid_snapshot_time)
    )
    state = convert_to_rdflib_graphs(state, is_quadstore=get_dataset_is_quadstore())

    if entity_uri not in state:
        return None

    last_valid_dt = convert_to_datetime(last_valid_snapshot_time)
    if last_valid_dt is None:
        msg = "last_valid_dt must not be None"
        raise AssertionError(msg)
    last_valid_state: Graph | Dataset = state[entity_uri][last_valid_dt.isoformat()]

    entity_types = [
        str(o)
        for _, _, o in get_triples_from_graph(
            last_valid_state, (URIRef(entity_uri), RDF.type, None)
        )
    ]
    highest_priority_type = get_highest_priority_class(entity_types)
    if not highest_priority_type:
        return None
    shape = determine_shape_for_classes([highest_priority_type])
    visible_types = [
        t
        for t in entity_types
        if is_entity_type_visible((t, determine_shape_for_classes([t])))
    ]
    if not visible_types:
        return None

    sort_values = {}
    for prop in sortable_properties:
        prop_uri = prop["property"]
        values = [
            str(o)
            for _, _, o in get_triples_from_graph(
                last_valid_state, (URIRef(entity_uri), URIRef(prop_uri), None)
            )
        ]
        sort_values[prop_uri] = values[0] if values else ""

    return {
        "uri": entity_uri,
        "deletionTime": result["deletionTime"]["value"],
        "deletedBy": custom_filter.format_agent_reference(
            result.get("agent", {}).get("value", "")
        ),
        "lastValidSnapshotTime": last_valid_snapshot_time,
        "type": custom_filter.human_readable_predicate(
            highest_priority_type, (highest_priority_type, shape)
        ),
        "label": custom_filter.human_readable_entity(
            entity_uri, (highest_priority_type, shape), last_valid_state
        ),
        "entity_types": visible_types,
        "sort_values": sort_values,
    }


def find_orphaned_entities(
    subject: URIRef,
    entity_type: str,
    predicate: URIRef | None = None,
    object_value: str | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    sparql = get_sparql()
    display_rules = get_display_rules()

    intermediate_classes = set()

    for rule in display_rules:
        if (
            "target" in rule
            and "class" in rule["target"]
            and rule["target"]["class"] == entity_type
        ):
            for prop in rule.get("displayProperties", []):
                if "intermediateRelation" in prop:
                    intermediate_classes.add(prop["intermediateRelation"]["class"])

    orphan_query = f"""
    SELECT DISTINCT ?entity ?type
    WHERE {{
        {f"<{subject}> <{predicate}> ?entity ." if predicate and object_value else ""}
        {f"FILTER(?entity = <{object_value}>)" if predicate and object_value else ""}

        # If no specific predicate, get all connected entities
        {f"<{subject}> ?p ?entity ." if not predicate else ""}

        FILTER(isIRI(?entity))
        ?entity a ?type .

        # No incoming references from other entities
        FILTER NOT EXISTS {{
            ?other ?anyPredicate ?entity .
            FILTER(?other != <{subject}>)
        }}

        # No outgoing references to active entities
        FILTER NOT EXISTS {{
            ?entity ?outgoingPredicate ?connectedEntity .
            ?connectedEntity ?furtherPredicate ?furtherObject .
            {f"FILTER(?connectedEntity != <{subject}>)" if not predicate else ""}
        }}

        # Exclude intermediate relation entities
        FILTER(?type NOT IN (<{">, <".join(intermediate_classes)}>))
    }}
    """

    # Query to find orphaned intermediate relations
    if predicate and object_value:
        intermediate_query = f"""
        SELECT DISTINCT ?entity ?type
        WHERE {{
            <{object_value}> a ?type .
            FILTER(?type IN (<{">, <".join(intermediate_classes)}>))
            BIND(<{object_value}> AS ?entity)
        }}
        """
    else:
        # Se stiamo cancellando l'intera entità, trova tutte le entità intermedie
        # collegate
        intermediate_query = f"""
        SELECT DISTINCT ?entity ?type
        WHERE {{
            # Find intermediate relations connected to the entity being deleted
            {{
                <{subject}> ?p ?entity .
                ?entity a ?type .
                FILTER(?type IN (<{">, <".join(intermediate_classes)}>))
            }} UNION {{
                ?entity ?p <{subject}> .
                ?entity a ?type .
                FILTER(?type IN (<{">, <".join(intermediate_classes)}>))
            }}
        }}
        """

    orphaned = []
    intermediate_orphans = []

    # Execute queries and process results
    for query, result_list in [
        (orphan_query, orphaned),
        (intermediate_query, intermediate_orphans),
    ]:
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        query_bindings = get_sparql_bindings(sparql.query().convert())

        for result in query_bindings:
            result_list.append(
                {"uri": result["entity"]["value"], "type": result["type"]["value"]}
            )

    return orphaned, intermediate_orphans


def import_entity_graph(
    editor: Editor,
    subject: URIRef,
    max_depth: int = 5,
    *,
    include_referencing_entities: bool = False,
) -> Editor:
    imported_subjects: set[str] = set()
    subject_str = str(subject)

    if include_referencing_entities:
        sparql = get_sparql()

        if editor.dataset_is_quadstore:
            query = f"""
            SELECT DISTINCT ?s
            WHERE {{
                GRAPH ?g {{
                    ?s ?p <{subject}> .
                }}
                FILTER(?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
            }}
            """
        else:
            query = f"""
            SELECT DISTINCT ?s
            WHERE {{
                ?s ?p <{subject}> .
                FILTER(?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
            }}
            """

        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        ref_bindings = get_sparql_bindings(sparql.query().convert())

        for result in ref_bindings:
            referencing_subject = result["s"]["value"]
            if (
                referencing_subject != subject_str
                and referencing_subject not in imported_subjects
            ):
                imported_subjects.add(referencing_subject)
                editor.import_entity(URIRef(referencing_subject))

    # Breadth-first traversal so each entity is visited at its minimal distance
    # from the subject: a depth-first walk would consume one level per hop along
    # ordering chains (e.g. oco:hasNext) and silently skip entities pushed beyond
    # max_depth, leaving them without provenance snapshots.
    queue: deque[tuple[str, int]] = deque([(subject_str, 1)])
    while queue:
        current_subject, current_depth = queue.popleft()
        if current_depth > max_depth or current_subject in imported_subjects:
            continue

        imported_subjects.add(current_subject)
        editor.import_entity(URIRef(current_subject))

        query = f"""
            SELECT ?p ?o
            WHERE {{
                <{current_subject}> ?p ?o .
                FILTER(isIRI(?o))
                FILTER(?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
            }}
        """

        sparql = get_sparql()
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        inner_bindings = get_sparql_bindings(sparql.query().convert())

        for result in inner_bindings:
            queue.append((result["o"]["value"], current_depth + 1))

    return editor


def get_entity_types(subject_uri: str) -> list[str]:
    sparql = get_sparql()

    query = f"""
    SELECT ?type WHERE {{
        <{subject_uri}> a ?type .
    }}
    """

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    bindings = get_sparql_bindings(sparql.query().convert())

    return [result["type"]["value"] for result in bindings]


def collect_referenced_entities(
    data: dict[str, str | dict | list] | list | str,
    existing_entities: set[str] | None = None,
) -> set[str]:
    """
    Recursively collect all URIs of existing entities referenced in the structured data.

    This function traverses the structured data to find explicit references to existing
    entities
    that need to be imported into the editor before calling preexisting_finished().

    Args:
        data: The structured data (can be dict, list, or string)
        existing_entities: Set to collect URIs (created if None)

    Returns:
        Set of URIs (strings) of existing entities that should be imported
    """

    if existing_entities is None:
        existing_entities = set()

    if isinstance(data, dict):
        if data.get("is_existing_entity") is True and "entity_uri" in data:
            existing_entities.add(str(data["entity_uri"]))

        # If it's an entity with entity_type, it's a new entity being created
        elif "entity_type" in data:
            properties = data.get("properties", {})
            if isinstance(properties, dict):
                for prop_values in properties.values():
                    collect_referenced_entities(prop_values, existing_entities)
        else:
            for value in data.values():
                collect_referenced_entities(value, existing_entities)

    elif isinstance(data, list):
        for item in data:
            collect_referenced_entities(item, existing_entities)

    return existing_entities


def import_referenced_entities(
    editor: Editor,
    structured_data: dict[str, str | dict | list] | list | str,
) -> None:
    referenced_entities = collect_referenced_entities(structured_data)
    for entity_uri in referenced_entities:
        try:
            editor.import_entity(URIRef(entity_uri))
        except (SPARQLWrapperException, OSError, ValueError):  # noqa: PERF203
            logging.getLogger(__name__).debug(
                "Failed to import referenced entity %s", entity_uri
            )
            continue
