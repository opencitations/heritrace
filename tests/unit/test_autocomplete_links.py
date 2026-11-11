# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from pathlib import Path

from flask import Flask
from rdflib import Graph

from heritrace.configuration.shapes import read_shapes, shapes_to_graph
from heritrace.configuration.vocabulary import SH
from heritrace.utils.shacl_presentation import read_presentation
from heritrace.utils.shacl_utils import get_form_fields_from_shacl

CONFIGURATION = Path("example_configurations/opencitations_meta")
SHAPES = "http://schema.org/"
ARTICLE = "http://purl.org/spar/fabio/JournalArticle"
PART_OF = "http://purl.org/vocab/frbr/core#partOf"
ROLE = "http://purl.org/spar/pro/isDocumentContextFor"
HELD_BY = "http://purl.org/spar/pro/isHeldBy"
HAS_NEXT = "https://w3id.org/oc/ontology/hasNext"
_SH_CLASS = SH["class"]


def _form_fields() -> dict:
    shapes = Graph().parse(CONFIGURATION / "shacl.ttl", format="turtle")
    return get_form_fields_from_shacl(shapes, Flask(__name__))


def _article_field(predicate: str) -> dict:
    return _form_fields()[(ARTICLE, f"{SHAPES}JournalArticleShape")][predicate][0]


def test_every_alternative_of_a_link_uses_the_autocomplete() -> None:
    alternatives = _article_field(PART_OF)["or"]

    assert alternatives
    assert all(alternative["autocomplete"] for alternative in alternatives)


def test_a_role_shows_its_fields_in_place() -> None:
    role = _article_field(ROLE)

    assert role["detailsEditor"] is True
    assert role["detailsViewer"] is True
    assert HELD_BY in {nested["uri"] for nested in role["nestedShape"]}


def test_a_role_follows_the_order_set_in_its_shape() -> None:
    assert _article_field(ROLE)["orderedBy"] == HAS_NEXT


def test_the_classes_of_a_link_survive_the_shape_model() -> None:
    shapes = Graph().parse(CONFIGURATION / "shacl.ttl", format="turtle")

    regenerated = shapes_to_graph(read_shapes(shapes))

    assert len(set(regenerated.objects(None, _SH_CLASS))) == len(
        set(shapes.objects(None, _SH_CLASS))
    )


def test_presentation_counts_the_types_a_shape_fixes() -> None:
    shapes = Graph().parse(CONFIGURATION / "shacl.ttl", format="turtle")

    presentation = read_presentation(shapes)

    assert presentation.fixed_type_count(f"{SHAPES}JournalArticleShape") == 2
    assert presentation.fixed_type_count(f"{SHAPES}ExpressionShape") == 1
    assert presentation.fixed_type_count(None) == 0
