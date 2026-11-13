# SPDX-FileCopyrightText: 2024-2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast
from urllib.parse import unquote

from rdflib import RDF, Graph, Literal, URIRef
from SPARQLWrapper import JSON

from heritrace.extensions import (
    get_custom_filter,
    get_form_fields,
    get_presentation,
    get_sparql,
    get_sparql_bindings,
)
from heritrace.language import localize
from heritrace.sparql import select_results
from heritrace.utils.shacl_presentation import inverse_predicate
from heritrace.utils.shacl_utils import index_order

if TYPE_CHECKING:
    from rdflib.query import ResultRow
    from rdflib.term import Node

    from heritrace.utils.shacl_presentation import PropertyPresentation


@dataclass(slots=True)
class GroupingContext:
    subject: URIRef
    triples: list[tuple[URIRef, URIRef, URIRef | Literal]]
    grouped_triples: OrderedDict
    fetched_values_map: dict[str, str]
    relevant_properties: set
    historical_snapshot: Graph | None
    highest_priority_class: str | None
    highest_priority_shape: str | None
    value_shapes: dict[str, str | None]
    value_triples: dict[str, list[tuple[Node, Node, Node]]]


def get_highest_priority_class(subject_classes: list[str]) -> str | None:
    """Return the class whose shape fixes the most values of rdf:type."""
    from heritrace.utils.shacl_utils import determine_shape_for_classes  # noqa: PLC0415

    presentation = get_presentation()
    return max(
        (str(class_uri) for class_uri in subject_classes),
        key=lambda class_uri: presentation.fixed_type_count(
            determine_shape_for_classes([class_uri])
        ),
        default=None,
    )


def _value_shapes(
    triples: list[tuple[URIRef, URIRef, URIRef | Literal]],
    historical_snapshot: Graph | None,
) -> tuple[dict[str, str | None], dict[str, list[tuple[Node, Node, Node]]]]:
    from heritrace.utils.shacl_utils import (  # noqa: PLC0415
        determine_shape_for_entity_triples,
    )
    from heritrace.utils.sparql_utils import get_triples_from_graph  # noqa: PLC0415

    values = sorted(
        {
            str(obj)
            for _, predicate, obj in triples
            if isinstance(obj, URIRef) and predicate != RDF.type
        }
    )
    value_triples: dict[str, list[tuple[Node, Node, Node]]] = {
        value: [] for value in values
    }
    if historical_snapshot is not None:
        for value in values:
            value_triples[value] = list(
                get_triples_from_graph(historical_snapshot, (URIRef(value), None, None))
            )
    elif values:
        sparql = get_sparql()
        sparql.setQuery(
            "SELECT ?s ?p ?o WHERE { VALUES ?s { "
            + " ".join(URIRef(value).n3() for value in values)
            + " } ?s ?p ?o }"
        )
        sparql.setReturnFormat(JSON)
        for binding in get_sparql_bindings(sparql.query().convert()):
            obj = binding["o"]
            value_triples[binding["s"]["value"]].append(
                (
                    URIRef(binding["s"]["value"]),
                    URIRef(binding["p"]["value"]),
                    URIRef(obj["value"])
                    if obj["type"] == "uri"
                    else Literal(obj["value"]),
                )
            )
    shapes = {
        value: determine_shape_for_entity_triples(entity_triples)
        for value, entity_triples in value_triples.items()
    }
    return shapes, value_triples


def _details_viewer_field(
    entity_key: tuple[str | None, str | None], predicate: str, object_shape: str | None
) -> dict | None:
    for field in get_form_fields().get(entity_key, {}).get(predicate, []):
        if field["detailsViewer"] and field.get("nodeShape") == object_shape:
            return field
    return None


def _detail_value(
    ctx: GroupingContext, nested: dict, value: URIRef | Literal
) -> dict[str, str | None]:
    custom_filter = get_custom_filter()
    if isinstance(value, Literal):
        return {"label": str(value), "uri": None}
    if nested["uri"] == str(RDF.type):
        return {
            "label": custom_filter.human_readable_class((str(value), None)),
            "uri": None,
        }
    shape = nested["nodeShape"] if nested["nodeShapes"] else None
    label = custom_filter.value_label(value, (None, shape), ctx.historical_snapshot)
    return {"label": label, "uri": str(value) if shape else None}


def _details(ctx: GroupingContext, value: str, field: dict) -> list[dict[str, object]]:
    details = []
    for nested in field["nestedShape"]:
        if nested["hidden"] or (
            "detailPaths" in field and nested["uri"] not in field["detailPaths"]
        ):
            continue
        values = [
            _detail_value(ctx, nested, cast("URIRef | Literal", linked))
            for _, linked_predicate, linked in ctx.value_triples[value]
            if str(linked_predicate) == nested["uri"]
        ]
        if values:
            details.append({"name": localize(nested["displayName"]), "values": values})
    return details


def _triple_data(
    ctx: GroupingContext,
    triple: tuple[URIRef, URIRef, URIRef | Literal],
    object_shape: str | None,
) -> dict:
    subject, predicate, obj = triple
    object_uri = str(obj)
    data = {
        "object": object_uri,
        "subjectClass": ctx.highest_priority_class,
        "subjectShape": ctx.highest_priority_shape,
        "objectShape": object_shape,
    }
    custom_filter = get_custom_filter()
    if predicate == RDF.type:
        from heritrace.utils.shacl_utils import (  # noqa: PLC0415
            determine_shape_for_classes,
        )

        label = custom_filter.human_readable_class(
            (object_uri, determine_shape_for_classes([object_uri]))
        )
        return {**data, "triple": (str(subject), str(predicate), label)}
    if isinstance(obj, Literal):
        return {**data, "triple": (str(subject), str(predicate), obj)}
    value_shape = ctx.value_shapes.get(object_uri)
    label = custom_filter.value_label(obj, (None, value_shape), ctx.historical_snapshot)
    if value_shape is None:
        return {**data, "triple": (str(subject), str(predicate), obj), "label": label}
    ctx.fetched_values_map[label] = object_uri
    viewer_field = _details_viewer_field(
        (ctx.highest_priority_class, ctx.highest_priority_shape),
        str(predicate),
        object_shape,
    )
    return {
        **data,
        "triple": (str(subject), str(predicate), label),
        "external_entity": object_uri,
        **(
            {"details": _details(ctx, object_uri, viewer_field)}
            if viewer_field is not None
            else {}
        ),
    }


def _new_group(
    ctx: GroupingContext,
    predicate: str,
    object_shape: str | None,
) -> dict:
    return {
        "property": predicate,
        "triples": [],
        "subjectClass": ctx.highest_priority_class,
        "subjectShape": ctx.highest_priority_shape,
        "objectShape": object_shape,
    }


def _property_shape_for_value(
    ctx: GroupingContext,
    presentations: list[PropertyPresentation],
    obj: URIRef | Literal,
) -> PropertyPresentation:
    value_shape = ctx.value_shapes.get(str(obj))
    for presentation in presentations:
        if presentation.node == value_shape:
            return presentation
    return presentations[0]


def _group_shape_properties(ctx: GroupingContext) -> None:
    by_predicate: OrderedDict[str, list[PropertyPresentation]] = OrderedDict()
    for prop in get_presentation().shape_properties(ctx.highest_priority_shape):
        by_predicate.setdefault(prop.path, []).append(prop)

    for predicate, presentations in by_predicate.items():
        ctx.relevant_properties.add(predicate)
        group_names = {}
        for presentation in presentations:
            group_name = localize(presentation.names) or predicate
            group_names[presentation.identifier] = group_name
            if group_name not in ctx.grouped_triples:
                ctx.grouped_triples[group_name] = _new_group(
                    ctx, predicate, presentation.node
                )
        inverse_of = inverse_predicate(predicate)
        if inverse_of is not None:
            first = presentations[0]
            _add_inverse_values(ctx, inverse_of, group_names[first.identifier], first)
            continue
        for triple in ctx.triples:
            if str(triple[1]) != predicate:
                continue
            presentation = _property_shape_for_value(ctx, presentations, triple[2])
            group_name = group_names[presentation.identifier]
            ctx.grouped_triples[group_name]["triples"].append(
                _triple_data(ctx, triple, presentation.node)
            )
        for presentation in presentations:
            if presentation.ordered_by is not None:
                _apply_ordering_to_group(
                    ctx, predicate, presentation, group_names[presentation.identifier]
                )


def _apply_ordering_to_group(
    ctx: GroupingContext,
    predicate: str,
    presentation: PropertyPresentation,
    display_name: str,
) -> None:
    order_property = cast("str", presentation.ordered_by)
    ctx.grouped_triples[display_name]["is_draggable"] = True
    ctx.grouped_triples[display_name]["ordered_by"] = order_property
    if presentation.indexed:
        process_index_ordering(ctx, predicate, order_property, display_name)
    else:
        process_ordering(ctx, predicate, order_property, display_name)


def process_index_ordering(
    ctx: GroupingContext,
    predicate: str,
    index_property: str,
    display_name: str,
) -> None:
    values = index_order(
        unquote(ctx.subject), predicate, index_property, ctx.historical_snapshot
    )
    positions = {value: position for position, value in enumerate(values)}
    ctx.grouped_triples[display_name]["triples"].sort(
        key=lambda x: (
            positions.get(
                ctx.fetched_values_map.get(str(x["triple"][2]), str(x["triple"][2])),
                len(positions),
            ),
            str(x["triple"][2]),
        )
    )


def get_grouped_triples(
    subject: URIRef,
    triples: list[tuple[URIRef, URIRef, URIRef | Literal]],
    valid_predicates_info: list[str],
    historical_snapshot: Graph | None = None,
    entity_key: tuple[str | None, str | None] = (None, None),
) -> tuple[OrderedDict, set]:
    highest_priority_class, highest_priority_shape = entity_key
    value_shapes, value_triples = _value_shapes(triples, historical_snapshot)

    ctx = GroupingContext(
        subject=subject,
        triples=triples,
        grouped_triples=OrderedDict(),
        fetched_values_map={},
        relevant_properties=set(),
        historical_snapshot=historical_snapshot,
        highest_priority_class=highest_priority_class,
        highest_priority_shape=highest_priority_shape,
        value_shapes=value_shapes,
        value_triples=value_triples,
    )

    _group_shape_properties(ctx)

    for prop_uri in valid_predicates_info:
        if prop_uri not in ctx.relevant_properties:
            ctx.relevant_properties.add(prop_uri)
            process_default_property(
                prop_uri,
                ctx.triples,
                ctx.grouped_triples,
                ctx.highest_priority_shape,
                ctx.highest_priority_class,
            )

    return ctx.grouped_triples, ctx.relevant_properties


def _fetch_inverse_values(
    predicate: str,
    target_class: str | None,
    ctx: GroupingContext,
) -> list[str]:
    decoded_subject = unquote(str(ctx.subject))

    query = f"""
        SELECT DISTINCT ?entity
        WHERE {{
            ?entity <{predicate}> <{decoded_subject}> .
    """

    if target_class:
        query += f"""
            ?entity a <{target_class}> .
        """

    query += """
        }
    """

    if ctx.historical_snapshot:
        return [
            str(row[0]) for row in select_results(ctx.historical_snapshot.query(query))
        ]

    sparql = get_sparql()
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    bindings = get_sparql_bindings(sparql.query().convert())
    return [res["entity"]["value"] for res in bindings]


def _add_inverse_values(
    ctx: GroupingContext,
    predicate: str,
    group_name: str,
    presentation: PropertyPresentation,
) -> None:
    from heritrace.extensions import get_shacl_graph  # noqa: PLC0415
    from heritrace.utils.shacl_display import get_shape_target_class  # noqa: PLC0415

    target_shape = presentation.node
    target_class = (
        get_shape_target_class(get_shacl_graph(), target_shape)
        if target_shape
        else None
    )
    custom_filter = get_custom_filter()
    for entity_uri in _fetch_inverse_values(predicate, target_class, ctx):
        label = custom_filter.value_label(
            entity_uri, (target_class, target_shape), ctx.historical_snapshot
        )
        ctx.fetched_values_map[label] = entity_uri
        ctx.grouped_triples[group_name]["triples"].append(
            {
                "triple": (str(ctx.subject), presentation.path, label),
                "external_entity": entity_uri,
                "object": entity_uri,
                "subjectClass": ctx.highest_priority_class,
                "subjectShape": ctx.highest_priority_shape,
                "objectShape": target_shape,
            }
        )


def process_ordering(
    ctx: GroupingContext,
    predicate: str,
    order_property: str,
    display_name: str,
) -> None:
    def get_ordered_sequence(
        order_results: list[dict[str, dict[str, str]]] | list[ResultRow],
    ) -> list[list[str]]:
        order_map = {}
        for res in order_results:
            if isinstance(res, dict):  # For live triplestore results
                ordered_entity = res["orderedEntity"]["value"]
                next_value = res["nextValue"]["value"]
            else:  # For historical snapshot results
                ordered_entity = str(res[0])
                next_value = str(res[1])

            order_map[str(ordered_entity)] = (
                None if str(next_value) == "NONE" else str(next_value)
            )

        all_sequences = []
        start_elements = set(order_map.keys()) - set(order_map.values())
        while start_elements:
            sequence = []
            current_element = start_elements.pop()
            while current_element in order_map:
                sequence.append(current_element)
                current_element = order_map[current_element]
            all_sequences.append(sequence)
        return all_sequences

    decoded_subject = unquote(ctx.subject)

    sparql = get_sparql()

    order_query = f"""
        SELECT ?orderedEntity (COALESCE(?next, "NONE") AS ?nextValue)
        WHERE {{
            <{decoded_subject}> <{predicate}> ?orderedEntity.
            OPTIONAL {{
                ?orderedEntity <{order_property}> ?next.
            }}
        }}
    """
    if ctx.historical_snapshot:
        order_results: list[dict[str, dict[str, str]]] | list[ResultRow] = list(
            select_results(ctx.historical_snapshot.query(order_query))
        )
    else:
        sparql.setQuery(order_query)
        sparql.setReturnFormat(JSON)
        order_results = get_sparql_bindings(sparql.query().convert())

    order_sequences = get_ordered_sequence(order_results)
    for sequence in order_sequences:
        ctx.grouped_triples[display_name]["triples"].sort(
            key=lambda x: (
                sequence.index(
                    ctx.fetched_values_map.get(str(x["triple"][2]), str(x["triple"][2]))
                )
                if ctx.fetched_values_map.get(str(x["triple"][2]), str(x["triple"][2]))
                in sequence
                else float("inf")
            )
        )


def process_default_property(
    prop_uri: str,
    triples: list[tuple[URIRef, URIRef, URIRef | Literal]],
    grouped_triples: OrderedDict,
    subject_shape: str | None = None,
    subject_class: str | None = None,
) -> None:
    display_name = prop_uri
    grouped_triples[display_name] = {
        "property": prop_uri,
        "triples": [],
        "subjectClass": subject_class,
        "subjectShape": subject_shape,
        "objectShape": None,
    }
    triples_for_prop = [triple for triple in triples if str(triple[1]) == prop_uri]
    for triple in triples_for_prop:
        new_triple_data = {
            "triple": (str(triple[0]), str(triple[1]), str(triple[2])),
            "object": str(triple[2]),
            "subjectClass": subject_class,
            "subjectShape": subject_shape,
            "objectShape": None,
        }
        grouped_triples[display_name]["triples"].append(new_triple_data)
