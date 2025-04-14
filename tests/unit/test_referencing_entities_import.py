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

    @patch('heritrace.utils.sparql_utils.SPARQLWrapper')
    def test_import_entity_graph_without_referencing(self, mock_sparqlwrapper):
        """Test that import_entity_graph works normally when not including referencing entities."""
        # Setup mock responses
        mock_sparql = MagicMock()
        # Configuriamo la risposta per includera anche l'importazione dell'oggetto referenziato
        mock_sparql.query.return_value.convert.side_effect = [
            {
                'results': {
                    'bindings': [
                        {'p': {'value': 'http://example.org/predicate'}, 'o': {'value': 'http://example.org/object'}}
                    ]
                }
            },
            {'results': {'bindings': []}}  # Empty results for the recursive call
        ]
        mock_sparqlwrapper.return_value = mock_sparql
        
        # Call the function
        result = import_entity_graph(self.mock_editor, 'http://example.org/subject')
        
        # Verify subject and its connected objects were imported
        self.mock_editor.import_entity.assert_any_call(URIRef('http://example.org/subject'))
        self.mock_editor.import_entity.assert_any_call(URIRef('http://example.org/object'))
        
        # Verifica che sono state fatte query solo per gli oggetti e non per i soggetti che referenziano
        queries = [call_args[0][0] for call_args in mock_sparql.setQuery.call_args_list]
        self.assertEqual(len(queries), 2)  # Una query per il soggetto principale e una per l'oggetto
        self.assertIn('<http://example.org/subject> ?p ?o', queries[0])
        self.assertIn('<http://example.org/object> ?p ?o', queries[1])

    @patch('heritrace.utils.sparql_utils.SPARQLWrapper')
    def test_import_entity_graph_with_referencing(self, mock_sparqlwrapper):
        """Test that import_entity_graph imports referencing entities when requested."""
        # Setup mock responses
        mock_sparql = MagicMock()
        
        # First query for referencing entities
        # Second query for outgoing connections
        mock_sparql.query.return_value.convert.side_effect = [
            {
                'results': {
                    'bindings': [
                        {'s': {'value': 'http://example.org/referencing1'}},
                        {'s': {'value': 'http://example.org/referencing2'}}
                    ]
                }
            },
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
        
        mock_sparqlwrapper.return_value = mock_sparql
        
        # Call the function with include_referencing_entities=True
        result = import_entity_graph(
            self.mock_editor, 
            'http://example.org/subject', 
            include_referencing_entities=True
        )
        
        # Verify all three entities were imported
        self.mock_editor.import_entity.assert_any_call(URIRef('http://example.org/subject'))
        self.mock_editor.import_entity.assert_any_call(URIRef('http://example.org/referencing1'))
        self.mock_editor.import_entity.assert_any_call(URIRef('http://example.org/referencing2'))
        
        # Verify the correct query was made for referencing entities
        self.assertGreaterEqual(mock_sparql.setQuery.call_count, 2)
        ref_query = mock_sparql.setQuery.call_args_list[0][0][0]
        self.assertIn('?s ?p <http://example.org/subject>', ref_query)

    @patch('heritrace.utils.sparql_utils.SPARQLWrapper')
    def test_import_entity_graph_with_quadstore(self, mock_sparqlwrapper):
        """Test that import_entity_graph handles quadstore correctly when including referencing entities."""
        # Setup mock for quadstore
        self.mock_editor.dataset_is_quadstore = True
        
        mock_sparql = MagicMock()
        mock_sparql.query.return_value.convert.side_effect = [
            {
                'results': {
                    'bindings': [
                        {'s': {'value': 'http://example.org/referencing1'}}
                    ]
                }
            },
            {'results': {'bindings': []}},
            {'results': {'bindings': []}}
        ]
        
        mock_sparqlwrapper.return_value = mock_sparql
        
        # Call the function
        result = import_entity_graph(
            self.mock_editor, 
            'http://example.org/subject', 
            include_referencing_entities=True
        )
        
        # Verify the correct query was used for quadstore
        ref_query = mock_sparql.setQuery.call_args_list[0][0][0]
        self.assertIn('GRAPH ?g', ref_query)
        self.assertIn('?s ?p <http://example.org/subject>', ref_query) 