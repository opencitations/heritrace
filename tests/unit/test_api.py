"""
Tests for the API routes in heritrace/routes/api.py.
"""

import json
from typing import Generator

import pytest
from flask import Flask, g
from flask.testing import FlaskClient
from heritrace.services.resource_lock_manager import ResourceLockManager
from heritrace.utils.strategies import OrphanHandlingStrategy, ProxyHandlingStrategy
from redis import Redis
from SPARQLWrapper import SPARQLWrapper, JSON


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
