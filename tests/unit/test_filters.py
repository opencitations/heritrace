"""
Unit tests for the Filter class in heritrace/utils/filters.py.
"""
from unittest.mock import MagicMock, patch

import pytest
from heritrace.utils.filters import Filter
from rdflib import Graph


@pytest.fixture
def mock_filter():
    """Create a mock Filter instance."""
    context = {"example": "http://example.org/"}
    display_rules = [
        {
            "target": {
                "class": "http://example.org/Person",
                "shape": "http://example.org/PersonShape"
            },
            "displayName": "Person",
            "fetchUriDisplay": "SELECT ?name WHERE { [[uri]] <http://example.org/name> ?name }"
        }
    ]
    sparql_endpoint = "http://example.org/sparql"
    return Filter(context, display_rules, sparql_endpoint)


def test_get_fetch_uri_display_with_graph_success(mock_filter):
    """Test get_fetch_uri_display with a graph that returns results successfully."""
    # Setup
    uri = "http://example.org/person/1"
    rule = {
        "fetchUriDisplay": "SELECT ?name WHERE { <http://example.org/person/1> <http://example.org/name> ?name }"
    }
    
    # Create a mock graph that returns a result
    mock_graph = MagicMock(spec=Graph)
    mock_results = MagicMock()
    mock_results.__iter__.return_value = [("John Doe",)]
    mock_graph.query.return_value = mock_results
    
    with patch('heritrace.utils.display_rules_utils.find_matching_rule') as mock_find_rule:
        mock_find_rule.return_value = mock_filter.display_rules[0]
        
        # Execute
        result = mock_filter.get_fetch_uri_display(uri, rule, mock_graph)
    
    # Verify
    assert result == "John Doe"
    mock_graph.query.assert_called_once()


def test_get_fetch_uri_display_with_graph_exception(mock_filter):
    """Test get_fetch_uri_display with a graph that raises an exception."""
    # Setup
    uri = "http://example.org/person/1"
    rule = {
        "fetchUriDisplay": "SELECT ?name WHERE { <http://example.org/person/1> <http://example.org/name> ?name }"
    }
    
    # Create a mock graph that raises an exception
    mock_graph = MagicMock(spec=Graph)
    mock_graph.query.side_effect = Exception("Test exception")
    
    # Execute
    with patch('builtins.print') as mock_print:
        result = mock_filter.get_fetch_uri_display(uri, rule, mock_graph)
    
    # Verify
    assert result is None
    mock_graph.query.assert_called_once()
    mock_print.assert_called_once()
    assert "Error executing fetchUriDisplay query: Test exception" in mock_print.call_args[0][0]


def test_get_fetch_uri_display_with_sparql_success(mock_filter):
    """Test get_fetch_uri_display with SPARQL endpoint that returns results successfully."""
    # Setup
    uri = "http://example.org/person/1"
    rule = {
        "fetchUriDisplay": "SELECT ?name WHERE { <http://example.org/person/1> <http://example.org/name> ?name }"
    }
    
    # Mock the SPARQL query response
    mock_response = {
        "results": {
            "bindings": [
                {
                    "name": {"value": "John Doe"}
                }
            ]
        }
    }
    
    # Execute
    with patch.object(mock_filter.sparql, 'query') as mock_query:
        mock_query.return_value.convert.return_value = mock_response
        result = mock_filter.get_fetch_uri_display(uri, rule, None)
    
    # Verify
    assert result == "John Doe"
    mock_query.assert_called_once()


def test_get_fetch_uri_display_with_sparql_exception(mock_filter):
    """Test get_fetch_uri_display with SPARQL endpoint that raises an exception."""
    # Setup
    uri = "http://example.org/person/1"
    rule = {
        "fetchUriDisplay": "SELECT ?name WHERE { <http://example.org/person/1> <http://example.org/name> ?name }"
    }
    
    # Mock the SPARQL query response
    mock_response = {
        "results": {
            "bindings": [
                {
                    "name": {"value": "John Doe"}
                }
            ]
        }
    }
    
    # Execute
    with patch('heritrace.utils.display_rules_utils.find_matching_rule') as mock_find_rule:
        mock_find_rule.return_value = mock_filter.display_rules[0]
        
        with patch.object(mock_filter.sparql, 'query') as mock_query:
            mock_query.side_effect = Exception("Test exception")
            with patch('builtins.print') as mock_print:
                result = mock_filter.get_fetch_uri_display(uri, rule, None)
    
    # Verify
    assert result is None
    mock_query.assert_called_once()
    mock_print.assert_called_once()
    assert "Error executing fetchUriDisplay query: Test exception" in mock_print.call_args[0][0]


def test_get_fetch_uri_display_no_matching_class(mock_filter):
    """Test get_fetch_uri_display when no matching class is found."""
    # Setup
    uri = "http://example.org/person/1"
    rule = {}  # Empty rule with no fetchUriDisplay
    
    # Execute
    result = mock_filter.get_fetch_uri_display(uri, rule, None)
    
    # Verify
    assert result is None


def test_get_fetch_uri_display_no_fetch_uri_display(mock_filter):
    """Test get_fetch_uri_display when rule has no fetchUriDisplay."""
    # Setup
    uri = "http://example.org/person/1"
    rule = {}  # Empty rule with no fetchUriDisplay
    
    # Execute
    result = mock_filter.get_fetch_uri_display(uri, rule, None)
    
    # Verify
    assert result is None


def test_get_fetch_uri_display_sparql_no_results(mock_filter):
    """Test get_fetch_uri_display with SPARQL endpoint that returns no results."""
    # Setup
    uri = "http://example.org/person/1"
    rule = {
        "fetchUriDisplay": "SELECT ?name WHERE { <http://example.org/person/1> <http://example.org/name> ?name }"
    }
    
    # Mock the SPARQL query response with no bindings
    mock_response = {
        "results": {
            "bindings": []
        }
    }
    
    # Execute
    with patch.object(mock_filter.sparql, 'query') as mock_query:
        mock_query.return_value.convert.return_value = mock_response
        result = mock_filter.get_fetch_uri_display(uri, rule, None)
        
        # Verify
        assert result is None
        mock_query.assert_called_once()
        
        # Test with no results.bindings
        mock_response = {
            "results": {}
        }
        mock_query.reset_mock()
        with patch.object(mock_filter.sparql, 'query') as mock_query:
            mock_query.return_value.convert.return_value = mock_response
            result = mock_filter.get_fetch_uri_display(uri, rule, None)
        
        assert result is None
        mock_query.assert_called_once()


def test_human_readable_primary_source_none(mock_filter):
    """Test human_readable_primary_source when primary_source is None."""
    # Setup
    primary_source = None
    
    # Execute
    with patch('heritrace.utils.filters.lazy_gettext', return_value="Unknown") as mock_lazy_gettext:
        result = mock_filter.human_readable_primary_source(primary_source)
    
    # Verify
    assert result == "Unknown"
    mock_lazy_gettext.assert_called_once_with("Unknown")


def test_human_readable_primary_source_with_prov_se(mock_filter):
    """Test human_readable_primary_source when primary_source contains '/prov/se'."""
    # Setup
    primary_source = "http://example.org/prov/se/123"
    expected_version_url = "/entity-version/http://example.org/123"
    
    # Execute
    with patch('heritrace.utils.filters.lazy_gettext', side_effect=lambda x: x) as mock_lazy_gettext:
        result = mock_filter.human_readable_primary_source(primary_source)
    
    # Verify
    assert "Version 123" in result
    assert expected_version_url in result
    assert 'Link to the primary source description' in result
    # Check that lazy_gettext was called twice
    assert mock_lazy_gettext.call_count == 2


def test_human_readable_primary_source_valid_url(mock_filter):
    """Test human_readable_primary_source when primary_source is a valid URL."""
    # Setup
    primary_source = "http://example.org/resource/123"
    
    # Execute
    with patch('heritrace.utils.filters.validators.url', return_value=True) as mock_validators:
        with patch('heritrace.utils.filters.lazy_gettext', return_value="Link to the primary source description") as mock_lazy_gettext:
            result = mock_filter.human_readable_primary_source(primary_source)
    
    # Verify
    assert primary_source in result
    assert "alt='Link to the primary source description target='_blank'" in result
    assert 'href' in result
    mock_validators.assert_called_once_with(primary_source)
    mock_lazy_gettext.assert_called_once_with("Link to the primary source description")


def test_human_readable_primary_source_invalid_url(mock_filter):
    """Test human_readable_primary_source when primary_source is not a valid URL."""
    # Setup
    primary_source = "not a valid url"
    
    # Execute
    with patch('heritrace.utils.filters.validators.url', return_value=False) as mock_validators:
        result = mock_filter.human_readable_primary_source(primary_source)
    
    # Verify
    assert result == primary_source
    mock_validators.assert_called_once_with(primary_source)


def test_format_source_reference_none(mock_filter):
    """Test format_source_reference when url is None."""
    # Setup
    url = None
    
    # Execute
    result = mock_filter.format_source_reference(url)
    
    # Verify
    assert result == "Unknown"


def test_format_source_reference_empty(mock_filter):
    """Test format_source_reference when url is empty string."""
    # Setup
    url = ""
    
    # Execute
    result = mock_filter.format_source_reference(url)
    
    # Verify
    assert result == "Unknown"


def test_format_source_reference_zenodo_url(mock_filter):
    """Test format_source_reference when url is a Zenodo URL."""
    # Setup
    url = "https://zenodo.org/record/12345"
    
    # Execute
    with patch('heritrace.utils.filters.is_zenodo_url', return_value=True) as mock_is_zenodo:
        with patch('heritrace.utils.filters.format_zenodo_source', return_value="Formatted Zenodo Source") as mock_format_zenodo:
            result = mock_filter.format_source_reference(url)
    
    # Verify
    assert result == "Formatted Zenodo Source"
    mock_is_zenodo.assert_called_once_with(url)
    mock_format_zenodo.assert_called_once_with(url)


def test_format_source_reference_generic_url(mock_filter):
    """Test format_source_reference when url is a generic URL."""
    # Setup
    url = "http://example.org/resource/123"
    
    # Execute
    with patch('heritrace.utils.filters.is_zenodo_url', return_value=False) as mock_is_zenodo:
        with patch.object(mock_filter, 'human_readable_primary_source', return_value="Formatted Generic Source") as mock_human_readable:
            result = mock_filter.format_source_reference(url)
    
    # Verify
    assert result == "Formatted Generic Source"
    mock_is_zenodo.assert_called_once_with(url)
    mock_human_readable.assert_called_once_with(url)


def test_format_agent_reference_none(mock_filter):
    """Test format_agent_reference when url is None."""
    # Setup
    url = None
    
    # Execute
    result = mock_filter.format_agent_reference(url)
    
    # Verify
    assert result == "Unknown"


def test_format_agent_reference_empty(mock_filter):
    """Test format_agent_reference when url is empty string."""
    # Setup
    url = ""
    
    # Execute
    result = mock_filter.format_agent_reference(url)
    
    # Verify
    assert result == "Unknown"


def test_format_agent_reference_orcid_url(mock_filter):
    """Test format_agent_reference when url is an ORCID URL."""
    # Setup
    url = "https://orcid.org/0000-0001-2345-6789"
    
    # Execute
    with patch('heritrace.utils.filters.is_orcid_url', return_value=True) as mock_is_orcid:
        with patch('heritrace.utils.filters.format_orcid_attribution', return_value="Formatted ORCID Attribution") as mock_format_orcid:
            result = mock_filter.format_agent_reference(url)
    
    # Verify
    assert result == "Formatted ORCID Attribution"
    mock_is_orcid.assert_called_once_with(url)
    mock_format_orcid.assert_called_once_with(url)


def test_format_agent_reference_generic_url(mock_filter):
    """Test format_agent_reference when url is a generic URL."""
    # Setup
    url = "http://example.org/person/123"
    
    # Execute
    with patch('heritrace.utils.filters.is_orcid_url', return_value=False) as mock_is_orcid:
        with patch('heritrace.utils.filters.validators.url', return_value=True) as mock_validators:
            result = mock_filter.format_agent_reference(url)
    
    # Verify
    assert f'<a href="{url}" target="_blank">{url}</a>' == result
    mock_is_orcid.assert_called_once_with(url)
    mock_validators.assert_called_once_with(url)


def test_format_agent_reference_not_url(mock_filter):
    """Test format_agent_reference when url is not a valid URL."""
    # Setup
    url = "not a valid url"
    
    # Execute
    with patch('heritrace.utils.filters.is_orcid_url', return_value=False) as mock_is_orcid:
        with patch('heritrace.utils.filters.validators.url', return_value=False) as mock_validators:
            result = mock_filter.format_agent_reference(url)
    
    # Verify
    assert result == url
    mock_is_orcid.assert_called_once_with(url)
    mock_validators.assert_called_once_with(url) 


def test_human_readable_entity_with_display_name(mock_filter):
    """Test human_readable_entity when rule has a displayName property."""
    uri = "http://example.org/person/1"
    entity_key = ("http://example.org/Person", "http://example.org/PersonShape")
    rule = {
        "displayName": "Custom Person Display Name"
    }
    
    with patch('heritrace.utils.display_rules_utils.find_matching_rule') as mock_find_rule:
        mock_find_rule.return_value = rule
        result = mock_filter.human_readable_entity(uri, entity_key)
    
    assert result == "Custom Person Display Name"
    mock_find_rule.assert_called_once_with(entity_key[0], entity_key[1], mock_filter.display_rules)


def test_human_readable_entity_with_fetch_uri_display(mock_filter):
    """Test human_readable_entity when rule has a fetchUriDisplay property and it returns a result."""
    # Setup
    uri = "http://example.org/person/1"
    entity_key = ("http://example.org/Person", "http://example.org/PersonShape")
    rule = {
        "fetchUriDisplay": "SELECT ?name WHERE { <http://example.org/person/1> <http://example.org/name> ?name }"
    }
    
    with patch('heritrace.utils.display_rules_utils.find_matching_rule') as mock_find_rule:
        mock_find_rule.return_value = rule
        with patch.object(mock_filter, 'get_fetch_uri_display', return_value="John Doe") as mock_get_fetch:
            result = mock_filter.human_readable_entity(uri, entity_key)
    
    assert result == "John Doe"
    mock_find_rule.assert_called_once_with(entity_key[0], entity_key[1], mock_filter.display_rules)
    mock_get_fetch.assert_called_once_with(uri, rule, None)


def test_human_readable_entity_with_fetch_uri_display_no_result(mock_filter):
    """Test human_readable_entity when rule has a fetchUriDisplay property but it returns no result."""
    uri = "http://example.org/person/1"
    entity_key = ("http://example.org/Person", "http://example.org/PersonShape")
    rule = {
        "fetchUriDisplay": "SELECT ?name WHERE { <http://example.org/person/1> <http://example.org/name> ?name }",
        "displayName": "Person Display Name"
    }
    
    with patch('heritrace.utils.display_rules_utils.find_matching_rule') as mock_find_rule:
        mock_find_rule.return_value = rule
        with patch.object(mock_filter, 'get_fetch_uri_display', return_value=None) as mock_get_fetch:
            result = mock_filter.human_readable_entity(uri, entity_key)
    
    assert result == "Person Display Name"
    mock_find_rule.assert_called_once_with(entity_key[0], entity_key[1], mock_filter.display_rules)
    mock_get_fetch.assert_called_once_with(uri, rule, None)


def test_human_readable_entity_no_rule(mock_filter):
    """Test human_readable_entity when no matching rule is found."""
    uri = "http://example.org/person/1"
    entity_key = ("http://example.org/Person", "http://example.org/PersonShape")
    
    with patch('heritrace.utils.display_rules_utils.find_matching_rule') as mock_find_rule:
        mock_find_rule.return_value = None
        result = mock_filter.human_readable_entity(uri, entity_key)
    
    assert result == uri
    mock_find_rule.assert_called_once_with(entity_key[0], entity_key[1], mock_filter.display_rules)


def test_human_readable_entity_rule_without_display_or_fetch(mock_filter):
    """Test human_readable_entity when rule has neither displayName nor fetchUriDisplay properties."""
    uri = "http://example.org/person/1"
    entity_key = ("http://example.org/Person", "http://example.org/PersonShape")
    rule = {}  # Empty rule without displayName or fetchUriDisplay
    
    with patch('heritrace.utils.display_rules_utils.find_matching_rule') as mock_find_rule:
        mock_find_rule.return_value = rule
        result = mock_filter.human_readable_entity(uri, entity_key)
    
    assert result == uri
    mock_find_rule.assert_called_once_with(entity_key[0], entity_key[1], mock_filter.display_rules)