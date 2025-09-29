from flask import current_app
from rdflib import URIRef


def generate_unique_uri(entity_type: URIRef | str = None, context_data: dict = None) -> URIRef:
    """
    Generate a unique URI for a given entity type using the application's URI generator.
    The counter increment is handled internally by the URI generator.

    Args:
        entity_type: The type of entity to generate a URI for
        context_data: Additional context data for special URI generation (e.g., Citation entities)

    Returns:
        URIRef: The generated unique URI
    """
    entity_type = str(entity_type)
    uri = current_app.config["URI_GENERATOR"].generate_uri(entity_type, context_data)
    return URIRef(uri) 