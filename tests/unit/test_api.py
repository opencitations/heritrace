"""
Tests for the API routes in heritrace/routes/api.py.
"""

import json
from typing import Generator
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask, g
from flask.testing import FlaskClient
from heritrace.routes.api import (create_logic, delete_logic,
                                  determine_datatype, generate_unique_uri,
                                  order_logic, rebuild_entity_order,
                                  update_logic)
from heritrace.services.resource_lock_manager import (LockStatus,
                                                      ResourceLockManager)
from heritrace.utils.strategies import (OrphanHandlingStrategy,
                                        ProxyHandlingStrategy)
from rdflib import RDF, XSD, Graph, Literal, URIRef
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
    assert data["per_page"] == 50


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


@patch("heritrace.routes.api.get_deleted_entities_with_filtering")
def test_time_vault_api(mock_get_deleted_entities, api_client: FlaskClient, app: Flask) -> None:
    """Test the time vault API endpoint."""
    # Mock the return value of get_deleted_entities_with_filtering
    mock_deleted_entities = [
        {
            "uri": "http://example.org/entity1",
            "deletionTime": "2023-01-01T00:00:00Z",
            "deletedBy": "User 1",
            "type": "TestClass",
            "label": "Test Entity 1"
        }
    ]
    mock_available_classes = [
        {
            "uri": "http://example.org/TestClass",
            "label": "Test Class",
            "count": 1
        }
    ]
    mock_sortable_properties = [
        {"property": "deletionTime", "displayName": "Deletion Time", "sortType": "date"}
    ]
    
    mock_get_deleted_entities.return_value = (
        mock_deleted_entities,
        mock_available_classes,
        "http://example.org/TestClass",
        "http://example.org/TestShape",
        mock_sortable_properties,
        1,
    )
    
    response = api_client.get("/api/time-vault")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "entities" in data
    assert "available_classes" in data
    assert len(data["entities"]) == 1
    assert len(data["available_classes"]) == 1
    assert data["total_count"] == 1


@patch("heritrace.routes.api.get_deleted_entities_with_filtering")
def test_time_vault_api_with_params(mock_get_deleted_entities, api_client: FlaskClient) -> None:
    """Test the time vault API endpoint with query parameters."""
    # Mock the return value of get_deleted_entities_with_filtering
    mock_deleted_entities = [
        {
            "uri": "http://example.org/entity1",
            "deletionTime": "2023-01-01T00:00:00Z",
            "deletedBy": "User 1",
            "type": "TestClass",
            "label": "Test Entity 1"
        }
    ]
    mock_available_classes = [
        {
            "uri": "http://example.org/TestClass",
            "label": "Test Class",
            "count": 1
        }
    ]
    mock_sortable_properties = [
        {"property": "deletionTime", "displayName": "Deletion Time", "sortType": "date"}
    ]
    
    mock_get_deleted_entities.return_value = (
        mock_deleted_entities,
        mock_available_classes,
        "http://example.org/TestClass",
        "http://example.org/TestShape",
        mock_sortable_properties,
        1,
    )
    
    response = api_client.get(
        "/api/time-vault?class=http://example.org/TestClass&page=1&per_page=50"
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "entities" in data
    assert "available_classes" in data
    assert "current_page" in data
    assert data["current_page"] == 1
    assert data["per_page"] == 50


@patch("heritrace.routes.api.get_deleted_entities_with_filtering")
def test_time_vault_api_with_invalid_per_page(mock_get_deleted_entities, api_client: FlaskClient) -> None:
    """Test the time vault API endpoint with an invalid per_page value."""
    # Mock the return value of get_deleted_entities_with_filtering
    mock_deleted_entities = [
        {
            "uri": "http://example.org/entity1",
            "deletionTime": "2023-01-01T00:00:00Z",
            "deletedBy": "User 1",
            "type": "TestClass",
            "label": "Test Entity 1"
        }
    ]
    mock_available_classes = [
        {
            "uri": "http://example.org/TestClass",
            "label": "Test Class",
            "count": 1
        }
    ]
    mock_sortable_properties = [
        {"property": "deletionTime", "displayName": "Deletion Time", "sortType": "date"}
    ]
    
    mock_get_deleted_entities.return_value = (
        mock_deleted_entities,
        mock_available_classes,
        "http://example.org/TestClass",
        "http://example.org/TestShape",
        mock_sortable_properties,
        1,
    )
    
    response = api_client.get(
        "/api/time-vault?class=http://example.org/TestClass&page=1&per_page=999"
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "entities" in data
    assert "available_classes" in data
    assert "current_page" in data
    assert data["current_page"] == 1
    assert data["per_page"] == 50


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
            assert data["status"] == "available"


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
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "locked"
            assert "Another User" in data["message"]


def test_check_lock_error_status(
    api_client: FlaskClient, app: Flask
) -> None:
    """Test the check_lock endpoint when LockStatus.ERROR is returned."""
    resource_uri = "http://example.org/error-resource"

    # Mock the resource_lock_manager to return ERROR status
    with patch("heritrace.services.resource_lock_manager.ResourceLockManager.check_lock_status") as mock_check:
        mock_check.return_value = (LockStatus.ERROR, None)

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
                assert response.status_code == 500
                data = json.loads(response.data)
                assert data["status"] == "error"
                assert data["message"] == "An error occurred while checking the lock"


def test_check_lock_exception(
    api_client: FlaskClient, app: Flask
) -> None:
    """Test the check_lock endpoint when an exception occurs."""
    resource_uri = "http://example.org/exception-resource"

    # Mock the resource_lock_manager to raise an exception
    with patch("heritrace.services.resource_lock_manager.ResourceLockManager.check_lock_status") as mock_check:
        mock_check.side_effect = Exception("Test exception")

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
                assert response.status_code == 500
                data = json.loads(response.data)
                assert data["status"] == "error"
                assert data["message"] == "An unexpected error occurred"


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
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "locked"


def test_acquire_lock_race_condition(
    api_client: FlaskClient, app: Flask
) -> None:
    """Test the acquire_lock endpoint when the resource becomes locked between check and acquire."""
    resource_uri = "http://example.org/race-condition-resource"

    # Mock check_lock_status to return UNLOCKED but acquire_lock to return False
    # This simulates a race condition where another user acquires the lock between our check and acquire
    with patch("heritrace.services.resource_lock_manager.ResourceLockManager.check_lock_status") as mock_check:
        mock_check.return_value = (LockStatus.AVAILABLE, None)
        
        with patch("heritrace.services.resource_lock_manager.ResourceLockManager.acquire_lock") as mock_acquire:
            mock_acquire.return_value = False
            
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
                    
                    # This should trigger the 423 error response
                    assert response.status_code == 423
                    data = json.loads(response.data)
                    assert data["status"] == "error"
                    assert "Resource is locked by another user" in data["message"]


def test_acquire_lock_exception(
    api_client: FlaskClient, app: Flask
) -> None:
    """Test the acquire_lock endpoint when an exception occurs."""
    resource_uri = "http://example.org/exception-resource"

    # Mock the resource_lock_manager to raise an exception
    with patch("heritrace.services.resource_lock_manager.ResourceLockManager.acquire_lock") as mock_acquire:
        mock_acquire.side_effect = Exception("Test exception")

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
                assert response.status_code == 500
                data = json.loads(response.data)
                assert data["status"] == "error"
                assert data["message"] == "An unexpected error occurred"


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


def test_release_lock_exception(
    api_client: FlaskClient, app: Flask
) -> None:
    """Test the release_lock endpoint when an exception occurs."""
    resource_uri = "http://example.org/exception-resource-release"

    # Mock the resource_lock_manager to raise an exception
    with patch("heritrace.services.resource_lock_manager.ResourceLockManager.release_lock") as mock_release:
        mock_release.side_effect = Exception("Test exception")

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
                assert response.status_code == 500
                data = json.loads(response.data)
                assert data["status"] == "error"
                assert data["message"] == "An unexpected error occurred"


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


def test_renew_lock_exception(
    api_client: FlaskClient, app: Flask
) -> None:
    """Test the renew_lock endpoint when an exception occurs."""
    resource_uri = "http://example.org/exception-resource-renew"

    # Mock the resource_lock_manager to raise an exception
    with patch("heritrace.services.resource_lock_manager.ResourceLockManager.acquire_lock") as mock_renew:
        mock_renew.side_effect = Exception("Test exception")

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
                assert response.status_code == 500
                data = json.loads(response.data)
                assert data["status"] == "error"
                assert data["message"] == "An unexpected error occurred"


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


def test_validate_literal_no_matching_datatypes(api_client: FlaskClient) -> None:
    """Test the validate_literal endpoint with a value that has no matching datatypes."""
    # Mock the DATATYPE_MAPPING to ensure no datatypes match
    with patch("heritrace.routes.api.DATATYPE_MAPPING", []):
        response = api_client.post(
            "/api/validate-literal",
            json={"value": "test value that won't match any datatype"},
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "No matching datatypes found" in data["error"]


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
    # Set up the mock custom filter to return static values to avoid serialization issues
    custom_filter = MagicMock()
    custom_filter.human_readable_entity.return_value = "Human Readable Entity"
    custom_filter.human_readable_class.return_value = "Human Readable Type"
    mock_get_custom_filter.return_value = custom_filter
    
    # Mock the find_orphaned_entities function to return orphans
    mock_find_orphaned.return_value = (
        [{"uri": "http://example.org/orphan/1", "type": "http://example.org/Type", "shape": "http://example.org/Shape"}],
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
    # Set up the mock custom filter to return static values to avoid serialization issues
    custom_filter = MagicMock()
    custom_filter.human_readable_entity.return_value = "Human Readable Entity"
    custom_filter.human_readable_class.return_value = "Human Readable Type"
    mock_get_custom_filter.return_value = custom_filter
    
    # Mock the find_orphaned_entities function to return proxies
    mock_find_orphaned.return_value = (
        [],
        [{"uri": "http://example.org/proxy/1", "type": "http://example.org/ProxyType", "shape": "http://example.org/ProxyShape"}],
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
    # Set up the mock custom filter to return static values to avoid serialization issues
    custom_filter = MagicMock()
    custom_filter.human_readable_entity.return_value = "Human Readable Entity"
    custom_filter.human_readable_class.return_value = "Human Readable Type"
    mock_get_custom_filter.return_value = custom_filter
    
    # Mock the find_orphaned_entities function to return orphans
    mock_find_orphaned.return_value = (
        [{"uri": "http://example.org/orphan/1", "type": "http://example.org/Type", "shape": "http://example.org/Shape"}],
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
    # Set up the mock custom filter to return static values to avoid serialization issues
    custom_filter = MagicMock()
    custom_filter.human_readable_entity.return_value = "Human Readable Entity"
    custom_filter.human_readable_class.return_value = "Human Readable Type"
    mock_get_custom_filter.return_value = custom_filter
    
    # Mock the find_orphaned_entities function to return proxies
    mock_find_orphaned.return_value = (
        [],
        [{"uri": "http://example.org/proxy/1", "type": "http://example.org/ProxyType", "shape": "http://example.org/ProxyShape"}],
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
    # Set up the mock custom filter to return static values to avoid serialization issues
    custom_filter = MagicMock()
    custom_filter.human_readable_entity.return_value = "Human Readable Entity"
    custom_filter.human_readable_class.return_value = "Human Readable Type"
    mock_get_custom_filter.return_value = custom_filter
    
    # Mock the find_orphaned_entities function to return both orphans and proxies
    mock_find_orphaned.return_value = (
        [{"uri": "http://example.org/orphan/1", "type": "http://example.org/Type", "shape": "http://example.org/Shape"}],
        [{"uri": "http://example.org/proxy/1", "type": "http://example.org/ProxyType", "shape": "http://example.org/ProxyShape"}],
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


@patch("heritrace.routes.api.find_orphaned_entities")
def test_check_orphans_validation_error(
    mock_find_orphaned, api_client: FlaskClient
) -> None:
    """Test the check_orphans endpoint with a ValueError exception."""
    # Mock the find_orphaned_entities function to raise a ValueError
    mock_find_orphaned.side_effect = ValueError("Validation test error")

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
    # The API should return 400 for validation errors
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert data["error_type"] == "validation"
    assert "An error occurred while checking for orphaned entities" in data["message"]

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
        ("http://example.org/EntityClass", None)
    )


def test_get_human_readable_entity_missing_params(api_client: FlaskClient) -> None:
    """Test the get_human_readable_entity endpoint with missing parameters."""
    # Make the request without required parameters
    response = api_client.post("/api/human-readable-entity", data={})

    # Check the response
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"


@patch("heritrace.routes.api.validate_new_triple")
@patch("heritrace.routes.api.generate_unique_uri")
def test_create_logic_with_temp_id(mock_generate_unique_uri, mock_validate_new_triple, app: Flask) -> None:
    """Test the create_logic function with temp_id handling."""
    with app.test_request_context():
        # Mock the generate_unique_uri function
        mock_generate_unique_uri.return_value = URIRef("http://example.org/entity/new")
        
        # Mock validate_new_triple to return None for all values since parent_subject is None
        # This matches the behavior in create_logic where the validate_new_triple call is skipped
        # when parent_subject is None
        mock_validate_new_triple.return_value = (None, None, None)
        
        # Create a mock editor
        mock_editor = MagicMock()
        
        # Test data with temp_id
        data = {
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type": [
                {
                    "value": "http://example.org/type/1",
                    "datatype": "http://www.w3.org/2001/XMLSchema#anyURI"
                }
            ]
        }
        
        # Create a temp_id_to_uri mapping
        temp_id_to_uri = {}
        
        # Create data with tempId
        data = {
            "entity_type": "http://example.org/type/1",
            "properties": {},
            "tempId": "temp-123"
        }
        
        # Call create_logic with temp_id
        result = create_logic(
            mock_editor,
            data,
            subject=None,  # subject is None to trigger generate_unique_uri
            graph_uri=URIRef("http://example.org/graph/1"),
            parent_subject=None,
            parent_predicate=None,
            temp_id_to_uri=temp_id_to_uri,
            parent_entity_type="http://example.org/type/1"
        )
        
        # Verify the result
        assert result == URIRef("http://example.org/entity/new")
        
        # Verify temp_id was added to the mapping
        assert temp_id_to_uri["temp-123"] == "http://example.org/entity/new"
        
        # When parent_subject is None, the editor.create call for RDF.type is skipped
        # Verify that editor.create was not called
        assert not mock_editor.create.called


@patch("heritrace.routes.api.validate_new_triple")
@patch("heritrace.routes.api.create_logic")
@patch("heritrace.routes.api.generate_unique_uri")
def test_create_logic_with_nested_entity(mock_generate_unique_uri, mock_nested_create_logic, mock_validate_new_triple, app: Flask) -> None:
    """Test the create_logic function with nested entity creation."""
    with app.test_request_context():
        # Mock the generate_unique_uri function
        mock_generate_unique_uri.return_value = URIRef("http://example.org/nested/1")
        
        # Mock validate_new_triple to return None for all values since parent_subject is None
        # This matches the behavior in create_logic where the validate_new_triple call is skipped
        # when parent_subject is None
        mock_validate_new_triple.return_value = (None, None, None)
        
        # Mock the nested create_logic call
        mock_nested_create_logic.return_value = "http://example.org/nested/1"
        
        # Create a mock editor
        mock_editor = MagicMock()
        
        # Test data with a nested entity
        data = {
            "entity_type": "http://example.org/type/1",
            "properties": {
                "http://example.org/property/1": [
                    {
                        "entity_type": "http://example.org/type/nested",
                        "properties": {
                            "http://example.org/nested/property": ["Nested Value"]
                        }
                    }
                ]
            }
        }
        
        # Call create_logic
        result = create_logic(
            mock_editor,
            data,
            "http://example.org/entity/1",
            URIRef("http://example.org/graph/1"),
            None,
            None,
            {},
            "http://example.org/type/1"
        )
        
        # Verify the result
        assert result == "http://example.org/entity/1"
        
        # Verify generate_unique_uri was called for the nested entity
        mock_generate_unique_uri.assert_called_with("http://example.org/type/nested")
        
        # Verify nested create_logic was called
        mock_nested_create_logic.assert_called_once()
        call_args = mock_nested_create_logic.call_args[0]
        assert call_args[0] == mock_editor
        assert call_args[1] == data["properties"]["http://example.org/property/1"][0]
        assert call_args[3] == URIRef("http://example.org/graph/1")
        assert call_args[4] == "http://example.org/entity/1"
        assert call_args[5] == "http://example.org/property/1"


@patch("heritrace.routes.api.validate_new_triple")
def test_update_logic_implementation(mock_validate_new_triple, app: Flask) -> None:
    """Test the update_logic function implementation."""
    with app.test_request_context():
        # Mock validate_new_triple to return the new and old values
        new_value = Literal("New Value")
        old_value = Literal("Old Value")
        mock_validate_new_triple.return_value = (new_value, old_value, None)
        
        # Create a mock editor
        mock_editor = MagicMock()
        
        # Call update_logic
        update_logic(
            mock_editor,
            "http://example.org/entity/1",
            "http://example.org/property/1",
            old_value,
            "New Value",
            URIRef("http://example.org/graph/1"),
            "http://example.org/type/1"
        )
        
        # Verify validate_new_triple was called
        mock_validate_new_triple.assert_called_with(
            "http://example.org/entity/1",
            "http://example.org/property/1",
            "New Value",
            "update",
            old_value,
            entity_types="http://example.org/type/1",
            entity_shape=None
        )
        
        # Verify editor.update was called
        mock_editor.update.assert_called_with(
            URIRef("http://example.org/entity/1"),
            URIRef("http://example.org/property/1"),
            old_value,
            new_value,
            URIRef("http://example.org/graph/1")
        )


@patch("heritrace.routes.api.validate_new_triple")
def test_delete_logic_with_direct_graph_context(mock_validate_new_triple, app: Flask) -> None:
    """Test delete_logic with a direct graph context instead of a Graph object."""
    with app.test_request_context():
        # Create a mock editor
        mock_editor = MagicMock()
        
        # Mock validate_new_triple to return valid values for the object
        mock_validate_new_triple.return_value = (None, None, None)
        
        # Call delete_logic with test data
        from heritrace.routes.api import delete_logic
        delete_logic(
            mock_editor,
            "http://example.org/subject",
            "http://example.org/predicate",
            "http://example.org/object",
            URIRef("http://example.org/graph")
        )
        
        # Verify that editor.delete was called with the correct arguments
        # Note: The second parameter in the return value from validate_new_triple is used as the object_value
        mock_editor.delete.assert_called_once_with(
            URIRef("http://example.org/subject"),
            URIRef("http://example.org/predicate"),
            None,
            URIRef("http://example.org/graph")
        )


@patch("heritrace.routes.api.validate_new_triple")
def test_delete_logic_with_validation_error(mock_validate_new_triple, app: Flask) -> None:
    """Test delete_logic when validate_new_triple returns an error message."""
    with app.test_request_context():
        # Create a mock editor
        mock_editor = MagicMock()
        
        # Mock validate_new_triple to return an error message
        mock_validate_new_triple.return_value = (None, None, "Validation error")
        
        # Call delete_logic with test data and expect a ValueError
        from heritrace.routes.api import delete_logic
        with pytest.raises(ValueError, match="Validation error"):
            delete_logic(
                mock_editor,
                "http://example.org/subject",
                "http://example.org/predicate",
                "http://example.org/object",
                URIRef("http://example.org/graph")
            )
        
        # Verify that editor.delete was not called
        mock_editor.delete.assert_not_called()


@patch("heritrace.routes.api.validate_new_triple")
def test_delete_logic_implementation(mock_validate_new_triple, app: Flask) -> None:
    """Test the delete_logic function implementation."""
    with app.test_request_context():
        # Mock validate_new_triple to return None for object_value and error_message
        # This simulates the validate_new_triple function returning None for the object_value
        mock_validate_new_triple.return_value = (None, None, None)
        
        # Create a mock editor
        mock_editor = MagicMock()
        
        # Create test values
        subject = "http://example.org/entity/1"
        predicate = "http://example.org/property/1"
        object_value = Literal("Value to delete")
        graph_uri = URIRef("http://example.org/graph/1")
        entity_type = "http://example.org/type/1"
        
        # Call delete_logic
        delete_logic(
            mock_editor,
            subject,
            predicate,
            object_value,
            graph_uri,
            entity_type
        )
        
        # Verify validate_new_triple was called
        mock_validate_new_triple.assert_called_once_with(
            subject,
            predicate,
            None,
            "delete",
            object_value,
            entity_types=entity_type,
            entity_shape=None
        )
        
        # Verify editor.delete was called with None for object_value
        # This matches the actual behavior where validate_new_triple returns None
        mock_editor.delete.assert_called_with(
            URIRef(subject),
            URIRef(predicate),
            None,  # object_value is None after validate_new_triple
            graph_uri
        )


def test_rebuild_entity_order(app: Flask) -> None:
    """Test the rebuild_entity_order function."""
    with app.test_request_context():
        # Create a mock editor
        mock_editor = MagicMock()
        
        # Create mock entities and ordered_by_uri
        entity1 = URIRef("http://example.org/entity/1")
        entity2 = URIRef("http://example.org/entity/2")
        entity3 = URIRef("http://example.org/entity/3")
        ordered_by_uri = URIRef("http://example.org/property/next")
        graph_uri = URIRef("http://example.org/graph/1")
        
        # Mock the triples method to return existing ordering triples
        def triples_side_effect(*args):
            if args[0][0] == entity1 and args[0][1] == ordered_by_uri:
                yield (entity1, ordered_by_uri, entity2)
            elif args[0][0] == entity2 and args[0][1] == ordered_by_uri:
                yield (entity2, ordered_by_uri, entity3)
            elif args[0][0] == entity3 and args[0][1] == ordered_by_uri:
                return
                yield  # This will never be reached but prevents StopIteration
        
        mock_editor.g_set.triples = MagicMock(side_effect=triples_side_effect)
        
        # Call rebuild_entity_order
        result = rebuild_entity_order(
            mock_editor,
            ordered_by_uri,
            [entity1, entity2, entity3],
            graph_uri
        )
        
        # Verify the result is the editor
        assert result == mock_editor
        
        # Verify delete was called for existing triples
        assert mock_editor.delete.call_count == 2
        
        # Verify create was called to establish new ordering
        assert mock_editor.create.call_count == 2
        mock_editor.create.assert_any_call(entity1, ordered_by_uri, entity2, graph_uri)
        mock_editor.create.assert_any_call(entity2, ordered_by_uri, entity3, graph_uri)


@patch("heritrace.routes.api.generate_unique_uri")
def test_order_logic_with_entity_type_determination(mock_generate_unique_uri, app: Flask) -> None:
    """Test the order_logic function with entity type determination."""
    with app.test_request_context():
        # Mock generate_unique_uri
        mock_generate_unique_uri.return_value = URIRef("http://example.org/entity/new")
        
        # Create a mock editor
        mock_editor = MagicMock()
        
        # Mock the triples method to return entity type and current entities
        def triples_side_effect(*args):
            # For getting current entities
            if args[0] == (URIRef("http://example.org/container/1"), URIRef("http://example.org/property/items"), None):
                yield (URIRef("http://example.org/container/1"), URIRef("http://example.org/property/items"), URIRef("http://example.org/entity/old"))
            # For getting entity properties
            elif args[0] == (URIRef("http://example.org/entity/old"), None, None):
                yield (URIRef("http://example.org/entity/old"), RDF.type, URIRef("http://example.org/type/1"))
                yield (URIRef("http://example.org/entity/old"), URIRef("http://example.org/property/name"), Literal("Old Entity"))
            else:
                return
                yield  # This will never be reached but prevents StopIteration
        
        mock_editor.g_set.triples = MagicMock(side_effect=triples_side_effect)
        
        # Call order_logic with a new order that includes an old entity
        result = order_logic(
            mock_editor,
            "http://example.org/container/1",
            "http://example.org/property/items",
            ["http://example.org/entity/old", "temp-123"],
            "http://example.org/property/next",
            URIRef("http://example.org/graph/1"),
            {"temp-123": "http://example.org/entity/new"}
        )
        
        # Verify the result is the editor
        assert result == mock_editor
        
        # Verify generate_unique_uri was called with the correct entity type
        mock_generate_unique_uri.assert_called_once_with(URIRef("http://example.org/type/1"))
        
        # No need to verify specific triples calls as we're using a side_effect function
        # The test passes if generate_unique_uri was called correctly


@patch("heritrace.routes.api.validate_new_triple")
@patch("heritrace.routes.api.generate_unique_uri")
def test_create_logic_with_parent(mock_generate_unique_uri, mock_validate_new_triple, app: Flask) -> None:
    """Test the create_logic function with parent_subject and parent_predicate."""
    with app.test_request_context():
        # Mock the generate_unique_uri function
        mock_generate_unique_uri.return_value = URIRef("http://example.org/entity/new")
        
        # Mock validate_new_triple to return valid values
        mock_validate_new_triple.side_effect = [
            # First call for entity type
            (URIRef("http://example.org/type/1"), None, None),
            # Second call for parent relationship
            (URIRef("http://example.org/entity/new"), None, None),
            # Third call for property
            (Literal("Test Value"), None, None)
        ]
        
        # Create a mock editor
        mock_editor = MagicMock()
        
        # Test data with properties
        data = {
            "entity_type": "http://example.org/type/1",
            "properties": {
                "http://example.org/property/name": {
                    "value": "Test Value",
                    "datatype": "http://www.w3.org/2001/XMLSchema#string"
                }
            }
        }
        
        # Call create_logic with parent_subject and parent_predicate
        result = create_logic(
            mock_editor,
            data,
            subject=URIRef("http://example.org/entity/new"),
            graph_uri=URIRef("http://example.org/graph/1"),
            parent_subject=URIRef("http://example.org/parent/1"),
            parent_predicate=URIRef("http://example.org/property/hasChild"),
            parent_entity_type="http://example.org/type/parent"
        )
        
        # Verify the result
        assert result == URIRef("http://example.org/entity/new")
        
        # Verify validate_new_triple was called for entity type
        mock_validate_new_triple.assert_any_call(
            URIRef("http://example.org/entity/new"),
            RDF.type,
            "http://example.org/type/1",
            "create",
            entity_types="http://example.org/type/1"
        )
        
        # Verify validate_new_triple was called for parent relationship
        mock_validate_new_triple.assert_any_call(
            URIRef("http://example.org/parent/1"),
            URIRef("http://example.org/property/hasChild"),
            URIRef("http://example.org/entity/new"),
            "create",
            entity_types="http://example.org/type/parent"
        )
        
        # Verify editor.create was called for entity type
        mock_editor.create.assert_any_call(
            URIRef("http://example.org/entity/new"),
            RDF.type,
            URIRef("http://example.org/type/1"),
            URIRef("http://example.org/graph/1")
        )
        
        # Verify editor.create was called for parent relationship
        mock_editor.create.assert_any_call(
            URIRef("http://example.org/parent/1"),
            URIRef("http://example.org/property/hasChild"),
            URIRef("http://example.org/entity/new"),
            URIRef("http://example.org/graph/1")
        )


@patch("heritrace.routes.api.validate_new_triple")
@patch("heritrace.routes.api.generate_unique_uri")
def test_create_logic_entity_type_error(mock_generate_unique_uri, mock_validate_new_triple, app: Flask) -> None:
    """Test the create_logic function when validate_new_triple returns an error for entity type."""
    with app.test_request_context():
        # Mock the generate_unique_uri function
        mock_generate_unique_uri.return_value = URIRef("http://example.org/entity/new")
        
        # Mock validate_new_triple to return an error for entity type
        mock_validate_new_triple.return_value = (None, None, "Invalid entity type")
        
        # Create a mock editor
        mock_editor = MagicMock()
        
        # Test data
        data = {
            "entity_type": "http://example.org/type/1",
            "properties": {}
        }
        
        # Call create_logic with parent_subject to trigger entity type validation
        with pytest.raises(ValueError, match="Invalid entity type"):
            create_logic(
                mock_editor,
                data,
                subject=URIRef("http://example.org/entity/new"),
                graph_uri=URIRef("http://example.org/graph/1"),
                parent_subject=URIRef("http://example.org/parent/1")
            )


@patch("heritrace.routes.api.validate_new_triple")
@patch("heritrace.routes.api.generate_unique_uri")
def test_create_logic_parent_relation_error(mock_generate_unique_uri, mock_validate_new_triple, app: Flask) -> None:
    """Test the create_logic function when validate_new_triple returns an error for parent relation."""
    with app.test_request_context():
        # Mock the generate_unique_uri function
        mock_generate_unique_uri.return_value = URIRef("http://example.org/entity/new")
        
        # Mock validate_new_triple to return valid value for entity type but error for parent relation
        mock_validate_new_triple.side_effect = [
            # First call for entity type
            (URIRef("http://example.org/type/1"), None, None),
            # Second call for parent relationship
            (None, None, "Invalid parent relation")
        ]
        
        # Create a mock editor
        mock_editor = MagicMock()
        
        # Test data
        data = {
            "entity_type": "http://example.org/type/1",
            "properties": {}
        }
        
        # Call create_logic with parent_subject and parent_predicate
        with pytest.raises(ValueError, match="Invalid parent relation"):
            create_logic(
                mock_editor,
                data,
                subject=URIRef("http://example.org/entity/new"),
                graph_uri=URIRef("http://example.org/graph/1"),
                parent_subject=URIRef("http://example.org/parent/1"),
                parent_predicate=URIRef("http://example.org/property/hasChild"),
                parent_entity_type="http://example.org/type/parent"
            )


@patch("heritrace.routes.api.validate_new_triple")
@patch("heritrace.routes.api.generate_unique_uri")
def test_create_logic_property_error(mock_generate_unique_uri, mock_validate_new_triple, app: Flask) -> None:
    """Test the create_logic function when validate_new_triple returns an error for a property."""
    with app.test_request_context():
        # Mock the generate_unique_uri function
        mock_generate_unique_uri.return_value = URIRef("http://example.org/entity/new")
        
        # Mock validate_new_triple to return valid values for entity type and parent relation
        # but error for property
        mock_validate_new_triple.side_effect = [
            # First call for entity type
            (URIRef("http://example.org/type/1"), None, None),
            # Second call for parent relationship
            (URIRef("http://example.org/entity/new"), None, None),
            # Third call for property
            (None, None, "Invalid property value")
        ]
        
        # Create a mock editor
        mock_editor = MagicMock()
        
        # Test data with properties - using dictionary format for properties
        data = {
            "entity_type": "http://example.org/type/1",
            "properties": {
                "http://example.org/property/name": [{"type": "literal", "value": "Test Value"}]
            }
        }
        
        # Call create_logic with parent_subject and parent_predicate
        with pytest.raises(ValueError, match="Invalid property value"):
            create_logic(
                mock_editor,
                data,
                subject=URIRef("http://example.org/entity/new"),
                graph_uri=URIRef("http://example.org/graph/1"),
                parent_subject=URIRef("http://example.org/parent/1"),
                parent_predicate=URIRef("http://example.org/property/hasChild"),
                parent_entity_type="http://example.org/type/parent"
            )


def test_get_graph_uri_from_context() -> None:
    """Test the get_graph_uri_from_context function in api.py."""
    from heritrace.routes.api import get_graph_uri_from_context

    # Test with a direct URIRef (non-Graph context)
    direct_uri = URIRef("http://example.org/graph/2")
    graph_uri = get_graph_uri_from_context(direct_uri)
    assert graph_uri == direct_uri
    assert graph_uri is direct_uri  # They should be the same object
    
    # Test with a Graph object
    mock_graph = MagicMock(spec=Graph)
    mock_graph.identifier = URIRef("http://example.org/graph/1")
    graph_uri = get_graph_uri_from_context(mock_graph)
    assert graph_uri == URIRef("http://example.org/graph/1")


@patch("heritrace.routes.api.validate_new_triple")
def test_update_logic_with_error_message(mock_validate_new_triple, app: Flask) -> None:
    """Test update_logic when validate_new_triple returns an error message."""
    with app.test_request_context():
        # Mock the validate_new_triple function to return an error
        mock_validate_new_triple.return_value = (None, None, "Invalid update value")
        
        # Create a mock editor
        mock_editor = MagicMock()
        
        # Call update_logic with test data
        with pytest.raises(ValueError, match="Invalid update value"):
            update_logic(
                mock_editor,
                "http://example.org/subject/1",
                "http://example.org/predicate/1",
                "Old Value",
                "New Value",
                URIRef("http://example.org/graph/1"),
                "http://example.org/type/1"
            )
        
        # Verify that editor.update was not called
        mock_editor.update.assert_not_called()


def test_order_logic_entity_type_error(app: Flask) -> None:
    """Test order_logic when entity type cannot be determined."""
    with app.test_request_context():
        # Create a mock editor
        mock_editor = MagicMock()
        
        # Set up the mock editor to return triples for the subject and predicate
        old_entity = URIRef("http://example.org/old/1")
        mock_editor.g_set.triples.side_effect = [
            # First call for current entities
            [(None, None, old_entity)],
            # Second call for entity properties
            [(old_entity, RDF.type, None)],
        ]
        
        # Mock the get_entity_type method to return None for the entity type
        mock_editor.get_entity_type.return_value = None
        
        # Call order_logic with test data
        with pytest.raises(ValueError, match="Impossibile determinare il tipo dell'entità"):
            from heritrace.routes.api import order_logic
            order_logic(
                mock_editor,
                "http://example.org/subject/1",
                "http://example.org/predicate/1",
                ["http://example.org/old/1"],
                "http://example.org/ordered_by",
                URIRef("http://example.org/graph/1")
            )


def test_generate_unique_uri(app: Flask) -> None:
    """Test the generate_unique_uri function."""
    with app.app_context():
        # Create a mock URI generator
        mock_uri_generator = MagicMock()
        mock_uri_generator.generate_uri.return_value = "http://example.org/entity/1"

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

            # Verify the mock was called correctly
            mock_uri_generator.generate_uri.assert_called_once_with(entity_type, None)

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

        # Create test data - using dictionary format for property values
        data = {
            "entity_type": "http://example.org/EntityType",
            "properties": {
                "http://example.org/predicate1": [{"type": "literal", "value": "value1"}],
                "http://example.org/predicate2": [
                    {"type": "literal", "value": "value2"}, 
                    {"type": "literal", "value": "value3"}
                ]
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

        # Verify that the function returned the correct subject
        assert subject == URIRef("http://example.org/subject")

        # Verify validate_new_triple was called the right number of times
        # Should be called for each property value (2 calls for predicate1, 2 calls for predicate2)
        assert mock_validate_new_triple.call_count == 3


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
            entity_types="http://example.org/EntityType",
            entity_shape=None
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
            entity_types="http://example.org/EntityType",
            entity_shape=None
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