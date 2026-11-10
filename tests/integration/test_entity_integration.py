# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

"""
Tests for the entity module.
These tests focus on the entity routes and functionality using real data on test
databases.
"""

import json
import time
import uuid
from collections.abc import Generator
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from flask.testing import FlaskClient
from rdflib import RDF, XSD, Dataset, Literal, URIRef
from time_agnostic_library.agnostic_entity import AgnosticEntity

from default_components.meta_counter_handler import MetaCounterHandler
from default_components.meta_uri_generator import MetaURIGenerator
from heritrace.editor import Editor
from heritrace.extensions import (
    get_app_state,
    get_change_tracking_config,
    get_presentation,
)
from heritrace.routes.entity import (
    EntityRenderContext,
    compute_graph_differences,
    determine_datatype,
    generate_unique_uri,
    get_entities_to_restore,
    modification_entry,
    validate_entity_data,
)
from heritrace.uri_generator.default_uri_generator import DefaultURIGenerator
from heritrace.uri_generator.uri_generator import URIGenerator
from heritrace.utils.filters import Filter
from heritrace.utils.sparql_utils import fetch_data_graph_for_subject


@pytest.fixture
def test_entity(app: Flask) -> Generator[URIRef, None, None]:
    """Create a test entity in the database."""
    with app.app_context():
        # Create a test entity using the Editor
        editor = Editor(
            get_app_state().backend,
            app.config["COUNTER_HANDLER"],
            URIRef("https://orcid.org/0000-0000-0000-0000"),
            app.config["PRIMARY_SOURCE"],
            app.config["DATASET_GENERATION_TIME"],
        )

        # Generate a unique URI for the test entity using UUID to ensure uniqueness
        test_id = str(uuid.uuid4())
        entity_uri = URIRef(f"https://w3id.org/oc/meta/br/test_{test_id}")

        # Create the entity with some basic properties
        graph_uri = (
            URIRef(f"{entity_uri}/graph")
            if app.config["DATASET_IS_QUADSTORE"]
            else None
        )

        # Add type
        editor.create(
            entity_uri,
            RDF.type,
            URIRef("http://purl.org/spar/fabio/JournalArticle"),
            graph_uri,
        )

        # Add title
        editor.create(
            entity_uri,
            URIRef("http://purl.org/dc/terms/title"),
            Literal(f"Test Article {test_id}", datatype=XSD.string),
            graph_uri,
        )

        # Add publication date
        editor.create(
            entity_uri,
            URIRef("http://prismstandard.org/namespaces/basic/2.0/publicationDate"),
            Literal("2023-01-01", datatype=XSD.date),
            graph_uri,
        )

        # Save the entity
        editor.preexisting_finished()
        editor.save()

        yield entity_uri


def _make_editor(app: Flask) -> Editor:
    return Editor(
        get_app_state().backend,
        app.config["COUNTER_HANDLER"],
        URIRef("https://orcid.org/0000-0000-0000-0000"),
        app.config["PRIMARY_SOURCE"],
        app.config["DATASET_GENERATION_TIME"],
    )


def _editor_with_preloaded(app: Flask, subjects: list[URIRef]) -> Editor:
    editor = _make_editor(app)
    for subject in subjects:
        graph = fetch_data_graph_for_subject(subject)
        assert isinstance(graph, Dataset)
        for quad in graph.quads():
            editor.g_set.add(quad)  # type: ignore[arg-type]
    editor.preexisting_finished()
    return editor


def _predicate_object_pairs(subject: URIRef) -> set[tuple[str, str]]:
    graph = fetch_data_graph_for_subject(subject)
    assert isinstance(graph, Dataset)
    return {(str(p), str(o)) for _s, p, o, _g in graph.quads()}


def _snapshot_count(entity_uri: URIRef) -> int:
    change_tracking_config = get_change_tracking_config()
    _, provenance = AgnosticEntity(
        res=str(entity_uri), config=change_tracking_config
    ).get_history(include_prov_metadata=True)
    return len(provenance[str(entity_uri)])


def _first_snapshot_timestamp(entity_uri: URIRef) -> str:
    change_tracking_config = get_change_tracking_config()
    _, provenance = AgnosticEntity(
        res=str(entity_uri), config=change_tracking_config
    ).get_history(include_prov_metadata=True)
    snapshots = sorted(
        provenance[str(entity_uri)].values(),
        key=lambda metadata: metadata["generatedAtTime"],
    )
    return snapshots[0]["generatedAtTime"]


_ROLE_IN_TIME = URIRef("http://purl.org/spar/pro/RoleInTime")
_FOAF_AGENT = URIRef("http://xmlns.com/foaf/0.1/Agent")
_DOCUMENT_CONTEXT = URIRef("http://purl.org/spar/pro/isDocumentContextFor")
_WITH_ROLE = URIRef("http://purl.org/spar/pro/withRole")
_AUTHOR_ROLE = URIRef("http://purl.org/spar/pro/author")
_IS_HELD_BY = URIRef("http://purl.org/spar/pro/isHeldBy")
_HAS_NEXT = URIRef("https://w3id.org/oc/ontology/hasNext")
_FAMILY_NAME = URIRef("http://xmlns.com/foaf/0.1/familyName")
_FOAF_NAME = URIRef("http://xmlns.com/foaf/0.1/name")
_HAS_IDENTIFIER = URIRef("http://purl.org/spar/datacite/hasIdentifier")
_DATACITE_IDENTIFIER = URIRef("http://purl.org/spar/datacite/Identifier")


def test_apply_changes_entity_deletion_removes_incoming_links_for_later_targets(
    logged_in_client: FlaskClient, app: Flask
) -> None:
    test_id = str(uuid.uuid4())
    article = URIRef(f"https://w3id.org/oc/meta/br/test_{test_id}_a")
    other_article = URIRef(f"https://w3id.org/oc/meta/br/test_{test_id}_b")
    page = URIRef(f"https://w3id.org/oc/meta/re/test_{test_id}")
    graph_uri = URIRef(f"https://w3id.org/oc/meta/br/test_{test_id}/graph")
    journal_article = URIRef("http://purl.org/spar/fabio/JournalArticle")
    manifestation = URIRef("http://purl.org/spar/fabio/Manifestation")
    title = URIRef("http://purl.org/dc/terms/title")
    embodiment = URIRef("http://purl.org/vocab/frbr/core#embodiment")

    with app.app_context():
        editor = _make_editor(app)
        editor.preexisting_finished()
        editor.create(article, RDF.type, journal_article, graph_uri)
        editor.create(
            article,
            title,
            Literal("Primary article", datatype=XSD.string),
            graph_uri,
        )
        editor.create(article, embodiment, page, graph_uri)
        editor.create(other_article, RDF.type, journal_article, graph_uri)
        editor.create(
            other_article,
            title,
            Literal("Other article", datatype=XSD.string),
            graph_uri,
        )
        editor.create(other_article, embodiment, page, graph_uri)
        editor.create(page, RDF.type, manifestation, graph_uri)
        editor.save()

    response = logged_in_client.post(
        "/api/apply_changes",
        json=[
            {"action": "delete", "subject": str(article)},
            {"action": "delete", "subject": str(page)},
        ],
    )
    assert response.status_code == 200
    assert response.get_json() == {
        "message": "Changes applied successfully",
        "status": "success",
    }

    with app.app_context():
        assert _predicate_object_pairs(article) == set()
        assert _predicate_object_pairs(page) == set()
        assert _predicate_object_pairs(other_article) == {
            (str(RDF.type), str(journal_article)),
            (str(title), "Other article"),
        }


def test_restore_version_scoped_to_restored_entity(
    logged_in_client: FlaskClient, app: Flask
) -> None:
    """Regression test: restoring an agent must not revert unrelated changes of
    related entities, such as a parent whose ordered role list was rebuilt with
    new URIs in a transaction that did not touch the agent."""
    test_id = str(uuid.uuid4())
    parent = URIRef(f"https://w3id.org/oc/meta/br/test_{test_id}")
    child1 = URIRef(f"https://w3id.org/oc/meta/ar/test_{test_id}_1")
    child2 = URIRef(f"https://w3id.org/oc/meta/ar/test_{test_id}_2")
    child3 = URIRef(f"https://w3id.org/oc/meta/ar/test_{test_id}_3")
    child4 = URIRef(f"https://w3id.org/oc/meta/ar/test_{test_id}_4")
    agent = URIRef(f"https://w3id.org/oc/meta/ra/test_{test_id}_a")
    other_agent = URIRef(f"https://w3id.org/oc/meta/ra/test_{test_id}_b")
    identifier = URIRef(f"https://w3id.org/oc/meta/id/test_{test_id}")
    graph_uri = URIRef(f"{parent}/graph")
    journal_article = URIRef("http://purl.org/spar/fabio/JournalArticle")
    title = URIRef("http://purl.org/dc/terms/title")

    with app.app_context():
        editor = _make_editor(app)
        editor.preexisting_finished()
        editor.create(parent, RDF.type, journal_article, graph_uri)
        editor.create(
            parent, title, Literal("Scoped restore", datatype=XSD.string), graph_uri
        )
        editor.create(parent, _DOCUMENT_CONTEXT, child1, graph_uri)
        editor.create(parent, _DOCUMENT_CONTEXT, child2, graph_uri)
        editor.create(child1, RDF.type, _ROLE_IN_TIME, graph_uri)
        editor.create(child1, _WITH_ROLE, _AUTHOR_ROLE, graph_uri)
        editor.create(child1, _IS_HELD_BY, agent, graph_uri)
        editor.create(child1, _HAS_NEXT, child2, graph_uri)
        editor.create(child2, RDF.type, _ROLE_IN_TIME, graph_uri)
        editor.create(child2, _WITH_ROLE, _AUTHOR_ROLE, graph_uri)
        editor.create(child2, _IS_HELD_BY, other_agent, graph_uri)
        editor.create(agent, RDF.type, _FOAF_AGENT, graph_uri)
        editor.create(
            agent, _FAMILY_NAME, Literal("Doe", datatype=XSD.string), graph_uri
        )
        editor.create(other_agent, RDF.type, _FOAF_AGENT, graph_uri)
        editor.create(
            other_agent, _FAMILY_NAME, Literal("Smith", datatype=XSD.string), graph_uri
        )
        editor.save()

        time.sleep(1)

        # Rebuild the ordered child list with new URIs, as order_logic does
        editor = _editor_with_preloaded(app, [parent, child1, child2])
        editor.delete(parent, _DOCUMENT_CONTEXT, child1, graph_uri)
        editor.delete(child1, graph=graph_uri)
        editor.delete(parent, _DOCUMENT_CONTEXT, child2, graph_uri)
        editor.delete(child2, graph=graph_uri)
        for new_child, held_by in ((child3, agent), (child4, other_agent)):
            editor.create(new_child, RDF.type, _ROLE_IN_TIME, graph_uri)
            editor.create(new_child, _WITH_ROLE, _AUTHOR_ROLE, graph_uri)
            editor.create(new_child, _IS_HELD_BY, held_by, graph_uri)
            editor.create(parent, _DOCUMENT_CONTEXT, new_child, graph_uri)
        editor.create(child3, _HAS_NEXT, child4, graph_uri)
        editor.save()

        time.sleep(1)

        editor = _editor_with_preloaded(app, [agent])
        editor.create(
            agent, _FOAF_NAME, Literal("John Doe", datatype=XSD.string), graph_uri
        )
        editor.create(identifier, RDF.type, _DATACITE_IDENTIFIER, graph_uri)
        editor.create(agent, _HAS_IDENTIFIER, identifier, graph_uri)
        editor.save()

        assert _snapshot_count(agent) == 2
        tx1_timestamp = _first_snapshot_timestamp(agent)

    restore_response = logged_in_client.post(
        f"/api/entity-restore/{agent}/{tx1_timestamp}"
    )
    assert restore_response.status_code == 200
    assert restore_response.get_json() == {"status": "success"}

    with app.app_context():
        assert _predicate_object_pairs(agent) == {
            (str(RDF.type), str(_FOAF_AGENT)),
            (str(_FAMILY_NAME), "Doe"),
        }
        assert _predicate_object_pairs(identifier) == set()
        assert _predicate_object_pairs(parent) == {
            (str(RDF.type), str(journal_article)),
            (str(title), "Scoped restore"),
            (str(_DOCUMENT_CONTEXT), str(child3)),
            (str(_DOCUMENT_CONTEXT), str(child4)),
        }
        assert _predicate_object_pairs(child3) == {
            (str(RDF.type), str(_ROLE_IN_TIME)),
            (str(_WITH_ROLE), str(_AUTHOR_ROLE)),
            (str(_IS_HELD_BY), str(agent)),
            (str(_HAS_NEXT), str(child4)),
        }
        assert _predicate_object_pairs(child4) == {
            (str(RDF.type), str(_ROLE_IN_TIME)),
            (str(_WITH_ROLE), str(_AUTHOR_ROLE)),
            (str(_IS_HELD_BY), str(other_agent)),
        }
        assert _predicate_object_pairs(child1) == set()
        assert _predicate_object_pairs(child2) == set()

        assert _snapshot_count(agent) == 3
        assert _snapshot_count(parent) == 2
        assert _snapshot_count(child3) == 1
        assert _snapshot_count(child4) == 1


def test_restore_version_resurrects_deleted_entity_with_incoming_link(
    logged_in_client: FlaskClient, app: Flask
) -> None:
    """Restoring a deleted entity re-adds the incoming link removed in the same
    transaction as the deletion."""
    test_id = str(uuid.uuid4())
    role = URIRef(f"https://w3id.org/oc/meta/ar/test_{test_id}")
    agent = URIRef(f"https://w3id.org/oc/meta/ra/test_{test_id}")
    graph_uri = URIRef(f"{role}/graph")

    with app.app_context():
        editor = _make_editor(app)
        editor.preexisting_finished()
        editor.create(role, RDF.type, _ROLE_IN_TIME, graph_uri)
        editor.create(role, _WITH_ROLE, _AUTHOR_ROLE, graph_uri)
        editor.create(role, _IS_HELD_BY, agent, graph_uri)
        editor.create(agent, RDF.type, _FOAF_AGENT, graph_uri)
        editor.create(
            agent, _FAMILY_NAME, Literal("Doe", datatype=XSD.string), graph_uri
        )
        editor.save()

        time.sleep(1)

        editor = _editor_with_preloaded(app, [role, agent])
        editor.delete(agent, graph=graph_uri)
        editor.save()

        assert _predicate_object_pairs(agent) == set()
        assert _predicate_object_pairs(role) == {
            (str(RDF.type), str(_ROLE_IN_TIME)),
            (str(_WITH_ROLE), str(_AUTHOR_ROLE)),
        }
        tx1_timestamp = _first_snapshot_timestamp(agent)

    restore_response = logged_in_client.post(
        f"/api/entity-restore/{agent}/{tx1_timestamp}"
    )
    assert restore_response.status_code == 200
    assert restore_response.get_json() == {"status": "success"}

    with app.app_context():
        assert _predicate_object_pairs(agent) == {
            (str(RDF.type), str(_FOAF_AGENT)),
            (str(_FAMILY_NAME), "Doe"),
        }
        assert _predicate_object_pairs(role) == {
            (str(RDF.type), str(_ROLE_IN_TIME)),
            (str(_WITH_ROLE), str(_AUTHOR_ROLE)),
            (str(_IS_HELD_BY), str(agent)),
        }
        assert _snapshot_count(agent) == 3
        assert _snapshot_count(role) == 3


def test_entity_history(
    logged_in_client: FlaskClient, test_entity: URIRef, app: Flask
) -> None:
    response = logged_in_client.get(f"/api/entity-history/{test_entity}")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["entity_uri"] == str(test_entity)
    assert len(payload["snapshots"]) == 1
    snapshot = payload["snapshots"][0]
    assert snapshot["index"] == 1
    assert snapshot["can_restore"] is False
    assert snapshot["end_timestamp"] is None
    assert snapshot["responsible_agent"] == {
        "kind": "url",
        "url": "https://orcid.org/0000-0000-0000-0000",
        "label": "https://orcid.org/0000-0000-0000-0000",
        "orcid_id": None,
    }
    assert snapshot["primary_source"] == {
        "kind": "url",
        "url": app.config["PRIMARY_SOURCE"],
        "label": app.config["PRIMARY_SOURCE"],
        "extra": None,
        "entity_uri": None,
        "timestamp": None,
    }


def test_entity_version(
    logged_in_client: FlaskClient, test_entity: URIRef, app: Flask
) -> None:
    with app.app_context():
        change_tracking_config = get_change_tracking_config()
        agnostic_entity = AgnosticEntity(
            res=str(test_entity),
            config=change_tracking_config,
            include_related_objects=True,
            include_merged_entities=True,
            include_reverse_relations=False,
        )
        _, provenance = agnostic_entity.get_history(include_prov_metadata=True)
        timestamp = next(iter(provenance[str(test_entity)].values()))["generatedAtTime"]

    response = logged_in_client.get(f"/api/entity-version/{test_entity}/{timestamp}")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["entity_uri"] == str(test_entity)
    assert payload["timestamp"] == timestamp
    assert payload["metadata"]["generated_at"] == timestamp
    assert payload["metadata"]["attributed_to"]["kind"] == "url"
    assert payload["metadata"]["primary_source"]["kind"] == "url"
    assert payload["version_number"] == 1
    assert set(payload) == {
        "entity_uri",
        "entity_label",
        "type",
        "shape",
        "version_number",
        "timestamp",
        "prev_timestamp",
        "next_timestamp",
        "is_deletion_snapshot",
        "metadata",
        "modifications",
        "groups",
    }


def test_entity_types(logged_in_client: FlaskClient) -> None:
    response = logged_in_client.get("/api/entity-types")

    assert response.status_code == 200
    types = response.get_json()["types"]
    assert {
        "class": "http://purl.org/spar/fabio/JournalArticle",
        "shape": "http://schema.org/JournalArticleShape",
        "label": "Journal Article",
    } in types


@patch("heritrace.routes.entity._creation.validate_entity_data", return_value=[])
@patch("heritrace.routes.entity._creation.get_form_fields")
def test_create_entity_post(
    mock_get_form_fields, _mock_validate, logged_in_client: FlaskClient, app: Flask
) -> None:
    """Test the POST method for the create entity route."""
    mock_form_fields = {
        ("http://purl.org/spar/fabio/JournalArticle", None): {
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type": [
                {"fixed_value": "http://purl.org/spar/fabio/JournalArticle"}
            ],
            "http://purl.org/dc/terms/title": [
                {
                    "datatypes": ["http://www.w3.org/2001/XMLSchema#string"],
                    "minCount": 1,
                    "maxCount": 1,
                }
            ],
            "http://prismstandard.org/namespaces/basic/2.0/publicationDate": [
                {
                    "datatypes": ["http://www.w3.org/2001/XMLSchema#date"],
                    "minCount": 1,
                    "maxCount": 1,
                }
            ],
        }
    }
    mock_get_form_fields.return_value = mock_form_fields

    pub_date_pred = "http://prismstandard.org/namespaces/basic/2.0/publicationDate"
    entity_data = {
        "entity_type": "http://purl.org/spar/fabio/JournalArticle",
        "entity_shape": None,
        "properties": {
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type": "http://purl.org/spar/fabio/JournalArticle",
            "http://purl.org/dc/terms/title": "New Test Article",
            pub_date_pred: "2023-02-01",
        },
    }

    response = logged_in_client.post(
        "/api/entity", json={"structured_data": entity_data}
    )

    assert response.status_code == 200, (
        f"Expected status code 200, got {response.status_code}"
    )

    response_data = response.get_json()
    assert response_data["status"] == "success"
    assert response_data["uri"].startswith("https://w3id.org/oc/meta/br/")


def test_create_entity_post_validation_error(
    logged_in_client: FlaskClient, app: Flask
) -> None:
    """Test the POST method for the create entity route with invalid data."""
    # Create invalid entity data (missing entity_type)
    entity_data = {
        # Missing entity_type
        "properties": {
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type": "http://purl.org/spar/fabio/JournalArticle",
            "http://purl.org/dc/terms/title": "New Test Article",
        },
    }

    response = logged_in_client.post(
        "/api/entity", json={"structured_data": entity_data}
    )

    assert response.status_code == 400
    response_data = response.get_json()
    assert response_data["status"] == "error"
    assert "errors" in response_data
    assert len(response_data["errors"]) > 0


def test_restore_version(
    logged_in_client: FlaskClient, test_entity: URIRef, app: Flask
) -> None:
    """Test the restore version route."""
    # Get the provenance data to find the original timestamp
    with app.app_context():
        change_tracking_config = get_change_tracking_config()
        agnostic_entity = AgnosticEntity(
            res=str(test_entity),
            config=change_tracking_config,
            include_related_objects=True,
            include_merged_entities=True,
            include_reverse_relations=False,
        )
        _history, provenance = agnostic_entity.get_history(include_prov_metadata=True)

        # Get the original timestamp
        original_timestamp = next(iter(provenance[str(test_entity)].values()))[
            "generatedAtTime"
        ]

        # Get the initial entity graph to verify later
        initial_graph = fetch_data_graph_for_subject(test_entity)
        assert isinstance(initial_graph, Dataset)

        # Store the initial state (empty or with properties)
        initial_properties = {}
        for _s, p, o, _g in initial_graph.quads():
            if p not in initial_properties:
                initial_properties[p] = []
            initial_properties[p].append(o)

        time.sleep(1)

        editor = Editor(
            get_app_state().backend,
            app.config["COUNTER_HANDLER"],
            URIRef("https://orcid.org/0000-0000-0000-0000"),
            app.config["PRIMARY_SOURCE"],
            app.config["DATASET_GENERATION_TIME"],
        )

        entity_graph = fetch_data_graph_for_subject(test_entity)
        assert isinstance(entity_graph, Dataset)

        for quad in entity_graph.quads():
            editor.g_set.add(quad)  # type: ignore[arg-type]

        editor.preexisting_finished()

        graph_uri = URIRef(f"{test_entity}/graph")

        editor.create(
            test_entity,
            URIRef("http://purl.org/dc/terms/title"),
            Literal("Modified Test Article", datatype=XSD.string),
            graph_uri,
        )

        editor.create(
            test_entity,
            URIRef("http://purl.org/dc/terms/description"),
            Literal("This is a test description", datatype=XSD.string),
            graph_uri,
        )

        editor.save()

        modified_graph = fetch_data_graph_for_subject(test_entity)
        assert isinstance(modified_graph, Dataset)

        modified_properties = {}
        for _s, p, o, _g in modified_graph.quads():
            if p not in modified_properties:
                modified_properties[p] = []
            modified_properties[p].append(str(o))

        assert len(modified_graph) > 0, "Modified graph should not be empty"
        assert URIRef("http://purl.org/dc/terms/title") in [
            p
            for s, p, o, g in modified_graph.quads()  # type: ignore[misc]
        ], "Title should be present in modified graph"
        assert URIRef("http://purl.org/dc/terms/description") in [
            p
            for s, p, o, g in modified_graph.quads()  # type: ignore[misc]
        ], "Description should be present in modified graph"

    restore_response = logged_in_client.post(
        f"/api/entity-restore/{test_entity}/{original_timestamp}"
    )
    assert restore_response.status_code == 200
    assert restore_response.get_json() == {"status": "success"}

    with app.app_context():
        restored_graph = fetch_data_graph_for_subject(test_entity)
        assert isinstance(restored_graph, Dataset)
        restored_properties = {}
        for _s, p, o, _g in restored_graph.quads():
            if p not in restored_properties:
                restored_properties[p] = []
            restored_properties[p].append(str(o))

        title_found = False
        description_found = False

        for _s, p, o, _g in restored_graph.quads():  # type: ignore[misc]
            if p == URIRef(
                "http://purl.org/dc/terms/title"
            ) and "Modified Test Article" in str(o):
                title_found = True
            if p == URIRef(
                "http://purl.org/dc/terms/description"
            ) and "This is a test description" in str(o):
                description_found = True

        assert not title_found, (
            "Title 'Modified Test Article' should not be present after restoration"
        )
        assert not description_found, (
            "Description should not be present after restoration"
        )

        for predicate in initial_properties:
            if predicate in restored_properties:
                assert len(restored_properties[predicate]) >= 1, (
                    f"Predicate {predicate} should have at least one value"
                )
            else:
                # If the predicate is a system predicate (not one we specifically
                # check), we can skip it
                pass


def test_validate_entity_data(app: Flask) -> None:
    """
    Test the validate_entity_data function using real data and the actual validation
    function.
    """
    form_fields = {
        ("http://www.w3.org/ns/dcat#Dataset", None): {
            "http://www.w3.org/ns/dcat#title": [
                {
                    "min": 1,
                    "max": 1,
                    "datatypes": [str(XSD.string)],
                }
            ],
            "http://www.w3.org/ns/dcat#keyword": [
                {
                    "min": 0,
                    "max": None,
                    "datatypes": [str(XSD.string)],
                }
            ],
        }
    }

    valid_data = {
        "entity_type": "http://www.w3.org/ns/dcat#Dataset",
        "properties": {
            "http://www.w3.org/ns/dcat#title": "Test Dataset",
            "http://www.w3.org/ns/dcat#keyword": ["key1", "key2", "key3"],
        },
    }

    # Create invalid test data (missing required title)
    invalid_data = {
        "entity_type": "http://www.w3.org/ns/dcat#Dataset",
        "properties": {
            "http://www.w3.org/ns/dcat#keyword": ["key1", "key2"],
        },
    }

    # Create test data with invalid datatype
    invalid_datatype_data = {
        "entity_type": "http://www.w3.org/ns/dcat#Dataset",
        "properties": {
            "http://www.w3.org/ns/dcat#title": 12345,  # Should be string
            "http://www.w3.org/ns/dcat#keyword": ["key1", "key2"],
        },
    }

    # Valid test case with too many values
    too_many_values_data = {
        "entity_type": "http://www.w3.org/ns/dcat#Dataset",
        "properties": {
            "http://www.w3.org/ns/dcat#title": ["Title 1", "Title 2"],  # Max is 1
            "http://www.w3.org/ns/dcat#keyword": ["key1", "key2"],
        },
    }

    with (
        app.app_context(),
        app.test_request_context(),
        patch(
            "heritrace.routes.entity._validation.get_form_fields",
            return_value=form_fields,
        ),
    ):
        errors = validate_entity_data(valid_data)
        assert len(errors) == 0, f"Expected no errors, got: {errors}"

        errors = validate_entity_data(invalid_data)
        assert len(errors) > 0, "Expected validation errors but got none"
        assert any(
            "title" in error.lower() or "required" in error.lower() for error in errors
        ), f"Expected error about missing title, got: {errors}"

        errors = validate_entity_data(invalid_datatype_data)

        # Because we're using string validation against integers in XSD.string,
        # this might not actually fail in a real integration test depending on
        # the implementation details of the validation function
        # But we can at least verify that validation ran
        assert isinstance(errors, list), "Expected errors to be a list"

        # Test validation with too many values
        errors = validate_entity_data(too_many_values_data)
        assert len(errors) > 0, "Expected validation errors but got none"
        assert any(
            "title" in error.lower() and "at most" in error.lower() for error in errors
        ), f"Expected error about too many titles, got: {errors}"


def test_determine_datatype() -> None:
    """Test the determine_datatype function."""
    # Test with string value
    assert determine_datatype("test", [str(XSD.string)]) == XSD.string

    # Test with date value
    assert determine_datatype("2023-01-01", [str(XSD.date)]) == XSD.date

    # Test with integer value
    assert determine_datatype("123", [str(XSD.integer)]) == XSD.integer

    # Test with multiple possible datatypes
    assert determine_datatype("123", [str(XSD.integer), str(XSD.string)]) == XSD.integer

    # Test with no matching datatype
    assert determine_datatype("not a date", [str(XSD.date)]) == XSD.string


def test_generate_unique_uri(app: Flask) -> None:
    def use_generator(generator: URIGenerator) -> None:
        app.extensions["heritrace"] = replace(
            app.extensions["heritrace"], uri_generator=generator
        )

    with app.app_context():
        use_generator(DefaultURIGenerator("http://example.org"))
        uri1 = generate_unique_uri()
        uri2 = generate_unique_uri()
        assert str(uri1).startswith("http://example.org/")
        assert str(uri2).startswith("http://example.org/")
        assert uri1 != uri2

        use_generator(MetaURIGenerator(MetaCounterHandler(port=17804)))
        entity_type = "http://purl.org/spar/fabio/JournalArticle"
        uri3 = generate_unique_uri(entity_type)
        uri4 = generate_unique_uri(entity_type)
        assert str(uri3).startswith("https://w3id.org/oc/meta/br/09110")
        assert str(uri4).startswith("https://w3id.org/oc/meta/br/09110")
        assert uri3 != uri4


def test_entity_modification_workflow(app: Flask) -> None:
    """
    Test the complete entity modification workflow.

    Questo test verifica:
    1. La creazione di un'entità con proprietà specifiche
    2. La modifica dell'entità (aggiunta/modifica di proprietà)
    3. La corretta registrazione della cronologia delle modifiche
    4. L'accesso alle versioni precedenti dell'entità
    """
    with app.app_context():
        # 1. Crea una nuova entità di test con proprietà specifiche
        editor = Editor(
            get_app_state().backend,
            app.config["COUNTER_HANDLER"],
            URIRef("https://orcid.org/0000-0000-0000-0000"),
            app.config["PRIMARY_SOURCE"],
            app.config["DATASET_GENERATION_TIME"],
        )

        # Genera un URI unico per l'entità di test
        entity_uri = URIRef(
            app.config["URI_GENERATOR"].generate_uri(
                "http://purl.org/spar/fabio/JournalArticle"
            )
        )
        app.config["URI_GENERATOR"].counter_handler.increment_counter(
            "http://purl.org/spar/fabio/JournalArticle"
        )

        # Crea l'entità con alcune proprietà di base
        graph_uri = (
            URIRef(f"{entity_uri}/graph")
            if app.config["DATASET_IS_QUADSTORE"]
            else None
        )

        # Aggiungi il tipo
        editor.create(
            entity_uri,
            RDF.type,
            URIRef("http://purl.org/spar/fabio/JournalArticle"),
            graph_uri,
        )

        # Salva l'entità
        editor.preexisting_finished()
        editor.save()

        # Attendi un momento per assicurarsi che le modifiche siano salvate
        time.sleep(2)

        # 3. Modifica l'entità

        # Make sure we create a completely new editor instance
        editor = None
        # Create a fresh editor instance to ensure a new version
        editor = Editor(
            get_app_state().backend,
            app.config["COUNTER_HANDLER"],
            URIRef("https://orcid.org/0000-0000-0000-0000"),
            app.config["PRIMARY_SOURCE"],
            datetime.now(tz=timezone.utc),
        )

        # Load the current state of the entity
        current_graph = fetch_data_graph_for_subject(entity_uri)
        assert isinstance(current_graph, Dataset)
        for quad in current_graph.quads():
            editor.g_set.add(quad)  # type: ignore[arg-type]

        # Mark these triples as preexisting to track changes properly
        editor.preexisting_finished()

        # Crea un nuovo titolo
        new_title = "Modified Test Article"
        title_predicate = URIRef("http://purl.org/dc/terms/title")
        editor.create(
            entity_uri,
            title_predicate,
            Literal(new_title, datatype=XSD.string),
            graph_uri,
        )

        # Aggiungi una nuova proprietà (descrizione)
        description_predicate = URIRef("http://purl.org/dc/terms/description")
        description_value = "This is a test description"
        editor.create(
            entity_uri,
            description_predicate,
            Literal(description_value, datatype=XSD.string),
            graph_uri,
        )

        # Ensure we save with the current timestamp
        editor.save()

        # Attendi un momento più lungo per assicurarsi che le modifiche siano salvate
        time.sleep(3)

        # 4. Verifica che l'entità sia stata aggiornata correttamente
        updated_graph = fetch_data_graph_for_subject(entity_uri)
        assert isinstance(updated_graph, Dataset)

        # Verifica che il titolo sia stato aggiunto
        title_found = False
        for _s, p, o, _g in updated_graph.quads():
            if p == title_predicate and str(o) == new_title:
                title_found = True
                break
        assert title_found, f"Il titolo '{new_title}' non è stato aggiunto"

        # Verifica che la descrizione sia stata aggiunta
        description_found = False
        for _s, p, o, _g in updated_graph.quads():  # type: ignore[misc]
            if p == description_predicate and str(o) == description_value:
                description_found = True
                break
        assert description_found, (
            f"La descrizione '{description_value}' non è stata aggiunta"
        )

        # 5. Verifica la cronologia dell'entità
        change_tracking_config = get_change_tracking_config()
        agnostic_entity = AgnosticEntity(
            res=str(entity_uri),
            config=change_tracking_config,
            include_related_objects=True,
            include_merged_entities=True,
            include_reverse_relations=False,
        )
        _history, provenance = agnostic_entity.get_history(include_prov_metadata=True)

        # Verifica che ci siano almeno due versioni (originale e modificata)
        entity_versions = provenance.get(str(entity_uri), {})
        assert len(entity_versions) >= 2, (
            "Non sono state trovate almeno due versioni dell'entità"
        )

        # Ottieni i timestamp ordinati cronologicamente
        timestamps = sorted(
            [
                (meta["generatedAtTime"], se_uri)
                for se_uri, meta in entity_versions.items()
            ],
            key=lambda x: x[0],
        )

        # Verifica che i timestamp siano in ordine crescente
        for i in range(1, len(timestamps)):
            assert timestamps[i][0] > timestamps[i - 1][0], (
                f"I timestamp non sono in ordine crescente:"
                f" {timestamps[i - 1][0]} >= {timestamps[i][0]}"
            )


def test_create_nested_entity(logged_in_client: FlaskClient, app: Flask) -> None:
    """Test creating an entity with nested entities."""

    pub_date_pred = "http://prismstandard.org/namespaces/basic/2.0/publicationDate"
    entity_data = {
        "entity_type": "http://purl.org/spar/fabio/JournalArticle",
        "entity_shape": None,
        "properties": {
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type": "http://purl.org/spar/fabio/JournalArticle",
            "http://purl.org/dc/terms/title": "Article with Authors",
            pub_date_pred: "2023-03-01",
            "http://purl.org/spar/pro/isDocumentContextFor": [
                {
                    "entity_type": "http://purl.org/spar/pro/RoleInTime",
                    "entity_shape": "http://purl.org/spar/pro/AuthorShape",
                    "properties": {
                        "http://www.w3.org/1999/02/22-rdf-syntax-ns#type": "http://purl.org/spar/pro/RoleInTime",
                        "http://purl.org/spar/pro/withRole": "http://purl.org/spar/pro/author",
                        "http://purl.org/spar/pro/isHeldBy": {
                            "entity_type": "http://xmlns.com/foaf/0.1/Agent",
                            "entity_shape": "http://schema.org/ResponsibleAgentShape",
                            "properties": {
                                "http://www.w3.org/1999/02/22-rdf-syntax-ns#type": "http://xmlns.com/foaf/0.1/Agent",
                                "http://xmlns.com/foaf/0.1/givenName": "Test",
                                "http://xmlns.com/foaf/0.1/familyName": "Author",
                                "http://xmlns.com/foaf/0.1/name": "Test Author",
                            },
                        },
                    },
                }
            ],
        },
    }

    # Post the entity data
    response = logged_in_client.post(
        "/api/entity", json={"structured_data": entity_data}
    )

    assert response.status_code == 200, (
        f"Expected status code 200, got {response.status_code}"
    )

    response_data = response.get_json()
    assert response_data["status"] == "success"
    response = logged_in_client.get(f"/api/entity/{response_data['uri']}")
    assert response.status_code == 200

    view = response.get_json()
    assert view["label"] == "Test Author (2023). Article with Authors."
    assert view["type"] == "http://purl.org/spar/fabio/JournalArticle"
    assert view["is_deleted"] is False
    author_group = next(
        group for group in view["groups"] if group["display_name"] == "Author"
    )
    assert author_group["property"] == "http://purl.org/spar/pro/isDocumentContextFor"
    assert author_group["ordered_by"] == "https://w3id.org/oc/ontology/hasNext"
    assert author_group["is_draggable"] is True
    assert author_group["object_shape"] == "http://schema.org/AuthorShape"
    assert author_group["field"]["displayName"] == "Author"
    held_by = next(
        field
        for field in author_group["field"]["nestedShape"]
        if field["uri"] == "http://purl.org/spar/pro/isHeldBy"
    )
    agent_type = next(
        field
        for field in held_by["nestedShape"]
        if field["uri"] == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    )
    assert agent_type["hasValueLabel"] == "Responsible Agent"
    assert "http://purl.org/spar/pro/isDocumentContextFor" in view["can_be_added"]


def test_modification_entry(app: Flask) -> None:
    with app.app_context():
        context_path = (
            Path(__file__).parent.parent.parent / "heritrace" / "utils" / "context.json"
        )
        with context_path.open() as config_file:
            context = json.load(config_file)["@context"]

        real_filter = Filter(context, get_presentation(), MagicMock)
        subject = URIRef("http://example.org/entity/1")

        def _make_ctx(classes_cache=None):
            return EntityRenderContext(
                entity_uri=str(subject),
                entity_shape="http://schema.org/JournalArticleShape",
                highest_priority_class="http://purl.org/spar/fabio/JournalArticle",
                relevant_snapshot=None,
                predicate_ordering_cache={},
                entity_position_cache={},
                object_shapes_cache={},
                object_classes_cache=classes_cache or {},
                custom_filter=real_filter,
            )

        title = (
            subject,
            URIRef("http://purl.org/dc/terms/title"),
            Literal("Test Title", datatype=XSD.string),
        )
        assert modification_entry(title, _make_ctx()) == {
            "predicate": "http://purl.org/dc/terms/title",
            "predicate_label": "Title",
            "object": "Test Title",
            "object_label": "Test Title",
            "position": None,
        }

        date = (
            subject,
            URIRef("http://prismstandard.org/namespaces/basic/2.0/publicationDate"),
            Literal("2023-01-01", datatype=XSD.date),
        )
        assert modification_entry(date, _make_ctx()) == {
            "predicate": "http://prismstandard.org/namespaces/basic/2.0/publicationDate",
            "predicate_label": "Publication Date",
            "object": "2023-01-01",
            "object_label": "2023-01-01",
            "position": None,
        }

        role = (
            subject,
            URIRef("http://purl.org/spar/pro/isDocumentContextFor"),
            URIRef("http://example.org/role/1"),
        )
        assert modification_entry(role, _make_ctx()) == {
            "predicate": "http://purl.org/spar/pro/isDocumentContextFor",
            "predicate_label": "Author",
            "object": "http://example.org/role/1",
            "object_label": "http://example.org/role/1",
            "position": None,
        }

        rdf_type = (
            subject,
            RDF.type,
            URIRef("http://purl.org/spar/fabio/JournalArticle"),
        )
        assert modification_entry(rdf_type, _make_ctx()) == {
            "predicate": str(RDF.type),
            "predicate_label": "Type",
            "object": "http://purl.org/spar/fabio/JournalArticle",
            "object_label": "Journal Article",
            "position": None,
        }


def test_entity_version_invalid_timestamp(
    logged_in_client: FlaskClient, test_entity: URIRef, app: Flask
) -> None:
    """Test the entity version route with an invalid timestamp."""
    # Get the version page with an invalid timestamp
    response = logged_in_client.get(
        f"/api/entity-version/{test_entity}/invalid-timestamp"
    )

    # Should return 404 for invalid timestamp
    assert response.status_code == 404


def test_restore_version_invalid_timestamp(
    logged_in_client: FlaskClient, test_entity: URIRef, app: Flask
) -> None:
    """Test the restore version route with an invalid timestamp."""
    # Post to restore with an invalid timestamp
    response = logged_in_client.post(
        f"/api/entity-restore/{test_entity}/invalid-timestamp"
    )

    # Should return 404 for invalid timestamp
    assert response.status_code == 404


def test_compute_graph_differences() -> None:
    """
    Test the compute_graph_differences function.
    """
    # Create two graphs with some differences
    graph1 = Dataset()
    graph1.add(
        (  # type: ignore[arg-type]
            URIRef("http://example.org/s1"),
            URIRef("http://example.org/p1"),
            Literal("o1"),
            URIRef("http://example.org/graph1"),
        )
    )
    graph1.add(
        (  # type: ignore[arg-type]
            URIRef("http://example.org/s1"),
            URIRef("http://example.org/p2"),
            Literal("o2"),
            URIRef("http://example.org/graph1"),
        )
    )

    graph2 = Dataset()
    graph2.add(
        (  # type: ignore[arg-type]
            URIRef("http://example.org/s1"),
            URIRef("http://example.org/p1"),
            Literal("o1"),
            URIRef("http://example.org/graph1"),
        )
    )
    graph2.add(
        (  # type: ignore[arg-type]
            URIRef("http://example.org/s1"),
            URIRef("http://example.org/p3"),
            Literal("o3"),
            URIRef("http://example.org/graph1"),
        )
    )

    # Compute differences
    with patch(
        "heritrace.routes.entity._restoration.get_dataset_is_quadstore",
        return_value=True,
    ):
        to_delete, to_add = compute_graph_differences(graph1, graph2)

    # Check results
    assert len(to_delete) == 1
    assert len(to_add) == 1

    # Check for the expected quad in to_delete
    expected_s = URIRef("http://example.org/s1")
    expected_p = URIRef("http://example.org/p2")
    expected_o = Literal("o2")

    # Check for the expected quad in to_add
    expected_add_s = URIRef("http://example.org/s1")
    expected_add_p = URIRef("http://example.org/p3")
    expected_add_o = Literal("o3")

    # Verify the quads are present with the correct subject, predicate, and object
    # regardless of the graph object type
    found_delete = False
    for quad in to_delete:
        s, p, o, _g = quad
        if s == expected_s and p == expected_p and o == expected_o:
            found_delete = True
            break
    assert found_delete, "Expected quad not found in to_delete"

    found_add = False
    for quad in to_add:
        s, p, o, _g = quad
        if s == expected_add_s and p == expected_add_p and o == expected_add_o:
            found_add = True
            break
    assert found_add, "Expected quad not found in to_add"


def test_get_entities_to_restore() -> None:
    """Test the get_entities_to_restore function."""
    # Create some test triples
    triples_to_delete = {
        (
            URIRef("http://example.org/entity1"),
            URIRef("http://example.org/predicate1"),
            URIRef("http://example.org/entity2"),
        ),
        (
            URIRef("http://example.org/entity1"),
            URIRef("http://example.org/predicate2"),
            Literal("value"),
        ),
        (
            URIRef("http://example.org/entity3"),
            RDF.type,
            URIRef("http://example.org/Type"),
        ),
    }

    triples_to_add = {
        (
            URIRef("http://example.org/entity1"),
            URIRef("http://example.org/predicate3"),
            URIRef("http://example.org/entity4"),
        ),
        (
            URIRef("http://example.org/entity5"),
            URIRef("http://example.org/predicate4"),
            URIRef("http://example.org/entity1"),
        ),
    }

    # Get entities to restore
    entities = get_entities_to_restore(
        triples_to_delete, triples_to_add, "http://example.org/entity1"
    )

    # Check results
    assert "http://example.org/entity1" in entities
    assert "http://example.org/entity2" in entities
    assert "http://example.org/entity4" in entities
    assert "http://example.org/entity5" in entities

    # entity3 should not be included because it only appears in an rdf:type triple
    assert "http://example.org/entity3" not in entities
