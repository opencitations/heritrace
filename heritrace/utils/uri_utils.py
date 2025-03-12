from flask import current_app
from rdflib import URIRef


def generate_unique_uri(entity_type: URIRef | str = None) -> URIRef:
    """
    Generate a unique URI for a given entity type using the application's URI generator.
    The counter increment is handled internally by the URI generator.
    
    Args:
        entity_type: The type of entity to generate a URI for
        
    Returns:
        URIRef: The generated unique URI
    """
    entity_type = str(entity_type)
    uri = current_app.config["URI_GENERATOR"].generate_uri(entity_type)
    return URIRef(uri) 