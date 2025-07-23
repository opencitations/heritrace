"""
Unit tests for shape-aware predicate display functionality.

Tests the enhanced human_readable_predicate method that can display different
labels for the same predicate based on the object entity's shape.
"""
from unittest.mock import MagicMock, patch

import pytest
from heritrace.utils.filters import Filter
from rdflib import RDF, Graph, URIRef


@pytest.fixture
def mock_shacl_graph():
    """Create a mock SHACL graph with Author, Editor, and Publisher shapes."""
    shacl_graph = Graph()
    
    # Add SHACL shapes with hasValue constraints
    shacl_ttl = """
    @prefix sh: <http://www.w3.org/ns/shacl#> .
    @prefix pro: <http://purl.org/spar/pro/> .
    @prefix schema: <http://schema.org/> .
    
    schema:AuthorShape a sh:NodeShape ;
        sh:targetClass pro:RoleInTime ;
        sh:property [
            sh:path pro:withRole ;
            sh:hasValue pro:author ;
        ] .
    
    schema:EditorShape a sh:NodeShape ;
        sh:targetClass pro:RoleInTime ;
        sh:property [
            sh:path pro:withRole ;
            sh:hasValue pro:editor ;
        ] .
    
    schema:PublisherShape a sh:NodeShape ;
        sh:targetClass pro:RoleInTime ;
        sh:property [
            sh:path pro:withRole ;
            sh:hasValue pro:publisher ;
        ] .
    """
    
    shacl_graph.parse(data=shacl_ttl, format="turtle")
    return shacl_graph


@pytest.fixture
def mock_filter_with_shape_rules():
    """Create a Filter with display rules that include shape-specific configurations."""
    context = {"pro": "http://purl.org/spar/pro/", "schema": "http://schema.org/"}
    display_rules = [
        {
            "target": {
                "class": "http://purl.org/spar/fabio/Expression",
                "shape": "http://schema.org/ExpressionShape"
            },
            "displayName": "Expression",
            "displayProperties": [
                {
                    "property": "http://purl.org/spar/pro/isDocumentContextFor",
                    "displayRules": [
                        {
                            "shape": "http://schema.org/AuthorShape",
                            "displayName": "Author"
                        },
                        {
                            "shape": "http://schema.org/EditorShape", 
                            "displayName": "Editor"
                        },
                        {
                            "shape": "http://schema.org/PublisherShape",
                            "displayName": "Publisher"
                        }
                    ]
                }
            ]
        }
    ]
    sparql_endpoint = "http://example.org/sparql"
    
    # Mock the get_sparql function
    mock_sparql = MagicMock()
    with patch('heritrace.extensions.get_sparql', return_value=mock_sparql):
        filter_instance = Filter(context, display_rules, sparql_endpoint)
    
    return filter_instance


class TestShapeAwarePredicate:
    """Test cases for shape-aware predicate display functionality."""

    def test_human_readable_predicate_with_author_shape(self, mock_filter_with_shape_rules):
        """Test that isDocumentContextFor displays as 'Author' when object has AuthorShape."""
        predicate_uri = "http://purl.org/spar/pro/isDocumentContextFor"
        entity_key = ("http://purl.org/spar/fabio/Expression", "http://schema.org/ExpressionShape")
        object_shape_uri = "http://schema.org/AuthorShape"
        
        with patch('heritrace.utils.display_rules_utils.find_matching_rule') as mock_find_rule:
            mock_find_rule.return_value = mock_filter_with_shape_rules.display_rules[0]
            
            result = mock_filter_with_shape_rules.human_readable_predicate(
                predicate_uri, entity_key, object_shape_uri=object_shape_uri
            )
        
        assert result == "Author"

    def test_human_readable_predicate_with_editor_shape(self, mock_filter_with_shape_rules):
        """Test that isDocumentContextFor displays as 'Editor' when object has EditorShape."""
        predicate_uri = "http://purl.org/spar/pro/isDocumentContextFor"
        entity_key = ("http://purl.org/spar/fabio/Expression", "http://schema.org/ExpressionShape")
        object_shape_uri = "http://schema.org/EditorShape"
        
        with patch('heritrace.utils.display_rules_utils.find_matching_rule') as mock_find_rule:
            mock_find_rule.return_value = mock_filter_with_shape_rules.display_rules[0]
            
            result = mock_filter_with_shape_rules.human_readable_predicate(
                predicate_uri, entity_key, object_shape_uri=object_shape_uri
            )
        
        assert result == "Editor"

    def test_human_readable_predicate_with_publisher_shape(self, mock_filter_with_shape_rules):
        """Test that isDocumentContextFor displays as 'Publisher' when object has PublisherShape."""
        predicate_uri = "http://purl.org/spar/pro/isDocumentContextFor"
        entity_key = ("http://purl.org/spar/fabio/Expression", "http://schema.org/ExpressionShape")
        object_shape_uri = "http://schema.org/PublisherShape"
        
        with patch('heritrace.utils.display_rules_utils.find_matching_rule') as mock_find_rule:
            mock_find_rule.return_value = mock_filter_with_shape_rules.display_rules[0]
            
            result = mock_filter_with_shape_rules.human_readable_predicate(
                predicate_uri, entity_key, object_shape_uri=object_shape_uri
            )
        
        assert result == "Publisher"

    def test_human_readable_predicate_fallback_when_shape_not_matched(self, mock_filter_with_shape_rules):
        """Test fallback to first display rule when object shape doesn't match any rule."""
        predicate_uri = "http://purl.org/spar/pro/isDocumentContextFor"
        entity_key = ("http://purl.org/spar/fabio/Expression", "http://schema.org/ExpressionShape")
        object_shape_uri = "http://schema.org/UnknownShape"
        
        with patch('heritrace.utils.display_rules_utils.find_matching_rule') as mock_find_rule:
            mock_find_rule.return_value = mock_filter_with_shape_rules.display_rules[0]
            
            result = mock_filter_with_shape_rules.human_readable_predicate(
                predicate_uri, entity_key, object_shape_uri=object_shape_uri
            )
        
        # Should fallback to first rule (Author)
        assert result == "Author"

    def test_human_readable_predicate_fallback_when_no_object_shape(self, mock_filter_with_shape_rules):
        """Test fallback to first display rule when no object shape is provided."""
        predicate_uri = "http://purl.org/spar/pro/isDocumentContextFor"
        entity_key = ("http://purl.org/spar/fabio/Expression", "http://schema.org/ExpressionShape")
        
        with patch('heritrace.utils.display_rules_utils.find_matching_rule') as mock_find_rule:
            mock_find_rule.return_value = mock_filter_with_shape_rules.display_rules[0]
            
            result = mock_filter_with_shape_rules.human_readable_predicate(
                predicate_uri, entity_key
            )
        
        # Should fallback to first rule (Author)
        assert result == "Author"

    @patch('heritrace.utils.shacl_utils.get_shacl_graph')
    def test_determine_shape_for_author_role(self, mock_get_shacl_graph, mock_shacl_graph):
        """Test that determine_shape_for_entity_triples correctly identifies AuthorShape."""
        from heritrace.utils.shacl_utils import \
            determine_shape_for_entity_triples
        
        mock_get_shacl_graph.return_value = mock_shacl_graph
        
        # Create triples for an author role
        author_triples = [
            (URIRef("http://example.org/role1"), RDF.type, URIRef("http://purl.org/spar/pro/RoleInTime")),
            (URIRef("http://example.org/role1"), URIRef("http://purl.org/spar/pro/withRole"), URIRef("http://purl.org/spar/pro/author")),
            (URIRef("http://example.org/role1"), URIRef("http://purl.org/spar/pro/isHeldBy"), URIRef("http://example.org/agent1"))
        ]
        
        result = determine_shape_for_entity_triples(author_triples)
        assert result == "http://schema.org/AuthorShape"

    @patch('heritrace.utils.shacl_utils.get_shacl_graph')
    def test_determine_shape_for_editor_role(self, mock_get_shacl_graph, mock_shacl_graph):
        """Test that determine_shape_for_entity_triples correctly identifies EditorShape."""
        from heritrace.utils.shacl_utils import \
            determine_shape_for_entity_triples
        
        mock_get_shacl_graph.return_value = mock_shacl_graph
        
        # Create triples for an editor role
        editor_triples = [
            (URIRef("http://example.org/role2"), RDF.type, URIRef("http://purl.org/spar/pro/RoleInTime")),
            (URIRef("http://example.org/role2"), URIRef("http://purl.org/spar/pro/withRole"), URIRef("http://purl.org/spar/pro/editor")),
            (URIRef("http://example.org/role2"), URIRef("http://purl.org/spar/pro/isHeldBy"), URIRef("http://example.org/agent2"))
        ]
        
        result = determine_shape_for_entity_triples(editor_triples)
        assert result == "http://schema.org/EditorShape"

    @patch('heritrace.utils.shacl_utils.get_shacl_graph')
    def test_determine_shape_for_publisher_role(self, mock_get_shacl_graph, mock_shacl_graph):
        """Test that determine_shape_for_entity_triples correctly identifies PublisherShape."""
        from heritrace.utils.shacl_utils import \
            determine_shape_for_entity_triples
        
        mock_get_shacl_graph.return_value = mock_shacl_graph
        
        # Create triples for a publisher role
        publisher_triples = [
            (URIRef("http://example.org/role3"), RDF.type, URIRef("http://purl.org/spar/pro/RoleInTime")),
            (URIRef("http://example.org/role3"), URIRef("http://purl.org/spar/pro/withRole"), URIRef("http://purl.org/spar/pro/publisher")),
            (URIRef("http://example.org/role3"), URIRef("http://purl.org/spar/pro/isHeldBy"), URIRef("http://example.org/agent3"))
        ]
        
        result = determine_shape_for_entity_triples(publisher_triples)
        assert result == "http://schema.org/PublisherShape"

    @patch('heritrace.utils.shacl_utils.get_shacl_graph')
    def test_hasvalue_constraints_prioritized_over_property_matches(self, mock_get_shacl_graph, mock_shacl_graph):
        """Test that hasValue constraints take priority over simple property matching."""
        from heritrace.utils.shacl_utils import \
            determine_shape_for_entity_triples
        
        mock_get_shacl_graph.return_value = mock_shacl_graph
        
        # Create triples for an entity that could match multiple shapes but has specific role
        mixed_triples = [
            (URIRef("http://example.org/role1"), RDF.type, URIRef("http://purl.org/spar/pro/RoleInTime")),
            (URIRef("http://example.org/role1"), URIRef("http://purl.org/spar/pro/withRole"), URIRef("http://purl.org/spar/pro/editor")),
            (URIRef("http://example.org/role1"), URIRef("http://purl.org/spar/pro/isHeldBy"), URIRef("http://example.org/agent1")),
            # Add extra properties that might confuse a simple property-based matcher
            (URIRef("http://example.org/role1"), URIRef("http://example.org/extraProperty1"), URIRef("http://example.org/value1")),
            (URIRef("http://example.org/role1"), URIRef("http://example.org/extraProperty2"), URIRef("http://example.org/value2"))
        ]
        
        result = determine_shape_for_entity_triples(mixed_triples)
        # Should still identify as EditorShape due to pro:withRole pro:editor, despite extra properties
        assert result == "http://schema.org/EditorShape"