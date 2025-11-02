import os
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List

from rdflib import RDF, Dataset, Graph, Literal, URIRef
from rdflib.plugins.sparql.algebra import translateUpdate
from rdflib.plugins.sparql.parser import parseUpdate
from SPARQLWrapper import JSON
from time_agnostic_library.agnostic_entity import AgnosticEntity

from heritrace.editor import Editor
from heritrace.extensions import (get_change_tracking_config,
                                  get_classes_with_multiple_shapes,
                                  get_custom_filter, get_dataset_is_quadstore,
                                  get_display_rules, get_provenance_sparql,
                                  get_shacl_graph, get_sparql)
from heritrace.utils.converters import convert_to_datetime
from heritrace.utils.display_rules_utils import (find_matching_rule,
                                                 get_highest_priority_class,
                                                 get_sortable_properties,
                                                 is_entity_type_visible)
from heritrace.utils.shacl_utils import (determine_shape_for_classes,
                                         determine_shape_for_entity_triples)
from heritrace.utils.virtuoso_utils import (VIRTUOSO_EXCLUDED_GRAPHS,
                                            is_virtuoso)

_AVAILABLE_CLASSES_CACHE = None


def get_triples_from_graph(graph_or_dataset, pattern):
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
        for s, p, o, g in graph_or_dataset.quads(pattern):
            yield (s, p, o)
    else:
        # For Graph, use triples() directly
        yield from graph_or_dataset.triples(pattern)
COUNT_LIMIT = int(os.getenv("COUNT_LIMIT", "10000"))


def precompute_available_classes_cache():
    """Pre-compute available classes cache at application startup."""
    global _AVAILABLE_CLASSES_CACHE
    _AVAILABLE_CLASSES_CACHE = get_available_classes()
    return _AVAILABLE_CLASSES_CACHE


def _wrap_virtuoso_graph_pattern(pattern: str) -> str:
    """Wrap a SPARQL pattern with Virtuoso GRAPH clause if needed."""
    if is_virtuoso():
        return f"""
            GRAPH ?g {{
                {pattern}
            }}
            FILTER(?g NOT IN (<{'>, <'.join(VIRTUOSO_EXCLUDED_GRAPHS)}>))
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
    result = sparql.query().convert()

    count = int(result["results"]["bindings"][0]["count"]["value"])

    if count > limit:
        return f"{limit}+", limit
    return str(count), count


def _get_entities_with_enhanced_shape_detection(class_uri: str, classes_with_multiple_shapes: set, limit: int = COUNT_LIMIT):
    """
    Get entities for a class using enhanced shape detection for classes with multiple shapes.
    Uses LIMIT to avoid loading all entities.
    """
    # Early exit if no classes have multiple shapes
    if not classes_with_multiple_shapes or class_uri not in classes_with_multiple_shapes:
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
    subjects_results = sparql.query().convert()

    subjects = [r["subject"]["value"] for r in subjects_results["results"]["bindings"]]

    if not subjects:
        return defaultdict(list)

    # Fetch triples only for these specific subjects
    subjects_filter = " ".join([f"(<{s}>)" for s in subjects])
    pattern_with_filter = f"?subject a <{class_uri}> . ?subject ?p ?o . VALUES (?subject) {{ {subjects_filter} }}"

    triples_query = f"""
        SELECT ?subject ?p ?o
        WHERE {{
            {pattern_with_filter}
        }}
    """

    sparql.setQuery(triples_query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    entities_triples = defaultdict(list)
    for binding in results["results"]["bindings"]:
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
                shape_to_entities[shape_uri].append({
                    "uri": subject_uri,
                    "class": class_uri,
                    "shape": shape_uri
                })

    return shape_to_entities


def get_classes_from_shacl_or_display_rules():
    """Extract classes from SHACL shapes or display_rules configuration."""
    SH_TARGET_CLASS = URIRef("http://www.w3.org/ns/shacl#targetClass")
    classes = set()

    shacl_graph = get_shacl_graph()
    if shacl_graph:
        for shape in shacl_graph.subjects(SH_TARGET_CLASS, None, unique=True):
            for target_class in shacl_graph.objects(shape, SH_TARGET_CLASS, unique=True):
                classes.add(str(target_class))

    if not classes:
        display_rules = get_display_rules()
        if display_rules:
            for rule in display_rules:
                if "target" in rule and "class" in rule["target"]:
                    classes.add(rule["target"]["class"])

    return list(classes)


def get_available_classes():
    """
    Fetch and format all available entity classes.
    Returns cached result if available (computed at startup).
    For small datasets (< COUNT_LIMIT), cache is invalidated to keep counts accurate.
    """
    global _AVAILABLE_CLASSES_CACHE

    if _AVAILABLE_CLASSES_CACHE is not None:
        total_count = sum(cls.get('count_numeric', 0) for cls in _AVAILABLE_CLASSES_CACHE)
        if total_count < COUNT_LIMIT:
            _AVAILABLE_CLASSES_CACHE = None

    if _AVAILABLE_CLASSES_CACHE is not None:
        return _AVAILABLE_CLASSES_CACHE

    custom_filter = get_custom_filter()
    classes_from_config = get_classes_from_shacl_or_display_rules()

    if classes_from_config:
        class_uris = classes_from_config
    else:
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
        results = sparql.query().convert()
        class_uris = [r["class"]["value"] for r in results["results"]["bindings"]]

    # Count instances for each class
    classes_with_counts = []
    for class_uri in class_uris:
        display_count, numeric_count = _count_class_instances(class_uri)
        classes_with_counts.append({
            "uri": class_uri,
            "display_count": display_count,
            "numeric_count": numeric_count
        })

    # Sort by count descending
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
                    available_classes.append({
                        "uri": class_uri,
                        "label": custom_filter.human_readable_class(entity_key),
                        "count": f"{len(entities)}+" if len(entities) >= COUNT_LIMIT else str(len(entities)),
                        "count_numeric": len(entities),
                        "shape": shape_uri
                    })
        else:
            shape_uri = determine_shape_for_classes([class_uri])
            entity_key = (class_uri, shape_uri)

            if is_entity_type_visible(entity_key):
                available_classes.append({
                    "uri": class_uri,
                    "label": custom_filter.human_readable_class(entity_key),
                    "count": class_data["display_count"],
                    "count_numeric": class_data["numeric_count"],
                    "shape": shape_uri
                })

    available_classes.sort(key=lambda x: x["label"].lower())
    return available_classes


def build_sort_clause(sort_property: str, entity_type: str, shape_uri: str = None) -> str:
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
        (s for s in rule["sortableBy"] if s.get("property") == sort_property),
        None
    )
    
    if not sort_config:
        return ""
        
    return f"OPTIONAL {{ ?subject <{sort_property}> ?sortValue }}"


def get_entities_for_class(
    selected_class, page, per_page, sort_property=None, sort_direction="ASC", selected_shape=None
):
    """
    Retrieve entities for a specific class with pagination and sorting.

    Args:
        selected_class (str): URI of the class to retrieve entities for
        page (int): Page number (1-indexed)
        per_page (int): Number of entities per page
        sort_property (str, optional): Property URI to sort by. Defaults to None.
        sort_direction (str, optional): Sort direction ("ASC" or "DESC"). Defaults to "ASC".
        selected_shape (str, optional): Shape URI for filtering entities. Defaults to None.

    Returns:
        tuple: (list of entities, total count)

    Performance Notes:
        - If sort_property is None, NO ORDER BY clause is applied to the SPARQL query.
          This significantly improves performance for large datasets by avoiding expensive
          sorting operations on URIs.
        - Without explicit ordering, the triplestore returns results in its natural order,
          which is deterministic within a session but may vary after database reloads.
        - For optimal performance with large datasets, configure display_rules.yaml without
          sortableBy properties to prevent users from triggering expensive sort operations.
    """
    sparql = get_sparql()
    custom_filter = get_custom_filter()
    classes_with_multiple_shapes = get_classes_with_multiple_shapes()

    use_shape_filtering = (selected_shape and selected_class in classes_with_multiple_shapes)

    if use_shape_filtering:
        # For shape filtering, we need to fetch entities and check their shape
        # Use a larger LIMIT to ensure we get enough entities after filtering
        offset = (page - 1) * per_page
        fetch_limit = per_page * 5  # Safety margin for filtering

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
        subjects_results = sparql.query().convert()

        subjects = [r["subject"]["value"] for r in subjects_results["results"]["bindings"]]

        if not subjects:
            return [], 0

        # Now fetch triples for these specific subjects
        subjects_filter = " ".join([f"(<{s}>)" for s in subjects])

        triples_query = f"""
            SELECT ?subject ?p ?o
            WHERE {{
                ?subject a <{selected_class}> . ?subject ?p ?o . VALUES (?subject) {{ {subjects_filter} }}
            }}
        """

        sparql.setQuery(triples_query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        entities_triples = defaultdict(list)
        for binding in results["results"]["bindings"]:
            subject = binding["subject"]["value"]
            predicate = binding["p"]["value"]
            obj = binding["o"]["value"]
            entities_triples[subject].append((subject, predicate, obj))

        filtered_entities = []
        for subject_uri, triples in entities_triples.items():
            entity_shape = determine_shape_for_entity_triples(list(triples))
            if entity_shape == selected_shape:
                entity_label = custom_filter.human_readable_entity(
                    subject_uri, (selected_class, selected_shape), None
                )
                filtered_entities.append({"uri": subject_uri, "label": entity_label})

        if sort_property and sort_direction:
            reverse_sort = sort_direction.upper() == "DESC"
            filtered_entities.sort(key=lambda x: x["label"].lower(), reverse=reverse_sort)

        # For shape-filtered results, we can't accurately determine total_count without scanning all entities
        # Return the number of filtered entities as an approximation
        total_count = len(filtered_entities)
        return filtered_entities[:per_page], total_count

    # Standard pagination path
    offset = (page - 1) * per_page
    sort_clause = ""
    order_clause = ""

    if sort_property:
        sort_clause = build_sort_clause(sort_property, selected_class, selected_shape)
        if sort_clause:
            order_clause = f"ORDER BY {sort_direction}(?sortValue)"

    entities_query = f"""
        SELECT ?subject {f"?sortValue" if sort_property else ""}
        WHERE {{
            ?subject a <{selected_class}> . {sort_clause}
        }}
        {order_clause}
        LIMIT {per_page}
        OFFSET {offset}
    """

    available_classes = get_available_classes()

    class_info = next(
        (c for c in available_classes
         if c["uri"] == selected_class and c.get("shape") == selected_shape),
        None
    )
    total_count = class_info.get("count_numeric", 0) if class_info else 0

    sparql.setQuery(entities_query)
    sparql.setReturnFormat(JSON)
    entities_results = sparql.query().convert()

    entities = []
    shape = selected_shape if selected_shape else determine_shape_for_classes([selected_class])

    for result in entities_results["results"]["bindings"]:
        subject_uri = result["subject"]["value"]
        entity_label = custom_filter.human_readable_entity(
            subject_uri, (selected_class, shape), None
        )
        entities.append({"uri": subject_uri, "label": entity_label})

    return entities, total_count


def get_catalog_data(
    selected_class: str,
    page: int,
    per_page: int,
    sort_property: str = None,
    sort_direction: str = "ASC",
    selected_shape: str = None
) -> dict:
    """
    Get catalog data with pagination and sorting.

    Args:
        selected_class (str): Selected class URI
        page (int): Current page number
        per_page (int): Items per page
        sort_property (str, optional): Property to sort by
        sort_direction (str, optional): Sort direction ('ASC' or 'DESC')
        selected_shape (str, optional): URI of the shape to use for sorting rules

    Returns:
        dict: Catalog data including entities, pagination info, and sort settings
    """

    entities = []
    total_count = 0
    sortable_properties = []

    if selected_class:
        sortable_properties = get_sortable_properties(
            (selected_class, selected_shape)
        )
        
        if not sort_property and sortable_properties:
            sort_property = sortable_properties[0]["property"]
            
        entities, total_count = get_entities_for_class(
            selected_class, page, per_page, sort_property, sort_direction, selected_shape
        )

    return {
        "entities": entities,
        "total_pages": (
            (total_count + per_page - 1) // per_page if total_count > 0 else 0
        ),
        "current_page": page,
        "per_page": per_page,
        "total_count": total_count,
        "sort_property": sort_property,
        "sort_direction": sort_direction,
        "sortable_properties": sortable_properties,
        "selected_class": selected_class,
        "selected_shape": selected_shape,
    }


def fetch_data_graph_for_subject(subject: str) -> Graph | Dataset:
    """
    Fetch all triples/quads associated with a subject from the dataset.
    Handles both triplestore and quadstore cases appropriately.

    Args:
        subject (str): The URI of the subject to fetch data for

    Returns:
        Graph|Dataset: A graph containing all triples/quads for the subject
    """
    g = Dataset() if get_dataset_is_quadstore() else Graph()
    sparql = get_sparql()

    if is_virtuoso():
        # For virtuoso we need to explicitly query the graph
        query = f"""
        SELECT ?predicate ?object ?g WHERE {{
            GRAPH ?g {{
                <{subject}> ?predicate ?object.
            }}
            FILTER(?g NOT IN (<{'>, <'.join(VIRTUOSO_EXCLUDED_GRAPHS)}>))
        }}
        """
    else:
        if get_dataset_is_quadstore():
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
    query_results = sparql.query().convert()
    results = query_results.get("results", {}).get("bindings", [])

    for result in results:
        # Create the appropriate value (Literal or URIRef)
        obj_data = result["object"]
        if obj_data["type"] in {"literal", "typed-literal"}:
            if "datatype" in obj_data:
                value = Literal(
                    obj_data["value"], datatype=URIRef(obj_data["datatype"])
                )
            else:
                # Create literal without explicit datatype to match Reader.import_entities_from_triplestore
                value = Literal(obj_data["value"])
        else:
            value = URIRef(obj_data["value"])

        # Add triple/quad based on store type
        if get_dataset_is_quadstore():
            graph_uri = URIRef(result["g"]["value"])
            g.add(
                (
                    URIRef(subject),
                    URIRef(result["predicate"]["value"]),
                    value,
                    graph_uri,
                )
            )
        else:
            g.add((URIRef(subject), URIRef(result["predicate"]["value"]), value))

    return g


def parse_sparql_update(query) -> dict:
    parsed = parseUpdate(query)
    translated = translateUpdate(parsed).algebra
    modifications = {}

    def extract_quads(quads):
        result = []
        for graph, triples in quads.items():
            for triple in triples:
                result.append((triple[0], triple[1], triple[2]))
        return result

    for operation in translated:
        if operation.name == "DeleteData":
            if hasattr(operation, "quads") and operation.quads:
                deletions = extract_quads(operation.quads)
            else:
                deletions = operation.triples
            if deletions:
                modifications.setdefault("Deletions", list()).extend(deletions)
        elif operation.name == "InsertData":
            if hasattr(operation, "quads") and operation.quads:
                additions = extract_quads(operation.quads)
            else:
                additions = operation.triples
            if additions:
                modifications.setdefault("Additions", list()).extend(additions)

    return modifications


def fetch_current_state_with_related_entities(
    provenance: dict,
) -> Graph | Dataset:
    """
    Fetch the current state of an entity and all its related entities known from provenance.

    Args:
        provenance (dict): Dictionary containing provenance metadata for main entity and related entities

    Returns:
        Dataset: A graph containing the current state of all entities
    """
    combined_graph = Dataset() if get_dataset_is_quadstore() else Graph()

    # Fetch state for all entities mentioned in provenance
    for entity_uri in provenance.keys():
        current_graph = fetch_data_graph_for_subject(entity_uri)

        if get_dataset_is_quadstore():
            for quad in current_graph.quads():
                combined_graph.add(quad)
        else:
            for triple in current_graph:
                combined_graph.add(triple)

    return combined_graph


def get_deleted_entities_with_filtering(
    page=1,
    per_page=50,
    sort_property="deletionTime",
    sort_direction="DESC",
    selected_class=None,
    selected_shape=None,
):
    """
    Fetch and process deleted entities from the provenance graph, with filtering and sorting.
    """
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

        ?lastValidSnapshot <http://www.w3.org/ns/prov#generatedAtTime> ?lastValidSnapshotTime .

        OPTIONAL { ?lastSnapshot <http://www.w3.org/ns/prov#wasAttributedTo> ?agent . }

        FILTER NOT EXISTS {
            ?laterSnapshot <http://www.w3.org/ns/prov#wasDerivedFrom> ?lastSnapshot .
        }
    }
    """
    provenance_sparql.setQuery(prov_query)
    provenance_sparql.setReturnFormat(JSON)
    prov_results = provenance_sparql.query().convert()

    results_bindings = prov_results["results"]["bindings"]
    if not results_bindings:
        return [], [], None, None, [], 0

    deleted_entities = []
    max_workers = max(1, min(os.cpu_count() or 4, len(results_bindings)))
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_entity = {
            executor.submit(process_deleted_entity, result, sortable_properties): result
            for result in results_bindings
        }
        for future in as_completed(future_to_entity):
            entity_info = future.result()
            if entity_info is not None:
                deleted_entities.append(entity_info)

    class_counts = {}
    for entity in deleted_entities:
        for type_uri in entity["entity_types"]:
            class_counts[type_uri] = class_counts.get(type_uri, 0) + 1

    available_classes = [
        {
            "uri": class_uri,
            "label": custom_filter.human_readable_class((class_uri, determine_shape_for_classes([class_uri]))),
            "count": count,
        }
        for class_uri, count in class_counts.items()
    ]

    reverse_sort = sort_direction.upper() == "DESC"
    if sort_property == "deletionTime":
        deleted_entities.sort(key=lambda e: e["deletionTime"], reverse=reverse_sort)
    else:
        deleted_entities.sort(
            key=lambda e: e["sort_values"].get(sort_property, "").lower(),
            reverse=reverse_sort,
        )

    available_classes.sort(key=lambda x: x["label"].lower())
    if not selected_class and available_classes:
        selected_class = available_classes[0]["uri"]

    if selected_class:
        if selected_shape is None:
            selected_shape = determine_shape_for_classes([selected_class])
        entity_key = (selected_class, selected_shape)
        sortable_properties.extend(
            get_sortable_properties(entity_key)
        )

    if selected_class:
        filtered_entities = [
            entity
            for entity in deleted_entities
            if selected_class in entity["entity_types"]
        ]
    else:
        filtered_entities = deleted_entities

    total_count = len(filtered_entities)
    offset = (page - 1) * per_page
    paginated_entities = filtered_entities[offset : offset + per_page]

    return paginated_entities, available_classes, selected_class, selected_shape, sortable_properties, total_count


def process_deleted_entity(result: dict, sortable_properties: list) -> dict | None:
    """
    Process a single deleted entity, filtering by visible classes.
    """
    change_tracking_config = get_change_tracking_config()
    custom_filter = get_custom_filter()

    entity_uri = result["entity"]["value"]
    last_valid_snapshot_time = result["lastValidSnapshotTime"]["value"]

    agnostic_entity = AgnosticEntity(
        res=entity_uri, config=change_tracking_config, include_related_objects=True, include_merged_entities=True, include_reverse_relations=True
    )
    state, _, _ = agnostic_entity.get_state_at_time(
        (last_valid_snapshot_time, last_valid_snapshot_time)
    )

    if entity_uri not in state:
        return None

    last_valid_time = convert_to_datetime(last_valid_snapshot_time, stringify=True)
    last_valid_state: Dataset = state[entity_uri][last_valid_time]

    entity_types = [
        str(o)
        for s, p, o in get_triples_from_graph(last_valid_state, (URIRef(entity_uri), RDF.type, None))
    ]
    highest_priority_type = get_highest_priority_class(entity_types)
    shape = determine_shape_for_classes([highest_priority_type])
    visible_types = [t for t in entity_types if is_entity_type_visible((t, determine_shape_for_classes([t])))]
    if not visible_types:
        return None

    sort_values = {}
    for prop in sortable_properties:
        prop_uri = prop["property"]
        values = [
            str(o)
            for s, p, o in get_triples_from_graph(
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


def find_orphaned_entities(subject, entity_type, predicate=None, object_value=None):
    """
    Find entities that would become orphaned after deleting a triple or an entire entity,
    including intermediate relation entities.

    An entity is considered orphaned if:
    1. It has no incoming references from other entities (except from the entity being deleted)
    2. It does not reference any entities that are subjects of other triples

    For intermediate relations, an entity is also considered orphaned if:
    1. It connects to the entity being deleted
    2. It has no other valid connections after the deletion
    3. It is directly involved in the deletion operation (if predicate and object_value are specified)

    Args:
        subject (str): The URI of the subject being deleted
        entity_type (str): The type of the entity being deleted
        predicate (str, optional): The predicate being deleted
        object_value (str, optional): The object value being deleted

    Returns:
        tuple: Lists of (orphaned_entities, intermediate_orphans)
    """
    sparql = get_sparql()
    display_rules = get_display_rules()

    intermediate_classes = set()

    for rule in display_rules:
        if "target" in rule and "class" in rule["target"] and rule["target"]["class"] == entity_type:
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
        FILTER(?type NOT IN (<{f">, <".join(intermediate_classes)}>))
    }}
    """

    # Query to find orphaned intermediate relations
    if predicate and object_value:
        intermediate_query = f"""
        SELECT DISTINCT ?entity ?type
        WHERE {{
            <{object_value}> a ?type .
            FILTER(?type IN (<{f">, <".join(intermediate_classes)}>))            
            BIND(<{object_value}> AS ?entity)
        }}
        """
    else:
        # Se stiamo cancellando l'intera entità, trova tutte le entità intermedie collegate
        intermediate_query = f"""
        SELECT DISTINCT ?entity ?type
        WHERE {{
            # Find intermediate relations connected to the entity being deleted
            {{
                <{subject}> ?p ?entity .
                ?entity a ?type .
                FILTER(?type IN (<{f">, <".join(intermediate_classes)}>))
            }} UNION {{
                ?entity ?p <{subject}> .
                ?entity a ?type .
                FILTER(?type IN (<{f">, <".join(intermediate_classes)}>))
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
        results = sparql.query().convert()

        for result in results["results"]["bindings"]:
            result_list.append(
                {"uri": result["entity"]["value"], "type": result["type"]["value"]}
            )

    return orphaned, intermediate_orphans


def import_entity_graph(editor: Editor, subject: str, max_depth: int = 5, include_referencing_entities: bool = False):
    """
    Recursively import the main subject and its connected entity graph up to a specified depth.

    This function imports the specified subject and all entities connected to it,
    directly or indirectly, up to the maximum depth specified. It traverses the
    graph of connected entities, importing each one into the editor.

    Args:
    editor (Editor): The Editor instance to use for importing.
    subject (str): The URI of the subject to start the import from.
    max_depth (int): The maximum depth of recursion (default is 5).
    include_referencing_entities (bool): Whether to include entities that have the subject as their object (default False).
                                         Useful when deleting an entity to ensure all references are properly removed.

    Returns:
    Editor: The updated Editor instance with all imported entities.
    """
    imported_subjects = set()

    # First import referencing entities if needed
    if include_referencing_entities:
        sparql = get_sparql()
        
        # Build query based on database type
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
        results = sparql.query().convert()
        
        # Import each referencing entity
        for result in results["results"]["bindings"]:
            referencing_subject = result["s"]["value"]
            if referencing_subject != subject and referencing_subject not in imported_subjects:
                imported_subjects.add(referencing_subject)
                editor.import_entity(URIRef(referencing_subject))

    def recursive_import(current_subject: str, current_depth: int):
        if current_depth > max_depth or current_subject in imported_subjects:
            return

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
        results = sparql.query().convert()

        for result in results["results"]["bindings"]:
            object_entity = result["o"]["value"]
            recursive_import(object_entity, current_depth + 1)

    recursive_import(subject, 1)
    return editor


def get_entity_types(subject_uri: str) -> List[str]:
    """
    Get all RDF types for an entity.

    Args:
        subject_uri: URI of the entity

    Returns:
        List of type URIs
    """
    sparql = get_sparql()

    query = f"""
    SELECT ?type WHERE {{
        <{subject_uri}> a ?type .
    }}
    """

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    return [result["type"]["value"] for result in results["results"]["bindings"]]


def collect_referenced_entities(data, existing_entities=None):
    """
    Recursively collect all URIs of existing entities referenced in the structured data.
    
    This function traverses the structured data to find explicit references to existing entities
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
            existing_entities.add(data["entity_uri"])
        
        # If it's an entity with entity_type, it's a new entity being created
        elif "entity_type" in data:
            properties = data.get("properties", {})
            for prop_values in properties.values():
                collect_referenced_entities(prop_values, existing_entities)
        else:
            for value in data.values():
                collect_referenced_entities(value, existing_entities)
                
    elif isinstance(data, list):
        for item in data:
            collect_referenced_entities(item, existing_entities)
                
    return existing_entities


def import_referenced_entities(editor, structured_data):
    """
    Import all existing entities referenced in structured data into the editor.
    
    This function should be called before editor.preexisting_finished() to ensure
    that all existing entities that will be linked have their snapshots created.
    
    Args:
        editor: The Editor instance
        structured_data: The structured data containing entity references
    """
    referenced_entities = collect_referenced_entities(structured_data)
    for entity_uri in referenced_entities:
        try:
            editor.import_entity(entity_uri)
        except Exception as e:
            print(f"Warning: Could not import entity {entity_uri}: {e}")
            continue