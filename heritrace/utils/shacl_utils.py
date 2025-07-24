from typing import List, Optional, Tuple

from flask import Flask
from heritrace.extensions import get_shacl_graph, get_sparql
from heritrace.utils.display_rules_utils import get_class_priority
from heritrace.utils.shacl_display import (apply_display_rules,
                                           extract_shacl_form_fields,
                                           order_form_fields,
                                           process_nested_shapes)
from rdflib import RDF, Graph
from SPARQLWrapper import JSON


def get_form_fields_from_shacl(shacl: Graph, display_rules: List[dict], app: Flask):
    """
    Analyze SHACL shapes to extract form fields for each entity type.
    
    Args:
        shacl: The SHACL graph
        display_rules: The display rules configuration
        app: Flask application instance

    Returns:
        OrderedDict: A dictionary where the keys are tuples (class, shape) and the values are dictionaries
                     of form fields with their properties.
    """
    if not shacl:
        return dict()

    # Step 1: Get the initial form fields from SHACL shapes
    form_fields = extract_shacl_form_fields(shacl, display_rules, app=app)

    # Step 2: Process nested shapes for each field
    processed_shapes = set()
    for entity_key in form_fields:
        for predicate in form_fields[entity_key]:
            for field_info in form_fields[entity_key][predicate]:
                if field_info.get("nodeShape"):
                    field_info["nestedShape"] = process_nested_shapes(
                        shacl,
                        display_rules,
                        field_info["nodeShape"],
                        app=app,
                        processed_shapes=processed_shapes,
                    )

    # Step 3: Apply display rules to the form fields
    if display_rules:
        form_fields = apply_display_rules(shacl, form_fields, display_rules)
    
    # Step 3.5: Ensure all form fields have displayName, using fallback for those without display rules
    ensure_display_names(form_fields)
    
    # Step 4: Order the form fields according to the display rules
    ordered_form_fields = order_form_fields(form_fields, display_rules)        
    return ordered_form_fields


def determine_shape_for_classes(class_list: List[str]) -> Optional[str]:
    """
    Determine the most appropriate SHACL shape for a list of class URIs.
    
    Args:
        class_list: List of class URIs to find shapes for
        
    Returns:
        The most appropriate shape URI based on priority, or None if no shapes are found
    """
    shacl_graph = get_shacl_graph()
    if not shacl_graph:
        return None
    
    all_shacl_shapes = []
    
    for class_uri in class_list:
        query_string = f"""
            SELECT DISTINCT ?shape WHERE {{
                ?shape <http://www.w3.org/ns/shacl#targetClass> <{class_uri}> .
            }}
        """
        
        results = shacl_graph.query(query_string)
        shapes = [str(row.shape) for row in results]
        
        for shape in shapes:
            all_shacl_shapes.append((class_uri, shape))

    return _find_highest_priority_shape(all_shacl_shapes)


def determine_shape_for_entity_triples(entity_triples: list) -> Optional[str]:
    """
    Determine the most appropriate SHACL shape for an entity based on its triples.
    
    Uses a multi-criteria scoring system to distinguish between shapes:
    1. sh:hasValue constraint matches (highest priority)
    2. Property matching - number of shape properties present in entity
    3. Class priority - predefined priority ordering
    
    Args:
        entity_triples: List of triples (subject, predicate, object) for the entity
        
    Returns:
        The most appropriate shape URI, or None if no shapes are found
    """
    shacl_graph = get_shacl_graph()
    if not shacl_graph:
        return None
    
    entity_classes = []
    entity_properties = set()
    
    for subject, predicate, obj in entity_triples:
        if str(predicate) == str(RDF.type):
            entity_classes.append(str(obj))
        entity_properties.add(str(predicate))
    
    if not entity_classes:
        return None
    
    candidate_shapes = []
    
    for class_uri in entity_classes:
        query_string = f"""
            SELECT DISTINCT ?shape WHERE {{
                ?shape <http://www.w3.org/ns/shacl#targetClass> <{class_uri}> .
            }}
        """
        
        results = shacl_graph.query(query_string)
        shapes = [str(row.shape) for row in results]
        
        for shape in shapes:
            candidate_shapes.append((class_uri, shape))
    
    if not candidate_shapes:
        return None
    
    if len(candidate_shapes) == 1:
        return candidate_shapes[0][1]
    
    shape_scores = {}
    
    for class_uri, shape_uri in candidate_shapes:
        shape_properties = _get_shape_properties(shacl_graph, shape_uri)
        property_matches = len(entity_properties.intersection(shape_properties))
        
        hasvalue_matches = _check_hasvalue_constraints(shacl_graph, shape_uri, entity_triples)
        
        entity_key = (class_uri, shape_uri)
        priority = get_class_priority(entity_key)
        
        # Combined score: (hasvalue_matches, property_matches, -priority)
        # hasValue matches are most important, then property matches, then priority
        combined_score = (hasvalue_matches, property_matches, -priority)
        shape_scores[shape_uri] = combined_score
    
    best_shape = max(shape_scores.keys(), key=lambda s: shape_scores[s])
    return best_shape


def _find_highest_priority_shape(class_shape_pairs: List[Tuple[str, str]]) -> Optional[str]:
    """
    Helper function to find the shape with the highest priority from a list of (class_uri, shape) pairs.
    
    Args:
        class_shape_pairs: List of tuples (class_uri, shape)
        
    Returns:
        The shape with the highest priority, or None if the list is empty
    """
    highest_priority = float('inf')
    highest_priority_shape = None
    
    for class_uri, shape in class_shape_pairs:
        entity_key = (class_uri, shape)
        priority = get_class_priority(entity_key)
        if priority < highest_priority:
            highest_priority = priority
            highest_priority_shape = shape
    
    return highest_priority_shape


def _get_shape_properties(shacl_graph: Graph, shape_uri: str) -> set:
    """
    Extract all properties defined in a SHACL shape.
    
    Args:
        shacl_graph: The SHACL graph
        shape_uri: URI of the shape to analyze
        
    Returns:
        Set of property URIs defined in the shape
    """
    properties = set()
    
    query_string = f"""
        PREFIX sh: <http://www.w3.org/ns/shacl#>
        SELECT DISTINCT ?property WHERE {{
            <{shape_uri}> sh:property ?propertyShape .
            ?propertyShape sh:path ?property .
        }}
    """
    
    results = shacl_graph.query(query_string)
    for row in results:
        properties.add(str(row.property))
    
    return properties


def _check_hasvalue_constraints(shacl_graph: Graph, shape_uri: str, entity_triples: list) -> int:
    """
    Check how many sh:hasValue constraints the entity satisfies for a given shape.
    
    Args:
        shacl_graph: The SHACL graph
        shape_uri: URI of the shape to check
        entity_triples: List of triples (subject, predicate, object) for the entity
        
    Returns:
        Number of hasValue constraints satisfied by the entity
    """
    # Get all hasValue constraints for this shape
    query_string = f"""
        PREFIX sh: <http://www.w3.org/ns/shacl#>
        SELECT DISTINCT ?property ?value WHERE {{
            <{shape_uri}> sh:property ?propertyShape .
            ?propertyShape sh:path ?property .
            ?propertyShape sh:hasValue ?value .
        }}
    """
    
    results = shacl_graph.query(query_string)
    constraints = [(str(row.property), str(row.value)) for row in results]
    
    if not constraints:
        return 0
    
    # Create a set of (predicate, object) pairs from entity triples
    entity_property_values = set()
    for _, predicate, obj in entity_triples:
        entity_property_values.add((str(predicate), str(obj)))
    
    # Count how many constraints are satisfied
    satisfied_constraints = 0
    for property_uri, required_value in constraints:
        if (property_uri, required_value) in entity_property_values:
            satisfied_constraints += 1
    
    return satisfied_constraints


def ensure_display_names(form_fields):
    """
    Ensures all form fields have a displayName, using URI formatting as fallback.
    
    Args:
        form_fields: Dictionary of form fields to process
    """
    from heritrace.utils.filters import format_uri_as_readable
    
    for entity_key, predicates in form_fields.items():
        for predicate_uri, details_list in predicates.items():
            for field_info in details_list:
                # Only add displayName if not already present
                if not field_info.get("displayName"):
                    field_info["displayName"] = format_uri_as_readable(predicate_uri)


def _find_entity_position_in_order_map(entity_uri: str, order_map: dict) -> Optional[int]:
    """
    Helper function to find entity position in an order map.
    
    This function handles the case where there might be multiple independent ordered chains
    within the same predicate relationship. Each chain has its own starting element and
    follows a linked-list structure where each entity points to the next one.
    
    Args:
        entity_uri: URI of the entity to find position for
        order_map: Dictionary mapping entities to their next entity in sequence.
                   Key = current entity URI, Value = next entity URI (or None for last element)
                   Example: {'entity1': 'entity2', 'entity2': 'entity3', 'entity3': None,
                            'entity4': 'entity5', 'entity5': None}
                   This represents two chains: [entity1 -> entity2 -> entity3] and [entity4 -> entity5]
        
    Returns:
        1-based position in the sequence, or None if not found
    """
    # Find all starting elements of ordered chains.
    # A start element is one that appears as a key in the order_map but never as a value,
    # meaning no other entity points to it (it's the head of a chain).
    start_elements = set(order_map.keys()) - set(v for v in order_map.values() if v is not None)
    
    if not start_elements:
        # No valid starting points found - this shouldn't happen in well-formed data
        return None
    
    # Since there can be multiple independent ordered chains, we need to check each one
    # to find which chain contains our target entity
    for start_element in start_elements:
        # Build the complete sequence for this chain by following the linked-list structure
        sequence = []
        current_element = start_element
        
        # Follow the chain from start to end
        while current_element in order_map:
            sequence.append(current_element)
            # Move to the next element in the chain (or None if we've reached the end)
            current_element = order_map[current_element]
        
        # Check if our target entity is in this particular chain
        try:
            # If found, return its 1-based position within this chain
            return sequence.index(entity_uri) + 1  # Convert from 0-based to 1-based indexing
        except ValueError:
            # Entity not found in this chain, try the next one
            continue
    
    # Entity was not found in any of the ordered chains
    return None


def get_entity_position_in_sequence(entity_uri: str, subject_uri: str, predicate_uri: str, 
                                   order_property: str, snapshot: Optional[Graph] = None) -> Optional[int]:
    """
    Get the position of an entity in an ordered sequence.
    
    Args:
        entity_uri: URI of the entity to find position for
        subject_uri: URI of the subject that has the ordered property
        predicate_uri: URI of the ordered predicate
        order_property: URI of the property that defines the ordering
        snapshot: Optional graph snapshot for historical queries
    
    Returns:
        1-based position in the sequence, or None if not found
    """
    order_query = f"""
        SELECT ?orderedEntity (COALESCE(?next, "NONE") AS ?nextValue)
        WHERE {{
            <{subject_uri}> <{predicate_uri}> ?orderedEntity.
            OPTIONAL {{
                ?orderedEntity <{order_property}> ?next.
            }}
        }}
    """
    
    if snapshot:
        order_results = list(snapshot.query(order_query))
                
        order_map = {}
        for res in order_results:
            ordered_entity = str(res[0])
            next_value = str(res[1])
            order_map[ordered_entity] = None if next_value == "NONE" else next_value
                
        position = _find_entity_position_in_order_map(entity_uri, order_map)
        return position
    else:
        sparql = get_sparql()
        sparql.setQuery(order_query)
        sparql.setReturnFormat(JSON)
        order_results = sparql.query().convert().get("results", {}).get("bindings", [])
        
        order_map = {}
        for res in order_results:
            ordered_entity = res["orderedEntity"]["value"]
            next_value = res["nextValue"]["value"]
            order_map[ordered_entity] = None if next_value == "NONE" else next_value
        
        return _find_entity_position_in_order_map(entity_uri, order_map)