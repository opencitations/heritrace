from collections import OrderedDict
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import unquote

from heritrace.extensions import (get_custom_filter, get_display_rules,
                                  get_form_fields, get_sparql)
from rdflib import Dataset, Graph, Literal, URIRef
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
    Classes without defined rules receive the lowest priority (highest number).
    
    Args:
        entity_key: A tuple (class_uri, shape_uri)
    """
    class_uri = entity_key[0]
    shape_uri = entity_key[1]
        
    rule = find_matching_rule(class_uri, shape_uri)
    return rule.get("priority", 0) if rule else float('inf')


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
    from heritrace.utils.shacl_utils import determine_shape_for_classes
    
    if not subject_classes:
        return None
    
    highest_priority = float('inf')
    highest_priority_class = None
    
    for class_uri in subject_classes:
        class_uri = str(class_uri)
        shape = determine_shape_for_classes([class_uri])
        entity_key = (class_uri, shape)
        priority = get_class_priority(entity_key)
        if priority < highest_priority:
            highest_priority = priority
            highest_priority_class = class_uri
    
    if highest_priority_class is None and subject_classes:
        highest_priority_class = str(subject_classes[0])
    
    return highest_priority_class


def get_grouped_triples(
    subject: URIRef, 
    triples: List[Tuple[URIRef, URIRef, URIRef|Literal]], 
    valid_predicates_info: List[str], 
    historical_snapshot: Optional[Graph] = None,
    highest_priority_class: Optional[str] = None,
    highest_priority_shape: Optional[str] = None
) -> Tuple[OrderedDict, set, dict]:
    """
    This function groups the triples based on the display rules. 
    It also fetches the values for the properties that are configured to be fetched from the query.
    
    Args:
        subject: The subject URI
        triples: List of triples for the subject
        valid_predicates_info: List of valid predicates for the subject
        historical_snapshot: Optional historical snapshot graph
        highest_priority_class: The highest priority class URI for the subject
        highest_priority_shape: The highest priority shape URI for the subject
    
    Returns:
        Tuple of grouped triples, relevant properties, and fetched values map
        
    Note:
        relevant_properties contains all properties that should be considered 
        "relevant" for UI operations (adding/deleting). This includes:
        - Properties configured in display rules when rules exist and match
        - ALL valid properties when no display rules exist or no rules match
        This ensures users can always interact with entities even without display rules.
    """
    display_rules = get_display_rules()
    form_fields = get_form_fields()

    grouped_triples = OrderedDict()
    relevant_properties = set()
    fetched_values_map = dict()

    matching_rule = find_matching_rule(highest_priority_class, highest_priority_shape, display_rules)
    matching_form_field = form_fields.get((highest_priority_class, highest_priority_shape))

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
        current_prop_config = None

        if display_rules and matching_rule:
            for prop_config in matching_rule.get("displayProperties", []):
                config_identifier = prop_config.get("displayName") if prop_config.get("isVirtual") else prop_config.get("property")
                if config_identifier == prop_uri:
                    current_prop_config = prop_config
                    break
            
            current_form_field = matching_form_field.get(prop_uri) if matching_form_field else None

            if current_prop_config:
                if "displayRules" in current_prop_config:
                    is_ordered = "orderedBy" in current_prop_config
                    order_property = current_prop_config.get("orderedBy")
                    
                    for display_rule_nested in current_prop_config["displayRules"]:
                        display_name_nested = display_rule_nested.get(
                            "displayName", prop_uri
                        )
                        relevant_properties.add(prop_uri)
                        object_shape = display_rule_nested.get("shape")
                        if current_prop_config.get("isVirtual"):
                            process_virtual_property_display(
                                display_name_nested,
                                current_prop_config,
                                subject,
                                grouped_triples,
                                fetched_values_map,
                                historical_snapshot,
                                highest_priority_shape,
                                highest_priority_class
                            )
                        else:
                            process_display_rule(
                                display_name_nested,
                                prop_uri,
                                display_rule_nested,
                                subject,
                                triples,
                                grouped_triples,
                                fetched_values_map,
                                historical_snapshot,
                                highest_priority_shape,
                                object_shape,
                                highest_priority_class
                            )
                        if is_ordered and not current_prop_config.get("isVirtual", False):
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

                        # Ensure the grouped_triples entry exists
                        if display_name_nested not in grouped_triples:
                            grouped_triples[display_name_nested] = {
                                "property": prop_uri,
                                "triples": [],
                                "subjectClass": highest_priority_class,
                                "subjectShape": highest_priority_shape,
                                "objectShape": display_rule_nested.get("shape")
                            }
                            
                        if "intermediateRelation" in display_rule_nested or "intermediateRelation" in current_prop_config:
                            # Set intermediateRelation from the appropriate source
                            if "intermediateRelation" in display_rule_nested:
                                grouped_triples[display_name_nested]["intermediateRelation"] = display_rule_nested["intermediateRelation"]
                            else:  # Must be in current_prop_config based on the if condition
                                grouped_triples[display_name_nested]["intermediateRelation"] = current_prop_config["intermediateRelation"]

                else:
                    display_name_simple = current_prop_config.get("displayName", prop_uri)
                    # Only add non-virtual properties to relevant_properties
                    # Virtual properties are handled separately in entity.py
                    if not current_prop_config.get("isVirtual"):
                        relevant_properties.add(prop_uri)

                    object_shape = None
                    if current_form_field:
                        for form_field in current_form_field:
                            object_shape = form_field.get("nodeShape")       
                            break                  

                    if current_prop_config.get("isVirtual"):
                        process_virtual_property_display(
                            display_name_simple,
                            current_prop_config,
                            subject,
                            grouped_triples,
                            fetched_values_map,
                            historical_snapshot,
                            highest_priority_shape,
                            highest_priority_class
                        )
                    else:
                        process_display_rule(
                            display_name_simple,
                            prop_uri,
                            current_prop_config,
                            subject,
                            triples,
                            grouped_triples,
                            fetched_values_map,
                            historical_snapshot,
                            highest_priority_shape,
                            object_shape,
                            highest_priority_class
                        )
                    if "orderedBy" in current_prop_config and not current_prop_config.get("isVirtual", False):
                        if display_name_simple not in grouped_triples:
                            grouped_triples[display_name_simple] = {"property": prop_uri, "triples": [], "subjectClass": highest_priority_class, "subjectShape": highest_priority_shape, "objectShape": current_prop_config.get("shape")}
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
                            highest_priority_shape
                        )
                    if "intermediateRelation" in current_prop_config:
                        if display_name_simple not in grouped_triples:
                             grouped_triples[display_name_simple] = {"property": prop_uri, "triples": [], "subjectClass": highest_priority_class, "subjectShape": highest_priority_shape, "objectShape": current_prop_config.get("shape")}
                        grouped_triples[display_name_simple]["intermediateRelation"] = current_prop_config["intermediateRelation"]
            else:
                # Property without specific configuration - add to relevant_properties
                # Don't process properties without configuration (they are not virtual in this case)
                relevant_properties.add(prop_uri)
                process_default_property(prop_uri, triples, grouped_triples, highest_priority_shape, highest_priority_class)
        else:
            # No display rules or no matching rule - add all properties to relevant_properties
            relevant_properties.add(prop_uri)
            process_default_property(prop_uri, triples, grouped_triples, highest_priority_shape, highest_priority_class)

    grouped_triples = OrderedDict(grouped_triples)
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
    subject_shape=None,
    object_shape=None,
    subject_class=None,
):
    if display_name not in grouped_triples:
        grouped_triples[display_name] = {
            "property": prop_uri,
            "triples": [],
            "subjectClass": subject_class,
            "subjectShape": subject_shape,
            "objectShape": object_shape,
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
                    object_uri = str(triple[2])
                    new_triple_data = {
                        "triple": new_triple,
                        "external_entity": external_entity,
                        "object": object_uri,
                        "subjectClass": subject_class,
                        "subjectShape": subject_shape,
                        "objectShape": object_shape,
                    }
                    grouped_triples[display_name]["triples"].append(new_triple_data)
            else:
                if str(triple[1]) == 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type':
                    from heritrace.utils.shacl_utils import determine_shape_for_classes
                    object_class_shape = determine_shape_for_classes([triple[2]])
                    result = get_custom_filter().human_readable_class((triple[2], object_class_shape))
                else:
                    result = triple[2]
                
                object_uri = str(triple[2])
                
                new_triple_data = {
                    "triple": (str(triple[0]), str(triple[1]), result),
                    "object": object_uri,
                    "subjectClass": subject_class,
                    "subjectShape": subject_shape,
                    "objectShape": object_shape,
                }
                grouped_triples[display_name]["triples"].append(new_triple_data)


def process_virtual_property_display(
    display_name: str,
    prop_config: dict,
    subject: URIRef,
    grouped_triples: OrderedDict,
    fetched_values_map: dict,
    historical_snapshot: Optional[Graph] = None,
    subject_shape: Optional[str] = None,
    subject_class: Optional[str] = None
):
    """Process virtual properties by querying for entities that reference the current entity."""

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

    decoded_subject = unquote(str(subject))

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

    if historical_snapshot:
        # Execute query on historical snapshot
        results = list(historical_snapshot.query(query))
        entity_uris = [str(row[0]) for row in results]
    else:
        # Execute query on live triplestore
        sparql = get_sparql()
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert().get("results", {}).get("bindings", [])
        entity_uris = [res["entity"]["value"] for res in results]

    # Now fetch display values for these entities if fetchValueFromQuery is configured

    if prop_config.get("fetchValueFromQuery") and entity_uris:

        if display_name not in grouped_triples:
            grouped_triples[display_name] = {
                "property": display_name,  # Use display name as identifier for virtual properties
                "triples": [],
                "subjectClass": subject_class,
                "subjectShape": subject_shape,
                "objectShape": None,  # Should be None for virtual properties to match key format
                "is_virtual": True
            }

        for entity_uri in entity_uris:
            # Execute the fetch query for each entity
            if historical_snapshot:
                result, external_entity = execute_historical_query(
                    prop_config["fetchValueFromQuery"],
                    subject,
                    URIRef(entity_uri),
                    historical_snapshot
                )
            else:
                result, external_entity = execute_sparql_query(
                    prop_config["fetchValueFromQuery"],
                    str(subject),
                    entity_uri 
                )

            if result:
                fetched_values_map[str(result)] = entity_uri
                new_triple_data = {
                    "triple": (str(subject), display_name, str(result)),
                    "external_entity": external_entity,
                    "object": entity_uri,
                    "subjectClass": subject_class,
                    "subjectShape": subject_shape,
                    "objectShape": target.get("shape"),
                    "is_virtual": True
                }
                grouped_triples[display_name]["triples"].append(new_triple_data)
    else:
        # Even if no entities are found, we should still create the entry for virtual properties
        # so they can be added via the interface

        if display_name not in grouped_triples:
            grouped_triples[display_name] = {
                "property": display_name,  # Use display name as identifier for virtual properties
                "triples": [],
                "subjectClass": subject_class,
                "subjectShape": subject_shape,
                "objectShape": None,  # Should be None for virtual properties to match key format
                "is_virtual": True
            }


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
    historical_snapshot: Dataset | Graph | None = None,
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


def process_default_property(prop_uri, triples, grouped_triples, subject_shape=None, subject_class=None):
    display_name = prop_uri
    grouped_triples[display_name] = {
        "property": prop_uri, 
        "triples": [], 
        "subjectClass": subject_class,
        "subjectShape": subject_shape,
        "objectShape": None
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
) -> Tuple[str, str]:
    decoded_subject = unquote(subject)
    decoded_value = unquote(value)
    query = query.replace("[[subject]]", f"<{decoded_subject}>")
    query = query.replace("[[value]]", f"<{decoded_value}>")
    results = historical_snapshot.query(query)
    if results:
        for result in results:
            if len(result) == 2:
                return (str(result[0]), str(result[1]))
    return None, None


def get_property_order_from_rules(highest_priority_class: str, shape_uri: str = None):
    """
    Extract ordered list of properties from display rules for given entity class and optionally a shape.

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
        if isinstance(prop, dict) and "property" in prop:
            ordered_properties.append(prop["property"])
    
    return ordered_properties


def get_predicate_ordering_info(predicate_uri: str, highest_priority_class: str, entity_shape: str = None) -> Optional[str]:
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
        if isinstance(prop, dict) and prop.get("property") == predicate_uri:
            return prop.get("orderedBy")
    
    return None


def get_shape_order_from_display_rules(highest_priority_class: str, entity_shape: str, predicate_uri: str) -> list:
    """
    Get the ordered list of shapes for a specific predicate from display rules.
    
    Args:
        highest_priority_class: The highest priority class for the entity
        entity_shape: The shape for the subject entity
        predicate_uri: The predicate URI to get shape ordering for
        
    Returns:
        List of shape URIs in the order specified in displayRules, or empty list if no rules found
    """    
    display_rules = get_display_rules()
    if not display_rules:
        return []
    
    rule = find_matching_rule(highest_priority_class, entity_shape, display_rules)
    if not rule or "displayProperties" not in rule:
        return []
    
    for prop_config in rule["displayProperties"]:
        if prop_config["property"] == predicate_uri:
            if "displayRules" in prop_config:
                return [display_rule.get("shape") for display_rule in prop_config["displayRules"] 
                       if display_rule.get("shape")]
    
    return []


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
