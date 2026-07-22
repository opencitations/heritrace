# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

"""
Tests for the apply_changes API route in heritrace/routes/api.py.
"""

import json
from unittest import mock
from unittest.mock import MagicMock, patch

from flask import Flask
from flask.testing import FlaskClient
from rdflib import Literal, URIRef

from heritrace.utils.strategies import OrphanHandlingStrategy, ProxyHandlingStrategy


@patch("heritrace.routes.api.import_entity_graph")
@patch("heritrace.routes.api.create_logic")
@patch("heritrace.utils.shacl_validation.validate_new_triple")
@patch("heritrace.routes.api.g")
def test_apply_changes_create(
    mock_g,
    mock_validate_new_triple,
    mock_create_logic,
    mock_import_entity_graph,
    logged_in_client: FlaskClient,
    app: Flask,
) -> None:
    """Test the apply_changes endpoint with a create action."""
    mock_g.resource_lock_manager = MagicMock()
    mock_editor = MagicMock()
    mock_import_entity_graph.return_value = mock_editor

    mock_create_logic.return_value = "http://example.org/entity/1"

    changes = [
        {
            "action": "create",
            "subject": "http://example.org/entity/1",
            "data": {
                "http://example.org/property/1": [
                    {
                        "value": "Test Value",
                        "datatype": "http://www.w3.org/2001/XMLSchema#string",
                    }
                ]
            },
            "affected_entities": [],
            "delete_affected": False,
        }
    ]

    response = logged_in_client.post("/api/apply_changes", json=changes)

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert "Changes applied successfully" in data["message"]

    mock_import_entity_graph.assert_called_once()
    mock_editor.save.assert_called_once()


@patch("heritrace.routes.api.import_entity_graph")
@patch("heritrace.routes.api.update_logic")
@patch("heritrace.utils.shacl_validation.validate_new_triple")
@patch("heritrace.routes.api.g")
def test_apply_changes_update(
    mock_g,
    mock_validate_new_triple,
    mock_update_logic,
    mock_import_entity_graph,
    logged_in_client: FlaskClient,
    app: Flask,
) -> None:
    """Test the apply_changes endpoint with an update action."""
    mock_g.resource_lock_manager = MagicMock()
    mock_editor = MagicMock()
    mock_import_entity_graph.return_value = mock_editor

    mock_validate_new_triple.return_value = (
        Literal("New Value"),
        Literal("Old Value"),
        "",
    )

    changes = [
        {
            "action": "update",
            "subject": "http://example.org/entity/1",
            "predicate": "http://example.org/property/1",
            "object": "Old Value",
            "newObject": "New Value",
            "entity_type": "http://example.org/Person",
            "affected_entities": [],
            "delete_affected": False,
        }
    ]

    response = logged_in_client.post("/api/apply_changes", json=changes)

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert "Changes applied successfully" in data["message"]

    mock_import_entity_graph.assert_called_once()
    mock_editor.save.assert_called_once()


@patch("heritrace.routes.api.import_entity_graph")
@patch("heritrace.routes.api.delete_logic")
@patch("heritrace.utils.shacl_validation.validate_new_triple")
@patch("heritrace.routes.api.g")
def test_apply_changes_delete(
    mock_g,
    mock_validate_new_triple,
    mock_delete_logic,
    mock_import_entity_graph,
    logged_in_client: FlaskClient,
    app: Flask,
) -> None:
    """Test the apply_changes endpoint with a delete action."""
    mock_g.resource_lock_manager = MagicMock()
    mock_editor = MagicMock()
    mock_import_entity_graph.return_value = mock_editor

    mock_validate_new_triple.return_value = (None, Literal("Value to Delete"), "")

    changes = [
        {
            "action": "delete",
            "subject": "http://example.org/entity/1",
            "predicate": "http://example.org/property/1",
            "object": "Value to Delete",
            "entity_type": "http://example.org/Person",
            "affected_entities": [],
            "delete_affected": False,
        }
    ]

    response = logged_in_client.post("/api/apply_changes", json=changes)

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert "Changes applied successfully" in data["message"]

    mock_import_entity_graph.assert_called_once()
    mock_editor.save.assert_called_once()


@patch("heritrace.routes.api.import_entity_graph")
@patch("heritrace.routes.api.delete_logic")
@patch("heritrace.routes.api.g")
def test_apply_changes_delete_integer_literal(
    mock_g,
    mock_delete_logic,
    mock_import_entity_graph,
    logged_in_client: FlaskClient,
) -> None:
    mock_g.resource_lock_manager = MagicMock()
    mock_editor = MagicMock()
    mock_import_entity_graph.return_value = mock_editor

    response = logged_in_client.post(
        "/api/apply_changes",
        json=[
            {
                "action": "delete",
                "subject": "http://example.org/entity/1",
                "predicate": "http://example.org/property/1",
                "object": 123,
                "affected_entities": [],
                "delete_affected": False,
            }
        ],
    )

    assert response.status_code == 200
    assert response.get_json()["status"] == "success"
    mock_delete_logic.assert_called_once_with(
        mock.ANY,
        URIRef("http://example.org/property/1"),
        "123",
    )


@patch("heritrace.routes.api.import_entity_graph")
@patch("heritrace.routes.api.order_logic")
@patch("heritrace.routes.api.g")
def test_apply_changes_order(
    mock_g,
    mock_order_logic,
    mock_import_entity_graph,
    logged_in_client: FlaskClient,
    app: Flask,
) -> None:
    """Test the apply_changes endpoint with an order action."""
    mock_g.resource_lock_manager = MagicMock()
    mock_editor = MagicMock()
    mock_import_entity_graph.return_value = mock_editor

    mock_order_logic.return_value = None

    changes = [
        {
            "action": "order",
            "subject": "http://example.org/entity/1",
            "predicate": "http://example.org/property/1",
            "object": ["Value1", "Value2", "Value3"],
            "newObject": ["Value2", "Value3", "Value1"],
            "affected_entities": [],
            "delete_affected": False,
        }
    ]

    response = logged_in_client.post("/api/apply_changes", json=changes)

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert "Changes applied successfully" in data["message"]

    mock_import_entity_graph.assert_called_once()
    mock_editor.save.assert_called_once()


@patch("heritrace.routes.api.import_entity_graph")
@patch("heritrace.routes.api.delete_logic")
@patch("heritrace.utils.shacl_validation.validate_new_triple")
@patch("heritrace.routes.api.g")
def test_apply_changes_with_affected_entities(
    mock_g,
    mock_validate_new_triple,
    mock_delete_logic,
    mock_import_entity_graph,
    logged_in_client: FlaskClient,
    app: Flask,
) -> None:
    """
    Test apply_changes handles affected entities (orphans/proxies) and duplicate
    deletions correctly.
    """
    mock_g.resource_lock_manager = MagicMock()
    mock_editor = MagicMock()
    mock_import_entity_graph.return_value = mock_editor

    mock_validate_new_triple.return_value = (None, Literal("Value to Delete"), "")

    app.config["ORPHAN_HANDLING_STRATEGY"] = OrphanHandlingStrategy.DELETE
    app.config["PROXY_HANDLING_STRATEGY"] = ProxyHandlingStrategy.DELETE

    # --- Test Scenario Data ---
    # 1. orphan1 will be deleted in phase 1 (orphan handling).
    # 2. proxy1 will be deleted in phase 1 (proxy handling).
    # 3. Duplicate orphan/proxy entries will be skipped in phase 1 (continue L543,
    # L558).
    # 4. A full entity deletion for orphan1 will be attempted in phase 2, should be
    # skipped (continue L573).
    # 5. A triple deletion where proxy1 is the object will be attempted in phase 2,
    # should be skipped (continue L581).
    orphan_uri = "http://example.org/orphan/1"
    proxy_uri = "http://example.org/proxy/1"
    main_entity_uri = "http://example.org/main/1"
    main_entity_predicate = "http://example.org/pred/1"
    main_entity_object = "Value to Delete"
    full_delete_target_uri = "http://example.org/full/delete/target"

    changes = [
        {
            "action": "delete",
            "subject": main_entity_uri,
            "predicate": main_entity_predicate,
            "object": main_entity_object,
            "entity_type": "http://example.org/MainType",
            "affected_entities": [
                {"uri": orphan_uri, "is_intermediate": False},  # First orphan
                {"uri": proxy_uri, "is_intermediate": True},  # First proxy
                {
                    "uri": orphan_uri,
                    "is_intermediate": False,
                },  # Duplicate orphan (for L543)
                {
                    "uri": proxy_uri,
                    "is_intermediate": True,
                },  # Duplicate proxy (for L558)
            ],
            "delete_affected": True,  # Instructs to delete orphans/proxies
        },
        # Attempt to delete the full orphan entity (should be skipped by L573)
        {
            "action": "delete",
            "subject": orphan_uri,
            "entity_type": "http://example.org/OrphanType",
        },
        # Attempt to delete a triple where the proxy is the object (should be skipped by
        # L581)
        {
            "action": "delete",
            "subject": "http://example.org/another/subj",
            "predicate": "http://example.org/relates/to",
            "object": proxy_uri,
            "entity_type": "http://example.org/AnotherType",
        },
        # Delete a full entity that wasn't an orphan/proxy (should hit L576)
        {
            "action": "delete",
            "subject": full_delete_target_uri,
            "entity_type": "http://example.org/FullDeleteType",
        },
        # A normal triple deletion for verification (will be processed again)
        {
            "action": "delete",
            "subject": main_entity_uri,
            "predicate": main_entity_predicate,
            "object": main_entity_object,
            "entity_type": "http://example.org/MainType",
        },
    ]

    response = logged_in_client.post("/api/apply_changes", json=changes)

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert "Changes applied successfully" in data["message"]

    mock_import_entity_graph.assert_has_calls(
        [
            mock.call(
                mock.ANY,
                URIRef(main_entity_uri),
                include_referencing_entities=False,
            ),
            mock.call(
                mock_editor,
                URIRef(full_delete_target_uri),
                include_referencing_entities=True,
            ),
            mock.call(
                mock_editor,
                URIRef(orphan_uri),
                include_referencing_entities=True,
            ),
            mock.call(
                mock_editor,
                URIRef(proxy_uri),
                include_referencing_entities=True,
            ),
        ]
    )
    assert mock_import_entity_graph.call_count == 4

    # Verify delete_logic calls:
    # Expected calls:
    # 1. For the unique orphan (phase 1)
    # 2. For the unique proxy (phase 1)
    # 3. For the full entity deletion (phase 2, L576)
    # 4 & 5. For the normal triple deletion (phase 2, L584, called twice as object is
    # literal)
    assert mock_delete_logic.call_count == 5

    # Check calls specifically for unique affected entities (should be called only once
    # each in phase 1)
    orphan_delete_calls = [
        call
        for call in mock_delete_logic.call_args_list
        if call[0][0].subject == URIRef(orphan_uri)
    ]
    proxy_delete_calls = [
        call
        for call in mock_delete_logic.call_args_list
        if call[0][0].subject == URIRef(proxy_uri)
    ]
    assert len(orphan_delete_calls) == 1, (
        f"Expected 1 delete call for orphan"
        f" {orphan_uri},"
        f" got {len(orphan_delete_calls)}"
    )
    assert len(proxy_delete_calls) == 1, (
        f"Expected 1 delete call for proxy {proxy_uri}, got {len(proxy_delete_calls)}"
    )

    # Check call specifically for the full entity deletion (phase 2)
    full_delete_calls = [
        call
        for call in mock_delete_logic.call_args_list
        if call[0][0].subject == URIRef(full_delete_target_uri)
        and call[0][0].entity_type == "http://example.org/FullDeleteType"
    ]
    assert len(full_delete_calls) == 1

    # Check that delete_logic was NOT called for the skipped operations in Phase 2
    # Full orphan entity deletion (skipped by L573)
    skipped_orphan_full_delete_calls = [
        call
        for call in mock_delete_logic.call_args_list
        if call[0][0].subject == URIRef(orphan_uri)
        and call[0][0].entity_type == "http://example.org/OrphanType"
        and len(call[0]) == 1  # no predicate/object_value
    ]
    assert len(skipped_orphan_full_delete_calls) == 0

    # More robust check for the skipped proxy object deletion call
    found_skipped_proxy_object_delete_call = False
    for call in mock_delete_logic.call_args_list:
        args, _kwargs = call
        op = args[0]
        if (
            op.subject == URIRef("http://example.org/another/subj")
            and len(args) > 2
            and str(args[2]) == proxy_uri
            and op.entity_type == "http://example.org/AnotherType"
        ):
            found_skipped_proxy_object_delete_call = True
            break
    assert not found_skipped_proxy_object_delete_call, (
        "delete_logic call for triple with deleted proxy object was found, but should"
        "have been skipped"
    )

    # Verify editor save was called
    mock_editor.save.assert_called_once()


@patch("heritrace.routes.api.g")
def test_apply_changes_no_data(
    mock_g, logged_in_client: FlaskClient, app: Flask
) -> None:
    """Test the apply_changes endpoint returns 400 when no data is provided."""
    mock_g.resource_lock_manager = (
        MagicMock()
    )  # Mock this to avoid potential AttributeError

    # Test with JSON "null" (explicitly set Content-Type)
    response_null = logged_in_client.post(
        "/api/apply_changes",
        data="null",  # Send the JSON literal "null"
        content_type="application/json",
    )
    assert response_null.status_code == 400
    data_null = json.loads(response_null.data)
    assert data_null["error"] == "No request data provided"

    # Test with empty list (Flask client sets Content-Type automatically)
    response_empty = logged_in_client.post("/api/apply_changes", json=[])
    assert response_empty.status_code == 400
    data_empty = json.loads(response_empty.data)
    assert data_empty["error"] == "No request data provided"


@patch("heritrace.routes.api.import_entity_graph")
@patch("heritrace.routes.api.g")  # Mock g
def test_apply_changes_validation_error(
    mock_g,
    mock_import_entity_graph,
    logged_in_client: FlaskClient,
    app: Flask,  # Use logged_in_client
) -> None:
    """Test the apply_changes endpoint with a validation error."""
    mock_g.resource_lock_manager = MagicMock()
    mock_editor = MagicMock()
    mock_editor.save.side_effect = ValueError("Invalid data")
    mock_import_entity_graph.return_value = mock_editor

    # Test data
    changes = [
        {
            "action": "create",
            "subject": "http://example.org/entity/1",
            "data": {
                "http://example.org/property/1": [
                    {
                        "value": "Test Value",
                        "datatype": "http://www.w3.org/2001/XMLSchema#string",
                    }
                ]
            },
            "affected_entities": [],
            "delete_affected": False,
        }
    ]

    response = logged_in_client.post("/api/apply_changes", json=changes)

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert data["error_type"] == "validation"
    assert "Invalid data" in data["message"]


@patch("heritrace.routes.api.import_entity_graph")
@patch("heritrace.routes.api.g")  # Mock g
def test_apply_changes_server_error(
    mock_g,
    mock_import_entity_graph,
    logged_in_client: FlaskClient,
    app: Flask,  # Use logged_in_client
) -> None:
    """Test the apply_changes endpoint with a server error."""
    mock_g.resource_lock_manager = MagicMock()
    mock_import_entity_graph.side_effect = Exception("General server error")

    changes = [
        {
            "action": "create",
            "subject": "http://example.org/entity/1",
            "data": {"http://example.org/property/1": ["Test Value"]},
        }
    ]

    response = logged_in_client.post("/api/apply_changes", json=changes)

    assert response.status_code == 500
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert "error_type" in data
    assert data["error_type"] == "system"
    assert "An error occurred while" in data["message"]


@patch("heritrace.routes.api.import_entity_graph")
@patch("heritrace.routes.api.g")
def test_apply_changes_database_error(
    mock_g, mock_import_entity_graph, logged_in_client: FlaskClient, app: Flask
) -> None:
    """Test the apply_changes endpoint with a database error during save operation."""
    mock_g.resource_lock_manager = MagicMock()
    mock_editor = MagicMock()
    mock_editor.save.side_effect = Exception("Database connection error")
    mock_import_entity_graph.return_value = mock_editor

    changes = [
        {
            "action": "create",
            "subject": "http://example.org/entity/1",
            "data": {
                "http://example.org/property/1": [
                    {
                        "value": "Test Value",
                        "datatype": "http://www.w3.org/2001/XMLSchema#string",
                    }
                ]
            },
        }
    ]

    response = logged_in_client.post("/api/apply_changes", json=changes)

    assert response.status_code == 500
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert data["error_type"] == "database"
    assert "Failed to save changes to the database" in data["message"]

    mock_import_entity_graph.assert_called_once()
    mock_editor.save.assert_called_once()


@patch("heritrace.routes.api.import_entity_graph")
@patch("heritrace.routes.api.create_logic")
@patch("heritrace.routes.api.import_referenced_entities")
@patch("heritrace.routes.api.transform_changes_with_virtual_properties")
@patch("heritrace.routes.api.g")
def test_apply_changes_with_quadstore(
    mock_g,
    mock_transform_changes,
    mock_import_referenced_entities,
    mock_create_logic,
    mock_import_entity_graph,
    logged_in_client: FlaskClient,
    app: Flask,
) -> None:
    """Test the apply_changes endpoint with a quadstore dataset."""
    mock_g.resource_lock_manager = MagicMock()
    mock_editor = MagicMock()
    mock_editor.dataset_is_quadstore = True

    mock_graph = MagicMock()
    mock_graph.identifier = URIRef("http://example.org/graph/1")

    mock_quad = (
        URIRef("http://example.org/entity/1"),
        URIRef("http://example.org/predicate/1"),
        Literal("Test Value"),
        mock_graph,
    )

    mock_editor.g_set.quads.return_value = [mock_quad]

    mock_import_entity_graph.return_value = mock_editor

    mock_create_logic.return_value = "http://example.org/entity/1"

    changes = [
        {
            "action": "create",
            "subject": "http://example.org/entity/1",
            "data": {
                "http://example.org/property/1": [
                    {
                        "value": "Test Value",
                        "datatype": "http://www.w3.org/2001/XMLSchema#string",
                    }
                ]
            },
            "affected_entities": [],
            "delete_affected": False,
        }
    ]

    mock_transform_changes.return_value = changes

    response = logged_in_client.post("/api/apply_changes", json=changes)

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert "Changes applied successfully" in data["message"]

    mock_import_entity_graph.assert_called_once()
    mock_editor.g_set.quads.assert_called_once_with(
        (URIRef("http://example.org/entity/1"), None, None, None)
    )

    mock_create_logic.assert_called_once()

    call_args = mock_create_logic.call_args[0]
    assert call_args[0] == mock_editor
    assert call_args[1] == changes[0]["data"]
    assert call_args[2] == URIRef(changes[0]["subject"])

    assert hasattr(call_args[3], "identifier")
    assert call_args[3].identifier == mock_graph.identifier

    mock_editor.save.assert_called_once()


@patch("heritrace.routes.api.import_entity_graph")
@patch("heritrace.routes.api.g")
def test_apply_changes_invalid_primary_source(
    mock_g, mock_import_entity_graph, logged_in_client: FlaskClient
) -> None:
    """Test apply_changes returns 400 for an invalid primary_source URL."""
    mock_g.resource_lock_manager = MagicMock()
    changes = [
        {
            "action": "create",
            "subject": "http://example.org/entity/1",
            "data": {"prop": "value"},
            "primary_source": "not-a-valid-url",
        }
    ]
    response = logged_in_client.post("/api/apply_changes", json=changes)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert "Invalid primary source URL" in data["error"]
    mock_import_entity_graph.assert_not_called()


@patch("heritrace.routes.api.import_entity_graph")
@patch("heritrace.routes.api.save_user_default_primary_source")
@patch("heritrace.routes.api.g")
def test_apply_changes_save_default_source(
    mock_g,
    mock_save_default,
    mock_import_entity_graph,
    logged_in_client: FlaskClient,
    app: Flask,
) -> None:
    """Test apply_changes calls save_user_default_primary_source when requested."""
    mock_g.resource_lock_manager = MagicMock()
    mock_editor = MagicMock()
    mock_import_entity_graph.return_value = mock_editor
    valid_source_url = "http://example.com/source"

    changes = [
        {
            "action": "create",
            "subject": "http://example.org/entity/1",
            "data": {"prop": "value"},
            "primary_source": valid_source_url,
            "save_default_source": True,
        }
    ]

    with app.test_request_context():
        with logged_in_client.session_transaction() as session:  # Use logged_in_client
            user_orcid = session["orcid"]  # Get ORCID from logged_in_client session

        response = logged_in_client.post(
            "/api/apply_changes", json=changes
        )  # Use logged_in_client

    assert response.status_code == 200
    mock_save_default.assert_called_once_with(user_orcid, valid_source_url)
    mock_import_entity_graph.assert_called_once()
    mock_editor.save.assert_called_once()


@patch("heritrace.routes.api.import_entity_graph")
@patch("heritrace.routes.api.Editor")
@patch("heritrace.routes.api.g")  # Mock g
def test_apply_changes_sets_editor_primary_source(
    mock_g, mock_editor_cls, mock_import_entity_graph, logged_in_client: FlaskClient
) -> None:
    """Test apply_changes correctly sets the primary_source on the Editor instance."""
    mock_g.resource_lock_manager = MagicMock()
    mock_editor_instance = mock_editor_cls.return_value
    mock_import_entity_graph.return_value = mock_editor_instance
    valid_source_url = "http://example.com/source"

    changes = [
        {
            "action": "create",
            "subject": "http://example.org/entity/1",
            "data": {"prop": "value"},
            "primary_source": valid_source_url,
            "save_default_source": False,
        }
    ]

    response = logged_in_client.post("/api/apply_changes", json=changes)

    assert response.status_code == 200
    mock_editor_cls.assert_called_once()
    mock_editor_instance.set_primary_source.assert_called_once_with(
        URIRef(valid_source_url)
    )
    mock_import_entity_graph.assert_called_once()
    mock_editor_instance.save.assert_called_once()


@patch("heritrace.routes.api.import_entity_graph")
@patch("heritrace.routes.api.Editor")
@patch("heritrace.routes.api.g")
def test_apply_changes_uses_no_operation_source_when_field_is_empty(
    mock_g,
    mock_editor_cls,
    mock_import_entity_graph,
    logged_in_client: FlaskClient,
    app: Flask,
) -> None:
    mock_g.resource_lock_manager = MagicMock()
    mock_editor_instance = mock_editor_cls.return_value
    mock_import_entity_graph.return_value = mock_editor_instance
    changes = [
        {
            "action": "update",
            "subject": "http://example.org/entity/1",
            "predicate": "http://example.org/title",
            "object": "Old title",
            "newObject": "Updated title",
            "primary_source": "",
        }
    ]

    with patch("heritrace.routes.api.update_logic"):
        response = logged_in_client.post("/api/apply_changes", json=changes)

    assert response.status_code == 200
    assert mock_editor_cls.call_args.args[3] == URIRef(app.config["PRIMARY_SOURCE"])
    mock_editor_instance.preexisting_finished.assert_called_once()
    mock_editor_instance.set_primary_source.assert_called_once_with(None)
