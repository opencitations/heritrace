# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

"""
Unit tests for choosing the shape of an entity from its triples.
"""

from unittest.mock import patch

import pytest
from rdflib import RDF, Graph, URIRef

from heritrace.utils.shacl_presentation import read_presentation
from heritrace.utils.shacl_utils import determine_shape_for_entity_triples


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


class TestShapeSelection:
    """Test cases for shape selection from entity triples."""

    @patch(
        "heritrace.utils.shacl_utils.get_presentation",
        return_value=read_presentation(Graph()),
    )
    @patch("heritrace.utils.shacl_utils.get_shacl_graph")
    def test_determine_shape_for_author_role(
        self, mock_get_shacl_graph, _mock_get_presentation, mock_shacl_graph
    ) -> None:
        """
        Test that determine_shape_for_entity_triples correctly identifies AuthorShape.
        """
        mock_get_shacl_graph.return_value = mock_shacl_graph

        # Create triples for an author role
        author_triples = [
            (
                URIRef("http://example.org/role1"),
                RDF.type,
                URIRef("http://purl.org/spar/pro/RoleInTime"),
            ),
            (
                URIRef("http://example.org/role1"),
                URIRef("http://purl.org/spar/pro/withRole"),
                URIRef("http://purl.org/spar/pro/author"),
            ),
            (
                URIRef("http://example.org/role1"),
                URIRef("http://purl.org/spar/pro/isHeldBy"),
                URIRef("http://example.org/agent1"),
            ),
        ]

        result = determine_shape_for_entity_triples(author_triples)
        assert result == "http://schema.org/AuthorShape"

    @patch(
        "heritrace.utils.shacl_utils.get_presentation",
        return_value=read_presentation(Graph()),
    )
    @patch("heritrace.utils.shacl_utils.get_shacl_graph")
    def test_determine_shape_for_editor_role(
        self, mock_get_shacl_graph, _mock_get_presentation, mock_shacl_graph
    ) -> None:
        """
        Test that determine_shape_for_entity_triples correctly identifies EditorShape.
        """
        mock_get_shacl_graph.return_value = mock_shacl_graph

        # Create triples for an editor role
        editor_triples = [
            (
                URIRef("http://example.org/role2"),
                RDF.type,
                URIRef("http://purl.org/spar/pro/RoleInTime"),
            ),
            (
                URIRef("http://example.org/role2"),
                URIRef("http://purl.org/spar/pro/withRole"),
                URIRef("http://purl.org/spar/pro/editor"),
            ),
            (
                URIRef("http://example.org/role2"),
                URIRef("http://purl.org/spar/pro/isHeldBy"),
                URIRef("http://example.org/agent2"),
            ),
        ]

        result = determine_shape_for_entity_triples(editor_triples)
        assert result == "http://schema.org/EditorShape"

    @patch(
        "heritrace.utils.shacl_utils.get_presentation",
        return_value=read_presentation(Graph()),
    )
    @patch("heritrace.utils.shacl_utils.get_shacl_graph")
    def test_determine_shape_for_publisher_role(
        self, mock_get_shacl_graph, _mock_get_presentation, mock_shacl_graph
    ) -> None:
        """
        Test that determine_shape_for_entity_triples correctly identifies
        PublisherShape.
        """
        mock_get_shacl_graph.return_value = mock_shacl_graph

        # Create triples for a publisher role
        publisher_triples = [
            (
                URIRef("http://example.org/role3"),
                RDF.type,
                URIRef("http://purl.org/spar/pro/RoleInTime"),
            ),
            (
                URIRef("http://example.org/role3"),
                URIRef("http://purl.org/spar/pro/withRole"),
                URIRef("http://purl.org/spar/pro/publisher"),
            ),
            (
                URIRef("http://example.org/role3"),
                URIRef("http://purl.org/spar/pro/isHeldBy"),
                URIRef("http://example.org/agent3"),
            ),
        ]

        result = determine_shape_for_entity_triples(publisher_triples)
        assert result == "http://schema.org/PublisherShape"

    @patch(
        "heritrace.utils.shacl_utils.get_presentation",
        return_value=read_presentation(Graph()),
    )
    @patch("heritrace.utils.shacl_utils.get_shacl_graph")
    def test_hasvalue_constraints_prioritized_over_property_matches(
        self, mock_get_shacl_graph, _mock_get_presentation, mock_shacl_graph
    ) -> None:
        """
        Test that hasValue constraints take priority over simple property matching.
        """
        mock_get_shacl_graph.return_value = mock_shacl_graph

        # Create triples for an entity that could match multiple shapes but has specific
        # role
        mixed_triples = [
            (
                URIRef("http://example.org/role1"),
                RDF.type,
                URIRef("http://purl.org/spar/pro/RoleInTime"),
            ),
            (
                URIRef("http://example.org/role1"),
                URIRef("http://purl.org/spar/pro/withRole"),
                URIRef("http://purl.org/spar/pro/editor"),
            ),
            (
                URIRef("http://example.org/role1"),
                URIRef("http://purl.org/spar/pro/isHeldBy"),
                URIRef("http://example.org/agent1"),
            ),
            # Add extra properties that might confuse a simple property-based matcher
            (
                URIRef("http://example.org/role1"),
                URIRef("http://example.org/extraProperty1"),
                URIRef("http://example.org/value1"),
            ),
            (
                URIRef("http://example.org/role1"),
                URIRef("http://example.org/extraProperty2"),
                URIRef("http://example.org/value2"),
            ),
        ]

        result = determine_shape_for_entity_triples(mixed_triples)
        # Should still identify as EditorShape due to pro:withRole pro:editor, despite
        # extra properties
        assert result == "http://schema.org/EditorShape"
