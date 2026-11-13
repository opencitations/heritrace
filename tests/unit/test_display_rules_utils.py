# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

"""
Tests for display_rules_utils.py
"""

from unittest.mock import MagicMock, patch

import pytest
from rdflib import RDF, Graph, Literal, URIRef

from heritrace.utils.display_rules_utils import (
    GroupingContext,
    get_grouped_triples,
    get_highest_priority_class,
    process_default_property,
    process_ordering,
)
from heritrace.utils.filters import Filter
from heritrace.utils.shacl_presentation import read_presentation


@pytest.fixture
def mock_triples():
    """Mock triples for testing."""
    return [
        (
            URIRef("http://example.org/person1"),
            URIRef("http://example.org/name"),
            URIRef("http://example.org/name1"),
        ),
        (
            URIRef("http://example.org/person1"),
            URIRef("http://example.org/age"),
            Literal("30"),
        ),
        (
            URIRef("http://example.org/person1"),
            URIRef("http://example.org/knows"),
            URIRef("http://example.org/person2"),
        ),
        (
            URIRef("http://example.org/person1"),
            URIRef("http://example.org/knows"),
            URIRef("http://example.org/person3"),
        ),
    ]


@pytest.fixture
def mock_subject_classes():
    """Mock subject classes for testing."""
    return [URIRef("http://example.org/Person"), URIRef("http://example.org/Agent")]


@pytest.fixture
def mock_valid_predicates_info():
    """Mock valid predicates info for testing."""
    return [
        "http://example.org/name",
        "http://example.org/age",
        "http://example.org/knows",
    ]


@pytest.fixture
def mock_sparql():
    """Mock SPARQL wrapper for testing."""
    mock = MagicMock()
    mock.query.return_value.convert.return_value = {
        "results": {
            "bindings": [
                {
                    "label": {"value": "John Doe"},
                    "entity": {"value": "http://example.org/name1"},
                }
            ]
        }
    }
    return mock


@pytest.fixture
def mock_historical_snapshot():
    """Mock historical snapshot for testing."""
    graph = Graph()
    graph.add(
        (
            URIRef("http://example.org/person1"),
            URIRef("http://example.org/name"),
            Literal("John Doe"),
        )
    )
    graph.add(
        (
            URIRef("http://example.org/person2"),
            URIRef("http://example.org/order"),
            URIRef("http://example.org/person3"),
        )
    )
    graph.add(
        (
            URIRef("http://example.org/person1"),
            URIRef("http://example.org/knows"),
            URIRef("http://example.org/person2"),
        )
    )
    graph.add(
        (
            URIRef("http://example.org/person1"),
            URIRef("http://example.org/knows"),
            URIRef("http://example.org/person3"),
        )
    )
    return graph


class TestGetHighestPriorityClass:
    @staticmethod
    def _shapes_for(class_uri_counts: dict[str, int]) -> MagicMock:
        presentation = MagicMock()
        presentation.fixed_type_count.side_effect = lambda shape: (
            class_uri_counts[shape] if shape else 0
        )
        return presentation

    def test_prefers_the_class_whose_shape_fixes_the_most_types(self) -> None:
        article = "http://example.org/Article"
        expression = "http://example.org/Expression"
        unconfigured = "http://example.org/Unconfigured"
        shapes = {article: "ArticleShape", expression: "ExpressionShape"}
        with (
            patch(
                "heritrace.utils.shacl_utils.determine_shape_for_classes",
                side_effect=lambda classes: shapes.get(classes[0]),
            ),
            patch(
                "heritrace.utils.display_rules_utils.get_presentation",
                return_value=self._shapes_for(
                    {"ArticleShape": 2, "ExpressionShape": 1}
                ),
            ),
        ):
            assert (
                get_highest_priority_class([unconfigured, expression, article])
                == article
            )

    def test_returns_none_without_classes(self) -> None:
        with patch(
            "heritrace.utils.display_rules_utils.get_presentation",
            return_value=self._shapes_for({}),
        ):
            assert get_highest_priority_class([]) is None

    def test_keeps_the_first_class_on_a_tie(self) -> None:
        with (
            patch(
                "heritrace.utils.shacl_utils.determine_shape_for_classes",
                return_value=None,
            ),
            patch(
                "heritrace.utils.display_rules_utils.get_presentation",
                return_value=self._shapes_for({}),
            ),
        ):
            assert (
                get_highest_priority_class(
                    ["http://example.org/Person", "http://example.org/Organization"]
                )
                == "http://example.org/Person"
            )


class TestProcessOrdering:
    """Tests for process_ordering function."""

    def test_process_ordering_with_sparql(self, mock_sparql) -> None:
        """Test processing ordering with SPARQL."""
        subject = "http://example.org/person1"
        predicate = "http://example.org/knows"
        order_property = "http://example.org/order"
        grouped_triples = {
            "Knows": {
                "triples": [
                    {
                        "triple": (
                            "http://example.org/person1",
                            "http://example.org/knows",
                            "http://example.org/person2",
                        ),
                        "object": "http://example.org/person2",
                    },
                    {
                        "triple": (
                            "http://example.org/person1",
                            "http://example.org/knows",
                            "http://example.org/person3",
                        ),
                        "object": "http://example.org/person3",
                    },
                ],
            },
        }
        display_name = "Knows"
        fetched_values_map = {}

        mock_sparql.query.return_value.convert.return_value = {
            "results": {
                "bindings": [
                    {
                        "orderedEntity": {"value": "http://example.org/person2"},
                        "nextValue": {"value": "http://example.org/person3"},
                    },
                    {
                        "orderedEntity": {"value": "http://example.org/person3"},
                        "nextValue": {"value": "NONE"},
                    },
                ],
            },
        }

        with patch(
            "heritrace.utils.display_rules_utils.get_sparql", return_value=mock_sparql
        ):
            ctx = GroupingContext(
                subject=subject,
                triples=[],
                grouped_triples=grouped_triples,
                fetched_values_map=fetched_values_map,
                relevant_properties=set(),
                historical_snapshot=None,
                highest_priority_class=None,
                highest_priority_shape=None,
                value_shapes={},
                value_triples={},
            )
            process_ordering(
                ctx,
                predicate,
                order_property,
                display_name,
            )

            assert (
                grouped_triples[display_name]["triples"][0]["object"]
                == "http://example.org/person2"
            )
            assert (
                grouped_triples[display_name]["triples"][1]["object"]
                == "http://example.org/person3"
            )

    @patch("heritrace.utils.display_rules_utils.get_sparql")
    def test_process_ordering_with_historical_snapshot(
        self, _mock_get_sparql, mock_historical_snapshot
    ) -> None:
        """Test processing ordering with historical snapshot."""
        subject = "http://example.org/person1"
        predicate = "http://example.org/knows"
        order_property = "http://example.org/order"
        grouped_triples = {
            "Knows": {
                "triples": [
                    {
                        "triple": (
                            "http://example.org/person1",
                            "http://example.org/knows",
                            "http://example.org/person2",
                        ),
                        "object": "http://example.org/person2",
                    },
                    {
                        "triple": (
                            "http://example.org/person1",
                            "http://example.org/knows",
                            "http://example.org/person3",
                        ),
                        "object": "http://example.org/person3",
                    },
                ],
            },
        }
        display_name = "Knows"
        fetched_values_map = {}

        ctx = GroupingContext(
            subject=subject,
            triples=[],
            grouped_triples=grouped_triples,
            fetched_values_map=fetched_values_map,
            relevant_properties=set(),
            historical_snapshot=mock_historical_snapshot,
            highest_priority_class=None,
            highest_priority_shape=None,
            value_shapes={},
            value_triples={},
        )
        process_ordering(
            ctx,
            predicate,
            order_property,
            display_name,
        )

        assert len(grouped_triples[display_name]["triples"]) == 2


class TestProcessDefaultProperty:
    """Tests for process_default_property function."""

    def test_process_default_property(self, mock_triples) -> None:
        """Test processing default property."""
        prop_uri = "http://example.org/age"
        grouped_triples = {}

        process_default_property(prop_uri, mock_triples, grouped_triples)

        assert prop_uri in grouped_triples
        assert grouped_triples[prop_uri]["property"] == prop_uri
        assert len(grouped_triples[prop_uri]["triples"]) == 1
        assert grouped_triples[prop_uri]["objectShape"] is None


GROUPING_SHAPES = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix shui: <http://www.w3.org/ns/shacl-ui/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/> .

[] a sh:ShapesGraph ;
  sh:declare [ sh:prefix "ex" ; sh:namespace "http://example.org/"^^xsd:anyURI ] .

ex:ArticleShape a sh:NodeShape ;
  sh:targetClass ex:Article ;
  sh:property [ sh:path ex:title ; sh:name "Title" ; sh:order 1 ] ;
  sh:property [
    sh:path ex:contributor ; sh:node ex:EditorShape ; sh:name "Editor" ; sh:order 3
  ] ;
  sh:property [
    sh:path ex:contributor ; sh:node ex:AuthorShape ; sh:name "Author" ; sh:order 2
  ] .

ex:AuthorShape a sh:NodeShape ;
  sh:targetClass ex:Role ;
  sh:property [ sh:path ex:withRole ; sh:hasValue ex:author ] ;
  sh:property [
    sh:path rdfs:label ;
    shui:propertyRole shui:LabelRole ;
    sh:values [
      sh:select "SELECT ?name WHERE { $this ex:heldBy/ex:name ?name }"
    ] ;
  ] .

ex:EditorShape a sh:NodeShape ;
  sh:targetClass ex:Role ;
  sh:property [ sh:path ex:withRole ; sh:hasValue ex:editor ] .
"""


def test_grouped_triples_follow_the_shapes() -> None:
    ex = "http://example.org/"
    shapes = Graph().parse(data=GROUPING_SHAPES, format="turtle")
    presentation = read_presentation(shapes)
    article, author, editor, agent = (
        URIRef(ex + name) for name in ("article", "author", "editor", "agent")
    )
    snapshot = Graph()
    for triple in [
        (article, URIRef(ex + "title"), Literal("Dune")),
        (article, URIRef(ex + "contributor"), author),
        (article, URIRef(ex + "contributor"), editor),
        (author, RDF.type, URIRef(ex + "Role")),
        (author, URIRef(ex + "withRole"), URIRef(ex + "author")),
        (author, URIRef(ex + "heldBy"), agent),
        (agent, URIRef(ex + "name"), Literal("Frank Herbert")),
        (editor, RDF.type, URIRef(ex + "Role")),
        (editor, URIRef(ex + "withRole"), URIRef(ex + "editor")),
    ]:
        snapshot.add(triple)
    entity_key = (ex + "Article", ex + "ArticleShape")
    form_fields = {
        entity_key: {
            ex + "contributor": [
                {
                    "nodeShape": ex + "AuthorShape",
                    "detailsViewer": True,
                    "nestedShape": [
                        {
                            "uri": ex + "withRole",
                            "displayName": {"": "Role"},
                            "hidden": False,
                            "nodeShapes": [],
                            "entityType": ex + "Role",
                            "subjectShape": ex + "AuthorShape",
                        },
                        {
                            "uri": ex + "heldBy",
                            "displayName": {"": "Held By"},
                            "hidden": False,
                            "nodeShape": ex + "AgentShape",
                            "nodeShapes": [ex + "AgentShape"],
                        },
                    ],
                }
            ]
        }
    }
    module = "heritrace.utils.display_rules_utils"
    with (
        patch(f"{module}.get_presentation", return_value=presentation),
        patch(
            f"{module}.get_custom_filter",
            return_value=Filter({}, presentation, MagicMock),
        ),
        patch(f"{module}.get_form_fields", return_value=form_fields),
        patch("heritrace.utils.shacl_utils.get_shacl_graph", return_value=shapes),
        patch(
            "heritrace.utils.shacl_utils.get_presentation", return_value=presentation
        ),
    ):
        grouped, relevant = get_grouped_triples(
            article,
            list(snapshot.triples((article, None, None))),
            [ex + "title", ex + "contributor", ex + "extra"],
            historical_snapshot=snapshot,
            entity_key=entity_key,
        )

    assert relevant == {ex + "title", ex + "contributor", ex + "extra"}
    assert [
        (name, group["objectShape"])
        for name, group in grouped.items()
        if name != ex + "extra"
    ] == [
        ("Title", None),
        ("Author", ex + "AuthorShape"),
        ("Editor", ex + "EditorShape"),
    ]
    assert grouped["Title"]["triples"] == [
        {
            "object": "Dune",
            "subjectClass": ex + "Article",
            "subjectShape": ex + "ArticleShape",
            "objectShape": None,
            "triple": (str(article), ex + "title", Literal("Dune")),
        }
    ]
    assert grouped["Author"]["triples"] == [
        {
            "object": str(author),
            "subjectClass": ex + "Article",
            "subjectShape": ex + "ArticleShape",
            "objectShape": ex + "AuthorShape",
            "triple": (str(article), ex + "contributor", "Frank Herbert"),
            "external_entity": str(author),
            "details": [
                {
                    "name": "Role",
                    "values": [{"label": ex + "author", "uri": None}],
                },
                {
                    "name": "Held By",
                    "values": [{"label": str(agent), "uri": str(agent)}],
                },
            ],
        }
    ]
    assert grouped["Editor"]["triples"] == [
        {
            "object": str(editor),
            "subjectClass": ex + "Article",
            "subjectShape": ex + "ArticleShape",
            "objectShape": ex + "EditorShape",
            "triple": (str(article), ex + "contributor", editor),
        }
    ]
    assert grouped[ex + "extra"]["triples"] == []
