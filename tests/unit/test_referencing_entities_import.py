import unittest
from unittest.mock import patch, MagicMock, call

from rdflib import URIRef
from heritrace.editor import Editor
from heritrace.utils.sparql_utils import import_entity_graph


class TestReferencingEntitiesImport(unittest.TestCase):
    def setUp(self):
        self.mock_editor = MagicMock(spec=Editor)
        self.mock_editor.dataset_endpoint = "http://example.org/sparql"
        self.mock_editor.dataset_is_quadstore = False

    @patch('heritrace.utils.sparql_utils.get_sparql')
    def test_import_entity_graph_without_referencing(self, mock_get_sparql):
        """Test that import_entity_graph works normally when not including referencing entities."""
        # Setup mock SPARQL wrapper
        mock_sparql = MagicMock()
        mock_get_sparql.return_value = mock_sparql
        
        # Mock the query results for the main subject
        mock_sparql.query.return_value.convert.side_effect = [
            # First query for the main subject
            {
                'results': {
                    'bindings': [
                        {'p': {'value': 'http://example.org/predicate'}, 'o': {'value': 'http://example.org/object'}}
                    ]
                }
            },
            # Second query for the object (recursive call)
            {
                'results': {
                    'bindings': []
                }
            }
        ]
        
        # Call the function
        result = import_entity_graph(self.mock_editor, 'http://example.org/subject')
        
        # Verify both subject and object were imported
        expected_calls = [
            call(URIRef('http://example.org/subject')),
            call(URIRef('http://example.org/object'))
        ]
        self.mock_editor.import_entity.assert_has_calls(expected_calls, any_order=True)
        
        # Verify the SPARQL queries were made correctly
        self.assertEqual(mock_sparql.setQuery.call_count, 2)
        
        # Check first query (main subject)
        query1 = mock_sparql.setQuery.call_args_list[0][0][0]
        self.assertIn('<http://example.org/subject> ?p ?o', query1)
        self.assertIn('FILTER(isIRI(?o))', query1)
        
        # Check second query (object)
        query2 = mock_sparql.setQuery.call_args_list[1][0][0]
        self.assertIn('<http://example.org/object> ?p ?o', query2)
        self.assertIn('FILTER(isIRI(?o))', query2)

    @patch('heritrace.utils.sparql_utils.get_sparql')
    def test_import_entity_graph_with_referencing(self, mock_get_sparql):
        """Test that import_entity_graph imports referencing entities when requested."""
        # Setup mock SPARQL wrapper
        mock_sparql = MagicMock()
        mock_get_sparql.return_value = mock_sparql
        
        # Mock the query results for the main subject
        mock_sparql.query.return_value.convert.side_effect = [
            # First query for referencing entities
            {
                'results': {
                    'bindings': [
                        {'s': {'value': 'http://example.org/referencing1'}},
                         {'s': {'value': 'http://example.org/referencing2'}}
                    ]
                }
            },
            # Second query for the main subject's objects
            {
                'results': {
                    'bindings': [
                        {'p': {'value': 'http://example.org/predicate'}, 'o': {'value': 'http://example.org/object'}}
                    ]
                }
            },
            # Empty results for recursive calls on other entities
            {'results': {'bindings': []}},
            {'results': {'bindings': []}},
            {'results': {'bindings': []}}
        ]
        
        # Call the function with include_referencing_entities=True
        result = import_entity_graph(
            self.mock_editor,
            'http://example.org/subject',
            include_referencing_entities=True
        )
        
        # Verify all entities were imported
        expected_calls = [
            call(URIRef('http://example.org/referencing1')),
            call(URIRef('http://example.org/referencing2')),
            call(URIRef('http://example.org/subject')),
            call(URIRef('http://example.org/object'))
        ]
        self.mock_editor.import_entity.assert_has_calls(expected_calls, any_order=True)
        
        # Verify the SPARQL queries were made correctly
        self.assertEqual(mock_sparql.setQuery.call_count, 3)
        
        # Check first query (referencing entities)
        query1 = mock_sparql.setQuery.call_args_list[0][0][0]
        self.assertIn('?s ?p <http://example.org/subject>', query1)
        self.assertIn('FILTER(?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)', query1)
        
        # Check second query (main subject's objects)
        query2 = mock_sparql.setQuery.call_args_list[1][0][0]
        self.assertIn('<http://example.org/subject> ?p ?o', query2)
        self.assertIn('FILTER(isIRI(?o))', query2)

    @patch('heritrace.utils.sparql_utils.get_sparql')
    def test_import_entity_graph_with_quadstore(self, mock_get_sparql):
        """Test that import_entity_graph handles quadstore correctly when including referencing entities."""
        # Setup mock SPARQL wrapper
        mock_sparql = MagicMock()
        mock_get_sparql.return_value = mock_sparql
        
        # Mock the query results for the main subject
        mock_sparql.query.return_value.convert.side_effect = [
            # First query for referencing entities (quadstore format)
            {
                'results': {
                    'bindings': [
                        {'s': {'value': 'http://example.org/referencing1'}}
                    ]
                }
            },
            # Second query for the main subject's objects
            {
                'results': {
                    'bindings': [
                        {'p': {'value': 'http://example.org/predicate'}, 'o': {'value': 'http://example.org/object'}}
                    ]
                }
            },
            # Empty results for recursive calls on other entities
            {'results': {'bindings': []}},
            {'results': {'bindings': []}}
        ]
        
        # Set the editor to use quadstore
        self.mock_editor.dataset_is_quadstore = True
        
        # Call the function with include_referencing_entities=True
        result = import_entity_graph(
            self.mock_editor,
            'http://example.org/subject',
            include_referencing_entities=True
        )
        
        # Verify all entities were imported
        expected_calls = [
            call(URIRef('http://example.org/referencing1')),
            call(URIRef('http://example.org/subject')),
            call(URIRef('http://example.org/object'))
        ]
        self.mock_editor.import_entity.assert_has_calls(expected_calls, any_order=True)
        
        # Verify the SPARQL queries were made correctly
        self.assertEqual(mock_sparql.setQuery.call_count, 3)
        
        # Check first query (referencing entities with GRAPH clause)
        query1 = mock_sparql.setQuery.call_args_list[0][0][0]
        self.assertIn('GRAPH ?g {', query1)
        self.assertIn('?s ?p <http://example.org/subject>', query1)
        self.assertIn('FILTER(?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)', query1)
        
        # Check second query (main subject's objects)
        query2 = mock_sparql.setQuery.call_args_list[1][0][0]
        self.assertIn('<http://example.org/subject> ?p ?o', query2)
        self.assertIn('FILTER(isIRI(?o))', query2)