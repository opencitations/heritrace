# SPDX-FileCopyrightText: 2024-2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from __future__ import annotations

import logging
from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import unquote

from rdflib import RDF, Graph, Literal, URIRef
from SPARQLWrapper import JSON

from heritrace.extensions import (
    get_custom_filter,
    get_display_rules,
    get_form_fields,
    get_presentation,
    get_sparql,
    get_sparql_bindings,
    select_results,
)

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


def find_matching_rule(
    class_uri: str | None = None,
    shape_uri: str | None = None,
    rules: list[dict] | None = None,
) -> dict | None:
    """
    Find the most appropriate rule for a given class and/or shape.
    At least one of class_uri or shape_uri must be provided.

    Args:
        class_uri: Optional URI of the class
        shape_uri: Optional URI of the shape
        rules: Optional list of rules to search in, defaults to global display_rules

    Returns:
        The matching rule or None if no match is found
    """
    if not rules:
        rules = get_display_rules()
    if not rules:
        return None

    # Initialize variables to track potential matches
    class_match = None
    shape_match = None

    for rule in rules:
        # Case 1: Both class and shape match (exact match)
        if (
            class_uri
            and shape_uri
            and "class" in rule["target"]
            and rule["target"]["class"] == str(class_uri)
            and "shape" in rule["target"]
            and rule["target"]["shape"] == str(shape_uri)
        ):
            # Exact match always takes highest precedence
            return rule

        # Case 2: Only class matches
        if (
            class_uri
            and "class" in rule["target"]
            and rule["target"]["class"] == str(class_uri)
            and "shape" not in rule["target"]
        ):
            if class_match is None:
                class_match = rule

        # Case 3: Only shape matches
        elif (
            shape_uri
            and "shape" in rule["target"]
            and rule["target"]["shape"] == str(shape_uri)
            and "class" not in rule["target"]
        ) and shape_match is None:
            shape_match = rule

    # Shape rules are more specific than class rules
    if shape_match:
        return shape_match
    return class_match


def is_entity_type_visible(entity_key: tuple[str, str | None]) -> bool:
    """
    Determines if an entity type should be displayed.

    Args:
        entity_key: A tuple (class_uri, shape_uri)
    """
    class_uri = entity_key[0]
    shape_uri = entity_key[1]

    rule = find_matching_rule(class_uri, shape_uri)
    return rule.get("shouldBeDisplayed", True) if rule else True


def get_sortable_properties(entity_key: tuple[str, str | None]) -> list[dict[str, str]]:
    """
    Gets the sortable properties from display rules for an entity type and/or shape.
    Infers the sorting type from form_fields_cache.

    Args:
        entity_key: A tuple (class_uri, shape_uri)

    Returns:
        List of dictionaries with sorting information
    """
    display_rules = get_display_rules()
    if not display_rules:
        return []

    form_fields = get_form_fields()

    class_uri = entity_key[0]
    shape_uri = entity_key[1]

    rule = find_matching_rule(class_uri, shape_uri, display_rules)
    if not rule or "sortableBy" not in rule:
        return []

    sort_props = []
    for sort_config in rule["sortableBy"]:
        prop = sort_config.copy()
        prop["displayName"] = get_custom_filter().human_readable_predicate(
            prop["property"], entity_key
        )

        # Default to string sorting
        prop["sortType"] = "string"

        # Try to determine the sort type from form fields
        if form_fields and (
            entity_key in form_fields and prop["property"] in form_fields[entity_key]
        ):
            field_info = form_fields[entity_key][prop["property"]][
                0
            ]  # Take the first field definition
            prop["sortType"] = determine_sort_type(field_info)

        sort_props.append(prop)

    return sort_props


def determine_sort_type(field_info: dict) -> str:
    """Helper function to determine sort type from field info."""
    # If there's a shape, it's a reference to an entity (sort by label)
    if field_info.get("nodeShape"):
        return "string"
    # Otherwise look at the datatypes
    if field_info.get("datatypes"):
        datatype = str(field_info["datatypes"][0]).lower()
        if any(t in datatype for t in ["date", "time"]):
            return "date"
        if any(t in datatype for t in ["int", "float", "decimal", "double", "number"]):
            return "number"
        if "boolean" in datatype:
            return "boolean"
    # Default to string
    return "string"


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


def _connecting_property(
    entity_key: tuple[str | None, str | None], predicate: str, object_shape: str | None
) -> str | None:
    for field in get_form_fields().get(entity_key, {}).get(predicate, []):
        relation = field.get("intermediateRelation")
        if relation and field.get("nodeShape") == object_shape:
            return relation["connectingProperty"]
    return None


def _linked_entity(
    ctx: GroupingContext,
    value: str,
    predicate: str,
    object_shape: str | None,
) -> str:
    connecting_property = _connecting_property(
        (ctx.highest_priority_class, ctx.highest_priority_shape),
        predicate,
        object_shape,
    )
    if connecting_property is None:
        return value
    for _, linked_predicate, linked in ctx.value_triples[value]:
        if str(linked_predicate) == connecting_property:
            return str(linked)
    return value


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
    value_shape = ctx.value_shapes.get(object_uri)
    if isinstance(obj, URIRef) and custom_filter.has_label(value_shape):
        label = custom_filter.entity_label(
            object_uri, value_shape, ctx.historical_snapshot
        )
        if label is not None:
            ctx.fetched_values_map[label] = object_uri
            return {
                **data,
                "triple": (str(subject), str(predicate), label),
                "external_entity": _linked_entity(
                    ctx, object_uri, str(predicate), object_shape
                ),
            }
    return {**data, "triple": (str(subject), str(predicate), obj)}


def _new_group(
    ctx: GroupingContext,
    predicate: str,
    object_shape: str | None,
    prop_config: dict,
) -> dict:
    return {
        "property": predicate,
        "triples": [],
        "subjectClass": ctx.highest_priority_class,
        "subjectShape": ctx.highest_priority_shape,
        "objectShape": object_shape,
        "intermediateRelation": prop_config.get("intermediateRelation"),
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


def _group_shape_properties(ctx: GroupingContext, prop_configs: dict) -> None:
    by_predicate: OrderedDict[str, list[PropertyPresentation]] = OrderedDict()
    for prop in get_presentation().shape_properties(ctx.highest_priority_shape):
        by_predicate.setdefault(prop.path, []).append(prop)

    for predicate, presentations in by_predicate.items():
        ctx.relevant_properties.add(predicate)
        prop_config = prop_configs.get(predicate, {})
        group_names = {}
        for presentation in presentations:
            group_name = presentation.name or predicate
            group_names[presentation.identifier] = group_name
            if group_name not in ctx.grouped_triples:
                ctx.grouped_triples[group_name] = _new_group(
                    ctx, predicate, presentation.node, prop_config
                )
        for triple in ctx.triples:
            if str(triple[1]) != predicate:
                continue
            presentation = _property_shape_for_value(ctx, presentations, triple[2])
            group_name = group_names[presentation.identifier]
            ctx.grouped_triples[group_name]["triples"].append(
                _triple_data(ctx, triple, presentation.node)
            )
        if "orderedBy" in prop_config:
            for group_name in dict.fromkeys(group_names.values()):
                _apply_ordering_to_group(
                    ctx, prop_config, prop_config["orderedBy"], group_name
                )


def _apply_ordering_to_group(
    ctx: GroupingContext,
    current_prop_config: dict,
    order_property: str | None,
    display_name: str,
) -> None:
    ctx.grouped_triples[display_name]["is_draggable"] = True
    ctx.grouped_triples[display_name]["ordered_by"] = order_property
    process_ordering(
        ctx,
        current_prop_config,
        order_property,
        display_name,
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

    matching_rule = find_matching_rule(highest_priority_class, highest_priority_shape)
    display_properties = (
        matching_rule.get("displayProperties", []) if matching_rule else []
    )
    prop_configs = {
        prop["property"]: prop
        for prop in display_properties
        if not prop.get("isVirtual")
    }

    _group_shape_properties(ctx, prop_configs)

    for prop_config in display_properties:
        if prop_config.get("isVirtual"):
            process_virtual_property_display(
                prop_config["displayName"], prop_config, ctx
            )

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


def _fetch_virtual_property_entities(
    reference_field: str,
    target_class: str | None,
    ctx: GroupingContext,
) -> list[str]:
    decoded_subject = unquote(str(ctx.subject))

    query = f"""
        SELECT DISTINCT ?entity
        WHERE {{
            ?entity <{reference_field}> <{decoded_subject}> .
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


def process_virtual_property_display(
    display_name: str,
    prop_config: dict,
    ctx: GroupingContext,
) -> None:
    from heritrace.utils.shacl_utils import (  # noqa: PLC0415
        determine_shape_for_classes,
    )

    implementation = prop_config.get("implementedVia", {})
    field_overrides = implementation.get("fieldOverrides", {})
    target = implementation.get("target", {})
    target_class = target.get("class")
    target_shape = target.get("shape") or determine_shape_for_classes([target_class])

    reference_field = None
    for field_uri, override in field_overrides.items():
        if override.get("value") == "${currentEntity}":
            reference_field = field_uri
            break

    if not reference_field:
        return

    ctx.grouped_triples[display_name] = {
        "property": display_name,
        "triples": [],
        "subjectClass": ctx.highest_priority_class,
        "subjectShape": ctx.highest_priority_shape,
        "objectShape": None,
        "is_virtual": True,
    }

    custom_filter = get_custom_filter()
    for entity_uri in _fetch_virtual_property_entities(
        reference_field, target_class, ctx
    ):
        label = custom_filter.human_readable_entity(
            entity_uri, (target_class, target_shape), ctx.historical_snapshot
        )
        ctx.fetched_values_map[label] = entity_uri
        ctx.grouped_triples[display_name]["triples"].append(
            {
                "triple": (str(ctx.subject), display_name, label),
                "external_entity": entity_uri,
                "object": entity_uri,
                "subjectClass": ctx.highest_priority_class,
                "subjectShape": ctx.highest_priority_shape,
                "objectShape": target_shape,
                "is_virtual": True,
            }
        )


def process_ordering(
    ctx: GroupingContext,
    prop: dict,
    order_property: str | None,
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
            <{decoded_subject}> <{prop["property"]}> ?orderedEntity.
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


def get_predicate_ordering_info(
    predicate_uri: str,
    highest_priority_class: str | None,
    entity_shape: str | None = None,
) -> str | None:
    """
    Check if a predicate is ordered and return its ordering property.

    Args:
        predicate_uri: URI of the predicate to check
        highest_priority_class: The highest priority class for the subject entity
        entity_shape: Optional shape for the subject entity

    Returns:
        The ordering property URI if the predicate is ordered, None otherwise
    """
    display_rules = get_display_rules()
    if not display_rules:
        return None

    rule = find_matching_rule(highest_priority_class, entity_shape, display_rules)
    if not rule:
        return None

    for prop in rule.get("displayProperties", []):
        if not isinstance(prop, dict):
            continue
        if prop.get("isVirtual"):
            continue  # Virtual properties don't have RDF predicates or ordering
        if prop.get("property") == predicate_uri:
            return prop.get("orderedBy")

    return None


def get_similarity_properties(
    entity_key: tuple[str, str | None],
) -> list[str | dict[str, list[str]]] | None:
    """Gets the similarity properties configuration for a given entity key.

    This configuration specifies which properties should be used for similarity matching
    using a list-based structure supporting OR logic between elements and
    nested AND logic within elements.

    Example structures:
        - ['prop1', 'prop2']                      # prop1 OR prop2
        - [{'and': ['prop3', 'prop4']}]          # prop3 AND prop4
        - ['prop1', {'and': ['prop2', 'prop3']}] # prop1 OR (prop2 AND prop3)

    Args:
        entity_key: A tuple (class_uri, shape_uri)

    Returns:
        A list where each element is either a property URI string or a dictionary
        {'and': [list_of_property_uris]}, representing the boolean logic.
        Returns None if no configuration is found or if the structure is invalid.
    """
    class_uri = entity_key[0]
    shape_uri = entity_key[1]

    # Find the matching rule
    rule = find_matching_rule(class_uri, shape_uri)
    if not rule:
        return None

    similarity_props = rule.get("similarity_properties")

    if not similarity_props or not isinstance(similarity_props, list):
        return None

    # Validate each element in the list.
    validated_props = []
    for item in similarity_props:
        if isinstance(item, str):
            validated_props.append(item)
        elif isinstance(item, dict) and len(item) == 1 and "and" in item:
            and_list = item["and"]
            if (
                isinstance(and_list, list)
                and and_list
                and all(isinstance(p, str) for p in and_list)
            ):
                validated_props.append(item)
            else:
                logging.getLogger(__name__).warning(
                    "Invalid 'and' group in similarity_properties"
                    " for class %s. Expected"
                    " {'and': ['prop_uri', ...]} with"
                    " a non-empty list of strings.",
                    class_uri,
                )
                return None
        else:
            logging.getLogger(__name__).warning(
                "Invalid item format in similarity_properties"
                " list for class %s. Expected a property URI"
                " string or {'and': [...]} dict.",
                class_uri,
            )
            return None

    return (
        validated_props or None
    )  # Return validated list or None if empty after validation
