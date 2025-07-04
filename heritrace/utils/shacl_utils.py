from typing import List, Optional, Tuple

from flask import Flask
from heritrace.extensions import get_shacl_graph
from heritrace.utils.display_rules_utils import get_class_priority
from heritrace.utils.shacl_display import (apply_display_rules,
                                           extract_shacl_form_fields,
                                           order_form_fields,
                                           process_nested_shapes)
from rdflib import RDF, Graph


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


def determine_shape_for_entity_triples(entity_triples_iter) -> Optional[str]:
    """
    Determine the most appropriate SHACL shape for an entity based on its triples.
    
    Uses both class priority and heuristic property matching to distinguish
    between shapes with the same target class but different properties
    (e.g., SpecialIssueShape vs IssueShape).
    
    Args:
        entity_triples_iter: Iterator of triples (subject, predicate, object) for the entity
        
    Returns:
        The most appropriate shape URI, or None if no shapes are found
    """
    shacl_graph = get_shacl_graph()
    if not shacl_graph:
        return None
    
    entity_classes = []
    entity_properties = set()
    
    for subject, predicate, obj in entity_triples_iter:
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
        
        entity_key = (class_uri, shape_uri)
        priority = get_class_priority(entity_key)
        
        # Combined score: (property_matches, -priority)
        # Higher property matches is better, lower priority number is better
        combined_score = (property_matches, -priority)
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