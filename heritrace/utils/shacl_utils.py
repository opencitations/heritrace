from typing import List, Optional, Tuple

from flask import Flask
from heritrace.extensions import get_shacl_graph
from heritrace.utils.display_rules_utils import get_class_priority
from heritrace.utils.shacl_display import (apply_display_rules,
                                           extract_shacl_form_fields,
                                           order_form_fields,
                                           process_nested_shapes)
from rdflib import Graph


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


def determine_shape_for_subject(class_list: List[str]) -> Optional[str]:
    """
    Determine the most appropriate SHACL shape for a subject based on its class list.
    
    Args:
        class_list: List of class URIs the subject belongs to
        
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