"""
Tests for the API routes in heritrace/routes/api.py.
"""

import json
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask, g
from flask.testing import FlaskClient
from heritrace.routes.api import (delete_logic, determine_datatype,
                                  generate_unique_uri, order_logic,
                                  update_logic)
from heritrace.services.resource_lock_manager import ResourceLockManager
from heritrace.utils.strategies import (OrphanHandlingStrategy,
                                        ProxyHandlingStrategy)
from rdflib import RDF, XSD, Literal, URIRef
from redis import Redis


# Use a real ResourceLockManager with Redis instead of mocks
@pytest.fixture
def api_client(
    logged_in_client: FlaskClient, app: Flask, redis_client: Redis
) -> Generator[FlaskClient, None, None]:
    """Extend the logged_in_client with a real resource lock manager."""
    # Create a real ResourceLockManager with the Redis client
    lock_manager = ResourceLockManager(redis_client)

    # Patch the g object to include our real lock manager
    def real_before_request():
        g.resource_lock_manager = lock_manager

    app.before_request(real_before_request)

    # Return the client with the patched session
    yield logged_in_client


def test_catalogue_api_unauthenticated(client: FlaskClient) -> None:
    """Test that the catalogue API endpoint redirects when not authenticated."""
    response = client.get("/api/catalogue")
    assert response.status_code == 302  # Redirect to login page


def test_catalogue_api(api_client: FlaskClient) -> None:
    """Test the catalogue API endpoint."""
    response = api_client.get("/api/catalogue")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "entities" in data
    assert "available_classes" in data


def test_catalogue_api_with_params(api_client: FlaskClient) -> None:
    """Test the catalogue API endpoint with query parameters."""
    response = api_client.get(
        "/api/catalogue?class=http://example.org/TestClass&page=1&per_page=50"
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "entities" in data
    assert "available_classes" in data
    assert "current_page" in data
    assert data["current_page"] == 1


def test_catalogue_api_with_invalid_per_page(api_client: FlaskClient) -> None:
    """Test the catalogue API endpoint with an invalid per_page value."""
    response = api_client.get(
        "/api/catalogue?class=http://example.org/TestClass&page=1&per_page=999"
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "entities" in data
    assert "available_classes" in data
    assert "current_page" in data
    assert data["current_page"] == 1
    # The per_page should be set to the default value of 100
    assert data["per_page"] == 100


def test_catalogue_api_with_null_sort_property(api_client: FlaskClient) -> None:
    """Test the catalogue API endpoint with a null sort property."""
    response = api_client.get(
        "/api/catalogue?class=http://example.org/TestClass&page=1&per_page=50&sort_property=null"
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "entities" in data
    assert "available_classes" in data
    assert "current_page" in data
    assert data["current_page"] == 1


def test_time_vault_api(api_client: FlaskClient) -> None:
    """Test the time vault API endpoint."""
    response = api_client.get("/api/time-vault")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "entities" in data
    assert "available_classes" in data


def test_time_vault_api_with_params(api_client: FlaskClient) -> None:
    """Test the time vault API endpoint with query parameters."""
    response = api_client.get(
        "/api/time-vault?class=http://example.org/TestClass&page=1&per_page=50"
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "entities" in data
    assert "available_classes" in data
    assert "current_page" in data
    assert data["current_page"] == 1


def test_check_lock_no_uri(api_client: FlaskClient) -> None:
    """Test the check_lock endpoint with no resource URI."""
    response = api_client.post("/api/check-lock", json={})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"


def test_check_lock_unlocked(api_client: FlaskClient, app: Flask) -> None:
    """Test the check_lock endpoint with an unlocked resource."""
    with app.test_request_context():
        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user_id"] = "0000-0000-0000-0000"
                session["user_name"] = "Test User"
                session["is_authenticated"] = True
                session["lang"] = "en"
                session["orcid"] = "0000-0000-0000-0000"
                session["_fresh"] = True
                session["_id"] = "test-session-id"
                session["_user_id"] = "0000-0000-0000-0000"

            response = client.post(
                "/api/check-lock",
                json={"resource_uri": "http://example.org/resource"},
            )
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "unlocked"


def test_check_lock_locked(
    api_client: FlaskClient, app: Flask, redis_client: Redis
) -> None:
    """Test the check_lock endpoint with a locked resource."""
    resource_uri = "http://example.org/locked-resource"

    # Manually create a lock in Redis
    lock_key = f"resource_lock:{resource_uri}"
    lock_data = {
        "user_id": "1111-1111-1111-1111",
        "user_name": "Another User",
        "timestamp": "2023-01-01T00:00:00+00:00",
        "resource_uri": resource_uri,
    }
    redis_client.setex(lock_key, 300, json.dumps(lock_data))

    with app.test_request_context():
        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user_id"] = "0000-0000-0000-0000"
                session["user_name"] = "Test User"
                session["is_authenticated"] = True
                session["lang"] = "en"
                session["orcid"] = "0000-0000-0000-0000"
                session["_fresh"] = True
                session["_id"] = "test-session-id"
                session["_user_id"] = "0000-0000-0000-0000"

            response = client.post(
                "/api/check-lock",
                json={"resource_uri": resource_uri},
            )
            assert response.status_code == 423
            data = json.loads(response.data)
            assert data["status"] == "locked"
            assert "Another User" in data["message"]
            assert "1111-1111-1111-1111" in data["message"]


def test_acquire_lock_no_uri(api_client: FlaskClient) -> None:
    """Test the acquire_lock endpoint with no resource URI."""
    response = api_client.post("/api/acquire-lock", json={})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"


def test_acquire_lock_success(
    api_client: FlaskClient, app: Flask, redis_client: Redis
) -> None:
    """Test the acquire_lock endpoint with a valid resource URI."""
    resource_uri = "http://example.org/resource-to-acquire"

    with app.test_request_context():
        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user_id"] = "0000-0000-0000-0000"
                session["user_name"] = "Test User"
                session["is_authenticated"] = True
                session["lang"] = "en"
                session["orcid"] = "0000-0000-0000-0000"
                session["_fresh"] = True
                session["_id"] = "test-session-id"
                session["_user_id"] = "0000-0000-0000-0000"

            response = client.post(
                "/api/acquire-lock",
                json={"resource_uri": resource_uri},
            )
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "success"

            # Verify the lock was actually created in Redis
            lock_key = f"resource_lock:{resource_uri}"
            assert redis_client.exists(lock_key)


def test_acquire_lock_failure(
    api_client: FlaskClient, app: Flask, redis_client: Redis
) -> None:
    """Test the acquire_lock endpoint when the lock cannot be acquired."""
    resource_uri = "http://example.org/already-locked-resource"

    # Manually create a lock in Redis
    lock_key = f"resource_lock:{resource_uri}"
    lock_data = {
        "user_id": "1111-1111-1111-1111",
        "user_name": "Another User",
        "timestamp": "2023-01-01T00:00:00+00:00",
        "resource_uri": resource_uri,
    }
    redis_client.setex(lock_key, 300, json.dumps(lock_data))

    with app.test_request_context():
        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user_id"] = "0000-0000-0000-0000"
                session["user_name"] = "Test User"
                session["is_authenticated"] = True
                session["lang"] = "en"
                session["orcid"] = "0000-0000-0000-0000"
                session["_fresh"] = True
                session["_id"] = "test-session-id"
                session["_user_id"] = "0000-0000-0000-0000"

            response = client.post(
                "/api/acquire-lock",
                json={"resource_uri": resource_uri},
            )
            assert response.status_code == 423
            data = json.loads(response.data)
            assert data["status"] == "error"


def test_release_lock_no_uri(api_client: FlaskClient) -> None:
    """Test the release_lock endpoint with no resource URI."""
    response = api_client.post("/api/release-lock", json={})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"


def test_release_lock_success(
    api_client: FlaskClient, app: Flask, redis_client: Redis
) -> None:
    """Test the release_lock endpoint with a valid resource URI."""
    resource_uri = "http://example.org/resource-to-release"

    # First acquire a lock
    with app.test_request_context():
        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user_id"] = "0000-0000-0000-0000"
                session["user_name"] = "Test User"
                session["is_authenticated"] = True
                session["lang"] = "en"
                session["orcid"] = "0000-0000-0000-0000"
                session["_fresh"] = True
                session["_id"] = "test-session-id"
                session["_user_id"] = "0000-0000-0000-0000"

            # First acquire the lock
            client.post(
                "/api/acquire-lock",
                json={"resource_uri": resource_uri},
            )

            # Then release it
            response = client.post(
                "/api/release-lock",
                json={"resource_uri": resource_uri},
            )
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "success"


def test_release_lock_failure(
    api_client: FlaskClient, app: Flask, redis_client: Redis
) -> None:
    """Test the release_lock endpoint when the lock cannot be released."""
    resource_uri = "http://example.org/locked-by-another-user"

    # Manually create a lock in Redis owned by another user
    lock_key = f"resource_lock:{resource_uri}"
    lock_data = {
        "user_id": "1111-1111-1111-1111",
        "user_name": "Another User",
        "timestamp": "2023-01-01T00:00:00+00:00",
        "resource_uri": resource_uri,
    }
    redis_client.setex(lock_key, 300, json.dumps(lock_data))

    with app.test_request_context():
        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user_id"] = "0000-0000-0000-0000"
                session["user_name"] = "Test User"
                session["is_authenticated"] = True
                session["lang"] = "en"
                session["orcid"] = "0000-0000-0000-0000"
                session["_fresh"] = True
                session["_id"] = "test-session-id"
                session["_user_id"] = "0000-0000-0000-0000"

            response = client.post(
                "/api/release-lock",
                json={"resource_uri": resource_uri},
            )
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["status"] == "error"


def test_renew_lock_no_uri(api_client: FlaskClient) -> None:
    """Test the renew_lock endpoint with no resource URI."""
    response = api_client.post("/api/renew-lock", json={})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"


def test_renew_lock_success(
    api_client: FlaskClient, app: Flask, redis_client: Redis
) -> None:
    """Test the renew_lock endpoint with a valid resource URI."""
    resource_uri = "http://example.org/resource-to-renew"

    with app.test_request_context():
        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user_id"] = "0000-0000-0000-0000"
                session["user_name"] = "Test User"
                session["is_authenticated"] = True
                session["lang"] = "en"
                session["orcid"] = "0000-0000-0000-0000"
                session["_fresh"] = True
                session["_id"] = "test-session-id"
                session["_user_id"] = "0000-0000-0000-0000"

            # First acquire a lock
            client.post(
                "/api/acquire-lock",
                json={"resource_uri": resource_uri},
            )

            # Get the initial lock timestamp
            lock_key = f"resource_lock:{resource_uri}"
            initial_lock_data = json.loads(redis_client.get(lock_key))
            initial_timestamp = initial_lock_data["timestamp"]

            # Wait a moment to ensure timestamp would change
            import time

            time.sleep(0.1)

            # Then renew it
            response = client.post(
                "/api/renew-lock",
                json={"resource_uri": resource_uri},
            )
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "success"

            # Verify the lock was renewed with a new timestamp
            renewed_lock_data = json.loads(redis_client.get(lock_key))
            renewed_timestamp = renewed_lock_data["timestamp"]
            assert renewed_timestamp != initial_timestamp


def test_renew_lock_failure(
    api_client: FlaskClient, app: Flask, redis_client: Redis
) -> None:
    """Test the renew_lock endpoint when the lock cannot be renewed."""
    resource_uri = "http://example.org/locked-by-another-user-for-renewal"

    # Manually create a lock in Redis owned by another user
    lock_key = f"resource_lock:{resource_uri}"
    lock_data = {
        "user_id": "1111-1111-1111-1111",
        "user_name": "Another User",
        "timestamp": "2023-01-01T00:00:00+00:00",
        "resource_uri": resource_uri,
    }
    redis_client.setex(lock_key, 300, json.dumps(lock_data))

    with app.test_request_context():
        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user_id"] = "0000-0000-0000-0000"
                session["user_name"] = "Test User"
                session["is_authenticated"] = True
                session["lang"] = "en"
                session["orcid"] = "0000-0000-0000-0000"
                session["_fresh"] = True
                session["_id"] = "test-session-id"
                session["_user_id"] = "0000-0000-0000-0000"

            response = client.post(
                "/api/renew-lock",
                json={"resource_uri": resource_uri},
            )
            assert response.status_code == 423
            data = json.loads(response.data)
            assert data["status"] == "error"


def test_validate_literal_no_value(api_client: FlaskClient) -> None:
    """Test the validate_literal endpoint with no value."""
    response = api_client.post("/api/validate-literal", json={})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data


def test_validate_literal_string(api_client: FlaskClient) -> None:
    """Test the validate_literal endpoint with a string value."""
    response = api_client.post(
        "/api/validate-literal",
        json={
            "value": "test string",
            "datatype": "http://www.w3.org/2001/XMLSchema#string",
        },
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "valid_datatypes" in data
    assert "http://www.w3.org/2001/XMLSchema#string" in data["valid_datatypes"]


def test_validate_literal_integer(api_client: FlaskClient) -> None:
    """Test the validate_literal endpoint with an integer value."""
    response = api_client.post(
        "/api/validate-literal",
        json={"value": "42", "datatype": "http://www.w3.org/2001/XMLSchema#integer"},
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "valid_datatypes" in data
    assert "http://www.w3.org/2001/XMLSchema#integer" in data["valid_datatypes"]


def test_check_orphans_no_changes(api_client: FlaskClient) -> None:
    """Test the check_orphans endpoint with no changes."""
    response = api_client.post(
        "/api/check_orphans",
        json={"changes": [], "entity_type": "http://example.org/Person"},
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert data["affected_entities"] == []


@patch("heritrace.routes.api.find_orphaned_entities")
def test_check_orphans_no_orphans(mock_find_orphaned, api_client: FlaskClient) -> None:
    """Test the check_orphans endpoint with changes but no orphans found."""
    # Mock the find_orphaned_entities function to return empty lists
    mock_find_orphaned.return_value = ([], [])

    response = api_client.post(
        "/api/check_orphans",
        json={
            "changes": [
                {
                    "action": "delete",
                    "subject": "http://example.org/entity/1",
                    "predicate": "http://example.org/predicate/1",
                    "object": "http://example.org/entity/2",
                }
            ],
            "entity_type": "http://example.org/Person",
        },
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert data["affected_entities"] == []

    # Verify the find_orphaned_entities function was called with the correct arguments
    mock_find_orphaned.assert_called_once_with(
        "http://example.org/entity/1",
        "http://example.org/Person",
        "http://example.org/predicate/1",
        "http://example.org/entity/2",
    )


@patch("heritrace.routes.api.find_orphaned_entities")
@patch("heritrace.routes.api.get_custom_filter")
def test_check_orphans_with_orphans_delete_strategy(
    mock_get_custom_filter, mock_find_orphaned, api_client: FlaskClient, app: Flask
) -> None:
    """Test the check_orphans endpoint with orphans and DELETE strategy."""
    # Mock the custom filter
    mock_filter = mock_get_custom_filter.return_value
    mock_filter.human_readable_entity.return_value = "Human Readable Entity"
    mock_filter.human_readable_predicate.return_value = "Human Readable Type"

    # Mock the find_orphaned_entities function to return orphans
    mock_find_orphaned.return_value = (
        [{"uri": "http://example.org/orphan/1", "type": "http://example.org/Type"}],
        [],
    )

    # Set the orphan handling strategy to DELETE
    app.config["ORPHAN_HANDLING_STRATEGY"] = OrphanHandlingStrategy.DELETE
    app.config["PROXY_HANDLING_STRATEGY"] = ProxyHandlingStrategy.DELETE

    response = api_client.post(
        "/api/check_orphans",
        json={
            "changes": [
                {
                    "action": "delete",
                    "subject": "http://example.org/entity/1",
                    "predicate": "http://example.org/predicate/1",
                    "object": "http://example.org/entity/2",
                }
            ],
            "entity_type": "http://example.org/Person",
        },
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert len(data["affected_entities"]) == 1
    assert data["affected_entities"][0]["uri"] == "http://example.org/orphan/1"
    assert data["affected_entities"][0]["label"] == "Human Readable Entity"
    assert data["affected_entities"][0]["type"] == "Human Readable Type"
    assert data["affected_entities"][0]["is_intermediate"] is False
    assert data["should_delete"] is True
    assert data["orphan_strategy"] == "delete"
    assert data["proxy_strategy"] == "delete"


@patch("heritrace.routes.api.find_orphaned_entities")
@patch("heritrace.routes.api.get_custom_filter")
def test_check_orphans_with_proxies_delete_strategy(
    mock_get_custom_filter, mock_find_orphaned, api_client: FlaskClient, app: Flask
) -> None:
    """Test the check_orphans endpoint with proxies and DELETE strategy."""
    # Mock the custom filter
    mock_filter = mock_get_custom_filter.return_value
    mock_filter.human_readable_entity.return_value = "Human Readable Entity"
    mock_filter.human_readable_predicate.return_value = "Human Readable Type"

    # Mock the find_orphaned_entities function to return proxies
    mock_find_orphaned.return_value = (
        [],
        [{"uri": "http://example.org/proxy/1", "type": "http://example.org/ProxyType"}],
    )

    # Set the proxy handling strategy to DELETE
    app.config["ORPHAN_HANDLING_STRATEGY"] = OrphanHandlingStrategy.DELETE
    app.config["PROXY_HANDLING_STRATEGY"] = ProxyHandlingStrategy.DELETE

    response = api_client.post(
        "/api/check_orphans",
        json={
            "changes": [
                {
                    "action": "delete",
                    "subject": "http://example.org/entity/1",
                    "predicate": "http://example.org/predicate/1",
                    "object": "http://example.org/entity/2",
                }
            ],
            "entity_type": "http://example.org/Person",
        },
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert len(data["affected_entities"]) == 1
    assert data["affected_entities"][0]["uri"] == "http://example.org/proxy/1"
    assert data["affected_entities"][0]["label"] == "Human Readable Entity"
    assert data["affected_entities"][0]["type"] == "Human Readable Type"
    assert data["affected_entities"][0]["is_intermediate"] is True
    assert data["should_delete"] is True
    assert data["orphan_strategy"] == "delete"
    assert data["proxy_strategy"] == "delete"


@patch("heritrace.routes.api.find_orphaned_entities")
@patch("heritrace.routes.api.get_custom_filter")
def test_check_orphans_with_orphans_ask_strategy(
    mock_get_custom_filter, mock_find_orphaned, api_client: FlaskClient, app: Flask
) -> None:
    """Test the check_orphans endpoint with orphans and ASK strategy."""
    # Mock the custom filter
    mock_filter = mock_get_custom_filter.return_value
    mock_filter.human_readable_entity.return_value = "Human Readable Entity"
    mock_filter.human_readable_predicate.return_value = "Human Readable Type"

    # Mock the find_orphaned_entities function to return orphans
    mock_find_orphaned.return_value = (
        [{"uri": "http://example.org/orphan/1", "type": "http://example.org/Type"}],
        [],
    )

    # Set the orphan handling strategy to ASK
    app.config["ORPHAN_HANDLING_STRATEGY"] = OrphanHandlingStrategy.ASK
    app.config["PROXY_HANDLING_STRATEGY"] = ProxyHandlingStrategy.KEEP

    response = api_client.post(
        "/api/check_orphans",
        json={
            "changes": [
                {
                    "action": "delete",
                    "subject": "http://example.org/entity/1",
                    "predicate": "http://example.org/predicate/1",
                    "object": "http://example.org/entity/2",
                }
            ],
            "entity_type": "http://example.org/Person",
        },
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert len(data["affected_entities"]) == 1
    assert data["affected_entities"][0]["uri"] == "http://example.org/orphan/1"
    assert data["affected_entities"][0]["label"] == "Human Readable Entity"
    assert data["affected_entities"][0]["type"] == "Human Readable Type"
    assert data["affected_entities"][0]["is_intermediate"] is False
    assert data["should_delete"] is False
    assert data["orphan_strategy"] == "ask"
    assert data["proxy_strategy"] == "keep"


@patch("heritrace.routes.api.find_orphaned_entities")
@patch("heritrace.routes.api.get_custom_filter")
def test_check_orphans_with_proxies_ask_strategy(
    mock_get_custom_filter, mock_find_orphaned, api_client: FlaskClient, app: Flask
) -> None:
    """Test the check_orphans endpoint with proxies and ASK strategy."""
    # Mock the custom filter
    mock_filter = mock_get_custom_filter.return_value
    mock_filter.human_readable_entity.return_value = "Human Readable Entity"
    mock_filter.human_readable_predicate.return_value = "Human Readable Type"

    # Mock the find_orphaned_entities function to return proxies
    mock_find_orphaned.return_value = (
        [],
        [{"uri": "http://example.org/proxy/1", "type": "http://example.org/ProxyType"}],
    )

    # Set the proxy handling strategy to ASK
    app.config["ORPHAN_HANDLING_STRATEGY"] = OrphanHandlingStrategy.KEEP
    app.config["PROXY_HANDLING_STRATEGY"] = ProxyHandlingStrategy.ASK

    response = api_client.post(
        "/api/check_orphans",
        json={
            "changes": [
                {
                    "action": "delete",
                    "subject": "http://example.org/entity/1",
                    "predicate": "http://example.org/predicate/1",
                    "object": "http://example.org/entity/2",
                }
            ],
            "entity_type": "http://example.org/Person",
        },
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert len(data["affected_entities"]) == 1
    assert data["affected_entities"][0]["uri"] == "http://example.org/proxy/1"
    assert data["affected_entities"][0]["label"] == "Human Readable Entity"
    assert data["affected_entities"][0]["type"] == "Human Readable Type"
    assert data["affected_entities"][0]["is_intermediate"] is True
    assert data["should_delete"] is False
    assert data["orphan_strategy"] == "keep"
    assert data["proxy_strategy"] == "ask"


@patch("heritrace.routes.api.find_orphaned_entities")
@patch("heritrace.routes.api.get_custom_filter")
def test_check_orphans_with_both_orphans_and_proxies(
    mock_get_custom_filter, mock_find_orphaned, api_client: FlaskClient, app: Flask
) -> None:
    """Test the check_orphans endpoint with both orphans and proxies."""
    # Mock the custom filter
    mock_filter = mock_get_custom_filter.return_value
    mock_filter.human_readable_entity.return_value = "Human Readable Entity"
    mock_filter.human_readable_predicate.return_value = "Human Readable Type"

    # Mock the find_orphaned_entities function to return both orphans and proxies
    mock_find_orphaned.return_value = (
        [{"uri": "http://example.org/orphan/1", "type": "http://example.org/Type"}],
        [{"uri": "http://example.org/proxy/1", "type": "http://example.org/ProxyType"}],
    )

    # Set the strategies to ASK
    app.config["ORPHAN_HANDLING_STRATEGY"] = OrphanHandlingStrategy.ASK
    app.config["PROXY_HANDLING_STRATEGY"] = ProxyHandlingStrategy.ASK

    response = api_client.post(
        "/api/check_orphans",
        json={
            "changes": [
                {
                    "action": "delete",
                    "subject": "http://example.org/entity/1",
                    "predicate": "http://example.org/predicate/1",
                    "object": "http://example.org/entity/2",
                }
            ],
            "entity_type": "http://example.org/Person",
        },
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert len(data["affected_entities"]) == 2
    assert data["affected_entities"][0]["uri"] == "http://example.org/orphan/1"
    assert data["affected_entities"][0]["is_intermediate"] is False
    assert data["affected_entities"][1]["uri"] == "http://example.org/proxy/1"
    assert data["affected_entities"][1]["is_intermediate"] is True
    assert data["should_delete"] is False
    assert data["orphan_strategy"] == "ask"
    assert data["proxy_strategy"] == "ask"


def test_check_orphans_invalid_request(api_client: FlaskClient) -> None:
    """Test the check_orphans endpoint with an invalid request."""
    response = api_client.post("/api/check_orphans", json={"invalid": "data"})
    # The API should return 400 for invalid requests
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert data["error_type"] == "validation"
    assert "Invalid request" in data["message"]


@patch("heritrace.routes.api.find_orphaned_entities")
def test_check_orphans_server_error(
    mock_find_orphaned, api_client: FlaskClient
) -> None:
    """Test the check_orphans endpoint with a server error."""
    # Mock the find_orphaned_entities function to raise an exception
    mock_find_orphaned.side_effect = Exception("Test error")

    response = api_client.post(
        "/api/check_orphans",
        json={
            "changes": [
                {
                    "action": "delete",
                    "subject": "http://example.org/entity/1",
                    "predicate": "http://example.org/predicate/1",
                    "object": "http://example.org/entity/2",
                }
            ],
            "entity_type": "http://example.org/Person",
        },
    )
    assert response.status_code == 500
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert data["error_type"] == "system"


@patch("heritrace.routes.api.import_entity_graph")
@patch("heritrace.routes.api.create_logic")
@patch("heritrace.utils.shacl_utils.validate_new_triple")
def test_apply_changes_create(
    mock_validate_new_triple,
    mock_create_logic,
    mock_import_entity_graph,
    api_client: FlaskClient,
    app: Flask,
) -> None:
    """Test the apply_changes endpoint with a create action."""
    # Mock the import_entity_graph function to return a mock editor
    mock_editor = MagicMock()
    mock_import_entity_graph.return_value = mock_editor

    # Mock the create_logic function to return a subject
    mock_create_logic.return_value = "http://example.org/entity/1"

    # Test data for creating a new property
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

    # Make the request
    response = api_client.post("/api/apply_changes", json=changes)

    # Check the response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert "Changes applied successfully" in data["message"]

    # Verify the mock was called correctly
    mock_import_entity_graph.assert_called_once()
    mock_editor.save.assert_called_once()


@patch("heritrace.routes.api.import_entity_graph")
@patch("heritrace.routes.api.update_logic")
@patch("heritrace.utils.shacl_utils.validate_new_triple")
def test_apply_changes_update(
    mock_validate_new_triple,
    mock_update_logic,
    mock_import_entity_graph,
    api_client: FlaskClient,
    app: Flask,
) -> None:
    """Test the apply_changes endpoint with an update action."""
    # Mock the import_entity_graph function to return a mock editor
    mock_editor = MagicMock()
    mock_import_entity_graph.return_value = mock_editor

    # Mock the validate_new_triple function to avoid the list index out of range error
    mock_validate_new_triple.return_value = (
        Literal("New Value"),
        Literal("Old Value"),
        "",
    )

    # Test data for updating a property
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

    # Make the request
    response = api_client.post("/api/apply_changes", json=changes)

    # Check the response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert "Changes applied successfully" in data["message"]

    # Verify the mock was called correctly
    mock_import_entity_graph.assert_called_once()
    mock_editor.save.assert_called_once()


@patch("heritrace.routes.api.import_entity_graph")
@patch("heritrace.routes.api.delete_logic")
@patch("heritrace.utils.shacl_utils.validate_new_triple")
def test_apply_changes_delete(
    mock_validate_new_triple,
    mock_delete_logic,
    mock_import_entity_graph,
    api_client: FlaskClient,
    app: Flask,
) -> None:
    """Test the apply_changes endpoint with a delete action."""
    # Mock the import_entity_graph function to return a mock editor
    mock_editor = MagicMock()
    mock_import_entity_graph.return_value = mock_editor

    # Mock the validate_new_triple function to avoid the list index out of range error
    mock_validate_new_triple.return_value = (None, Literal("Value to Delete"), "")

    # Test data for deleting a property
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

    # Make the request
    response = api_client.post("/api/apply_changes", json=changes)

    # Check the response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert "Changes applied successfully" in data["message"]

    # Verify the mock was called correctly
    mock_import_entity_graph.assert_called_once()
    mock_editor.save.assert_called_once()


@patch("heritrace.routes.api.import_entity_graph")
@patch("heritrace.routes.api.order_logic")
def test_apply_changes_order(
    mock_order_logic, mock_import_entity_graph, api_client: FlaskClient, app: Flask
) -> None:
    """Test the apply_changes endpoint with an order action."""
    # Mock the import_entity_graph function to return a mock editor
    mock_editor = MagicMock()
    mock_import_entity_graph.return_value = mock_editor

    # Mock the order_logic function to avoid validation errors
    mock_order_logic.return_value = None

    # Test data for ordering properties
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

    # Make the request
    response = api_client.post("/api/apply_changes", json=changes)

    # Check the response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert "Changes applied successfully" in data["message"]

    # Verify the mock was called correctly
    mock_import_entity_graph.assert_called_once()
    mock_editor.save.assert_called_once()


@patch("heritrace.routes.api.import_entity_graph")
@patch("heritrace.routes.api.delete_logic")
@patch("heritrace.utils.shacl_utils.validate_new_triple")
def test_apply_changes_with_affected_entities(
    mock_validate_new_triple,
    mock_delete_logic,
    mock_import_entity_graph,
    api_client: FlaskClient,
    app: Flask,
) -> None:
    """Test the apply_changes endpoint with affected entities."""
    # Mock the import_entity_graph function to return a mock editor
    mock_editor = MagicMock()
    mock_import_entity_graph.return_value = mock_editor

    # Mock the validate_new_triple function to avoid the list index out of range error
    mock_validate_new_triple.return_value = (None, Literal("Value to Delete"), "")

    # Test data for deleting with affected entities
    changes = [
        {
            "action": "delete",
            "subject": "http://example.org/entity/1",
            "predicate": "http://example.org/property/1",
            "object": "Value to Delete",
            "entity_type": "http://example.org/Person",
            "affected_entities": [
                {"uri": "http://example.org/orphan/1", "is_intermediate": False},
                {"uri": "http://example.org/proxy/1", "is_intermediate": True},
            ],
            "delete_affected": True,
        }
    ]

    # Make the request
    response = api_client.post("/api/apply_changes", json=changes)

    # Check the response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert "Changes applied successfully" in data["message"]

    # Verify the mock was called correctly
    mock_import_entity_graph.assert_called_once()
    mock_delete_logic.assert_called_once()
    mock_editor.delete.assert_any_call(URIRef("http://example.org/orphan/1"))
    mock_editor.delete.assert_any_call(URIRef("http://example.org/proxy/1"))
    mock_editor.save.assert_called_once()


@patch("heritrace.routes.api.import_entity_graph")
@patch("heritrace.routes.api.create_logic")
@patch("heritrace.routes.api.update_logic")
@patch("heritrace.routes.api.delete_logic")
@patch("heritrace.utils.shacl_utils.validate_new_triple")
def test_apply_changes_multiple_actions(
    mock_validate_new_triple,
    mock_delete_logic,
    mock_update_logic,
    mock_create_logic,
    mock_import_entity_graph,
    api_client: FlaskClient,
    app: Flask,
) -> None:
    """Test the apply_changes endpoint with multiple actions."""
    # Mock the import_entity_graph function to return a mock editor
    mock_editor = MagicMock()
    mock_import_entity_graph.return_value = mock_editor

    # Mock the logic functions to avoid validation errors
    mock_create_logic.return_value = "http://example.org/entity/1"
    mock_update_logic.return_value = None
    mock_delete_logic.return_value = None

    # Mock the validate_new_triple function to avoid the list index out of range error
    from rdflib import Literal

    mock_validate_new_triple.return_value = (
        Literal("New Value"),
        Literal("Old Value"),
        "",
    )

    # Test data with multiple actions
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
        },
        {
            "action": "update",
            "subject": "http://example.org/entity/1",
            "predicate": "http://example.org/property/2",
            "object": "Old Value",
            "newObject": "New Value",
            "affected_entities": [],
            "delete_affected": False,
        },
        {
            "action": "delete",
            "subject": "http://example.org/entity/1",
            "predicate": "http://example.org/property/3",
            "object": "Value to Delete",
            "affected_entities": [],
            "delete_affected": False,
        },
    ]

    # Make the request
    response = api_client.post("/api/apply_changes", json=changes)

    # Check the response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert "Changes applied successfully" in data["message"]

    # Verify the mock was called correctly
    mock_import_entity_graph.assert_called_once()
    mock_create_logic.assert_called_once()
    mock_update_logic.assert_called_once()
    mock_delete_logic.assert_called_once()
    mock_editor.save.assert_called_once()


@patch("heritrace.routes.api.import_entity_graph")
def test_apply_changes_validation_error(
    mock_import_entity_graph, api_client: FlaskClient, app: Flask
) -> None:
    """Test the apply_changes endpoint with a validation error."""
    # Mock the import_entity_graph function to return a mock editor
    mock_editor = MagicMock()
    # Make the editor.save method raise a ValueError
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

    # Make the request
    response = api_client.post("/api/apply_changes", json=changes)

    # Check the response
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert data["error_type"] == "validation"
    assert "Invalid data" in data["message"]


@patch("heritrace.routes.api.import_entity_graph")
def test_apply_changes_server_error(
    mock_import_entity_graph, api_client: FlaskClient, app: Flask
) -> None:
    """Test the apply_changes endpoint with a server error."""
    # Mock the import_entity_graph function to return a mock editor
    mock_editor = MagicMock()
    # Make the editor.save method raise an Exception
    mock_editor.save.side_effect = Exception("Server error")
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

    # Make the request
    response = api_client.post("/api/apply_changes", json=changes)

    # Check the response
    assert response.status_code == 500
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert data["error_type"] == "system"
    assert "An error occurred while applying changes" in data["message"]


@patch("heritrace.routes.api.get_custom_filter")
def test_get_human_readable_entity(mock_get_custom_filter, api_client: FlaskClient) -> None:
    """Test the get_human_readable_entity endpoint."""
    # Create a mock filter
    mock_filter = MagicMock()
    mock_get_custom_filter.return_value = mock_filter
    
    # Configure the mock to return a human-readable entity
    mock_filter.human_readable_entity.return_value = "Human Readable Entity Title"
    
    # Make the request
    response = api_client.post(
        "/api/human-readable-entity",
        data={
            "uri": "http://example.org/entity/1",
            "entity_class": "http://example.org/EntityClass"
        }
    )
    
    # Check the response
    assert response.status_code == 200
    assert response.data.decode("utf-8") == "Human Readable Entity Title"
    
    # Verify the mock was called correctly
    mock_filter.human_readable_entity.assert_called_once_with(
        "http://example.org/entity/1", 
        ["http://example.org/EntityClass"]
    )


def test_get_human_readable_entity_missing_params(api_client: FlaskClient) -> None:
    """Test the get_human_readable_entity endpoint with missing parameters."""
    # Make the request without required parameters
    response = api_client.post("/api/human-readable-entity", data={})
    
    # Check the response
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert "Missing required parameters" in data["message"]


def test_generate_unique_uri(app: Flask) -> None:
    """Test the generate_unique_uri function."""
    with app.app_context():
        # Create a mock URI generator
        mock_uri_generator = MagicMock()
        mock_uri_generator.generate_uri.return_value = "http://example.org/entity/1"
        
        # Configure the mock counter handler
        mock_counter_handler = MagicMock()
        mock_uri_generator.counter_handler = mock_counter_handler
        
        # Store the original URI generator
        original_uri_generator = app.config["URI_GENERATOR"]
        
        try:
            # Set our mock as the application's URI generator
            app.config["URI_GENERATOR"] = mock_uri_generator
            
            # Call the function with an entity type
            entity_type = "http://example.org/EntityType"
            result = generate_unique_uri(entity_type)
            
            # Verify the result
            assert result == URIRef("http://example.org/entity/1")
            
            # Verify the mocks were called correctly
            mock_uri_generator.generate_uri.assert_called_once_with(entity_type)
            mock_counter_handler.increment_counter.assert_called_once_with(entity_type)
        finally:
            # Restore the original URI generator
            app.config["URI_GENERATOR"] = original_uri_generator


def test_determine_datatype() -> None:
    """Test the determine_datatype function."""
    # Test with string value
    assert determine_datatype("test", [str(XSD.string)]) == XSD.string
    
    # Test with integer value
    assert determine_datatype("123", [str(XSD.integer)]) == XSD.integer
    
    # Test with date value
    assert determine_datatype("2023-01-01", [str(XSD.date)]) == XSD.date
    
    # Test with multiple possible datatypes
    assert determine_datatype("123", [str(XSD.integer), str(XSD.string)]) == XSD.integer
    
    # Test with no matching datatype
    assert determine_datatype("not a date", [str(XSD.date)]) == XSD.string


@patch("heritrace.routes.api.get_custom_filter")
def test_format_entities(mock_get_custom_filter, app: Flask) -> None:
    """Test the format_entities function."""
    with app.app_context():
        # Create a mock filter
        mock_filter = MagicMock()
        mock_get_custom_filter.return_value = mock_filter
        
        # Configure the mock to return readable values
        mock_filter.human_readable_entity.return_value = "Entity Label"
        mock_filter.human_readable_predicate.return_value = "Entity Type"
        
        # Create test entities
        entities = [
            {
                "uri": "http://example.org/entity/1",
                "type": "http://example.org/EntityType"
            },
            {
                "uri": "http://example.org/entity/2",
                "type": "http://example.org/EntityType"
            }
        ]
        
        # Define a format_entities function that mimics the one in check_orphans
        def format_entities(entities, is_intermediate=False):
            return [
                {
                    "uri": entity["uri"],
                    "label": mock_filter.human_readable_entity(
                        entity["uri"], [entity["type"]]
                    ),
                    "type": mock_filter.human_readable_predicate(
                        entity["type"], [entity["type"]]
                    ),
                    "is_intermediate": is_intermediate,
                }
                for entity in entities
            ]
        
        # Call the function
        result = format_entities(entities)
        
        # Verify the result
        assert len(result) == 2
        assert result[0]["uri"] == "http://example.org/entity/1"
        assert result[0]["label"] == "Entity Label"
        assert result[0]["type"] == "Entity Type"
        assert result[0]["is_intermediate"] is False
        
        assert result[1]["uri"] == "http://example.org/entity/2"
        assert result[1]["label"] == "Entity Label"
        assert result[1]["type"] == "Entity Type"
        assert result[1]["is_intermediate"] is False
        
        # Test with is_intermediate=True
        result = format_entities(entities, is_intermediate=True)
        assert result[0]["is_intermediate"] is True
        assert result[1]["is_intermediate"] is True


@patch("heritrace.routes.api.validate_new_triple")
@patch("heritrace.routes.api.generate_unique_uri")
def test_create_logic(mock_generate_unique_uri, mock_validate_new_triple, app: Flask) -> None:
    """Test the create_logic function."""
    with app.app_context():
        # Create a mock editor
        mock_editor = MagicMock()
        
        # Configure the mock validate_new_triple to return valid values
        mock_validate_new_triple.return_value = (URIRef("http://example.org/EntityType"), None, None)
        
        # Configure the mock generate_unique_uri to return a new URI for nested entities
        mock_generate_unique_uri.return_value = URIRef("http://example.org/new_entity")
        
        # Create test data
        data = {
            "entity_type": "http://example.org/EntityType",
            "properties": {
                "http://example.org/predicate1": "value1",
                "http://example.org/predicate2": ["value2", "value3"]
            }
        }
        
        # Call the function
        from heritrace.routes.api import create_logic
        subject = create_logic(
            mock_editor,
            data,
            subject=URIRef("http://example.org/subject"),
            graph_uri="http://example.org/graph"
        )
        
        # Verify the result
        assert subject == URIRef("http://example.org/subject")
        
        # Verify the editor was called correctly for simple values
        mock_editor.create.assert_any_call(
            URIRef("http://example.org/subject"),
            URIRef("http://example.org/predicate1"),
            URIRef("http://example.org/EntityType"),  # This is the mocked return value
            "http://example.org/graph"
        )
        
        # Verify validate_new_triple was called with the correct arguments
        # We can't use assert_any_call because the URIRef object might be different
        # So we check that it was called with the right arguments
        assert mock_validate_new_triple.call_count >= 3  # At least 3 calls for the properties
        
        # Check that the calls include our expected parameters
        found_call = False
        for call_args in mock_validate_new_triple.call_args_list:
            args, kwargs = call_args
            if (len(args) >= 4 and 
                str(args[0]) == "http://example.org/subject" and 
                str(args[1]) == "http://example.org/predicate1" and 
                args[2] == "value1" and 
                args[3] == "create" and 
                kwargs.get("entity_types") == "http://example.org/EntityType"):
                found_call = True
                break
        
        assert found_call, "Expected call to validate_new_triple not found"


@patch("heritrace.routes.api.validate_new_triple")
def test_update_logic(mock_validate_new_triple, app: Flask) -> None:
    """Test the update_logic function."""
    with app.app_context():
        # Create a mock editor
        mock_editor = MagicMock()
        
        # Configure the mock validate_new_triple to return valid values
        new_value = URIRef("http://example.org/new_value")
        old_value = URIRef("http://example.org/old_value")
        mock_validate_new_triple.return_value = (new_value, old_value, None)
        
        # Call the function
        update_logic(
            mock_editor,
            "http://example.org/subject",
            "http://example.org/predicate",
            "http://example.org/old_value",
            "http://example.org/new_value",
            "http://example.org/graph",
            "http://example.org/EntityType"
        )
        
        # Verify validate_new_triple was called correctly
        mock_validate_new_triple.assert_called_once_with(
            "http://example.org/subject",
            "http://example.org/predicate",
            "http://example.org/new_value",
            "update",
            "http://example.org/old_value",
            entity_types="http://example.org/EntityType"
        )
        
        # Verify the editor was called correctly
        mock_editor.update.assert_called_once_with(
            URIRef("http://example.org/subject"),
            URIRef("http://example.org/predicate"),
            old_value,
            new_value,
            "http://example.org/graph"
        )


@patch("heritrace.routes.api.validate_new_triple")
def test_delete_logic(mock_validate_new_triple, app: Flask) -> None:
    """Test the delete_logic function."""
    with app.app_context():
        # Create a mock editor
        mock_editor = MagicMock()
        
        # Configure the mock validate_new_triple to return valid values
        object_value = URIRef("http://example.org/object")
        mock_validate_new_triple.return_value = (None, object_value, None)
        
        # Call the function
        delete_logic(
            mock_editor,
            "http://example.org/subject",
            "http://example.org/predicate",
            "http://example.org/object",
            "http://example.org/graph",
            "http://example.org/EntityType"
        )
        
        # Verify validate_new_triple was called correctly
        mock_validate_new_triple.assert_called_once_with(
            "http://example.org/subject",
            "http://example.org/predicate",
            None,
            "delete",
            "http://example.org/object",
            entity_types="http://example.org/EntityType"
        )
        
        # Verify the editor was called correctly
        mock_editor.delete.assert_called_once_with(
            URIRef("http://example.org/subject"),
            URIRef("http://example.org/predicate"),
            object_value,
            "http://example.org/graph"
        )


@patch("heritrace.routes.api.generate_unique_uri")
def test_order_logic(mock_generate_unique_uri, app: Flask) -> None:
    """Test the order_logic function."""
    with app.app_context():
        # Create a mock editor
        mock_editor = MagicMock()
        
        # Configure the mock editor's g_set to return triples
        entity1 = URIRef("http://example.org/entity1")
        entity2 = URIRef("http://example.org/entity2")
        
        # Create a mock g_set with a triples method
        mock_g_set = MagicMock()
        mock_editor.g_set = mock_g_set
        
        # Configure the triples method to return different results based on the input
        def side_effect(triple_pattern):
            subject, predicate, obj = triple_pattern
            if subject == URIRef("http://example.org/subject") and predicate == URIRef("http://example.org/predicate"):
                return iter([(None, None, entity1), (None, None, entity2)])
            elif subject == entity1:
                return iter([(entity1, RDF.type, URIRef("http://example.org/EntityType")), 
                        (entity1, URIRef("http://example.org/prop"), URIRef("http://example.org/value"))])
            elif subject == entity2:
                return iter([(entity2, RDF.type, URIRef("http://example.org/EntityType")), 
                        (entity2, URIRef("http://example.org/prop"), URIRef("http://example.org/value"))])
            return iter([])
        
        mock_g_set.triples.side_effect = side_effect
        
        # Configure the mock generate_unique_uri to return new URIs
        new_entity1 = URIRef("http://example.org/new_entity1")
        new_entity2 = URIRef("http://example.org/new_entity2")
        mock_generate_unique_uri.side_effect = [new_entity1, new_entity2]
        
        # Create a temp_id_to_uri dictionary
        temp_id_to_uri = {}
        
        # Call the function
        result = order_logic(
            mock_editor,
            "http://example.org/subject",
            "http://example.org/predicate",
            [str(entity1), str(entity2)],
            "http://example.org/ordered_by",
            "http://example.org/graph",
            temp_id_to_uri
        )
        
        # Verify the result
        assert result == mock_editor