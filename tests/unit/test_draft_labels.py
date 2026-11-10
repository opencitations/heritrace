# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pyparsing import ParseException
from rdflib import Graph

from heritrace.utils.draft_labels import draft_label
from heritrace.utils.filters import Filter
from heritrace.utils.shacl_presentation import ShapesPresentation, read_presentation

FOAF = "http://xmlns.com/foaf/0.1/"
DATACITE = "http://purl.org/spar/datacite/"
LITERAL = "http://www.essepuntato.it/2010/06/literalreification/hasLiteralValue"
PRO = "http://purl.org/spar/pro/"


def labels_from(presentation: ShapesPresentation):
    return patch(
        "heritrace.utils.draft_labels.get_custom_filter",
        return_value=Filter({}, presentation, MagicMock),
    )


def configuration_labels(configuration: str):
    graph = Graph().parse(
        Path("example_configurations") / configuration / "shacl.ttl", format="turtle"
    )
    return labels_from(read_presentation(graph))


@pytest.fixture
def configured_draft_labels():
    with configuration_labels("opencitations_meta"):
        yield


def identifier_entry(properties):
    return {
        "parent_class": FOAF + "Agent",
        "parent_shape": "http://schema.org/ResponsibleAgentShape",
        "predicate": DATACITE + "hasIdentifier",
        "entity": {
            "entity_type": DATACITE + "Identifier",
            "entity_shape": "http://schema.org/AgentIdentifierShape",
            "properties": properties,
        },
    }


def test_draft_relation_labels(logged_in_client, configured_draft_labels):
    identifier = identifier_entry(
        {
            DATACITE + "usesIdentifierScheme": [DATACITE + "orcid"],
            LITERAL: ["0000-0002-8420-0696"],
        }
    )
    author = {
        "parent_class": "http://purl.org/spar/fabio/JournalArticle",
        "parent_shape": "http://schema.org/JournalArticleShape",
        "predicate": PRO + "isDocumentContextFor",
        "entity": {
            "entity_type": PRO + "RoleInTime",
            "entity_shape": "http://schema.org/AuthorShape",
            "properties": {
                PRO + "withRole": PRO + "author",
                PRO + "isHeldBy": {
                    "entity_type": FOAF + "Agent",
                    "entity_shape": "http://schema.org/ResponsibleAgentShape",
                    "properties": {
                        FOAF + "name": ["Arcangelo Massari"],
                        DATACITE + "hasIdentifier": [identifier["entity"]],
                    },
                },
            },
        },
    }
    response = logged_in_client.post(
        "/api/draft-labels", json={"entries": [author, identifier]}
    )
    assert response.status_code == 200
    assert response.json == {
        "labels": [
            "Arcangelo Massari [orcid:0000-0002-8420-0696]",
            "orcid:0000-0002-8420-0696",
        ]
    }


def test_incomplete_and_unconfigured_drafts(logged_in_client, configured_draft_labels):
    incomplete = identifier_entry(
        {DATACITE + "usesIdentifierScheme": [DATACITE + "doi"]}
    )
    unconfigured = identifier_entry({LITERAL: ["abc"]})
    unconfigured["predicate"] = "https://example.org/related"
    unconfigured["entity"]["entity_type"] = "https://example.org/Unknown"
    unconfigured["entity"]["entity_shape"] = ""
    response = logged_in_client.post(
        "/api/draft-labels", json={"entries": [incomplete, unconfigured]}
    )
    assert response.status_code == 200
    assert response.json == {"labels": [None, None]}


def test_entity_rule_and_existing_reference(app, configured_draft_labels):
    entry = identifier_entry(
        {
            DATACITE + "usesIdentifierScheme": [DATACITE + "doi"],
            LITERAL: ["10.1234/example"],
        }
    )
    entry["parent_class"] = "https://example.org/Unknown"
    entry["parent_shape"] = ""
    with app.app_context(), patch("heritrace.utils.sparql_utils.get_sparql") as remote:
        assert draft_label(entry) == "doi:10.1234/example"
        entry["entity"].update(
            is_existing_entity=True, entity_uri="https://w3id.org/oc/meta/id/1"
        )
        assert draft_label(entry) == "doi:10.1234/example"
        del entry["entity"]["properties"]
        assert draft_label(entry) is None
        remote.assert_not_called()


@pytest.mark.parametrize(
    ("uri", "expected"),
    [
        ("https://w3id.org/oc/meta/ra/1", "Ada Lovelace [omid:ra/1]"),
        ("https://example.org/agent/1", "Ada Lovelace"),
    ],
)
def test_saved_author_uses_available_properties(
    app, configured_draft_labels, uri, expected
):
    entry = {
        "parent_class": "https://example.org/Unknown",
        "parent_shape": "",
        "predicate": "https://example.org/related",
        "entity": {
            "entity_type": FOAF + "Agent",
            "entity_shape": "http://schema.org/ResponsibleAgentShape",
            "is_existing_entity": True,
            "entity_uri": uri,
            "properties": {FOAF + "name": ["Ada Lovelace"]},
        },
    }
    with app.app_context(), patch("heritrace.utils.sparql_utils.get_sparql") as remote:
        assert draft_label(entry) == expected
        remote.assert_not_called()


@pytest.mark.parametrize("with_reference", [False, True])
def test_author_names_need_no_dataset(
    logged_in_client, configured_draft_labels, with_reference
):
    properties: dict[str, list[str] | list[dict[str, str | bool]]] = {
        FOAF + "givenName": ["Theodore A."],
        FOAF + "familyName": ["Slotkin"],
    }
    if with_reference:
        properties[DATACITE + "hasIdentifier"] = [
            {
                "is_existing_entity": True,
                "entity_uri": "https://w3id.org/oc/meta/id/1",
            }
        ]
    entry = {
        "parent_class": "http://purl.org/spar/fabio/JournalArticle",
        "parent_shape": "http://schema.org/JournalArticleShape",
        "predicate": PRO + "isDocumentContextFor",
        "entity": {
            "entity_type": PRO + "RoleInTime",
            "entity_shape": "http://schema.org/AuthorShape",
            "properties": {
                PRO + "withRole": PRO + "author",
                PRO + "isHeldBy": {
                    "entity_type": FOAF + "Agent",
                    "entity_shape": "http://schema.org/ResponsibleAgentShape",
                    "properties": properties,
                },
            },
        },
    }
    with patch("heritrace.utils.sparql_utils.get_sparql") as remote:
        response = logged_in_client.post("/api/draft-labels", json={"entries": [entry]})
        assert response.status_code == 200
        assert response.json == {"labels": ["Slotkin, Theodore A."]}
        remote.assert_not_called()


def test_draft_label_query_errors_propagate(app):
    presentation = ShapesPresentation(
        shape_names={},
        properties={},
        fixed_type_counts={},
        label_queries={"http://schema.org/AgentIdentifierShape": "invalid SPARQL"},
    )
    with app.app_context(), labels_from(presentation), pytest.raises(ParseException):
        draft_label(identifier_entry({LITERAL: ["abc"]}))


def test_draft_rules_use_field_datatypes(logged_in_client):
    entity_class = "https://example.org/Measurement"
    entity_shape = "https://example.org/MeasurementShape"
    predicate = "https://example.org/value"
    presentation = ShapesPresentation(
        shape_names={},
        properties={},
        fixed_type_counts={},
        label_queries={
            entity_shape: """
                SELECT (STR(?value) AS ?display) WHERE {
                    $this <https://example.org/value> ?value .
                    FILTER(?value = 42)
                }
            """
        },
    )
    entry = identifier_entry({predicate: ["42"]})
    entry["entity"]["entity_type"] = entity_class
    entry["entity"]["entity_shape"] = entity_shape
    fields = {
        (entity_class, entity_shape): {
            predicate: [{"datatypes": ["http://www.w3.org/2001/XMLSchema#integer"]}],
        }
    }
    with (
        labels_from(presentation),
        patch("heritrace.utils.draft_labels.get_form_fields", return_value=fields),
    ):
        response = logged_in_client.post("/api/draft-labels", json={"entries": [entry]})
    assert response.status_code == 200
    assert response.json == {"labels": ["42"]}


@pytest.mark.parametrize(
    ("predicate", "shape"),
    [("^http://purl.org/spar/cito/hasCitingEntity", "CitationShape")],
)
def test_inverse_path_uses_entity_label(logged_in_client, predicate, shape):
    entry = {
        "parent_class": "http://purl.org/spar/fabio/JournalArticle",
        "parent_shape": "http://schema.org/JournalArticleShape",
        "predicate": predicate,
        "entity": {
            "entity_type": "http://purl.org/spar/cito/Citation",
            "entity_shape": "http://schema.org/" + shape,
            "properties": {
                "http://purl.org/spar/cito/" + relation: {
                    "entity_type": "http://purl.org/spar/fabio/Book",
                    "entity_shape": "http://schema.org/BookShape",
                    "properties": {"http://purl.org/dc/terms/title": [title]},
                }
                for relation, title in [
                    ("hasCitingEntity", "Source book"),
                    ("hasCitedEntity", "Target book"),
                ]
            },
        },
    }
    with configuration_labels("paratext"):
        response = logged_in_client.post("/api/draft-labels", json={"entries": [entry]})
    assert response.status_code == 200
    assert response.json == {"labels": ['Citation from "Source book" to "Target book"']}
