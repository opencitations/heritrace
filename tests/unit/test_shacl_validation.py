import unittest
from unittest.mock import MagicMock, patch

from heritrace.utils.shacl_utils import determine_shape_for_classes
from heritrace.utils.shacl_validation import (get_valid_predicates,
                                              validate_new_triple)
from rdflib import RDF, XSD, Graph, Literal, URIRef


class TestShaclValidation(unittest.TestCase):
    """Test class for shacl_validation module."""

    def test_validate_new_triple_matching_triples(self):
        """Test that validate_new_triple updates old_value when matching triples are found."""
        subject = "http://example.org/subject"
        predicate = "http://example.org/predicate"
        new_value = "New Value"
        
        data_graph = Graph()
        existing_value = Literal("Existing Value", datatype=XSD.string)
        data_graph.add((URIRef(subject), URIRef(predicate), existing_value))
        
        old_value_str = str(existing_value)
        
        with patch("heritrace.utils.shacl_validation.fetch_data_graph_for_subject", return_value=data_graph):
            mock_shacl = MagicMock()
            mock_shacl.__len__.return_value = 0
            with patch("heritrace.utils.shacl_validation.get_shacl_graph", return_value=mock_shacl):
                with patch("validators.url", return_value=False):
                    valid_value, returned_old_value, error = validate_new_triple(
                        subject,
                        predicate,
                        new_value,
                        "update",
                        old_value=old_value_str
                    )
                    
                    self.assertEqual(returned_old_value, existing_value)
                    self.assertEqual(str(returned_old_value), "Existing Value")
                    self.assertEqual(returned_old_value.datatype, XSD.string)
                    
                    self.assertIsInstance(valid_value, Literal)
                    self.assertEqual(str(valid_value), "New Value")
                    
                    self.assertEqual(error, "")
    
    def test_get_valid_predicates_no_shacl(self):
        """Test that get_valid_predicates handles the case when shacl is None."""
        s_type = URIRef("http://example.org/TestType")
        predicate1 = URIRef("http://example.org/predicate1")
        predicate2 = URIRef("http://example.org/predicate2")
        triples = [
            (URIRef("http://example.org/subject"), RDF.type, s_type),
            (URIRef("http://example.org/subject"), predicate1, URIRef("http://example.org/object1")),
            (URIRef("http://example.org/subject"), predicate2, URIRef("http://example.org/object2")),
        ]
        
        with patch("heritrace.utils.shacl_validation.get_shacl_graph", return_value=None):
            result = get_valid_predicates(triples, s_type)
            
            can_add, can_delete, datatypes, mandatory_values, optional_values, all_predicates = result
            
            # Verify that can_add and can_delete contain strings, not URIRef
            self.assertEqual(len(can_add), 3)
            self.assertIn(str(RDF.type), can_add)
            self.assertIn(str(predicate1), can_add)
            self.assertIn(str(predicate2), can_add)
            # Verify all items in can_add are strings
            self.assertTrue(all(isinstance(item, str) for item in can_add), 
                           f"can_add should contain only strings, got: {[type(item) for item in can_add]}")
            
            self.assertEqual(len(datatypes), 3)
            for pred in [RDF.type, predicate1, predicate2]:
                self.assertTrue(str(pred) in datatypes)
                self.assertEqual(datatypes[str(pred)], XSD.string)
                
            self.assertEqual(mandatory_values, {})
            self.assertEqual(optional_values, {})
            
            self.assertEqual(len(can_delete), 3)
            # Verify all items in can_delete are strings
            self.assertTrue(all(isinstance(item, str) for item in can_delete), 
                           f"can_delete should contain only strings, got: {[type(item) for item in can_delete]}")
            expected_predicates = {str(RDF.type), str(predicate1), str(predicate2)}
            self.assertEqual(set(can_delete), expected_predicates)
            self.assertEqual(len(all_predicates), 3)

    def test_get_valid_predicates_type_consistency(self):
        """Test that get_valid_predicates returns consistent string types regardless of SHACL presence.
        
        This verifies the fix for the bug where can_be_added/can_be_deleted were URIRef 
        when no SHACL rules existed, but strings when SHACL rules existed.
        """
        s_type = URIRef("http://example.org/TestType")
        predicate1 = URIRef("http://example.org/predicate1")
        predicate2 = URIRef("http://example.org/predicate2")
        triples = [
            (URIRef("http://example.org/subject"), RDF.type, s_type),
            (URIRef("http://example.org/subject"), predicate1, URIRef("http://example.org/object1")),
            (URIRef("http://example.org/subject"), predicate2, URIRef("http://example.org/object2")),
        ]
        
        # Test case 1: No SHACL graph
        with patch("heritrace.utils.shacl_validation.get_shacl_graph", return_value=None):
            result_no_shacl = get_valid_predicates(triples, s_type)
            can_add_no_shacl, can_delete_no_shacl = result_no_shacl[0], result_no_shacl[1]
            
        # Test case 2: Empty SHACL graph
        empty_graph = Graph()
        with patch("heritrace.utils.shacl_validation.get_shacl_graph", return_value=empty_graph):
            result_empty_shacl = get_valid_predicates(triples, s_type)
            can_add_empty_shacl, can_delete_empty_shacl = result_empty_shacl[0], result_empty_shacl[1]
            
        # Test case 3: No entity types
        triples_no_type = [
            (URIRef("http://example.org/subject"), predicate1, URIRef("http://example.org/object1")),
            (URIRef("http://example.org/subject"), predicate2, URIRef("http://example.org/object2")),
        ]
        with patch("heritrace.utils.shacl_validation.get_shacl_graph", return_value=Graph()):
            result_no_type = get_valid_predicates(triples_no_type, s_type)
            can_add_no_type, can_delete_no_type = result_no_type[0], result_no_type[1]
        
        # Verify all cases return strings consistently
        for case_name, can_add, can_delete in [
            ("no_shacl", can_add_no_shacl, can_delete_no_shacl),
            ("empty_shacl", can_add_empty_shacl, can_delete_empty_shacl),
            ("no_type", can_add_no_type, can_delete_no_type)
        ]:
            with self.subTest(case=case_name):
                self.assertTrue(all(isinstance(item, str) for item in can_add), 
                               f"case {case_name}: can_add should contain only strings, got: {[type(item) for item in can_add]}")
                self.assertTrue(all(isinstance(item, str) for item in can_delete), 
                               f"case {case_name}: can_delete should contain only strings, got: {[type(item) for item in can_delete]}")
    
    def test_determine_shape_for_classes_no_shacl(self):
        """Test that determine_shape_for_classes returns None when shacl_graph is None."""
        class_list = ["http://example.org/Class1"]
        with patch('heritrace.utils.shacl_utils.get_shacl_graph', return_value=None):
            result = determine_shape_for_classes(class_list)
            self.assertIsNone(result)
