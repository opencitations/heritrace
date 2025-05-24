"""
Utility functions for entity operations.
"""
from typing import Optional

from heritrace.utils.shacl_utils import determine_shape_for_subject
from heritrace.utils.sparql_utils import get_entity_types


def get_entity_shape(entity_uri: str) -> Optional[str]:
    """
    Get the SHACL shape for an entity by first retrieving its classes
    and then determining the appropriate shape.
    
    Args:
        entity_uri: URI of the entity
        
    Returns:
        The shape URI or None if no shape is found
    """
    entity_classes = get_entity_types(entity_uri)
    
    if entity_classes:
        return determine_shape_for_subject(entity_classes)
    
    return None
