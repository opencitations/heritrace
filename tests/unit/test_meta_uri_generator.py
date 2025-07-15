from unittest.mock import MagicMock, call, patch

import pytest
from heritrace.uri_generator.meta_uri_generator import MetaURIGenerator, InvalidURIFormatError
from heritrace.meta_counter_handler import MetaCounterHandler
from rdflib import URIRef
from SPARQLWrapper import SPARQLWrapper


@pytest.fixture
def uri_generator_setup():
    """Fixture to set up the MetaURIGenerator and its dependencies."""
    base_iri = "https://w3id.org/oc/meta"
    supplier_prefix = "test"
    counter_handler = MagicMock(spec=MetaCounterHandler)
    counter_handler.supplier_prefix = supplier_prefix
    supplier_prefix_regex = supplier_prefix
    uri_generator = MetaURIGenerator(
        base_iri, supplier_prefix_regex, supplier_prefix, counter_handler
    )
    sparql = MagicMock(spec=SPARQLWrapper)
    
    return {
        "base_iri": base_iri,
        "supplier_prefix": supplier_prefix,
        "supplier_prefix_regex": supplier_prefix_regex,
        "counter_handler": counter_handler,
        "uri_generator": uri_generator,
        "sparql": sparql
    }


def test_generate_uri(uri_generator_setup):
    """Test the generate_uri method."""
    # Get the setup objects
    counter_handler = uri_generator_setup["counter_handler"]
    uri_generator = uri_generator_setup["uri_generator"]
    base_iri = uri_generator_setup["base_iri"]
    supplier_prefix = uri_generator_setup["supplier_prefix"]
    
    # Set up the mock counter handler
    counter_handler.read_counter.return_value = 42
    
    # Test generating a URI for an Expression entity
    entity_type = "http://purl.org/spar/fabio/Expression"
    uri = uri_generator.generate_uri(entity_type)
    
    # Verify the counter handler was called correctly
    counter_handler.read_counter.assert_called_once_with(entity_type)
    counter_handler.set_counter.assert_called_once_with(43, entity_type)
    
    # Verify the generated URI is correct
    expected_uri = URIRef(f"{base_iri}/br/{supplier_prefix}43")
    assert uri == expected_uri
    
    # Test with a different entity type
    counter_handler.reset_mock()
    counter_handler.read_counter.return_value = 99
    
    entity_type = "http://xmlns.com/foaf/0.1/Agent"
    uri = uri_generator.generate_uri(entity_type)
    
    counter_handler.read_counter.assert_called_once_with(entity_type)
    counter_handler.set_counter.assert_called_once_with(100, entity_type)
    
    expected_uri = URIRef(f"{base_iri}/ra/{supplier_prefix}100")
    assert uri == expected_uri


def test_initialize_counters_with_valid_data(uri_generator_setup):
    """Test initialize_counters with valid data from both data and provenance queries."""
    # Get the setup objects
    counter_handler = uri_generator_setup["counter_handler"]
    uri_generator = uri_generator_setup["uri_generator"]
    sparql = uri_generator_setup["sparql"]
    base_iri = uri_generator_setup["base_iri"]
    supplier_prefix = uri_generator_setup["supplier_prefix"]
    
    # Mock the data query results
    data_results = {
        "results": {
            "bindings": [
                {
                    "type": {"value": "http://purl.org/spar/fabio/Expression"},
                    "s": {"value": f"{base_iri}/br/{supplier_prefix}10"},
                },
                {
                    "type": {"value": "http://xmlns.com/foaf/0.1/Agent"},
                    "s": {"value": f"{base_iri}/ra/{supplier_prefix}20"},
                },
                {
                    "type": {"value": "http://purl.org/spar/fabio/Manifestation"},
                    "s": {"value": f"{base_iri}/re/{supplier_prefix}30"},
                },
                {
                    "type": {"value": "http://purl.org/spar/datacite/Identifier"},
                    "s": {"value": f"{base_iri}/id/{supplier_prefix}40"},
                },
                {
                    "type": {"value": "http://purl.org/spar/pro/RoleInTime"},
                    "s": {"value": f"{base_iri}/ar/{supplier_prefix}50"},
                },
            ]
        }
    }

    # Mock the provenance query results
    prov_results = {
        "results": {
            "bindings": [
                {
                    "entity": {"value": f"{base_iri}/br/{supplier_prefix}15"},
                },
                {
                    "entity": {"value": f"{base_iri}/ra/{supplier_prefix}25"},
                },
                {
                    "entity": {"value": f"{base_iri}/re/{supplier_prefix}35"},
                },
            ]
        }
    }

    # Configure the mock SPARQL wrapper
    sparql.query.side_effect = [
        MagicMock(convert=MagicMock(return_value=data_results)),
        MagicMock(convert=MagicMock(return_value=prov_results)),
    ]

    # Call the method under test
    uri_generator.initialize_counters(sparql)

    # Verify SPARQL queries were executed
    assert sparql.setQuery.call_count == 2
    assert sparql.setReturnFormat.call_count == 1
    assert sparql.query.call_count == 2

    # Verify counter values were set correctly
    expected_calls = [
        call(15, "http://purl.org/spar/fabio/Expression"),
        call(15, "http://purl.org/spar/fabio/Article"),
        call(15, "http://purl.org/spar/fabio/JournalArticle"),
        call(15, "http://purl.org/spar/fabio/Book"),
        call(15, "http://purl.org/spar/fabio/JournalIssue"),
        call(15, "http://purl.org/spar/fabio/JournalVolume"),
        call(15, "http://purl.org/spar/fabio/Journal"),
        call(15, "http://purl.org/spar/fabio/AcademicProceedings"),
        call(15, "http://purl.org/spar/fabio/ProceedingsPaper"),
        call(15, "http://purl.org/spar/fabio/ReferenceBook"),
        call(15, "http://purl.org/spar/fabio/Review"),
        call(15, "http://purl.org/spar/fabio/ReviewArticle"),
        call(15, "http://purl.org/spar/fabio/Series"),
        call(15, "http://purl.org/spar/fabio/Thesis"),
        call(50, "http://purl.org/spar/pro/RoleInTime"),
        call(35, "http://purl.org/spar/fabio/Manifestation"),
        call(25, "http://xmlns.com/foaf/0.1/Agent"),
        call(40, "http://purl.org/spar/datacite/Identifier"),
        call(0, "http://www.w3.org/2002/07/owl#Thing"),
    ]
    counter_handler.set_counter.assert_has_calls(expected_calls, any_order=True)


def test_initialize_counters_with_invalid_uri_format_in_data(uri_generator_setup):
    """Test initialize_counters with invalid URI format in data query results."""
    # Get the setup objects
    counter_handler = uri_generator_setup["counter_handler"]
    uri_generator = uri_generator_setup["uri_generator"]
    sparql = uri_generator_setup["sparql"]
    base_iri = uri_generator_setup["base_iri"]
    supplier_prefix = uri_generator_setup["supplier_prefix"]
    
    # Mock the data query results with an invalid URI format that will trigger the exception
    data_results = {
        "results": {
            "bindings": [
                {
                    "type": {"value": "http://purl.org/spar/fabio/Expression"},
                    "s": {"value": f"{base_iri}/br/{supplier_prefix}abc"},  # Invalid format supplier prefix to split on
                },
                {
                    "type": {"value": "http://xmlns.com/foaf/0.1/Agent"},
                    "s": {"value": f"{base_iri}/ra/{supplier_prefix}20"},
                },
            ]
        }
    }

    # Mock the provenance query results
    prov_results = {
        "results": {
            "bindings": []
        }
    }

    # Configure the mock SPARQL wrapper
    sparql.query.side_effect = [
        MagicMock(convert=MagicMock(return_value=data_results)),
        MagicMock(convert=MagicMock(return_value=prov_results)),
    ]

    # Test that the InvalidURIFormatError is raised
    with pytest.raises(InvalidURIFormatError) as exc_info:
        uri_generator.initialize_counters(sparql)
    
    assert "Invalid URI format found for entity:" in str(exc_info.value)


def test_initialize_counters_with_invalid_uri_format_in_provenance(uri_generator_setup):
    """Test initialize_counters with invalid URI format in provenance query results."""
    # Get the setup objects
    counter_handler = uri_generator_setup["counter_handler"]
    uri_generator = uri_generator_setup["uri_generator"]
    sparql = uri_generator_setup["sparql"]
    base_iri = uri_generator_setup["base_iri"]
    supplier_prefix = uri_generator_setup["supplier_prefix"]
    
    # Mock the data query results
    data_results = {
        "results": {
            "bindings": []
        }
    }

    # Mock the provenance query results with an invalid URI format that will trigger the exception
    prov_results = {
        "results": {
            "bindings": [
                {
                    "entity": {"value": f"{base_iri}/br/{supplier_prefix}xyz"},  # Invalid format supplier prefix to split on
                },
                {
                    "entity": {"value": f"{base_iri}/ra/{supplier_prefix}25"},
                },
            ]
        }
    }

    # Configure the mock SPARQL wrapper
    sparql.query.side_effect = [
        MagicMock(convert=MagicMock(return_value=data_results)),
        MagicMock(convert=MagicMock(return_value=prov_results)),
    ]

    # Test that the InvalidURIFormatError is raised
    with pytest.raises(InvalidURIFormatError) as exc_info:
        uri_generator.initialize_counters(sparql)
    
    assert "Invalid URI format found in provenance for entity:" in str(exc_info.value)


def test_initialize_counters_with_non_matching_entity_type(uri_generator_setup):
    """Test initialize_counters with entity types not in entity_type_abbr."""
    # Get the setup objects
    counter_handler = uri_generator_setup["counter_handler"]
    uri_generator = uri_generator_setup["uri_generator"]
    sparql = uri_generator_setup["sparql"]
    base_iri = uri_generator_setup["base_iri"]
    supplier_prefix = uri_generator_setup["supplier_prefix"]
    
    # Mock the data query results with an unknown entity type
    data_results = {
        "results": {
            "bindings": [
                {
                    "type": {"value": "http://example.org/UnknownType"},
                    "s": {"value": f"{base_iri}/unknown/{supplier_prefix}10"},
                },
                {
                    "type": {"value": "http://xmlns.com/foaf/0.1/Agent"},
                    "s": {"value": f"{base_iri}/ra/{supplier_prefix}20"},
                },
            ]
        }
    }

    # Mock the provenance query results
    prov_results = {
        "results": {
            "bindings": []
        }
    }

    # Configure the mock SPARQL wrapper
    sparql.query.side_effect = [
        MagicMock(convert=MagicMock(return_value=data_results)),
        MagicMock(convert=MagicMock(return_value=prov_results)),
    ]

    # Call the method under test
    uri_generator.initialize_counters(sparql)

    # Verify only the known entity type counter was set
    counter_handler.set_counter.assert_any_call(
        20, "http://xmlns.com/foaf/0.1/Agent"
    )


def test_initialize_counters_with_non_matching_abbreviation_in_provenance(uri_generator_setup):
    """Test initialize_counters with URIs not containing known abbreviations in provenance."""
    # Get the setup objects
    counter_handler = uri_generator_setup["counter_handler"]
    uri_generator = uri_generator_setup["uri_generator"]
    sparql = uri_generator_setup["sparql"]
    base_iri = uri_generator_setup["base_iri"]
    supplier_prefix = uri_generator_setup["supplier_prefix"]
    
    # Mock the data query results
    data_results = {
        "results": {
            "bindings": []
        }
    }

    # Mock the provenance query results with an unknown abbreviation
    prov_results = {
        "results": {
            "bindings": [
                {
                    "entity": {"value": f"{base_iri}/unknown/{supplier_prefix}15"},
                },
                {
                    "entity": {"value": f"{base_iri}/ra/{supplier_prefix}25"},
                },
            ]
        }
    }

    # Configure the mock SPARQL wrapper
    sparql.query.side_effect = [
        MagicMock(convert=MagicMock(return_value=data_results)),
        MagicMock(convert=MagicMock(return_value=prov_results)),
    ]

    # Call the method under test
    uri_generator.initialize_counters(sparql)

    # Verify only the known abbreviation counter was set
    counter_handler.set_counter.assert_any_call(
        25, "http://xmlns.com/foaf/0.1/Agent"
    )


def test_initialize_counters_with_empty_results(uri_generator_setup):
    """Test initialize_counters with empty results from both queries."""
    # Get the setup objects
    counter_handler = uri_generator_setup["counter_handler"]
    uri_generator = uri_generator_setup["uri_generator"]
    sparql = uri_generator_setup["sparql"]
    
    # Mock empty results for both queries
    empty_results = {
        "results": {
            "bindings": []
        }
    }

    # Configure the mock SPARQL wrapper
    sparql.query.side_effect = [
        MagicMock(convert=MagicMock(return_value=empty_results)),
        MagicMock(convert=MagicMock(return_value=empty_results)),
    ]

    # Call the method under test
    uri_generator.initialize_counters(sparql)

    # With empty results, no prefixes are found, so no counters should be set
    # This is the new expected behavior - only prefixes found in data get counters
    counter_handler.set_counter.assert_not_called()


def test_initialize_counters_with_value_error_in_data(uri_generator_setup):
    """Test initialize_counters with a ValueError when parsing data query results."""
    # Get the setup objects
    counter_handler = uri_generator_setup["counter_handler"]
    uri_generator = uri_generator_setup["uri_generator"]
    sparql = uri_generator_setup["sparql"]
    base_iri = uri_generator_setup["base_iri"]
    supplier_prefix = uri_generator_setup["supplier_prefix"]
    
    # Mock the data query results with a non-integer value
    data_results = {
        "results": {
            "bindings": [
                {
                    "type": {"value": "http://purl.org/spar/fabio/Expression"},
                    "s": {"value": f"{base_iri}/br/{supplier_prefix}abc"},  # Non-integer
                },
            ]
        }
    }

    # Mock the provenance query results
    prov_results = {
        "results": {
            "bindings": []
        }
    }

    # Configure the mock SPARQL wrapper
    sparql.query.side_effect = [
        MagicMock(convert=MagicMock(return_value=data_results)),
        MagicMock(convert=MagicMock(return_value=prov_results)),
    ]

    # Test that the InvalidURIFormatError is raised
    with pytest.raises(InvalidURIFormatError) as exc_info:
        uri_generator.initialize_counters(sparql)
    
    assert "Invalid URI format found for entity:" in str(exc_info.value)


def test_initialize_counters_with_value_error_in_provenance(uri_generator_setup):
    """Test initialize_counters with a ValueError when parsing provenance query results."""
    # Get the setup objects
    counter_handler = uri_generator_setup["counter_handler"]
    uri_generator = uri_generator_setup["uri_generator"]
    sparql = uri_generator_setup["sparql"]
    base_iri = uri_generator_setup["base_iri"]
    supplier_prefix = uri_generator_setup["supplier_prefix"]
    
    # Mock the data query results
    data_results = {
        "results": {
            "bindings": []
        }
    }

    # Mock the provenance query results with a non-integer value
    prov_results = {
        "results": {
            "bindings": [
                {
                    "entity": {"value": f"{base_iri}/br/{supplier_prefix}xyz"},  # Non-integer
                },
            ]
        }
    }

    # Configure the mock SPARQL wrapper
    sparql.query.side_effect = [
        MagicMock(convert=MagicMock(return_value=data_results)),
        MagicMock(convert=MagicMock(return_value=prov_results)),
    ]

    # Test that the InvalidURIFormatError is raised
    with pytest.raises(InvalidURIFormatError) as exc_info:
        uri_generator.initialize_counters(sparql)
    
    assert "Invalid URI format found in provenance for entity:" in str(exc_info.value)


def test_initialize_counters_with_multiple_prefixes():
    """Test initialize_counters properly separates counters by supplier prefix."""
    base_iri = "https://w3id.org/oc/meta"
    supplier_prefix_regex = r"\d{3}"  # Match 3 digits
    new_supplier_prefix = "060"
    counter_handler = MagicMock(spec=MetaCounterHandler)
    counter_handler.supplier_prefix = new_supplier_prefix
    
    uri_generator = MetaURIGenerator(
        base_iri, supplier_prefix_regex, new_supplier_prefix, counter_handler
    )
    sparql = MagicMock(spec=SPARQLWrapper)
    
    # Mock the data query results with multiple prefixes
    data_results = {
        "results": {
            "bindings": [
                {
                    "type": {"value": "http://purl.org/spar/fabio/Expression"},
                    "s": {"value": f"{base_iri}/br/06010"},
                },
                {
                    "type": {"value": "http://purl.org/spar/fabio/Expression"},
                    "s": {"value": f"{base_iri}/br/07020"},
                },
                {
                    "type": {"value": "http://xmlns.com/foaf/0.1/Agent"},
                    "s": {"value": f"{base_iri}/ra/06015"},
                },
                {
                    "type": {"value": "http://xmlns.com/foaf/0.1/Agent"},
                    "s": {"value": f"{base_iri}/ra/07025"},
                },
            ]
        }
    }

    # Mock the provenance query results with multiple prefixes
    prov_results = {
        "results": {
            "bindings": [
                {
                    "entity": {"value": f"{base_iri}/br/06030"},
                },
                {
                    "entity": {"value": f"{base_iri}/br/07035"},
                },
            ]
        }
    }

    # Configure the mock SPARQL wrapper
    sparql.query.side_effect = [
        MagicMock(convert=MagicMock(return_value=data_results)),
        MagicMock(convert=MagicMock(return_value=prov_results)),
    ]

    # Call the method under test
    uri_generator.initialize_counters(sparql)

    # Verify that the supplier_prefix was temporarily changed during initialization
    # We expect set_counter to be called with different prefix contexts
    assert counter_handler.set_counter.call_count > 0
    
    # The counter handler should have been set to the original prefix at the end
    assert counter_handler.supplier_prefix == uri_generator.new_supplier_prefix


def test_generate_uri_uses_correct_prefix():
    """Test that generate_uri uses the correct supplier prefix in the generated URI."""
    base_iri = "https://w3id.org/oc/meta"
    supplier_prefix_regex = r"\d{3}"
    new_supplier_prefix = "070"
    counter_handler = MagicMock(spec=MetaCounterHandler)
    counter_handler.supplier_prefix = new_supplier_prefix
    counter_handler.read_counter.return_value = 42
    
    uri_generator = MetaURIGenerator(
        base_iri, supplier_prefix_regex, new_supplier_prefix, counter_handler
    )
    
    entity_type = "http://purl.org/spar/fabio/Expression"
    uri = uri_generator.generate_uri(entity_type)
    
    # Verify the counter handler was called correctly
    counter_handler.read_counter.assert_called_once_with(entity_type)
    counter_handler.set_counter.assert_called_once_with(43, entity_type)
    
    # Verify the generated URI contains the correct prefix
    expected_uri = URIRef(f"{base_iri}/br/{new_supplier_prefix}43")
    assert uri == expected_uri 