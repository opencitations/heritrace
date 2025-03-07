"""
Unit tests for the get_inverse_references function in entity.py.
"""
import pytest
from unittest.mock import MagicMock, patch
from heritrace.routes.entity import get_inverse_references
from heritrace.utils.filters import Filter


@pytest.fixture
def mock_sparql():
    """Create a mock SPARQL client."""
    sparql_mock = MagicMock()
    sparql_mock.setQuery = MagicMock()
    sparql_mock.setReturnFormat = MagicMock()
    sparql_mock.query = MagicMock()
    return sparql_mock


@pytest.fixture
def mock_custom_filter():
    """Create a mock custom filter."""
    filter_mock = MagicMock(spec=Filter)
    return filter_mock


def test_get_inverse_references_virtuoso(mock_sparql, mock_custom_filter):
    """Test get_inverse_references when using Virtuoso."""
    # Setup
    subject_uri = "http://example.org/entity/1"
    mock_sparql.query().convert.return_value = {
        "results": {
            "bindings": [
                {
                    "s": {"value": "http://example.org/entity/2"},
                    "p": {"value": "http://example.org/predicate"},
                    "g": {"value": "http://example.org/graph"}
                }
            ]
        }
    }
    
    # Mock type query result
    def mock_query_convert():
        return {
            "results": {
                "bindings": [
                    {"type": {"value": "http://example.org/Person"}}
                ]
            }
        }
    
    mock_sparql.query().convert.side_effect = [
        mock_sparql.query().convert.return_value,  # First call for references
        mock_query_convert()  # Second call for types
    ]

    with patch('heritrace.routes.entity.get_sparql', return_value=mock_sparql), \
         patch('heritrace.routes.entity.get_custom_filter', return_value=mock_custom_filter), \
         patch('heritrace.routes.entity.is_virtuoso', True), \
         patch('heritrace.routes.entity.VIRTUOSO_EXCLUDED_GRAPHS', ['http://example.org/excluded']):
        
        # Execute
        result = get_inverse_references(subject_uri)
        
        # Verify
        assert len(result) == 1
        assert result[0]["subject"] == "http://example.org/entity/2"
        assert result[0]["predicate"] == "http://example.org/predicate"
        assert result[0]["types"] == ["http://example.org/Person"]
        
        # Verify SPARQL query contains Virtuoso-specific GRAPH clause
        mock_sparql.setQuery.assert_any_call(pytest.approx("""
        SELECT DISTINCT ?s ?p ?g WHERE {
            GRAPH ?g {
                ?s ?p <http://example.org/entity/1> .
            }
            FILTER(?g NOT IN (<http://example.org/excluded>))
            FILTER(?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
        }
        """, abs=1))


def test_get_inverse_references_non_virtuoso(mock_sparql, mock_custom_filter):
    """Test get_inverse_references when not using Virtuoso."""
    # Setup
    subject_uri = "http://example.org/entity/1"
    mock_sparql.query().convert.return_value = {
        "results": {
            "bindings": [
                {
                    "s": {"value": "http://example.org/entity/2"},
                    "p": {"value": "http://example.org/predicate"}
                }
            ]
        }
    }
    
    # Mock type query result
    def mock_query_convert():
        return {
            "results": {
                "bindings": [
                    {"type": {"value": "http://example.org/Person"}}
                ]
            }
        }
    
    mock_sparql.query().convert.side_effect = [
        mock_sparql.query().convert.return_value,  # First call for references
        mock_query_convert()  # Second call for types
    ]

    with patch('heritrace.routes.entity.get_sparql', return_value=mock_sparql), \
         patch('heritrace.routes.entity.get_custom_filter', return_value=mock_custom_filter), \
         patch('heritrace.routes.entity.is_virtuoso', False):
        
        # Execute
        result = get_inverse_references(subject_uri)
        
        # Verify
        assert len(result) == 1
        assert result[0]["subject"] == "http://example.org/entity/2"
        assert result[0]["predicate"] == "http://example.org/predicate"
        assert result[0]["types"] == ["http://example.org/Person"]
        
        # Verify SPARQL query does not contain Virtuoso-specific GRAPH clause
        mock_sparql.setQuery.assert_any_call(pytest.approx("""
        SELECT DISTINCT ?s ?p WHERE {
            ?s ?p <http://example.org/entity/1> .
            FILTER(?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
        }
        """, abs=1))


def test_get_inverse_references_no_results(mock_sparql, mock_custom_filter):
    """Test get_inverse_references when no references are found."""
    # Setup
    subject_uri = "http://example.org/entity/1"
    mock_sparql.query().convert.return_value = {
        "results": {
            "bindings": []
        }
    }

    with patch('heritrace.routes.entity.get_sparql', return_value=mock_sparql), \
         patch('heritrace.routes.entity.get_custom_filter', return_value=mock_custom_filter), \
         patch('heritrace.routes.entity.is_virtuoso', False):
        
        # Execute
        result = get_inverse_references(subject_uri)
        
        # Verify
        assert len(result) == 0


def test_get_inverse_references_multiple_types(mock_sparql, mock_custom_filter):
    """Test get_inverse_references when an entity has multiple types."""
    # Setup
    subject_uri = "http://example.org/entity/1"
    mock_sparql.query().convert.return_value = {
        "results": {
            "bindings": [
                {
                    "s": {"value": "http://example.org/entity/2"},
                    "p": {"value": "http://example.org/predicate"}
                }
            ]
        }
    }
    
    # Mock type query result with multiple types
    def mock_query_convert():
        return {
            "results": {
                "bindings": [
                    {"type": {"value": "http://example.org/Person"}},
                    {"type": {"value": "http://example.org/Employee"}}
                ]
            }
        }
    
    mock_sparql.query().convert.side_effect = [
        mock_sparql.query().convert.return_value,  # First call for references
        mock_query_convert()  # Second call for types
    ]

    with patch('heritrace.routes.entity.get_sparql', return_value=mock_sparql), \
         patch('heritrace.routes.entity.get_custom_filter', return_value=mock_custom_filter), \
         patch('heritrace.routes.entity.is_virtuoso', False), \
         patch('heritrace.routes.entity.get_highest_priority_class', 
               return_value="http://example.org/Person"):
        
        # Execute
        result = get_inverse_references(subject_uri)
        
        # Verify
        assert len(result) == 1
        assert result[0]["types"] == ["http://example.org/Person"]
        
        # Verify get_highest_priority_class was called with all types
        from heritrace.routes.entity import get_highest_priority_class
        get_highest_priority_class.assert_called_once_with(
            ["http://example.org/Person", "http://example.org/Employee"]
        )


def test_get_inverse_references_no_types(mock_sparql, mock_custom_filter):
    """Test get_inverse_references when an entity has no types."""
    # Setup
    subject_uri = "http://example.org/entity/1"
    mock_sparql.query().convert.return_value = {
        "results": {
            "bindings": [
                {
                    "s": {"value": "http://example.org/entity/2"},
                    "p": {"value": "http://example.org/predicate"}
                }
            ]
        }
    }
    
    # Mock type query result with no types
    def mock_query_convert():
        return {
            "results": {
                "bindings": []
            }
        }
    
    mock_sparql.query().convert.side_effect = [
        mock_sparql.query().convert.return_value,  # First call for references
        mock_query_convert()  # Second call for types
    ]

    with patch('heritrace.routes.entity.get_sparql', return_value=mock_sparql), \
         patch('heritrace.routes.entity.get_custom_filter', return_value=mock_custom_filter), \
         patch('heritrace.routes.entity.is_virtuoso', False), \
         patch('heritrace.routes.entity.get_highest_priority_class', return_value=None):
        
        # Execute
        result = get_inverse_references(subject_uri)
        
        # Verify
        assert len(result) == 1
        assert result[0]["types"] == [None]
