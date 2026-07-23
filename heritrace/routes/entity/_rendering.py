# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from flask_babel import gettext
from rdflib import RDF, Graph, Literal, URIRef
from rdflib.term import Node

from heritrace.routes.entity._types import (
    EntityIdentity,
    EntityRenderContext,
    HistoryContext,
)
from heritrace.utils.display_rules_utils import (
    get_highest_priority_class,
    get_predicate_ordering_info,
    get_property_order_from_rules,
    get_shape_order_from_display_rules,
)
from heritrace.utils.shacl_utils import (
    determine_shape_for_entity_triples,
    get_entity_position_in_sequence,
)
from heritrace.utils.sparql_utils import get_triples_from_graph
from heritrace.utils.uri_utils import is_valid_url


def determine_object_class_and_shape(
    object_value: str, relevant_snapshot: Graph | None
) -> tuple[str | None, str | None]:
    if not is_valid_url(str(object_value)) or not relevant_snapshot:
        return None, None

    object_triples = list(
        get_triples_from_graph(relevant_snapshot, (URIRef(object_value), None, None))
    )
    if not object_triples:
        return None, None

    object_shape_uri = determine_shape_for_entity_triples(object_triples)
    object_classes = [
        str(o)
        for _, _, o in get_triples_from_graph(
            relevant_snapshot, (URIRef(object_value), RDF.type, None)
        )
    ]
    object_class = (
        get_highest_priority_class(object_classes) if object_classes else None
    )

    return object_class, object_shape_uri


def _build_modification_caches(
    triples: list[tuple[Node, Node, Node]],
    relevant_snapshot: Graph | None,
) -> tuple[dict[str, str | None], dict[str, str | None]]:
    object_shapes_cache: dict[str, str | None] = {}
    object_classes_cache: dict[str, str | None] = {}

    if relevant_snapshot:
        for triple in triples:
            object_value = str(triple[2])
            object_class, object_shape = determine_object_class_and_shape(
                object_value, relevant_snapshot
            )
            object_classes_cache[object_value] = object_class
            object_shapes_cache[object_value] = object_shape

    return object_shapes_cache, object_classes_cache


def _build_predicate_shape_groups(
    triples: list[tuple[Node, Node, Node]],
    object_shapes_cache: dict[str, str | None],
    identity: EntityIdentity,
) -> tuple[dict, dict, dict]:
    predicate_shape_groups: dict[tuple[str, str | None], list] = {}
    predicate_ordering_cache: dict[str, str | None] = {}
    entity_position_cache: dict[tuple[str, str], int | None] = {}

    for triple in triples:
        predicate = str(triple[1])
        object_value = str(triple[2])
        object_shape_uri = object_shapes_cache.get(object_value)

        if predicate not in predicate_ordering_cache:
            predicate_ordering_cache[predicate] = get_predicate_ordering_info(
                predicate, identity.highest_priority_class, identity.entity_shape
            )

        order_property = predicate_ordering_cache[predicate]
        if order_property and is_valid_url(object_value) and identity.relevant_snapshot:
            position_key = (object_value, predicate)
            if position_key not in entity_position_cache:
                entity_position_cache[position_key] = get_entity_position_in_sequence(
                    object_value,
                    identity.entity_uri,
                    predicate,
                    order_property,
                    identity.relevant_snapshot,
                )

        group_key = (predicate, object_shape_uri)
        if group_key not in predicate_shape_groups:
            predicate_shape_groups[group_key] = []
        predicate_shape_groups[group_key].append(triple)

    return predicate_shape_groups, predicate_ordering_cache, entity_position_cache


def _get_cached_position(
    triple: tuple[URIRef, URIRef, URIRef | Literal],
    predicate_uri: str,
    cache: dict,
) -> int | float:
    object_value = str(triple[2])
    position_key = (object_value, predicate_uri)
    if position_key in cache:
        return cache[position_key]
    return float("inf")


def _sort_and_format_group(
    group_triples: list[tuple[URIRef, URIRef, URIRef | Literal]],
    predicate_uri: str,
    ctx: EntityRenderContext,
) -> str:
    order_property = ctx.predicate_ordering_cache.get(predicate_uri)
    sorted_triples = (
        sorted(
            group_triples,
            key=lambda t: _get_cached_position(
                t, predicate_uri, ctx.entity_position_cache
            ),
        )
        if order_property and ctx.relevant_snapshot
        else group_triples
    )

    text = ""
    for triple in sorted_triples:
        text += format_triple_modification(triple, ctx)
    return text


def _render_ordered_groups(
    predicate_shape_groups: dict,
    ordered_properties: list,
    ctx: EntityRenderContext,
) -> tuple[str, set]:
    text = ""
    processed_predicates: set[tuple[str, str | None]] = set()

    for predicate in ordered_properties:
        shape_order = get_shape_order_from_display_rules(
            ctx.highest_priority_class, ctx.entity_shape, predicate
        )
        predicate_groups = []
        for group_key, group_triples in predicate_shape_groups.items():
            predicate_uri, object_shape_uri = group_key
            if predicate_uri == predicate:
                if object_shape_uri and object_shape_uri in shape_order:
                    shape_priority = shape_order.index(object_shape_uri)
                else:
                    shape_priority = len(shape_order)

                predicate_groups.append((shape_priority, group_key, group_triples))

        predicate_groups.sort(key=lambda x: x[0])
        for _, group_key, group_triples in predicate_groups:
            processed_predicates.add(group_key)
            predicate_uri, _ = group_key
            text += _sort_and_format_group(group_triples, predicate_uri, ctx)

    return text, processed_predicates


def _render_remaining_groups(
    predicate_shape_groups: dict,
    processed_predicates: set,
    ctx: EntityRenderContext,
) -> str:
    text = ""
    for group_key, group_triples in predicate_shape_groups.items():
        if group_key not in processed_predicates:
            predicate_uri, _ = group_key
            text += _sort_and_format_group(group_triples, predicate_uri, ctx)
    return text


def generate_modification_text(
    modifications: dict[str, list[tuple[Node, Node, Node]]],
    ctx: HistoryContext,
    current_snapshot: Graph,
    current_snapshot_timestamp: str,
) -> str:
    modification_text = "<p><strong>" + gettext("Modifications") + "</strong></p>"

    ordered_properties = get_property_order_from_rules(
        ctx.highest_priority_class, ctx.entity_shape
    )

    for mod_type, triples in modifications.items():
        modification_text += "<ul class='list-group mb-3'><p>"
        if mod_type == gettext("Additions"):
            modification_text += '<i class="bi bi-plus-circle-fill text-success"></i>'
        elif mod_type == gettext("Deletions"):
            modification_text += '<i class="bi bi-dash-circle-fill text-danger"></i>'
        modification_text += " <em>" + gettext(mod_type) + "</em></p>"

        relevant_snapshot = None
        if (
            mod_type == gettext("Deletions")
            and ctx.history
            and ctx.entity_uri
            and current_snapshot_timestamp
        ):
            current_index = ctx.sorted_timestamps.index(current_snapshot_timestamp)
            if current_index > 0:
                relevant_snapshot = ctx.history[ctx.entity_uri][
                    ctx.sorted_timestamps[current_index - 1]
                ]
        else:
            relevant_snapshot = current_snapshot

        object_shapes_cache, object_classes_cache = _build_modification_caches(
            triples, relevant_snapshot
        )

        identity = EntityIdentity(
            entity_uri=ctx.entity_uri,
            highest_priority_class=ctx.highest_priority_class,
            entity_shape=ctx.entity_shape,
            relevant_snapshot=relevant_snapshot,
        )

        predicate_shape_groups, predicate_ordering_cache, entity_position_cache = (
            _build_predicate_shape_groups(
                triples,
                object_shapes_cache,
                identity,
            )
        )

        render_ctx = EntityRenderContext(
            entity_uri=ctx.entity_uri,
            entity_shape=ctx.entity_shape,
            highest_priority_class=ctx.highest_priority_class,
            relevant_snapshot=relevant_snapshot,
            predicate_ordering_cache=predicate_ordering_cache,
            entity_position_cache=entity_position_cache,
            object_shapes_cache=object_shapes_cache,
            object_classes_cache=object_classes_cache,
            custom_filter=ctx.custom_filter,
        )

        ordered_text, processed_predicates = _render_ordered_groups(
            predicate_shape_groups, ordered_properties, render_ctx
        )
        modification_text += ordered_text

        modification_text += _render_remaining_groups(
            predicate_shape_groups, processed_predicates, render_ctx
        )

        modification_text += "</ul>"

    return modification_text


def format_triple_modification(
    triple: tuple[URIRef, URIRef, URIRef | Literal],
    ctx: EntityRenderContext,
) -> str:
    predicate = triple[1]
    object_value = triple[2]

    object_shape_uri = ctx.object_shapes_cache.get(str(object_value))

    predicate_label = ctx.custom_filter.human_readable_predicate(
        predicate,
        (ctx.highest_priority_class, ctx.entity_shape),
        object_shape_uri=object_shape_uri,
    )

    object_class = ctx.object_classes_cache.get(str(object_value))
    object_label = get_object_label(
        object_value,
        predicate,
        object_shape_uri,
        object_class,
        ctx,
    )

    order_info = ""
    if is_valid_url(str(object_value)):
        order_property = ctx.predicate_ordering_cache.get(str(predicate))
        if order_property:
            position_key = (str(object_value), str(predicate))
            position = ctx.entity_position_cache.get(position_key)
            if position is not None:
                order_info = f' <span class="order-position-badge">#{position}</span>'

    return f"""
        <li class='d-flex align-items-center'>
            <span class='flex-grow-1 d-flex flex-column
            justify-content-center ms-3 mb-2 w-100'>
                <strong>{predicate_label}{order_info}</strong>
                <span class="object-value word-wrap">{object_label}</span>
            </span>
        </li>"""


def get_object_label(
    object_value: str,
    predicate: str,
    object_shape_uri: str | None,
    object_class: str | None,
    ctx: EntityRenderContext,
) -> str:
    predicate = str(predicate)

    if predicate == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type":
        return ctx.custom_filter.human_readable_class((str(object_value), None))

    if is_valid_url(object_value):
        if object_shape_uri or object_class:
            return ctx.custom_filter.human_readable_entity(
                object_value, (object_class, object_shape_uri), ctx.relevant_snapshot
            )
        return str(object_value)

    return str(object_value)
