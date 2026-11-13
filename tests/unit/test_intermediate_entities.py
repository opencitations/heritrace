# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from pathlib import Path
from unittest.mock import MagicMock

from flask import Flask
from rdflib import Graph

from heritrace.configuration.shapes import read_shapes, unsupported_parts
from heritrace.extensions import identify_classes_with_multiple_shapes
from heritrace.utils.filters import Filter
from heritrace.utils.shacl_presentation import read_presentation
from heritrace.utils.shacl_utils import get_form_fields_from_shacl

CONFIGURATION = Path("example_configurations/paratext")
ARTICLE_KEY = (
    "http://purl.org/spar/fabio/JournalArticle",
    "http://schema.org/JournalArticleShape",
)
CITING = "http://purl.org/spar/cito/hasCitingEntity"
CITED = "http://purl.org/spar/cito/hasCitedEntity"
ROLE = "http://purl.org/spar/pro/isDocumentContextFor"
HELD_BY = "http://purl.org/spar/pro/isHeldBy"
ROLE_CLASS = "http://purl.org/spar/pro/RoleInTime"
ISSUE_CLASS = "http://purl.org/spar/fabio/JournalIssue"
PART_OF = "http://purl.org/vocab/frbr/core#partOf"


def _shapes() -> Graph:
    return Graph().parse(CONFIGURATION / "shacl.ttl", format="turtle")


def _article_fields() -> dict:
    return get_form_fields_from_shacl(_shapes(), Flask(__name__))[ARTICLE_KEY]


def _nested_uris(field: dict) -> set[str]:
    return {nested["uri"] for nested in field["nestedShape"]}


def test_an_inverse_path_leaves_out_the_property_of_the_path() -> None:
    fields = _article_fields()

    citing_side = fields[f"^{CITING}"][0]
    cited_side = fields[f"^{CITED}"][0]

    assert citing_side["displayName"] == {"en": "Citations", "it": "Citazioni"}
    assert citing_side["composite"] is True
    assert CITED in _nested_uris(citing_side)
    assert CITING not in _nested_uris(citing_side)
    assert CITING in _nested_uris(cited_side)
    assert CITED not in _nested_uris(cited_side)


def test_citation_links_only_search_existing_entities() -> None:
    cited_options = next(
        nested
        for nested in _article_fields()[f"^{CITING}"][0]["nestedShape"]
        if nested["uri"] == CITED
    )["or"]

    issue_shapes = {
        option["nodeShape"]
        for option in cited_options
        if option["entityType"] == ISSUE_CLASS
    }
    assert all(option["nestedShape"] == [] for option in cited_options)
    assert all(option["autocomplete"] for option in cited_options)
    assert all(
        option["objectClass"] == option["entityType"] for option in cited_options
    )
    assert issue_shapes == {
        "http://schema.org/IssueShape",
        "http://schema.org/SpecialIssueShape",
    }


def test_inverse_paths_appear_in_nested_forms() -> None:
    containers = next(iter(_article_fields()[PART_OF]))["or"]

    nested_paths = {
        nested["uri"] for option in containers for nested in option["nestedShape"]
    }

    assert f"^{CITING}" in nested_paths


def test_details_widgets_carry_every_field_of_the_nested_shape() -> None:
    authors = next(
        field
        for field in _article_fields()[ROLE]
        if field["nodeShape"] == "http://schema.org/AuthorShape"
    )

    assert authors["detailsEditor"] is True
    assert authors["detailsViewer"] is True
    assert HELD_BY in _nested_uris(authors)


def test_a_property_shape_can_declare_the_fields_shown_in_place() -> None:
    authors = next(
        field
        for field in _article_fields()[ROLE]
        if field["nodeShape"] == "http://schema.org/AuthorShape"
    )

    assert authors["detailPaths"] == [HELD_BY]


def test_shapes_with_inverse_paths_and_dash_terms_survive_the_model() -> None:
    shapes = _shapes()

    assert unsupported_parts(shapes, read_shapes(shapes)) == []


def test_classes_with_multiple_shapes_come_from_the_shapes() -> None:
    assert ROLE_CLASS in identify_classes_with_multiple_shapes(_shapes())


def test_an_incomplete_entity_is_named_after_its_local_name() -> None:
    shapes = _shapes()
    sparql = MagicMock()
    sparql.query.return_value.convert.side_effect = [
        {"head": {"vars": ["display"]}, "results": {"bindings": [{}]}},
        {"head": {"vars": ["value", "label"]}, "results": {"bindings": []}},
    ]

    label = Filter(read_presentation(shapes), lambda: sparql).value_label(
        "http://example.org/role", (ROLE_CLASS, "http://schema.org/AuthorShape")
    )

    assert label == "Role"
