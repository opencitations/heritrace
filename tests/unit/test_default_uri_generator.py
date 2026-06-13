# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from unittest.mock import MagicMock

import pytest
from rdflib import URIRef
from SPARQLWrapper import SPARQLWrapper

from heritrace.uri_generator.default_uri_generator import DefaultURIGenerator


@pytest.fixture
def uri_generator_setup():
    """Fixture to set up the DefaultURIGenerator and its dependencies."""
    base_iri = "https://example.org"
    uri_generator = DefaultURIGenerator(base_iri)
    sparql = MagicMock(spec=SPARQLWrapper)

    return {"base_iri": base_iri, "uri_generator": uri_generator, "sparql": sparql}


def test_initialize_counters(uri_generator_setup) -> None:
    """
    Test the initialize_counters method of DefaultURIGenerator.

    Since DefaultURIGenerator uses UUIDs and doesn't need counter initialization,
    this test verifies that the method can be called without errors but doesn't
    perform any actual operations.
    """
    # Get the setup objects
    uri_generator = uri_generator_setup["uri_generator"]
    sparql = uri_generator_setup["sparql"]

    # Call the method
    uri_generator.initialize_counters(sparql)

    # Verify that no operations were performed on the sparql object
    sparql.assert_not_called()


def test_generate_uri(uri_generator_setup) -> None:
    """Test the generate_uri method of DefaultURIGenerator."""
    # Get the setup objects
    uri_generator = uri_generator_setup["uri_generator"]
    base_iri = uri_generator_setup["base_iri"]

    # Generate a URI
    uri = uri_generator.generate_uri()

    # Verify the URI format
    assert isinstance(uri, URIRef)
    assert str(uri).startswith(f"{base_iri}/")

    # The rest of the URI should be a UUID (32 hex characters)
    uuid_part = str(uri).replace(f"{base_iri}/", "")
    assert len(uuid_part) == 32
    # Check that it's a valid hex string
    int(uuid_part, 16)

    # Generate another URI and verify it's different
    uri2 = uri_generator.generate_uri()
    assert uri != uri2


def test_base_iri_from_environment(monkeypatch) -> None:
    """DefaultURIGenerator falls back to the BASE_IRI environment variable."""
    base_iri = "https://example.org/from-env"
    monkeypatch.setenv("BASE_IRI", base_iri)

    uri_generator = DefaultURIGenerator()

    assert uri_generator.base_iri == base_iri

    uri = uri_generator.generate_uri()
    assert str(uri).startswith(f"{base_iri}/")
    uuid_part = str(uri).replace(f"{base_iri}/", "")
    assert len(uuid_part) == 32
    int(uuid_part, 16)
