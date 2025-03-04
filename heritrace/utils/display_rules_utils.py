from collections import OrderedDict
from typing import Tuple
from urllib.parse import unquote

from heritrace.extensions import get_display_rules, get_sparql
from rdflib import ConjunctiveGraph, Graph, URIRef
from rdflib.plugins.sparql.algebra import translateQuery
from rdflib.plugins.sparql.parser import parseQuery
from SPARQLWrapper import JSON

display_rules = get_display_rules()


def get_class_priority(class_uri):
    """
    Restituisce la priorità di una classe specifica.
    Calcola la priorità direttamente dalle regole di visualizzazione.
    """
    rules = get_display_rules()
    if not rules:
        return 0

    for rule in rules:
        if rule["class"] == str(class_uri):
            return rule.get("priority", 0)
    return 0


def is_entity_type_visible(entity_type):
    display_rules = get_display_rules()

    for rule in display_rules:
        if rule["class"] == entity_type:
            return rule.get("shouldBeDisplayed", True)
    return True


def get_sortable_properties(entity_type: str, display_rules, form_fields_cache) -> list:
    """
    Ottiene le proprietà ordinabili dalle regole di visualizzazione per un tipo di entità.
    Inferisce il tipo di ordinamento dal form_fields_cache.

    Args:
        entity_type: L'URI del tipo di entità

    Returns:
        Lista di dizionari con le informazioni di ordinamento
    """
    if not display_rules:
        return []

    for rule in display_rules:
        if rule["class"] == entity_type and "sortableBy" in rule:
            # Aggiungiamo displayName ottenuto dalla proprietà nella classe
            sort_props = []
            for sort_config in rule["sortableBy"]:
                prop = sort_config.copy()

                # Trova la displayProperty corrispondente per ottenere il displayName
                for display_prop in rule["displayProperties"]:
                    if display_prop["property"] == prop["property"]:
                        if "displayRules" in display_prop:
                            prop["displayName"] = display_prop["displayRules"][0][
                                "displayName"
                            ]
                        else:
                            prop["displayName"] = display_prop.get(
                                "displayName", prop["property"]
                            )
                        break

                # Determina il tipo di ordinamento dalle form fields
                if form_fields_cache and entity_type in form_fields_cache:
                    entity_fields = form_fields_cache[entity_type]
                    if prop["property"] in entity_fields:
                        field_info = entity_fields[prop["property"]][
                            0
                        ]  # Prendi il primo field definition

                        # Se c'è una shape, è una referenza a un'entità (ordina per label)
                        if field_info.get("nodeShape"):
                            prop["sortType"] = "string"
                        # Altrimenti guarda i datatypes
                        elif field_info.get("datatypes"):
                            datatype = str(field_info["datatypes"][0]).lower()
                            if any(t in datatype for t in ["date", "time"]):
                                prop["sortType"] = "date"
                            elif any(
                                t in datatype
                                for t in ["int", "float", "decimal", "double", "number"]
                            ):
                                prop["sortType"] = "number"
                            else:
                                prop["sortType"] = "string"
                        else:
                            prop["sortType"] = "string"

                sort_props.append(prop)

            return sort_props

    return []


def get_highest_priority_class(subject_classes):
    max_priority = None
    highest_priority_class = None
    for cls in subject_classes:
        priority = get_class_priority(str(cls))
        if max_priority is None or priority > max_priority:
            max_priority = priority
            highest_priority_class = cls
    return highest_priority_class


def get_grouped_triples(
    subject, triples, subject_classes, valid_predicates_info, historical_snapshot=None
):
    display_rules = get_display_rules()

    grouped_triples = OrderedDict()
    relevant_properties = set()
    fetched_values_map = (
        dict()
    )  # Map of original values to values returned by the query
    primary_properties = valid_predicates_info
    highest_priority_class = get_highest_priority_class(subject_classes)
    highest_priority_rules = [
        rule for rule in display_rules if rule["class"] == str(highest_priority_class)
    ]
    for prop_uri in primary_properties:
        if display_rules and highest_priority_rules:
            matched_rules = []
            for rule in highest_priority_rules:
                for prop in rule["displayProperties"]:
                    if prop["property"] == prop_uri:
                        matched_rules.append(rule)
            if matched_rules:
                rule = matched_rules[0]
                for prop in rule["displayProperties"]:
                    if prop["property"] == prop_uri:
                        is_ordered = "orderedBy" in prop
                        order_property = prop.get("orderedBy")

                        if "displayRules" in prop:
                            for display_rule in prop["displayRules"]:
                                display_name = display_rule.get("displayName", prop_uri)
                                relevant_properties.add(prop_uri)
                                process_display_rule(
                                    display_name,
                                    prop_uri,
                                    display_rule,
                                    subject,
                                    triples,
                                    grouped_triples,
                                    fetched_values_map,
                                    historical_snapshot,
                                )

                                if is_ordered:
                                    grouped_triples[display_name]["is_draggable"] = True
                                    grouped_triples[display_name][
                                        "ordered_by"
                                    ] = order_property
                                    process_ordering(
                                        subject,
                                        prop,
                                        order_property,
                                        grouped_triples,
                                        display_name,
                                        fetched_values_map,
                                        historical_snapshot,
                                    )

                                if "intermediateRelation" in prop:
                                    grouped_triples[display_name][
                                        "intermediateRelation"
                                    ] = prop["intermediateRelation"]
                        else:
                            display_name = prop.get("displayName", prop_uri)
                            relevant_properties.add(prop_uri)
                            process_display_rule(
                                display_name,
                                prop_uri,
                                prop,
                                subject,
                                triples,
                                grouped_triples,
                                fetched_values_map,
                                historical_snapshot,
                            )

                            if is_ordered:
                                grouped_triples[display_name]["is_draggable"] = True
                                grouped_triples[display_name][
                                    "ordered_by"
                                ] = order_property
                                process_ordering(
                                    subject,
                                    prop,
                                    order_property,
                                    grouped_triples,
                                    display_name,
                                    fetched_values_map,
                                    historical_snapshot,
                                )

                            if "intermediateRelation" in prop:
                                grouped_triples[display_name][
                                    "intermediateRelation"
                                ] = prop["intermediateRelation"]
            else:
                process_default_property(prop_uri, triples, grouped_triples)
        else:
            process_default_property(prop_uri, triples, grouped_triples)

    if display_rules:
        ordered_display_names = []
        for rule in display_rules:
            if URIRef(rule["class"]) in subject_classes:
                for prop in rule["displayProperties"]:
                    if "displayRules" in prop:
                        for display_rule in prop["displayRules"]:
                            display_name = display_rule.get(
                                "displayName", prop["property"]
                            )
                            if display_name in grouped_triples:
                                ordered_display_names.append(display_name)
                    else:
                        display_name = prop.get("displayName", prop["property"])
                        if display_name in grouped_triples:
                            ordered_display_names.append(display_name)
        for display_name in grouped_triples.keys():
            if display_name not in ordered_display_names:
                ordered_display_names.append(display_name)
    else:
        ordered_display_names = list(grouped_triples.keys())

    grouped_triples = OrderedDict(
        (k, grouped_triples[k]) for k in ordered_display_names
    )
    return grouped_triples, relevant_properties


def process_display_rule(
    display_name,
    prop_uri,
    rule,
    subject,
    triples,
    grouped_triples,
    fetched_values_map,
    historical_snapshot=None,
):
    if display_name not in grouped_triples:
        grouped_triples[display_name] = {
            "property": prop_uri,
            "triples": [],
            "shape": rule.get("shape"),
            "intermediateRelation": rule.get("intermediateRelation"),
        }
    for triple in triples:
        if str(triple[1]) == prop_uri:
            if rule.get("fetchValueFromQuery"):
                if historical_snapshot:
                    result, external_entity = execute_historical_query(
                        rule["fetchValueFromQuery"],
                        subject,
                        triple[2],
                        historical_snapshot,
                    )
                else:
                    result, external_entity = execute_sparql_query(
                        rule["fetchValueFromQuery"], subject, triple[2]
                    )
                if result:
                    fetched_values_map[str(result)] = str(triple[2])
                    new_triple = (str(triple[0]), str(triple[1]), str(result))
                    new_triple_data = {
                        "triple": new_triple,
                        "external_entity": external_entity,
                        "object": str(triple[2]),
                        "shape": rule.get("shape"),
                    }
                    grouped_triples[display_name]["triples"].append(new_triple_data)
            else:
                new_triple_data = {
                    "triple": (str(triple[0]), str(triple[1]), str(triple[2])),
                    "object": str(triple[2]),
                    "shape": rule.get("shape"),
                }
                grouped_triples[display_name]["triples"].append(new_triple_data)


def execute_sparql_query(query: str, subject: str, value: str) -> Tuple[str, str]:
    sparql = get_sparql()

    decoded_subject = unquote(subject)
    decoded_value = unquote(value)
    query = query.replace("[[subject]]", f"<{decoded_subject}>")
    query = query.replace("[[value]]", f"<{decoded_value}>")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert().get("results", {}).get("bindings", [])
    if results:
        parsed_query = parseQuery(query)
        algebra_query = translateQuery(parsed_query).algebra
        variable_order = algebra_query["PV"]
        result = results[0]
        values = [
            result.get(str(var_name), {}).get("value", None)
            for var_name in variable_order
        ]
        first_value = values[0] if len(values) > 0 else None
        second_value = values[1] if len(values) > 1 else None
        return (first_value, second_value)
    return None, None


def process_ordering(
    subject,
    prop,
    order_property,
    grouped_triples,
    display_name,
    fetched_values_map,
    historical_snapshot: ConjunctiveGraph | Graph | None = None,
):
    def get_ordered_sequence(order_results):
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

    decoded_subject = unquote(subject)

    sparql = get_sparql()

    order_query = f"""
        SELECT ?orderedEntity (COALESCE(?next, "NONE") AS ?nextValue)
        WHERE {{
            <{decoded_subject}> <{prop['property']}> ?orderedEntity.
            OPTIONAL {{
                ?orderedEntity <{order_property}> ?next.
            }}
        }}
    """
    if historical_snapshot:
        order_results = list(historical_snapshot.query(order_query))
    else:
        sparql.setQuery(order_query)
        sparql.setReturnFormat(JSON)
        order_results = sparql.query().convert().get("results", {}).get("bindings", [])

    order_sequences = get_ordered_sequence(order_results)
    for sequence in order_sequences:
        grouped_triples[display_name]["triples"].sort(
            key=lambda x: (
                sequence.index(
                    fetched_values_map.get(str(x["triple"][2]), str(x["triple"][2]))
                )
                if fetched_values_map.get(str(x["triple"][2]), str(x["triple"][2]))
                in sequence
                else float("inf")
            )
        )


def process_default_property(prop_uri, triples, grouped_triples):
    display_name = prop_uri
    grouped_triples[display_name] = {"property": prop_uri, "triples": [], "shape": None}
    triples_for_prop = [triple for triple in triples if str(triple[1]) == prop_uri]
    for triple in triples_for_prop:
        new_triple_data = {
            "triple": (str(triple[0]), str(triple[1]), str(triple[2])),
            "object": str(triple[2]),
            "shape": None,
        }
        grouped_triples[display_name]["triples"].append(new_triple_data)


def execute_historical_query(
    query: str, subject: str, value: str, historical_snapshot: Graph
) -> Tuple[str, str]:
    decoded_subject = unquote(subject)
    decoded_value = unquote(value)
    query = query.replace("[[subject]]", f"<{decoded_subject}>")
    query = query.replace("[[value]]", f"<{decoded_value}>")
    results = historical_snapshot.query(query)
    if results:
        for result in results:
            return (str(result[0]), str(result[1]))
    return None, None


def get_property_order_from_rules(subject_classes: list, display_rules: list) -> list:
    """
    Extract ordered list of properties from display rules for given entity classes.

    Args:
        subject_classes: List of class URIs for the entity
        display_rules: List of display rule configurations

    Returns:
        List of property URIs in the order specified by display rules
    """
    ordered_properties = []
    highest_priority_class = get_highest_priority_class(subject_classes)

    if display_rules and highest_priority_class:
        # Find matching rule for the entity's highest priority class
        for rule in display_rules:
            if rule["class"] == str(highest_priority_class):
                # Extract properties in order from displayProperties
                for prop in rule.get("displayProperties", []):
                    if isinstance(prop, dict) and "property" in prop:
                        ordered_properties.append(prop["property"])
                break

    return ordered_properties
