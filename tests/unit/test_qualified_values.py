# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from collections.abc import Generator
from unittest.mock import patch

import pytest
from flask import Flask
from rdflib import RDF, Graph, URIRef
from rdflib.namespace import DCTERMS

from heritrace.utils.shacl_utils import get_form_fields_from_shacl
from heritrace.utils.shacl_validation import cardinality_error, get_valid_predicates

FABIO = "http://purl.org/spar/fabio/"
VOLUME = URIRef("https://example.org/volume")
TOPIC = "https://example.org/Topic"
SHAPES = Graph().parse(
    data=f"""
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix fabio: <{FABIO}> .

<https://example.org/VolumeShape> sh:targetClass fabio:JournalVolume ;
  sh:property [
    sh:path rdf:type ;
    sh:qualifiedValueShape [ sh:hasValue fabio:JournalVolume ] ;
    sh:qualifiedMinCount 1 ;
    sh:qualifiedMaxCount 1
  ] , [
    sh:path rdf:type ;
    sh:qualifiedValueShape [ sh:hasValue fabio:Expression ] ;
    sh:qualifiedMinCount 1 ;
    sh:qualifiedMaxCount 1
  ] , [
    sh:path dcterms:type ;
    sh:qualifiedValueShape [
      sh:or ( [ sh:hasValue fabio:Book ] [ sh:hasValue fabio:Thesis ] )
    ] ;
    sh:qualifiedMaxCount 1
  ] , [
    sh:path dcterms:subject ;
    sh:qualifiedValueShape [ sh:hasValue <{TOPIC}> ] ;
    sh:qualifiedMaxCount 1
  ] .
""",
    format="turtle",
)


@pytest.fixture
def shapes_app(app: Flask) -> Generator[Flask, None, None]:
    with patch("heritrace.utils.shacl_validation.get_shacl_graph", return_value=SHAPES):
        yield app


def _volume(*triples: tuple[URIRef, str]) -> Graph:
    graph = Graph()
    for predicate, value in triples:
        graph.add((VOLUME, predicate, URIRef(value)))
    return graph


@pytest.mark.usefixtures("shapes_app")
def test_each_field_counts_only_its_qualified_values() -> None:
    volume = _volume(
        (RDF.type, f"{FABIO}JournalVolume"),
        (RDF.type, f"{FABIO}Expression"),
        (DCTERMS.type, f"{FABIO}Book"),
        (DCTERMS.type, f"{FABIO}Manuscript"),
    )
    without_expression = _volume((RDF.type, f"{FABIO}JournalVolume"))
    two_genres = volume + _volume((DCTERMS.type, f"{FABIO}Thesis"))

    assert [
        cardinality_error(volume, VOLUME, RDF.type),
        cardinality_error(volume, VOLUME, DCTERMS.type),
        cardinality_error(without_expression, VOLUME, RDF.type),
        cardinality_error(two_genres, VOLUME, DCTERMS.type),
    ] == [
        None,
        None,
        "The property Type requires at least 1 value equal to 'Expression'",
        "The property Type allows at most 1 value among 'Book', 'Thesis'",
    ]


@pytest.mark.usefixtures("shapes_app")
def test_a_qualified_value_without_a_minimum_is_offered_rather_than_fixed() -> None:
    fields = get_form_fields_from_shacl(SHAPES, Flask(__name__))[
        (f"{FABIO}JournalVolume", "https://example.org/VolumeShape")
    ]
    _, _, _, mandatory_values, optional_values, _ = get_valid_predicates(
        [(VOLUME, RDF.type, URIRef(f"{FABIO}JournalVolume"))],
        URIRef(f"{FABIO}JournalVolume"),
    )

    assert [
        (field["hasValue"], field["optionalValues"], field["min"], field["max"])
        for field in fields[str(DCTERMS.subject)] + fields[str(RDF.type)]
    ] == [
        (None, [TOPIC], 0, 1),
        (f"{FABIO}JournalVolume", [], 1, 1),
        (f"{FABIO}Expression", [], 1, 1),
    ]
    assert (dict(mandatory_values), optional_values[str(DCTERMS.subject)]) == (
        {str(RDF.type): [f"{FABIO}JournalVolume", f"{FABIO}Expression"]},
        [TOPIC],
    )
