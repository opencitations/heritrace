"""
Tests for the apply_changes API route in heritrace/routes/api.py.
"""

import json
from unittest import mock
from unittest.mock import MagicMock, patch

from flask import Flask
from flask.testing import FlaskClient
from heritrace.utils.strategies import (OrphanHandlingStrategy,
                                        ProxyHandlingStrategy)
from rdflib import Literal, URIRef


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
@patch("heritrace.routes.api.order_logic")
@patch("heritrace.routes.api.g")
def test_apply_changes_order(
    mock_g, mock_order_logic, mock_import_entity_graph, logged_in_client: FlaskClient, app: Flask
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
    """Test apply_changes handles affected entities (orphans/proxies) and duplicate deletions correctly."""
    mock_g.resource_lock_manager = MagicMock()
    mock_editor = MagicMock()
    mock_import_entity_graph.return_value = mock_editor

    mock_validate_new_triple.return_value = (None, Literal("Value to Delete"), "")

    app.config["ORPHAN_HANDLING_STRATEGY"] = OrphanHandlingStrategy.DELETE
    app.config["PROXY_HANDLING_STRATEGY"] = ProxyHandlingStrategy.DELETE

    # --- Test Scenario Data ---
    # 1. orphan1 will be deleted in phase 1 (orphan handling).
    # 2. proxy1 will be deleted in phase 1 (proxy handling).
    # 3. Duplicate orphan/proxy entries will be skipped in phase 1 (continue L543, L558).
    # 4. A full entity deletion for orphan1 will be attempted in phase 2, should be skipped (continue L573).
    # 5. A triple deletion where proxy1 is the object will be attempted in phase 2, should be skipped (continue L581).
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
                {"uri": orphan_uri, "is_intermediate": False}, # First orphan
                {"uri": proxy_uri, "is_intermediate": True},   # First proxy
                {"uri": orphan_uri, "is_intermediate": False}, # Duplicate orphan (for L543)
                {"uri": proxy_uri, "is_intermediate": True},   # Duplicate proxy (for L558)
            ],
            "delete_affected": True, # Instructs to delete orphans/proxies
        },
        # Attempt to delete the full orphan entity (should be skipped by L573)
        {
            "action": "delete",
            "subject": orphan_uri,
            "entity_type": "http://example.org/OrphanType",
        },
        # Attempt to delete a triple where the proxy is the object (should be skipped by L581)
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
        }
    ]

    response = logged_in_client.post("/api/apply_changes", json=changes)

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert "Changes applied successfully" in data["message"]

    # Verify import_entity_graph was called (only once for the first change's subject)
    # Note: include_referencing_entities is True because the changes list *contains* a full entity deletion
    mock_import_entity_graph.assert_called_once_with(
        mock.ANY, # editor instance
        main_entity_uri,
        include_referencing_entities=True
    )

    # Verify delete_logic calls:
    # Expected calls:
    # 1. For the unique orphan (phase 1)
    # 2. For the unique proxy (phase 1)
    # 3. For the full entity deletion (phase 2, L576)
    # 4 & 5. For the normal triple deletion (phase 2, L584, called twice as object is literal)
    assert mock_delete_logic.call_count == 5

    # Check calls specifically for unique affected entities (should be called only once each in phase 1)
    orphan_delete_calls = [
        call for call in mock_delete_logic.call_args_list
        if call[0][1] == orphan_uri # Check subject URI
    ]
    proxy_delete_calls = [
        call for call in mock_delete_logic.call_args_list
        if call[0][1] == proxy_uri # Check subject URI
    ]
    assert len(orphan_delete_calls) == 1, f"Expected 1 delete call for orphan {orphan_uri}, got {len(orphan_delete_calls)}"
    assert len(proxy_delete_calls) == 1, f"Expected 1 delete call for proxy {proxy_uri}, got {len(proxy_delete_calls)}"

    # Check call specifically for the full entity deletion (L576)
    full_delete_call_args = mock.call(
        mock_editor,
        full_delete_target_uri,
        graph_uri=None,
        entity_type="http://example.org/FullDeleteType",
        entity_shape=None
        )
    mock_delete_logic.assert_any_call(*full_delete_call_args[1], **full_delete_call_args[2])


    # Check that delete_logic was NOT called for the skipped operations in Phase 2
    # Full orphan entity deletion (skipped by L573)
    skipped_full_orphan_delete_call = mock.call(
        mock_editor,
        orphan_uri,
        None, # predicate
        None, # object_value
        graph_uri=None,
        entity_type="http://example.org/OrphanType"
    )
    # Triple with deleted proxy object (skipped by L581)
    skipped_proxy_object_delete_call_args = mock.call(
        mock_editor,
        "http://example.org/another/subj",
        "http://example.org/relates/to",
        proxy_uri, # Check the raw object value from the change
        None, # graph_uri
        "http://example.org/AnotherType"
    )
    assert skipped_full_orphan_delete_call not in mock_delete_logic.call_args_list

    # More robust check for the skipped proxy object deletion call
    found_skipped_proxy_object_delete_call = False
    for call in mock_delete_logic.call_args_list:
        # Check arguments matching the skipped operation
        args, kwargs = call
        if (
            len(args) > 3 and
            args[1] == URIRef("http://example.org/another/subj") and
            args[2] == URIRef("http://example.org/relates/to") and
            str(args[3]) == proxy_uri and
            kwargs.get("entity_type") == "http://example.org/AnotherType"
        ):
            found_skipped_proxy_object_delete_call = True
            break
    assert not found_skipped_proxy_object_delete_call, "delete_logic call for triple with deleted proxy object was found, but should have been skipped"

    # Verify editor save was called
    mock_editor.save.assert_called_once()


@patch("heritrace.routes.api.g")
def test_apply_changes_no_data(mock_g, logged_in_client: FlaskClient, app: Flask) -> None:
    """Test the apply_changes endpoint returns 400 when no data is provided."""
    mock_g.resource_lock_manager = MagicMock() # Mock this to avoid potential AttributeError

    # Test with JSON "null" (explicitly set Content-Type)
    response_null = logged_in_client.post(
        "/api/apply_changes",
        data="null", # Send the JSON literal "null"
        content_type="application/json"
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
@patch("heritrace.routes.api.g") # Mock g
def test_apply_changes_validation_error(
    mock_g, mock_import_entity_graph, logged_in_client: FlaskClient, app: Flask # Use logged_in_client
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
@patch("heritrace.routes.api.g") # Mock g
def test_apply_changes_server_error(
    mock_g, mock_import_entity_graph, logged_in_client: FlaskClient, app: Flask # Use logged_in_client
) -> None:
    """Test the apply_changes endpoint with a server error."""
    mock_g.resource_lock_manager = MagicMock()
    mock_import_entity_graph.side_effect = Exception("General server error")

    changes = [
        {
            "action": "create",
            "subject": "http://example.org/entity/1",
            "data": {
                "http://example.org/property/1": ["Test Value"]
            }
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
@patch("heritrace.routes.api.g")
def test_apply_changes_with_quadstore(
    mock_g, mock_create_logic, mock_import_entity_graph, logged_in_client: FlaskClient, app: Flask
) -> None:
    """Test the apply_changes endpoint with a quadstore dataset."""
    mock_g.resource_lock_manager = MagicMock()
    mock_editor = MagicMock()
    mock_editor.dataset_is_quadstore = True

    mock_graph = MagicMock()
    mock_graph.identifier = URIRef("http://example.org/graph/1")

    mock_quad = (URIRef("http://example.org/entity/1"), URIRef("http://example.org/predicate/1"),
                Literal("Test Value"), mock_graph)

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

    response = logged_in_client.post("/api/apply_changes", json=changes)

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert "Changes applied successfully" in data["message"]

    mock_import_entity_graph.assert_called_once()
    mock_editor.g_set.quads.assert_called_once_with((URIRef("http://example.org/entity/1"), None, None, None))

    mock_create_logic.assert_called_once()

    call_args = mock_create_logic.call_args[0]
    assert call_args[0] == mock_editor
    assert call_args[1] == changes[0]["data"]
    assert call_args[2] == changes[0]["subject"]

    assert hasattr(call_args[3], 'identifier')
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
    mock_g, mock_save_default, mock_import_entity_graph, logged_in_client: FlaskClient, app: Flask
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
        with logged_in_client.session_transaction() as session: # Use logged_in_client
            user_orcid = session["orcid"] # Get ORCID from logged_in_client session

        response = logged_in_client.post("/api/apply_changes", json=changes) # Use logged_in_client

    assert response.status_code == 200
    mock_save_default.assert_called_once_with(user_orcid, valid_source_url)
    mock_import_entity_graph.assert_called_once()
    mock_editor.save.assert_called_once()


@patch("heritrace.routes.api.import_entity_graph")
@patch("heritrace.routes.api.Editor")
@patch("heritrace.routes.api.g") # Mock g
def test_apply_changes_sets_editor_primary_source(
    mock_g, MockEditor, mock_import_entity_graph, logged_in_client: FlaskClient
) -> None:
    """Test apply_changes correctly sets the primary_source on the Editor instance."""
    mock_g.resource_lock_manager = MagicMock()
    mock_editor_instance = MockEditor.return_value
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
    MockEditor.assert_called_once()
    mock_editor_instance.set_primary_source.assert_called_once_with(valid_source_url)
    mock_import_entity_graph.assert_called_once()
    mock_editor_instance.save.assert_called_once() 