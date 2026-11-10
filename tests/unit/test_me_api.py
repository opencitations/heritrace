# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from unittest.mock import patch

from flask.testing import FlaskClient
from rdflib import XSD, Graph, Literal

from heritrace.configuration.vocabulary import DASH, SH
from heritrace.utils.datatypes import get_datatype_options
from tests.test_config import TestConfig


def test_me_for_anonymous_users_exposes_only_the_config(client: FlaskClient) -> None:
    response = client.get("/api/me")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["user"] is None
    assert payload["default_primary_source"] is None
    assert payload["config"] == {
        "app_title": "ParaText Test",
        "app_subtitle": "Bibliographical database - Test Environment",
        "shacl": True,
        "datatype_options": get_datatype_options(),
    }


def test_me_for_signed_in_users_includes_the_user_and_default_source(
    logged_in_client: FlaskClient,
) -> None:
    with patch(
        "heritrace.routes.api.get_user_default_primary_source",
        return_value="https://example.org/source",
    ) as default_source:
        response = logged_in_client.get("/api/me")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["user"] == {
        "id": "0000-0000-0000-0000",
        "name": "Test User",
        "orcid": "0000-0000-0000-0000",
    }
    assert payload["default_primary_source"] == "https://example.org/source"
    default_source.assert_called_once_with("0000-0000-0000-0000")


def test_entity_types_are_listed_with_their_labels(
    logged_in_client: FlaskClient,
) -> None:
    response = logged_in_client.get("/api/entity-types")

    assert response.status_code == 200
    types = response.get_json()["types"]
    assert {
        "class": "http://purl.org/spar/fabio/Article",
        "shape": "http://schema.org/ArticleShape",
        "label": "Article",
    } in types
    assert {
        "class": "http://purl.org/spar/fabio/JournalArticle",
        "shape": "http://schema.org/JournalArticleShape",
        "label": "Journal Article",
    } in types


def test_entity_types_leave_out_hidden_shapes(logged_in_client: FlaskClient) -> None:
    shapes = Graph().parse(TestConfig.CONFIG_DIR / "shacl.ttl")
    true = Literal("true", datatype=XSD.boolean)
    hidden = {str(shape) for shape in shapes.subjects(DASH.hidden, true)}
    targeted = {str(shape) for shape in shapes.subjects(SH.targetClass)}

    response = logged_in_client.get("/api/entity-types")

    listed = {entry["shape"] for entry in response.get_json()["types"]}
    assert hidden
    assert listed == targeted - hidden
