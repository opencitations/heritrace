# SPDX-FileCopyrightText: 2024-2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from __future__ import annotations

import logging
from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import unquote

from rdflib import Graph, Literal, URIRef
from rdflib.plugins.sparql.algebra import translateQuery
from rdflib.plugins.sparql.parser import parseQuery
from SPARQLWrapper import JSON

from heritrace.extensions import (
    get_custom_filter,
    get_display_rules,
    get_form_fields,
    get_sparql,
    get_sparql_bindings,
    select_results,
)

if TYPE_CHECKING:
    from rdflib.query import ResultRow


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


_SUBJECT_LABEL_PAIR_LENGTH = 2


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
    highest_priority = float("inf")

    # Scan all rules to find the best match based on priority
    for rule in rules:
        rule_priority = rule.get("priority", 0)

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
            if class_match is None or rule_priority < highest_priority:
                class_match = rule
                highest_priority = rule_priority

        # Case 3: Only shape matches
        elif (
            shape_uri
            and "shape" in rule["target"]
            and rule["target"]["shape"] == str(shape_uri)
            and "class" not in rule["target"]
        ) and (shape_match is None or rule_priority < highest_priority):
            shape_match = rule
            highest_priority = rule_priority

    # Return the best match based on priority
    # Shape rules typically have higher specificity,
    # so prefer them if they have equal priority
    if shape_match and (
        class_match is None
        or shape_match.get("priority", 0) <= class_match.get("priority", 0)
    ):
        return shape_match
    if class_match:
        return class_match

    return None


def get_class_priority(entity_key: tuple[str, str | None]) -> float:
    """
    Returns the priority of a specific entity key (class_uri, shape_uri).
    Calculates the priority directly from the display rules.
    Classes without defined rules receive the lowest priority (highest number).

    Args:
        entity_key: A tuple (class_uri, shape_uri)
    """
    class_uri = entity_key[0]
    shape_uri = entity_key[1]

    rule = find_matching_rule(class_uri, shape_uri)
    return rule.get("priority", 0) if rule else float("inf")


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

        for display_prop in rule["displayProperties"]:
            if display_prop["property"] == prop["property"]:
                if "displayRules" in display_prop:
                    prop["displayName"] = display_prop["displayRules"][0]["displayName"]
                else:
                    prop["displayName"] = display_prop.get(
                        "displayName", prop["property"]
                    )
                break

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
    """
    Find the highest priority class from the given list of classes.

    Args:
        subject_classes: List of class URIs

    Returns:
        The highest priority class or None if no classes are provided
    """
    from heritrace.utils.shacl_utils import determine_shape_for_classes  # noqa: PLC0415

    if not subject_classes:
        return None

    highest_priority = float("inf")
    highest_priority_class = None

    for raw_class_uri in subject_classes:
        class_uri = str(raw_class_uri)
        shape = determine_shape_for_classes([class_uri])
        entity_key = (class_uri, shape)
        priority = get_class_priority(entity_key)
        if priority < highest_priority:
            highest_priority = priority
            highest_priority_class = class_uri

    if highest_priority_class is None and subject_classes:
        highest_priority_class = str(subject_classes[0])

    return highest_priority_class


def _ensure_grouped_entry(
    ctx: GroupingContext,
    display_name: str,
    prop_uri: str,
    object_shape: str | None,
) -> None:
    if display_name not in ctx.grouped_triples:
        ctx.grouped_triples[display_name] = {
            "property": prop_uri,
            "triples": [],
            "subjectClass": ctx.highest_priority_class,
            "subjectShape": ctx.highest_priority_shape,
            "objectShape": object_shape,
        }


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


def _apply_intermediate_relation(
    grouped_triples: OrderedDict,
    display_name: str,
    *sources: dict,
) -> None:
    for source in sources:
        if "intermediateRelation" in source:
            grouped_triples[display_name]["intermediateRelation"] = source[
                "intermediateRelation"
            ]
            return


def _process_property_with_nested_display_rules(
    prop_uri: str,
    current_prop_config: dict,
    ctx: GroupingContext,
) -> None:
    is_ordered = "orderedBy" in current_prop_config
    order_property = current_prop_config.get("orderedBy")

    for display_rule_nested in current_prop_config["displayRules"]:
        display_name_nested = display_rule_nested.get("displayName", prop_uri)
        ctx.relevant_properties.add(prop_uri)
        object_shape = display_rule_nested.get("shape")
        if current_prop_config.get("isVirtual"):
            process_virtual_property_display(
                display_name_nested,
                current_prop_config,
                ctx,
            )
        else:
            process_display_rule(
                display_name_nested,
                prop_uri,
                display_rule_nested,
                ctx,
                object_shape=object_shape,
            )
        if is_ordered and not current_prop_config.get("isVirtual", False):
            _apply_ordering_to_group(
                ctx,
                current_prop_config,
                order_property,
                display_name_nested,
            )

        _ensure_grouped_entry(
            ctx,
            display_name_nested,
            prop_uri,
            display_rule_nested.get("shape"),
        )

        _apply_intermediate_relation(
            ctx.grouped_triples,
            display_name_nested,
            display_rule_nested,
            current_prop_config,
        )


def _process_property_with_simple_config(
    prop_uri: str,
    current_prop_config: dict,
    current_form_field: list[dict] | None,
    ctx: GroupingContext,
) -> None:
    display_name_simple = current_prop_config.get("displayName", prop_uri)
    # Only add non-virtual properties to relevant_properties
    # Virtual properties are handled separately in entity.py
    if not current_prop_config.get("isVirtual"):
        ctx.relevant_properties.add(prop_uri)

    object_shape = None
    if current_form_field:
        for form_field in current_form_field:
            object_shape = form_field.get("nodeShape")
            break

    if current_prop_config.get("isVirtual"):
        process_virtual_property_display(
            display_name_simple,
            current_prop_config,
            ctx,
        )
    else:
        process_display_rule(
            display_name_simple,
            prop_uri,
            current_prop_config,
            ctx,
            object_shape=object_shape,
        )
    if "orderedBy" in current_prop_config and not current_prop_config.get(
        "isVirtual", False
    ):
        _ensure_grouped_entry(
            ctx,
            display_name_simple,
            prop_uri,
            current_prop_config.get("shape"),
        )
        _apply_ordering_to_group(
            ctx,
            current_prop_config,
            current_prop_config.get("orderedBy"),
            display_name_simple,
        )
    if "intermediateRelation" in current_prop_config:
        _ensure_grouped_entry(
            ctx,
            display_name_simple,
            prop_uri,
            current_prop_config.get("shape"),
        )
        ctx.grouped_triples[display_name_simple]["intermediateRelation"] = (
            current_prop_config["intermediateRelation"]
        )


def _process_property_with_display_rules(
    prop_uri: str,
    matching_rule: dict,
    matching_form_field: dict | None,
    ctx: GroupingContext,
) -> None:
    current_prop_config = None
    for prop_config in matching_rule.get("displayProperties", []):
        config_identifier = (
            prop_config.get("displayName")
            if prop_config.get("isVirtual")
            else prop_config.get("property")
        )
        if config_identifier == prop_uri:
            current_prop_config = prop_config
            break

    current_form_field = (
        matching_form_field.get(prop_uri) if matching_form_field else None
    )

    if current_prop_config:
        if "displayRules" in current_prop_config:
            _process_property_with_nested_display_rules(
                prop_uri,
                current_prop_config,
                ctx,
            )
        else:
            _process_property_with_simple_config(
                prop_uri,
                current_prop_config,
                current_form_field,
                ctx,
            )
    else:
        # Property without specific configuration - add to relevant_properties
        # Don't process properties without config
        # (they are not virtual in this case)
        ctx.relevant_properties.add(prop_uri)
        process_default_property(
            prop_uri,
            ctx.triples,
            ctx.grouped_triples,
            ctx.highest_priority_shape,
            ctx.highest_priority_class,
        )


def get_grouped_triples(  # noqa: PLR0913
    subject: URIRef,
    triples: list[tuple[URIRef, URIRef, URIRef | Literal]],
    valid_predicates_info: list[str],
    historical_snapshot: Graph | None = None,
    highest_priority_class: str | None = None,
    highest_priority_shape: str | None = None,
) -> tuple[OrderedDict, set]:
    display_rules = get_display_rules()
    form_fields = get_form_fields()

    grouped_triples = OrderedDict()
    relevant_properties: set = set()
    fetched_values_map: dict[str, str] = {}

    ctx = GroupingContext(
        subject=subject,
        triples=triples,
        grouped_triples=grouped_triples,
        fetched_values_map=fetched_values_map,
        relevant_properties=relevant_properties,
        historical_snapshot=historical_snapshot,
        highest_priority_class=highest_priority_class,
        highest_priority_shape=highest_priority_shape,
    )

    matching_rule = find_matching_rule(
        highest_priority_class, highest_priority_shape, display_rules
    )
    matching_form_field = form_fields.get(
        (highest_priority_class, highest_priority_shape)
    )

    ordered_properties = []
    if display_rules and matching_rule:
        for prop_config in matching_rule.get("displayProperties", []):
            if prop_config.get("isVirtual"):
                prop_uri = prop_config.get("displayName")
            else:
                prop_uri = prop_config.get("property")
            if prop_uri and prop_uri not in ordered_properties:
                ordered_properties.append(prop_uri)

    for prop_uri in valid_predicates_info:
        if prop_uri not in ordered_properties:
            ordered_properties.append(prop_uri)

    for prop_uri in ordered_properties:
        if display_rules and matching_rule:
            _process_property_with_display_rules(
                prop_uri,
                matching_rule,
                matching_form_field,
                ctx,
            )
        else:
            # No display rules or no matching rule -
            # add all properties to relevant_properties
            ctx.relevant_properties.add(prop_uri)
            process_default_property(
                prop_uri,
                ctx.triples,
                ctx.grouped_triples,
                ctx.highest_priority_shape,
                ctx.highest_priority_class,
            )

    ctx.grouped_triples = OrderedDict(ctx.grouped_triples)
    return ctx.grouped_triples, ctx.relevant_properties


def process_display_rule(
    display_name: str,
    prop_uri: str,
    rule: dict,
    ctx: GroupingContext,
    object_shape: str | None = None,
) -> None:
    if display_name not in ctx.grouped_triples:
        ctx.grouped_triples[display_name] = {
            "property": prop_uri,
            "triples": [],
            "subjectClass": ctx.highest_priority_class,
            "subjectShape": ctx.highest_priority_shape,
            "objectShape": object_shape,
            "intermediateRelation": rule.get("intermediateRelation"),
        }
    for triple in ctx.triples:
        if str(triple[1]) == prop_uri:
            if rule.get("fetchValueFromQuery"):
                if ctx.historical_snapshot:
                    result, external_entity = execute_historical_query(
                        rule["fetchValueFromQuery"],
                        ctx.subject,
                        triple[2],
                        ctx.historical_snapshot,
                    )
                else:
                    result, external_entity = execute_sparql_query(
                        rule["fetchValueFromQuery"], ctx.subject, triple[2]
                    )
                if result:
                    ctx.fetched_values_map[str(result)] = str(triple[2])
                    new_triple = (str(triple[0]), str(triple[1]), str(result))
                    object_uri = str(triple[2])
                    new_triple_data = {
                        "triple": new_triple,
                        "external_entity": external_entity,
                        "object": object_uri,
                        "subjectClass": ctx.highest_priority_class,
                        "subjectShape": ctx.highest_priority_shape,
                        "objectShape": object_shape,
                    }
                    ctx.grouped_triples[display_name]["triples"].append(new_triple_data)
            else:
                if str(triple[1]) == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type":
                    from heritrace.utils.shacl_utils import (  # noqa: PLC0415
                        determine_shape_for_classes,
                    )

                    object_class_shape = determine_shape_for_classes([triple[2]])
                    result = get_custom_filter().human_readable_class(
                        (triple[2], object_class_shape)
                    )
                else:
                    result = triple[2]

                object_uri = str(triple[2])

                new_triple_data = {
                    "triple": (str(triple[0]), str(triple[1]), result),
                    "object": object_uri,
                    "subjectClass": ctx.highest_priority_class,
                    "subjectShape": ctx.highest_priority_shape,
                    "objectShape": object_shape,
                }
                ctx.grouped_triples[display_name]["triples"].append(new_triple_data)


def process_virtual_property_display(  # noqa: C901, PLR0912
    display_name: str,
    prop_config: dict,
    ctx: GroupingContext,
) -> None:
    implementation = prop_config.get("implementedVia", {})
    field_overrides = implementation.get("fieldOverrides", {})
    target = implementation.get("target", {})
    target_class = target.get("class")

    # Find which field should reference the current entity
    reference_field = None
    for field_uri, override in field_overrides.items():
        if override.get("value") == "${currentEntity}":
            reference_field = field_uri
            break

    if not reference_field:
        return

    decoded_subject = unquote(str(ctx.subject))

    # Query for entities that reference the current entity via the reference field
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
        # Execute query on historical snapshot
        entity_uris = [
            str(row[0]) for row in select_results(ctx.historical_snapshot.query(query))
        ]
    else:
        # Execute query on live triplestore
        sparql = get_sparql()
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        bindings = get_sparql_bindings(sparql.query().convert())
        entity_uris = [res["entity"]["value"] for res in bindings]

    # Now fetch display values for these entities if fetchValueFromQuery is configured

    if prop_config.get("fetchValueFromQuery") and entity_uris:
        if display_name not in ctx.grouped_triples:
            ctx.grouped_triples[display_name] = {
                # Use display name as identifier
                # for virtual properties
                "property": display_name,
                "triples": [],
                "subjectClass": ctx.highest_priority_class,
                "subjectShape": ctx.highest_priority_shape,
                # Should be None for virtual properties
                # to match key format
                "objectShape": None,
                "is_virtual": True,
            }

        for entity_uri in entity_uris:
            # Execute the fetch query for each entity
            if ctx.historical_snapshot:
                result, external_entity = execute_historical_query(
                    prop_config["fetchValueFromQuery"],
                    ctx.subject,
                    URIRef(entity_uri),
                    ctx.historical_snapshot,
                )
            else:
                result, external_entity = execute_sparql_query(
                    prop_config["fetchValueFromQuery"], str(ctx.subject), entity_uri
                )

            if result:
                ctx.fetched_values_map[str(result)] = entity_uri
                new_triple_data = {
                    "triple": (str(ctx.subject), display_name, str(result)),
                    "external_entity": external_entity,
                    "object": entity_uri,
                    "subjectClass": ctx.highest_priority_class,
                    "subjectShape": ctx.highest_priority_shape,
                    "objectShape": target.get("shape"),
                    "is_virtual": True,
                }
                ctx.grouped_triples[display_name]["triples"].append(new_triple_data)
    # Even if no entities are found, we should still create
    # the entry for virtual properties
    # so they can be added via the interface

    elif display_name not in ctx.grouped_triples:
        ctx.grouped_triples[display_name] = {
            # Use display name as identifier
            # for virtual properties
            "property": display_name,
            "triples": [],
            "subjectClass": ctx.highest_priority_class,
            "subjectShape": ctx.highest_priority_shape,
            # Should be None for virtual properties
            # to match key format
            "objectShape": None,
            "is_virtual": True,
        }


def execute_sparql_query(
    query: str, subject: str, value: str
) -> tuple[str | None, str | None]:
    sparql = get_sparql()

    decoded_subject = unquote(subject)
    decoded_value = unquote(value)
    query = query.replace("[[subject]]", f"<{decoded_subject}>")
    query = query.replace("[[value]]", f"<{decoded_value}>")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    bindings = get_sparql_bindings(sparql.query().convert())
    if bindings:
        parsed_query = parseQuery(query)
        algebra_query = translateQuery(parsed_query).algebra
        variable_order = algebra_query["PV"]
        result = bindings[0]
        values = [
            result.get(str(var_name), {}).get("value", None)
            for var_name in variable_order
        ]
        first_value = values[0] if len(values) > 0 else None
        second_value = values[1] if len(values) > 1 else None
        return (first_value, second_value)
    return None, None


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


def execute_historical_query(
    query: str, subject: str, value: str, historical_snapshot: Graph
) -> tuple[str | None, str | None]:
    decoded_subject = unquote(subject)
    decoded_value = unquote(value)
    query = query.replace("[[subject]]", f"<{decoded_subject}>")
    query = query.replace("[[value]]", f"<{decoded_value}>")
    results = historical_snapshot.query(query)
    for row in select_results(results):
        if len(row) == _SUBJECT_LABEL_PAIR_LENGTH:
            return (str(row[0]), str(row[1]))
    return None, None


def get_property_order_from_rules(
    highest_priority_class: str | None, shape_uri: str | None = None
) -> list[str]:
    """
    Extract ordered list of properties from display rules
    for given entity class and optionally a shape.

    Args:
        highest_priority_class: The highest priority class for the entity
        shape_uri: Optional shape URI for the entity

    Returns:
        List of property URIs in the order specified by display rules
    """
    if not highest_priority_class:
        return []

    rule = find_matching_rule(highest_priority_class, shape_uri)
    if not rule:
        return []

    ordered_properties = []
    for prop in rule.get("displayProperties", []):
        if not isinstance(prop, dict):
            continue
        if prop.get("isVirtual"):
            continue  # Virtual properties don't have RDF predicates
        if "property" in prop:
            ordered_properties.append(prop["property"])

    return ordered_properties


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


def get_shape_order_from_display_rules(
    highest_priority_class: str | None, entity_shape: str | None, predicate_uri: str
) -> list[str]:
    """
    Get the ordered list of shapes for a specific predicate from display rules.

    Args:
        highest_priority_class: The highest priority class for the entity
        entity_shape: The shape for the subject entity
        predicate_uri: The predicate URI to get shape ordering for

    Returns:
        List of shape URIs in the order specified in
        displayRules, or empty list if no rules found
    """
    display_rules = get_display_rules()
    if not display_rules:
        return []

    rule = find_matching_rule(highest_priority_class, entity_shape, display_rules)
    if not rule or "displayProperties" not in rule:
        return []

    for prop_config in rule["displayProperties"]:
        if not isinstance(prop_config, dict):
            continue
        if prop_config.get("isVirtual"):
            continue  # Virtual properties don't have RDF predicates or display rules
        if "property" not in prop_config:
            continue  # Defensive check for malformed configuration
        if prop_config["property"] == predicate_uri and "displayRules" in prop_config:
            return [
                display_rule.get("shape")
                for display_rule in prop_config["displayRules"]
                if display_rule.get("shape")
            ]

    return []


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
