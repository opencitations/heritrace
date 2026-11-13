# SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from unittest.mock import MagicMock, patch

import pytest
from rdflib import Graph, Literal, URIRef

from heritrace.utils.filters import Filter, field_with_labels, format_uri_as_readable
from heritrace.utils.shacl_presentation import (
    labels_use_inverse_relations,
    read_presentation,
)

EX = "http://example.org/"

SHAPES = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix shui: <http://www.w3.org/ns/shacl-ui/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/> .

[] a sh:ShapesGraph ;
  sh:declare [ sh:prefix "ex" ; sh:namespace "http://example.org/"^^xsd:anyURI ] .

ex:BookShape a sh:NodeShape ;
  sh:targetClass ex:Book ;
  sh:name "Book" ;
  sh:property [
    sh:path ex:contributor ;
    sh:node ex:AuthorShape ;
    sh:name "Author" ;
    sh:order 2 ;
  ] ;
  sh:property [
    sh:path ex:contributor ;
    sh:node ex:EditorShape ;
    sh:name "Editor" ;
    sh:order 3 ;
  ] ;
  sh:property [
    sh:path ex:title ;
    sh:name "Title" ;
    sh:order 1 ;
  ] ;
  sh:property [
    sh:path rdfs:label ;
    shui:propertyRole shui:LabelRole ;
    sh:values [ sh:select "SELECT ?label WHERE { $this ex:title ?label }" ] ;
  ] .

ex:hardcover rdfs:label "Hardcover"@en .
ex:paperBack rdfs:label "Paper back from the shapes"@en .

ex:PageShape a sh:NodeShape ;
  sh:targetClass ex:Page ;
  sh:name "Page" .

ex:AuthorShape a sh:NodeShape ;
  sh:targetClass ex:Role ;
  sh:property [
    sh:path ex:name ;
    shui:propertyRole shui:LabelRole ;
  ] .

ex:EditorShape a sh:NodeShape ;
  sh:targetClass ex:Role ;
  sh:property [
    sh:path rdfs:label ;
    shui:propertyRole shui:LabelRole ;
    sh:values [
      sh:select "SELECT ?label WHERE { ?book ex:contributor $this ; ex:title ?label }"
    ] ;
  ] .
"""

BOOK_KEY = (EX + "Book", EX + "BookShape")


@pytest.fixture
def shapes_filter():
    presentation = read_presentation(Graph().parse(data=SHAPES, format="turtle"))
    return Filter(presentation, MagicMock)


def test_class_names_come_from_node_shapes(shapes_filter) -> None:
    assert shapes_filter.human_readable_class(BOOK_KEY) == "Book"
    assert shapes_filter.human_readable_class((EX + "Role", EX + "AuthorShape")) == (
        "Role"
    )
    assert shapes_filter.human_readable_class(None) == "Unknown"
    assert shapes_filter.human_readable_class((None, None)) == "Unknown"


def test_value_labels_follow_the_shacl_ui_order(shapes_filter) -> None:
    data = Graph().parse(
        data=f"""
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        <{EX}book1> <{EX}title> "Dune" ; rdfs:label "Ignored" .
        <{EX}book2> rdfs:label "Book two"@en, "Libro due"@it .
        <{EX}paperBack> rdfs:label "Paperback"@en .
        """,
        format="turtle",
    )

    def label(value: URIRef | Literal, key=(None, None)) -> str:
        return shapes_filter.value_label(value, key, data)

    assert label(Literal("Dune")) == "Dune"
    assert label(URIRef(EX + "book1"), BOOK_KEY) == "Dune"
    assert label(URIRef(EX + "book2"), BOOK_KEY) == "Book two"
    assert label(URIRef(EX + "paperBack")) == "Paperback"
    assert label(URIRef(EX + "hardcover")) == "Hardcover"
    assert label(URIRef(EX + "page1"), (EX + "Page", EX + "PageShape")) == "Page1"
    assert label(URIRef("https://other.org/isbnCode")) == "Isbn code"


def test_predicate_names_depend_on_the_object_shape(shapes_filter) -> None:
    contributor = EX + "contributor"
    assert (
        shapes_filter.human_readable_predicate(
            contributor, BOOK_KEY, object_shape_uri=EX + "EditorShape"
        )
        == "Editor"
    )
    assert shapes_filter.human_readable_predicate(contributor, BOOK_KEY) == "Author"
    assert shapes_filter.human_readable_predicate(EX + "isbnCode", BOOK_KEY) == (
        "Isbn code"
    )
    assert shapes_filter.human_readable_predicate("https://other.org/x", BOOK_KEY) == (
        "X"
    )


def test_option_names_and_descriptions_follow_the_label_rule() -> None:
    graph = Graph().parse(
        data="""
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix ex: <http://example.org/> .

        [] sh:path ex:cover ; sh:in ( ex:hardcover ex:paperBack ) .
        ex:hardcover rdfs:label "Hardcover"@en, "Copertina rigida"@it ;
          rdfs:comment "A cover made of board."@en .
        """,
        format="turtle",
    )
    shapes_filter = Filter(read_presentation(graph), MagicMock)

    field = field_with_labels(
        {"optionalValues": [EX + "hardcover", EX + "paperBack"]}, shapes_filter
    )

    assert field["optionalValueLabels"] == {
        EX + "hardcover": "Hardcover",
        EX + "paperBack": "Paper back",
    }
    assert field["optionalValueDescriptions"] == {
        EX + "hardcover": "A cover made of board."
    }


def test_entity_labels_follow_the_label_role(shapes_filter) -> None:
    data = Graph()
    book, role = URIRef(EX + "book/1"), URIRef(EX + "role/1")
    data.add((book, URIRef(EX + "title"), Literal("Dune")))
    data.add((book, URIRef(EX + "contributor"), role))
    data.add((role, URIRef(EX + "name"), Literal("Frank Herbert")))

    assert shapes_filter.value_label(book, BOOK_KEY, data) == "Dune"
    assert (
        shapes_filter.value_label(role, (EX + "Role", EX + "AuthorShape"), data)
        == "Frank Herbert"
    )
    assert (
        shapes_filter.value_label(role, (EX + "Role", EX + "EditorShape"), data)
        == "Dune"
    )
    assert (
        shapes_filter.value_label(EX + "x", (EX + "Thing", EX + "ThingShape"), data)
        == "X"
    )


def test_entity_labels_from_the_dataset_endpoint(shapes_filter) -> None:
    sparql = MagicMock()
    sparql.query.return_value.convert.return_value = {
        "head": {"vars": ["label"]},
        "results": {"bindings": [{"label": {"type": "literal", "value": "Dune"}}]},
    }
    with patch.object(shapes_filter, "_get_sparql", return_value=sparql):
        assert shapes_filter.value_label(EX + "book/1", BOOK_KEY) == "Dune"
    sparql.setQuery.assert_called_once_with(
        "PREFIX ex: <http://example.org/>\n"
        "SELECT ?label WHERE { <http://example.org/book/1> ex:title ?label }"
    )


def test_inverse_relations_are_needed_only_by_inverse_labels(shapes_filter) -> None:
    assert labels_use_inverse_relations(shapes_filter.presentation) is True
    book_only = read_presentation(
        Graph().parse(
            data=SHAPES.split("ex:AuthorShape a sh:NodeShape", maxsplit=1)[0],
            format="turtle",
        )
    )
    assert labels_use_inverse_relations(book_only) is False


@pytest.mark.parametrize(
    ("uri", "readable"),
    [
        ("http://example.org/hasPublicationDate", "Has publication date"),
        ("http://www.w3.org/2001/XMLSchema#anyURI", "Any URI"),
        ("http://www.w3.org/2001/XMLSchema#NCName", "NC name"),
        ("http://www.w3.org/2001/XMLSchema#ENTITIES", "ENTITIES"),
        ("http://www.w3.org/2001/XMLSchema#base64Binary", "Base64 binary"),
        ("http://example.org/cittàNatale", "Città natale"),
    ],
)
def test_readable_names_keep_acronyms_whole(uri: str, readable: str) -> None:
    assert format_uri_as_readable(uri) == readable


def test_format_source_reference_none(shapes_filter) -> None:
    assert shapes_filter.format_source_reference(None) == {
        "kind": "unknown",
        "url": None,
        "label": "Unknown",
        "extra": None,
        "entity_uri": None,
        "timestamp": None,
    }


def test_format_source_reference_version(shapes_filter) -> None:
    result = shapes_filter.format_source_reference("http://example.org/br/1/prov/se/3")
    assert result == {
        "kind": "version",
        "url": "http://example.org/br/1/prov/se/3",
        "label": "Version 3",
        "extra": None,
        "entity_uri": "http://example.org/br/1",
        "timestamp": "3",
    }


def test_format_source_reference_generic_url(shapes_filter) -> None:
    url = "http://example.org/resource/123"
    assert shapes_filter.format_source_reference(url) == {
        "kind": "url",
        "url": url,
        "label": url,
        "extra": None,
        "entity_uri": None,
        "timestamp": None,
    }


def test_format_source_reference_text(shapes_filter) -> None:
    assert shapes_filter.format_source_reference("not a valid url") == {
        "kind": "text",
        "url": None,
        "label": "not a valid url",
        "extra": None,
        "entity_uri": None,
        "timestamp": None,
    }


def test_format_source_reference_zenodo_url(shapes_filter) -> None:
    url = "https://zenodo.org/record/12345"
    zenodo_ref = {
        "kind": "zenodo",
        "url": url,
        "label": "Citation",
        "extra": None,
        "entity_uri": None,
        "timestamp": None,
    }
    with patch(
        "heritrace.utils.filters.zenodo_source", return_value=zenodo_ref
    ) as mock_zenodo:
        assert shapes_filter.format_source_reference(url) == zenodo_ref
    mock_zenodo.assert_called_once_with(url)


def test_format_agent_reference_none(shapes_filter) -> None:
    assert shapes_filter.format_agent_reference(None) == {
        "kind": "unknown",
        "url": None,
        "label": "Unknown",
        "orcid_id": None,
    }


def test_format_agent_reference_orcid_url(shapes_filter) -> None:
    url = "https://orcid.org/0000-0001-2345-6789"
    orcid_ref = {
        "kind": "orcid",
        "url": url,
        "label": "Jane Doe",
        "orcid_id": "0000-0001-2345-6789",
    }
    with patch(
        "heritrace.utils.filters.orcid_agent", return_value=orcid_ref
    ) as mock_orcid:
        assert shapes_filter.format_agent_reference(url) == orcid_ref
    mock_orcid.assert_called_once_with(url)


def test_format_agent_reference_generic_url(shapes_filter) -> None:
    url = "http://example.org/person/123"
    assert shapes_filter.format_agent_reference(url) == {
        "kind": "url",
        "url": url,
        "label": url,
        "orcid_id": None,
    }


def test_format_agent_reference_text(shapes_filter) -> None:
    assert shapes_filter.format_agent_reference("not a valid url") == {
        "kind": "text",
        "url": None,
        "label": "not a valid url",
        "orcid_id": None,
    }
