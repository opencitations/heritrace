import unittest
from unittest.mock import MagicMock, patch

from heritrace.utils.shacl_utils import determine_shape_for_subject
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
            with patch("heritrace.utils.shacl_validation.get_highest_priority_class", return_value=None):
                result = get_valid_predicates(triples)
                
                existing_predicates, can_be_added, default_datatypes, mandatory_values, can_be_deleted, s_types, valid_predicates = result
                
                self.assertEqual(len(existing_predicates), 3)
                self.assertTrue(RDF.type in existing_predicates)
                self.assertTrue(predicate1 in existing_predicates)
                self.assertTrue(predicate2 in existing_predicates)
                
                self.assertEqual(existing_predicates, can_be_added)
                
                self.assertEqual(len(default_datatypes), 3)
                for pred in [str(RDF.type), str(predicate1), str(predicate2)]:
                    self.assertTrue(pred in default_datatypes)
                    self.assertEqual(default_datatypes[pred], XSD.string)
                
                self.assertEqual(mandatory_values, {})
                self.assertEqual(can_be_deleted, {})
                
                self.assertEqual(len(s_types), 1)
                self.assertEqual(s_types[0], s_type)
                
                self.assertEqual(len(valid_predicates), 3)
                self.assertTrue(str(RDF.type) in valid_predicates)
                self.assertTrue(str(predicate1) in valid_predicates)
                self.assertTrue(str(predicate2) in valid_predicates)
                
    def test_determine_shape_for_subject_no_shacl(self):
        """Test that determine_shape_for_subject returns None when shacl_graph is None."""
        class_list = ["http://example.org/TestClass1", "http://example.org/TestClass2"]
        
        with patch("heritrace.utils.shacl_utils.get_shacl_graph", return_value=None):
            result = determine_shape_for_subject(class_list)
            
            self.assertIsNone(result)
