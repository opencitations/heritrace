from typing import List

from flask import Flask
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