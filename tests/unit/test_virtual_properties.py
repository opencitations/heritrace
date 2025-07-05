"""
Unit tests for virtual properties functionality.

This module tests the virtual properties utilities which allow entities
to display computed or derived relationships.
"""

import pytest
from unittest.mock import MagicMock, patch

from rdflib import Graph, Literal, URIRef
from SPARQLWrapper import JSON

from heritrace.utils.virtual_properties import (
    fetch_virtual_property_values,
    fetch_virtual_property_values_from_graph,
    fetch_virtual_property_values_from_sparql,
    process_virtual_properties
)


class TestProcessVirtualProperties:
    """Test the main virtual properties processing function."""

    def test_process_virtual_properties_no_rule(self):
        """Test processing when no rule is provided."""
        result = process_virtual_properties("http://example.com/entity", None)
        assert result == []

    def test_process_virtual_properties_empty_rule(self):
        """Test processing with empty rule."""
        rule = {"displayProperties": []}
        result = process_virtual_properties("http://example.com/entity", rule)
        assert result == []

    def test_process_virtual_properties_no_virtual_properties(self):
        """Test processing when rule has no virtual properties."""
        rule = {
            "displayProperties": [
                {"property": "http://example.com/prop1"}
            ]
        }
        result = process_virtual_properties("http://example.com/entity", rule)
        assert result == []

    @patch('heritrace.utils.virtual_properties.fetch_virtual_property_values')
    def test_process_virtual_properties_with_virtual_property(self, mock_fetch):
        """Test processing with a valid virtual property."""
        mock_fetch.return_value = [URIRef("http://example.com/target1"), URIRef("http://example.com/target2")]
        
        rule = {
            "displayProperties": [
                {
                    "virtual_property": "http://example.com/virtual_prop",
                    "implementedVia": {
                        "class": "http://example.com/IntermediateClass",
                        "sourceProperty": "http://example.com/sourceProperty",
                        "targetProperty": "http://example.com/targetProperty"
                    }
                }
            ]
        }
        
        result = process_virtual_properties("http://example.com/entity", rule)
        
        assert len(result) == 2
        assert result[0] == (URIRef("http://example.com/entity"), URIRef("http://example.com/virtual_prop"), URIRef("http://example.com/target1"))
        assert result[1] == (URIRef("http://example.com/entity"), URIRef("http://example.com/virtual_prop"), URIRef("http://example.com/target2"))
        
        mock_fetch.assert_called_once_with(
            "http://example.com/entity",
            {
                "class": "http://example.com/IntermediateClass",
                "sourceProperty": "http://example.com/sourceProperty",
                "targetProperty": "http://example.com/targetProperty"
            },
            None
        )

    @patch('heritrace.utils.virtual_properties.fetch_virtual_property_values')
    def test_process_virtual_properties_mixed_properties(self, mock_fetch):
        """Test processing with both virtual and regular properties."""
        mock_fetch.return_value = [URIRef("http://example.com/target")]
        
        rule = {
            "displayProperties": [
                {"property": "http://example.com/regular_prop"},
                {
                    "virtual_property": "http://example.com/virtual_prop",
                    "implementedVia": {
                        "class": "http://example.com/IntermediateClass",
                        "sourceProperty": "http://example.com/sourceProperty",
                        "targetProperty": "http://example.com/targetProperty"
                    }
                }
            ]
        }
        
        result = process_virtual_properties("http://example.com/entity", rule)
        
        assert len(result) == 1
        assert result[0] == (URIRef("http://example.com/entity"), URIRef("http://example.com/virtual_prop"), URIRef("http://example.com/target"))


class TestFetchVirtualPropertyValues:
    """Test the virtual property values fetching function."""

    def test_fetch_virtual_property_values_with_historical_snapshot(self):
        """Test fetching values with historical snapshot."""
        mock_graph = MagicMock()
        
        # Mock the subjects method to return intermediate entities
        intermediate = URIRef("http://example.com/intermediate1")
        mock_graph.subjects.return_value = [intermediate]
        
        # Mock the __contains__ method for graph containment check
        def mock_contains(*args):
            if len(args) == 1:
                triple = args[0]
            else:
                triple = args[1] if len(args) > 1 else args[0]
                
            return (triple[0] == intermediate and 
                   triple[1] == URIRef("http://example.com/sourceProperty") and
                   triple[2] == URIRef("http://example.com/entity"))
        
        mock_graph.__contains__ = mock_contains
        
        # Mock the objects method to return target values
        mock_graph.objects = lambda subject, predicate, unique=True: [URIRef("http://example.com/target")]
        
        implementation = {
            "class": "http://example.com/IntermediateClass",
            "sourceProperty": "http://example.com/sourceProperty",
            "targetProperty": "http://example.com/targetProperty"
        }
        
        result = fetch_virtual_property_values("http://example.com/entity", implementation, mock_graph)
        
        assert result == [URIRef("http://example.com/target")]

    @patch('heritrace.utils.virtual_properties.fetch_virtual_property_values_from_sparql')
    def test_fetch_virtual_property_values_with_sparql(self, mock_fetch_sparql):
        """Test fetching values using SPARQL."""
        mock_fetch_sparql.return_value = [URIRef("http://example.com/target")]
        
        implementation = {
            "class": "http://example.com/IntermediateClass",
            "sourceProperty": "http://example.com/sourceProperty",
            "targetProperty": "http://example.com/targetProperty"
        }
        
        result = fetch_virtual_property_values("http://example.com/entity", implementation)
        
        assert result == [URIRef("http://example.com/target")]
        mock_fetch_sparql.assert_called_once_with(
            "http://example.com/entity",
            "http://example.com/IntermediateClass",
            "http://example.com/sourceProperty",
            "http://example.com/targetProperty"
        )


class TestFetchVirtualPropertyValuesFromSparql:
    """Test the SPARQL-based virtual property values fetching function."""

    @patch('heritrace.utils.virtual_properties.get_sparql')
    def test_fetch_virtual_property_values_from_sparql_success(self, mock_get_sparql):
        """Test successful SPARQL query for virtual property values."""
        mock_sparql = MagicMock()
        mock_get_sparql.return_value = mock_sparql
        
        mock_sparql.query.return_value.convert.return_value = {
            "results": {
                "bindings": [
                    {"target": {"type": "uri", "value": "http://example.com/target1"}},
                    {"target": {"type": "literal", "value": "Test Value"}},
                    {"target": {"type": "typed-literal", "value": "42", "datatype": "http://www.w3.org/2001/XMLSchema#int"}},
                    {"target": {"type": "literal", "value": "Hello", "xml:lang": "en"}}
                ]
            }
        }
        
        result = fetch_virtual_property_values_from_sparql(
            "http://example.com/entity",
            "http://example.com/IntermediateClass",
            "http://example.com/sourceProperty",
            "http://example.com/targetProperty"
        )
        
        assert len(result) == 4
        assert result[0] == URIRef("http://example.com/target1")
        assert result[1] == Literal("Test Value")
        assert result[2] == Literal("42", datatype=URIRef("http://www.w3.org/2001/XMLSchema#int"))
        assert result[3] == Literal("Hello", lang="en")
        
        mock_sparql.setQuery.assert_called_once()
        mock_sparql.setReturnFormat.assert_called_once_with(JSON)

    @patch('heritrace.utils.virtual_properties.get_sparql')
    def test_fetch_virtual_property_values_from_sparql_no_results(self, mock_get_sparql):
        """Test SPARQL query with no results."""
        mock_sparql = MagicMock()
        mock_get_sparql.return_value = mock_sparql
        
        mock_sparql.query.return_value.convert.return_value = {
            "results": {"bindings": []}
        }
        
        result = fetch_virtual_property_values_from_sparql(
            "http://example.com/entity",
            "http://example.com/IntermediateClass",
            "http://example.com/sourceProperty",
            "http://example.com/targetProperty"
        )
        
        assert result == []

    @patch('heritrace.utils.virtual_properties.get_sparql')
    def test_fetch_virtual_property_values_from_sparql_exception(self, mock_get_sparql):
        """Test SPARQL query with exception."""
        mock_sparql = MagicMock()
        mock_get_sparql.return_value = mock_sparql
        
        mock_sparql.query.side_effect = Exception("SPARQL error")
        
        result = fetch_virtual_property_values_from_sparql(
            "http://example.com/entity",
            "http://example.com/IntermediateClass",
            "http://example.com/sourceProperty",
            "http://example.com/targetProperty"
        )
        
        assert result == []

    @patch('heritrace.utils.virtual_properties.get_sparql')
    def test_fetch_virtual_property_values_from_sparql_query_format(self, mock_get_sparql):
        """Test that the SPARQL query is properly formatted."""
        mock_sparql = MagicMock()
        mock_get_sparql.return_value = mock_sparql
        
        mock_sparql.query.return_value.convert.return_value = {
            "results": {"bindings": []}
        }
        
        fetch_virtual_property_values_from_sparql(
            "http://example.com/entity",
            "http://example.com/IntermediateClass",
            "http://example.com/sourceProperty",
            "http://example.com/targetProperty"
        )
        
        # Verify that the query was called with expected structure
        query_call = mock_sparql.setQuery.call_args[0][0]
        assert "?intermediate a <http://example.com/IntermediateClass>" in query_call
        assert "?intermediate <http://example.com/sourceProperty> <http://example.com/entity>" in query_call
        assert "?intermediate <http://example.com/targetProperty> ?target" in query_call
        assert "SELECT DISTINCT ?target WHERE" in query_call


class TestFetchVirtualPropertyValuesFromGraph:
    """Test the graph-based virtual property values fetching function."""

    def test_fetch_virtual_property_values_from_graph_success(self):
        """Test successful graph query for virtual property values."""
        mock_graph = MagicMock()
        
        # Mock intermediate entities
        intermediate1 = URIRef("http://example.com/intermediate1")
        intermediate2 = URIRef("http://example.com/intermediate2")
        
        # Mock the subjects query to return intermediate entities
        mock_graph.subjects.return_value = [intermediate1, intermediate2]
        
        # Mock the __contains__ method to simulate graph containment
        def mock_contains(*args):
            if len(args) == 1:
                triple = args[0]
            else:
                # Handle case where MagicMock passes self as first argument
                triple = args[1] if len(args) > 1 else args[0]
            
            subject, predicate, obj = triple
            if (subject == intermediate1 and 
                predicate == URIRef("http://example.com/sourceProperty") and
                obj == URIRef("http://example.com/entity")):
                return True
            return False
        
        mock_graph.__contains__ = mock_contains
        
        # Mock the objects query to return target values
        def mock_objects(subject, predicate, unique=True):
            if subject == intermediate1 and predicate == URIRef("http://example.com/targetProperty"):
                return [URIRef("http://example.com/target1"), Literal("Test Value")]
            return []
        
        mock_graph.objects = mock_objects
        
        result = fetch_virtual_property_values_from_graph(
            "http://example.com/entity",
            "http://example.com/IntermediateClass",
            "http://example.com/sourceProperty",
            "http://example.com/targetProperty",
            mock_graph
        )
        
        assert len(result) == 2
        assert URIRef("http://example.com/target1") in result
        assert Literal("Test Value") in result

    def test_fetch_virtual_property_values_from_graph_no_intermediates(self):
        """Test graph query with no intermediate entities."""
        mock_graph = MagicMock()
        mock_graph.subjects.return_value = []
        
        result = fetch_virtual_property_values_from_graph(
            "http://example.com/entity",
            "http://example.com/IntermediateClass",
            "http://example.com/sourceProperty",
            "http://example.com/targetProperty",
            mock_graph
        )
        
        assert result == []

    def test_fetch_virtual_property_values_from_graph_no_matching_source(self):
        """Test graph query with intermediates but no matching source property."""
        mock_graph = MagicMock()
        
        intermediate1 = URIRef("http://example.com/intermediate1")
        mock_graph.subjects.return_value = [intermediate1]
        
        # Mock __contains__ to return False (no matching source property)
        def mock_contains(*args):
            return False
        
        mock_graph.__contains__ = mock_contains
        
        result = fetch_virtual_property_values_from_graph(
            "http://example.com/entity",
            "http://example.com/IntermediateClass",
            "http://example.com/sourceProperty",
            "http://example.com/targetProperty",
            mock_graph
        )
        
        assert result == []

    def test_fetch_virtual_property_values_from_graph_no_targets(self):
        """Test graph query with matching intermediates but no target values."""
        mock_graph = MagicMock()
        
        intermediate1 = URIRef("http://example.com/intermediate1")
        mock_graph.subjects.return_value = [intermediate1]
        
        # Mock __contains__ to return True (matching source property)
        def mock_contains(*args):
            return True
        
        mock_graph.__contains__ = mock_contains
        
        # Mock objects to return empty list (no target values)
        mock_graph.objects = lambda subject, predicate, unique=True: []
        
        result = fetch_virtual_property_values_from_graph(
            "http://example.com/entity",
            "http://example.com/IntermediateClass",
            "http://example.com/sourceProperty",
            "http://example.com/targetProperty",
            mock_graph
        )
        
        assert result == []


class TestVirtualPropertiesIntegration:
    """Integration tests for virtual properties functionality."""

    @patch('heritrace.utils.virtual_properties.get_sparql')
    def test_end_to_end_virtual_property_processing(self, mock_get_sparql):
        """Test complete virtual property processing from rule to results."""
        mock_sparql = MagicMock()
        mock_get_sparql.return_value = mock_sparql
        
        mock_sparql.query.return_value.convert.return_value = {
            "results": {
                "bindings": [
                    {"target": {"type": "uri", "value": "http://example.com/author1"}},
                    {"target": {"type": "uri", "value": "http://example.com/author2"}}
                ]
            }
        }
        
        rule = {
            "displayProperties": [
                {
                    "virtual_property": "http://example.com/hasAuthor",
                    "implementedVia": {
                        "class": "http://example.com/Publication",
                        "sourceProperty": "http://example.com/aboutWork",
                        "targetProperty": "http://example.com/hasCreator"
                    }
                }
            ]
        }
        
        result = process_virtual_properties("http://example.com/work", rule)
        
        assert len(result) == 2
        assert (URIRef("http://example.com/work"), URIRef("http://example.com/hasAuthor"), URIRef("http://example.com/author1")) in result
        assert (URIRef("http://example.com/work"), URIRef("http://example.com/hasAuthor"), URIRef("http://example.com/author2")) in result

    def test_virtual_properties_with_historical_snapshot(self):
        """Test virtual properties processing with historical snapshot."""
        mock_graph = MagicMock()
        
        # Set up the mock graph to simulate a historical snapshot
        intermediate = URIRef("http://example.com/publication1")
        mock_graph.subjects.return_value = [intermediate]
        
        def mock_contains(*args):
            if len(args) == 1:
                triple = args[0]
            else:
                triple = args[1] if len(args) > 1 else args[0]
                
            return (
                triple[0] == intermediate and
                triple[1] == URIRef("http://example.com/aboutWork") and
                triple[2] == URIRef("http://example.com/work")
            )
        
        mock_graph.__contains__ = mock_contains
        mock_graph.objects = lambda subject, predicate, unique=True: [URIRef("http://example.com/author_historical")]
        
        rule = {
            "displayProperties": [
                {
                    "virtual_property": "http://example.com/hasAuthor",
                    "implementedVia": {
                        "class": "http://example.com/Publication",
                        "sourceProperty": "http://example.com/aboutWork",
                        "targetProperty": "http://example.com/hasCreator"
                    }
                }
            ]
        }
        
        result = process_virtual_properties("http://example.com/work", rule, mock_graph)
        
        assert len(result) == 1
        assert result[0] == (URIRef("http://example.com/work"), URIRef("http://example.com/hasAuthor"), URIRef("http://example.com/author_historical")) 