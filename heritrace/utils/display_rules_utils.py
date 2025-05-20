from collections import OrderedDict
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import unquote

from heritrace.extensions import get_display_rules, get_form_fields, get_sparql
from rdflib import ConjunctiveGraph, Graph, URIRef
from rdflib.plugins.sparql.algebra import translateQuery
from rdflib.plugins.sparql.parser import parseQuery
from SPARQLWrapper import JSON

display_rules = get_display_rules()


def find_matching_rule(class_uri=None, shape_uri=None, rules=None):
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
    highest_priority = float('inf')
        
    # Scan all rules to find the best match based on priority
    for rule in rules:            
        rule_priority = rule.get("priority", 0)
        
        # Case 1: Both class and shape match (exact match)
        if class_uri and shape_uri and \
           "class" in rule["target"] and rule["target"]["class"] == str(class_uri) and \
           "shape" in rule["target"] and rule["target"]["shape"] == str(shape_uri):
            # Exact match always takes highest precedence
            return rule
        
        # Case 2: Only class matches
        elif class_uri and "class" in rule["target"] and rule["target"]["class"] == str(class_uri) and \
             "shape" not in rule["target"]:
            if class_match is None or rule_priority < highest_priority:
                class_match = rule
                highest_priority = rule_priority
        
        # Case 3: Only shape matches
        elif shape_uri and "shape" in rule["target"] and rule["target"]["shape"] == str(shape_uri) and \
             "class" not in rule["target"]:
            if shape_match is None or rule_priority < highest_priority:
                shape_match = rule
                highest_priority = rule_priority
    
    # Return the best match based on priority
    # Shape rules typically have higher specificity, so prefer them if they have equal priority
    if shape_match and (class_match is None or 
                        shape_match.get("priority", 0) <= class_match.get("priority", 0)):
        return shape_match
    elif class_match:
        return class_match
    
    return None


def get_class_priority(entity_key):
    """
    Returns the priority of a specific entity key (class_uri, shape_uri).
    Calculates the priority directly from the display rules.
    
    Args:
        entity_key: A tuple (class_uri, shape_uri)
    """
    class_uri = entity_key[0]
    shape_uri = entity_key[1]
        
    rule = find_matching_rule(class_uri, shape_uri)
    return rule.get("priority", 0) if rule else 0


def is_entity_type_visible(entity_key):
    """
    Determines if an entity type should be displayed.
    
    Args:
        entity_key: A tuple (class_uri, shape_uri)
    """
    class_uri = entity_key[0]
    shape_uri = entity_key[1]
        
    rule = find_matching_rule(class_uri, shape_uri)
    return rule.get("shouldBeDisplayed", True) if rule else True


def get_sortable_properties(entity_key: Tuple[str, str]) -> List[Dict[str, str]]:
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
                    prop["displayName"] = display_prop["displayRules"][0][
                        "displayName"
                    ]
                else:
                    prop["displayName"] = display_prop.get(
                        "displayName", prop["property"]
                    )
                break
        
        # Default to string sorting
        prop["sortType"] = "string"
        
        # Try to determine the sort type from form fields
        if form_fields:
            # First try with the exact entity_key (class, shape)
            if entity_key in form_fields and prop["property"] in form_fields[entity_key]:
                field_info = form_fields[entity_key][prop["property"]][0]  # Take the first field definition
                prop["sortType"] = determine_sort_type(field_info)

        sort_props.append(prop)

    return sort_props


def determine_sort_type(field_info):
    """Helper function to determine sort type from field info."""
    # If there's a shape, it's a reference to an entity (sort by label)
    if field_info.get("nodeShape"):
        return "string"
    # Otherwise look at the datatypes
    elif field_info.get("datatypes"):
        datatype = str(field_info["datatypes"][0]).lower()
        if any(t in datatype for t in ["date", "time"]):
            return "date"
        elif any(
            t in datatype
            for t in ["int", "float", "decimal", "double", "number"]
        ):
            return "number"
        elif "boolean" in datatype:
            return "boolean"
    # Default to string
    return "string"


def get_highest_priority_class(subject_classes):
    """
    Find the highest priority class from the given list of classes.
    
    Args:
        subject_classes: List of class URIs
        
    Returns:
        The highest priority class or None if no classes are provided
    """
    if not subject_classes:
        return None
    
    highest_priority = float('inf')
    highest_priority_class = None
    
    for class_uri in subject_classes:
        entity_key = (class_uri, None)
        priority = get_class_priority(entity_key)
        if priority < highest_priority:
            highest_priority = priority
            highest_priority_class = class_uri
    
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
        rule
        for rule in display_rules
        if "target" in rule and "class" in rule["target"] and rule["target"]["class"] == str(highest_priority_class)
    ]
    for prop_uri in primary_properties:
        if display_rules and highest_priority_rules:
            matched_rules = []
            for rule in highest_priority_rules:
                for prop_config in rule["displayProperties"]:
                    if prop_config["property"] == prop_uri:
                        matched_rules.append(rule)
                        current_prop_config = prop_config
                        break
                if matched_rules:
                    break
            
            if matched_rules:
                if "displayRules" in current_prop_config and current_prop_config.get("fetchValueFromQuery"):
                    display_name_top_level = current_prop_config.get("displayName", prop_uri)
                    relevant_properties.add(prop_uri)
                    
                    process_display_rule(
                        display_name_top_level,
                        prop_uri,
                        current_prop_config,
                        subject,
                        triples,
                        grouped_triples,
                        fetched_values_map,
                        historical_snapshot,
                    )

                    if "orderedBy" in current_prop_config:
                        if display_name_top_level not in grouped_triples:
                            grouped_triples[display_name_top_level] = {"property": prop_uri, "triples": [], "shape": current_prop_config.get("shape")}
                        grouped_triples[display_name_top_level]["is_draggable"] = True
                        grouped_triples[display_name_top_level]["ordered_by"] = current_prop_config.get("orderedBy")
                        process_ordering(
                            subject,
                            current_prop_config,
                            current_prop_config.get("orderedBy"),
                            grouped_triples,
                            display_name_top_level,
                            fetched_values_map,
                            historical_snapshot,
                        )
                    if "intermediateRelation" in current_prop_config:
                        if display_name_top_level not in grouped_triples:
                             grouped_triples[display_name_top_level] = {"property": prop_uri, "triples": [], "shape": current_prop_config.get("shape")}
                        grouped_triples[display_name_top_level]["intermediateRelation"] = current_prop_config["intermediateRelation"]

                elif "displayRules" in current_prop_config:
                    is_ordered = "orderedBy" in current_prop_config
                    order_property = current_prop_config.get("orderedBy")
                    
                    for display_rule_nested in current_prop_config["displayRules"]:
                        display_name_nested = display_rule_nested.get(
                            "displayName", prop_uri
                        )
                        relevant_properties.add(prop_uri)
                        process_display_rule(
                            display_name_nested,
                            prop_uri,
                            display_rule_nested,
                            subject,
                            triples,
                            grouped_triples,
                            fetched_values_map,
                            historical_snapshot,
                        )
                        if is_ordered:
                            if display_name_nested not in grouped_triples:
                                grouped_triples[display_name_nested] = {
                                    "property": prop_uri,
                                    "triples": [],
                                    "shape": display_rule_nested.get("shape"),
                                }
                            grouped_triples[display_name_nested]["is_draggable"] = True
                            grouped_triples[display_name_nested]["ordered_by"] = order_property
                            process_ordering(
                                subject,
                                current_prop_config,
                                order_property,
                                grouped_triples,
                                display_name_nested,
                                fetched_values_map,
                                historical_snapshot,
                            )

                        if "intermediateRelation" in display_rule_nested:
                            if display_name_nested not in grouped_triples:
                                grouped_triples[display_name_nested] = { "property": prop_uri, "triples": [], "shape": display_rule_nested.get("shape")}
                            grouped_triples[display_name_nested]["intermediateRelation"] = display_rule_nested["intermediateRelation"]
                        elif "intermediateRelation" in current_prop_config:
                             if display_name_nested not in grouped_triples:
                                grouped_triples[display_name_nested] = { "property": prop_uri, "triples": [], "shape": display_rule_nested.get("shape")}
                             grouped_triples[display_name_nested]["intermediateRelation"] = current_prop_config["intermediateRelation"]

                else:
                    display_name_simple = current_prop_config.get("displayName", prop_uri)
                    relevant_properties.add(prop_uri)
                    process_display_rule(
                        display_name_simple,
                        prop_uri,
                        current_prop_config,
                        subject,
                        triples,
                        grouped_triples,
                        fetched_values_map,
                        historical_snapshot,
                    )
                    if "orderedBy" in current_prop_config:
                        if display_name_simple not in grouped_triples:
                            grouped_triples[display_name_simple] = {"property": prop_uri, "triples": [], "shape": current_prop_config.get("shape")}
                        grouped_triples[display_name_simple]["is_draggable"] = True
                        grouped_triples[display_name_simple]["ordered_by"] = current_prop_config.get("orderedBy")
                        process_ordering(
                            subject,
                            current_prop_config,
                            current_prop_config.get("orderedBy"),
                            grouped_triples,
                            display_name_simple,
                            fetched_values_map,
                            historical_snapshot,
                        )
                    if "intermediateRelation" in current_prop_config:
                        if display_name_simple not in grouped_triples:
                             grouped_triples[display_name_simple] = {"property": prop_uri, "triples": [], "shape": current_prop_config.get("shape")}
                        grouped_triples[display_name_simple]["intermediateRelation"] = current_prop_config["intermediateRelation"]
            else:
                process_default_property(prop_uri, triples, grouped_triples)
        else:
            process_default_property(prop_uri, triples, grouped_triples)

    if display_rules:
        ordered_display_names = []
        for rule in display_rules:
            if "target" in rule and "class" in rule["target"] and URIRef(rule["target"]["class"]) in subject_classes:
                for prop in rule.get("displayProperties", []):
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


def get_property_order_from_rules(subject_classes: list, display_rules: list, shape_uri: str = None):
    """
    Extract ordered list of properties from display rules for given entity classes and optionally a shape.

    Args:
        subject_classes: List of class URIs for the entity
        display_rules: List of display rule configurations
        shape_uri: Optional shape URI for the entity

    Returns:
        List of property URIs in the order specified by display rules
    """
    if not display_rules:
        return []
    
    ordered_properties = []
    
    # First, find the highest priority class
    highest_priority_class = get_highest_priority_class(subject_classes)
    if not highest_priority_class:
        return []
    
    # If we have a shape, try to find a rule matching both class and shape
    if shape_uri:
        rule = find_matching_rule(highest_priority_class, shape_uri, display_rules)
        if rule:
            # Extract properties in order from displayProperties
            for prop in rule.get("displayProperties", []):
                if isinstance(prop, dict) and "property" in prop:
                    ordered_properties.append(prop["property"])
            return ordered_properties
    
    # If no match with shape or no shape provided, find a rule matching just the class
    rule = find_matching_rule(highest_priority_class, None, display_rules)
    if rule:
        # Extract properties in order from displayProperties
        for prop in rule.get("displayProperties", []):
            if isinstance(prop, dict) and "property" in prop:
                ordered_properties.append(prop["property"])
    
    return ordered_properties


def get_similarity_properties(entity_key: Tuple[str, str]) -> Optional[List[Union[str, Dict[str, List[str]]]]]:
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
        print(f"Warning: Invalid format for similarity_properties in class {class_uri}")
        return None
    
    # Validate each element in the list.
    validated_props = []
    for item in similarity_props:
        if isinstance(item, str):
            validated_props.append(item)
        elif isinstance(item, dict) and len(item) == 1 and "and" in item:
            and_list = item["and"]
            if isinstance(and_list, list) and and_list and all(isinstance(p, str) for p in and_list):
                validated_props.append(item)
            else:
                print(
                    f"Warning: Invalid 'and' group in similarity_properties" + 
                    (f" for class {class_uri}" if class_uri else "") + 
                    (f" with shape {shape_uri}" if shape_uri else "") + 
                    f". Expected {{'and': ['prop_uri', ...]}} with a non-empty list of strings."
                )
                return None  # Invalid 'and' group structure
        else:
            print(
                f"Warning: Invalid item format in similarity_properties list" + 
                (f" for class {class_uri}" if class_uri else "") + 
                (f" with shape {shape_uri}" if shape_uri else "") + 
                f". Expected a property URI string or {{'and': [...]}} dict."
            )
            return None  # Invalid item type

    return validated_props if validated_props else None  # Return validated list or None if empty after validation
