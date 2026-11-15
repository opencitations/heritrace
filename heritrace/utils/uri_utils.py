# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from urllib.parse import urlparse

import validators
from rdflib import URIRef


def generate_unique_uri(
    entity_type: str | None = None, context_data: dict | None = None
) -> URIRef:
    """
    Generate a unique URI for a given entity type using the application's URI generator.
    The counter increment is handled internally by the URI generator.

    Args:
        entity_type: The type of entity to generate a URI for
        context_data: Additional context data for special URI generation (e.g., Citation
        entities)

    Returns:
        URIRef: The generated unique URI
    """
    entity_type = str(entity_type)
    from heritrace.extensions import get_uri_generator  # noqa: PLC0415

    uri = get_uri_generator().generate_uri(entity_type, context_data)
    return URIRef(uri)


# What HERITRACE takes as an IRI: a scheme and no spaces.
def is_iri(value: str) -> bool:
    parsed = urlparse(value)
    return bool(parsed.scheme) and not any(char.isspace() for char in value)


def is_valid_url(value: str | None) -> bool:
    return bool(value and validators.url(value))  # type: ignore[arg-type]
