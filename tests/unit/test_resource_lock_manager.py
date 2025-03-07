import json
import time
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from heritrace.services.resource_lock_manager import (
    LockInfo,
    LockStatus,
    ResourceLockManager,
)
from heritrace.services.sparql import SparqlService


@pytest.fixture
def mock_sparql_service():
    """Create a mock SparqlService instance."""
    mock_service = MagicMock(spec=SparqlService)
    # Configure the mock to return an empty list of linked resources by default
    mock_service.get_linked_resources.return_value = []
    return mock_service

@pytest.fixture
def resource_lock_manager(redis_client, mock_sparql_service) -> ResourceLockManager:
    """Create a ResourceLockManager instance with a real Redis client and mock SPARQL service."""
    return ResourceLockManager(redis_client, mock_sparql_service)


def test_generate_lock_key(resource_lock_manager: ResourceLockManager):
    """Test the _generate_lock_key method."""
    resource_uri = "http://example.org/resource/123"
    expected_key = f"resource_lock:{resource_uri}"
    assert resource_lock_manager._generate_lock_key(resource_uri) == expected_key


def test_get_lock_info_no_lock(resource_lock_manager: ResourceLockManager):
    """Test get_lock_info when no lock exists."""
    resource_uri = "http://example.org/resource/no-lock"
    # Ensure no lock exists
    lock_key = resource_lock_manager._generate_lock_key(resource_uri)
    resource_lock_manager.redis.delete(lock_key)

    lock_info = resource_lock_manager.get_lock_info(resource_uri)
    assert lock_info is None


def test_get_lock_info_with_lock(resource_lock_manager: ResourceLockManager):
    """Test get_lock_info when a lock exists."""
    resource_uri = "http://example.org/resource/with-lock"
    lock_key = resource_lock_manager._generate_lock_key(resource_uri)

    # Create a lock manually
    lock_data = {
        "user_id": "0000-0001-2345-6789",
        "user_name": "Test User",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resource_uri": resource_uri,
    }
    resource_lock_manager.redis.setex(lock_key, 300, json.dumps(lock_data))

    # Get the lock info
    lock_info = resource_lock_manager.get_lock_info(resource_uri)

    assert lock_info is not None
    assert isinstance(lock_info, LockInfo)
    assert lock_info.user_id == lock_data["user_id"]
    assert lock_info.user_name == lock_data["user_name"]
    assert lock_info.timestamp == lock_data["timestamp"]
    assert lock_info.resource_uri == lock_data["resource_uri"]


@patch("heritrace.services.resource_lock_manager.current_user")
def test_check_lock_status_available(
    mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test check_lock_status when resource is available."""
    resource_uri = "http://example.org/resource/available"
    lock_key = resource_lock_manager._generate_lock_key(resource_uri)

    # Ensure no lock exists
    resource_lock_manager.redis.delete(lock_key)

    mock_current_user.orcid = "0000-0001-2345-6789"

    status, lock_info = resource_lock_manager.check_lock_status(resource_uri)

    assert status == LockStatus.AVAILABLE
    assert lock_info is None


@patch("heritrace.services.resource_lock_manager.current_user")
def test_check_lock_status_locked_by_other(
    mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test check_lock_status when resource is locked by another user."""
    resource_uri = "http://example.org/resource/locked-by-other"
    lock_key = resource_lock_manager._generate_lock_key(resource_uri)

    # Create a lock by another user
    lock_data = {
        "user_id": "0000-0002-3456-7890",  # Different user
        "user_name": "Other User",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resource_uri": resource_uri,
    }
    resource_lock_manager.redis.setex(lock_key, 300, json.dumps(lock_data))

    mock_current_user.orcid = "0000-0001-2345-6789"  # Current user

    status, lock_info = resource_lock_manager.check_lock_status(resource_uri)

    assert status == LockStatus.LOCKED
    assert lock_info is not None
    assert lock_info.user_id == "0000-0002-3456-7890"


@patch("heritrace.services.resource_lock_manager.current_user")
def test_check_lock_status_locked_by_self(
    mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test check_lock_status when resource is locked by the current user."""
    resource_uri = "http://example.org/resource/locked-by-self"
    lock_key = resource_lock_manager._generate_lock_key(resource_uri)

    user_id = "0000-0001-2345-6789"
    mock_current_user.orcid = user_id

    # Create a lock by the current user
    lock_data = {
        "user_id": user_id,
        "user_name": "Current User",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resource_uri": resource_uri,
    }
    resource_lock_manager.redis.setex(lock_key, 300, json.dumps(lock_data))

    status, lock_info = resource_lock_manager.check_lock_status(resource_uri)

    assert status == LockStatus.AVAILABLE
    assert lock_info is not None
    assert lock_info.user_id == user_id


@patch("heritrace.services.resource_lock_manager.current_user")
def test_acquire_lock_success(
    mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test acquire_lock when resource is available."""
    resource_uri = "http://example.org/resource/to-acquire"
    lock_key = resource_lock_manager._generate_lock_key(resource_uri)

    # Ensure no lock exists
    resource_lock_manager.redis.delete(lock_key)

    user_id = "0000-0001-2345-6789"
    mock_current_user.orcid = user_id
    mock_current_user.name = "Test User"

    success = resource_lock_manager.acquire_lock(resource_uri)

    assert success is True

    # Verify lock was created
    lock_data = resource_lock_manager.redis.get(lock_key)
    assert lock_data is not None

    lock_json = json.loads(lock_data)
    assert lock_json["user_id"] == user_id
    assert lock_json["user_name"] == "Test User"
    assert lock_json["resource_uri"] == resource_uri


@patch("heritrace.services.resource_lock_manager.current_user")
def test_acquire_lock_already_locked_by_self(
    mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test acquire_lock when resource is already locked by the current user."""
    resource_uri = "http://example.org/resource/already-locked-by-self"
    lock_key = resource_lock_manager._generate_lock_key(resource_uri)

    user_id = "0000-0001-2345-6789"
    mock_current_user.orcid = user_id
    mock_current_user.name = "Test User"

    # Create a lock by the current user
    lock_data = {
        "user_id": user_id,
        "user_name": "Test User",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resource_uri": resource_uri,
    }
    resource_lock_manager.redis.setex(lock_key, 300, json.dumps(lock_data))

    # Try to acquire the lock again
    success = resource_lock_manager.acquire_lock(resource_uri)

    assert success is True

    # Verify lock was updated (timestamp should be newer)
    new_lock_data = resource_lock_manager.redis.get(lock_key)
    assert new_lock_data is not None

    new_lock_json = json.loads(new_lock_data)
    assert new_lock_json["user_id"] == user_id
    assert new_lock_json["timestamp"] != lock_data["timestamp"]


@patch("heritrace.services.resource_lock_manager.current_user")
def test_acquire_lock_already_locked_by_other(
    mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test acquire_lock when resource is already locked by another user."""
    resource_uri = "http://example.org/resource/already-locked-by-other"
    lock_key = resource_lock_manager._generate_lock_key(resource_uri)

    # Create a lock by another user
    lock_data = {
        "user_id": "0000-0002-3456-7890",  # Different user
        "user_name": "Other User",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resource_uri": resource_uri,
    }
    resource_lock_manager.redis.setex(lock_key, 300, json.dumps(lock_data))

    mock_current_user.orcid = "0000-0001-2345-6789"  # Current user
    mock_current_user.name = "Test User"

    # Try to acquire the lock
    success = resource_lock_manager.acquire_lock(resource_uri)

    assert success is False

    # Verify lock was not changed
    new_lock_data = resource_lock_manager.redis.get(lock_key)
    assert new_lock_data is not None

    new_lock_json = json.loads(new_lock_data)
    assert new_lock_json["user_id"] == "0000-0002-3456-7890"  # Still the other user


@patch("heritrace.services.resource_lock_manager.current_user")
def test_release_lock_success(
    mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test release_lock when resource is locked by the current user."""
    resource_uri = "http://example.org/resource/to-release"
    lock_key = resource_lock_manager._generate_lock_key(resource_uri)

    user_id = "0000-0001-2345-6789"
    mock_current_user.orcid = user_id

    # Create a lock by the current user
    lock_data = {
        "user_id": user_id,
        "user_name": "Test User",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resource_uri": resource_uri,
    }
    resource_lock_manager.redis.setex(lock_key, 300, json.dumps(lock_data))

    # Release the lock
    success = resource_lock_manager.release_lock(resource_uri)

    assert success is True

    # Verify lock was deleted
    lock_exists = resource_lock_manager.redis.exists(lock_key)
    assert lock_exists == 0


@patch("heritrace.services.resource_lock_manager.current_user")
def test_release_lock_not_locked(
    mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test release_lock when resource is not locked."""
    resource_uri = "http://example.org/resource/not-locked"
    lock_key = resource_lock_manager._generate_lock_key(resource_uri)

    # Ensure no lock exists
    resource_lock_manager.redis.delete(lock_key)

    mock_current_user.orcid = "0000-0001-2345-6789"

    # Try to release the lock
    success = resource_lock_manager.release_lock(resource_uri)

    assert success is False


@patch("heritrace.services.resource_lock_manager.current_user")
def test_release_lock_locked_by_other(
    mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test release_lock when resource is locked by another user."""
    resource_uri = "http://example.org/resource/locked-by-other-to-release"
    lock_key = resource_lock_manager._generate_lock_key(resource_uri)

    # Create a lock by another user
    lock_data = {
        "user_id": "0000-0002-3456-7890",  # Different user
        "user_name": "Other User",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resource_uri": resource_uri,
    }
    resource_lock_manager.redis.setex(lock_key, 300, json.dumps(lock_data))

    mock_current_user.orcid = "0000-0001-2345-6789"  # Current user

    # Try to release the lock
    success = resource_lock_manager.release_lock(resource_uri)

    assert success is False

    # Verify lock still exists
    lock_exists = resource_lock_manager.redis.exists(lock_key)
    assert lock_exists == 1


@patch("heritrace.services.resource_lock_manager.current_user")
def test_lock_expiration(mock_current_user, resource_lock_manager: ResourceLockManager):
    """Test that locks expire after the configured duration."""
    resource_uri = "http://example.org/resource/expiring"
    lock_key = resource_lock_manager._generate_lock_key(resource_uri)

    user_id = "0000-0001-2345-6789"
    mock_current_user.orcid = user_id
    mock_current_user.name = "Test User"

    # Set a very short lock duration for testing
    original_duration = resource_lock_manager.lock_duration
    resource_lock_manager.lock_duration = 1  # 1 second

    try:
        # Acquire the lock
        success = resource_lock_manager.acquire_lock(resource_uri)
        assert success is True

        # Verify lock exists
        lock_exists = resource_lock_manager.redis.exists(lock_key)
        assert lock_exists == 1

        # Wait for the lock to expire
        time.sleep(2)

        # Verify lock no longer exists
        lock_exists = resource_lock_manager.redis.exists(lock_key)
        assert lock_exists == 0

    finally:
        # Restore original duration
        resource_lock_manager.lock_duration = original_duration


@patch("heritrace.services.resource_lock_manager.current_user")
def test_check_lock_status_exception(
    mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test check_lock_status when an exception occurs."""
    resource_uri = "http://example.org/resource/exception"

    # Mock get_lock_info to raise an exception
    with patch.object(
        resource_lock_manager, "get_lock_info", side_effect=Exception("Test exception")
    ):
        status, lock_info = resource_lock_manager.check_lock_status(resource_uri)

        # Verify that the method returns ERROR status and None for lock_info
        assert status == LockStatus.ERROR
        assert lock_info is None


@patch("heritrace.services.resource_lock_manager.current_user")
def test_acquire_lock_exception(
    mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test acquire_lock when an exception occurs."""
    resource_uri = "http://example.org/resource/exception"

    mock_current_user.orcid = "0000-0001-2345-6789"
    mock_current_user.name = "Test User"

    # Mock redis.setex to raise an exception
    with patch.object(
        resource_lock_manager.redis, "setex", side_effect=Exception("Test exception")
    ):
        success = resource_lock_manager.acquire_lock(resource_uri)

        # Verify that the method returns False when an exception occurs
        assert success is False


@patch("heritrace.services.resource_lock_manager.current_user")
def test_release_lock_exception(
    mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test release_lock when an exception occurs."""
    resource_uri = "http://example.org/resource/exception"

    user_id = "0000-0001-2345-6789"
    mock_current_user.orcid = user_id

    # Create a lock by the current user
    lock_key = resource_lock_manager._generate_lock_key(resource_uri)
    lock_data = {
        "user_id": user_id,
        "user_name": "Test User",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resource_uri": resource_uri,
    }
    resource_lock_manager.redis.setex(lock_key, 300, json.dumps(lock_data))

    # Mock redis.delete to raise an exception
    with patch.object(
        resource_lock_manager.redis, "delete", side_effect=Exception("Test exception")
    ):
        success = resource_lock_manager.release_lock(resource_uri)

        # Verify that the method returns False when an exception occurs
        assert success is False


def test_get_linked_resources(resource_lock_manager: ResourceLockManager, mock_sparql_service):
    """Test the _get_linked_resources method."""
    resource_uri = "http://example.org/resource/with-links"
    linked_resources = [
        "http://example.org/resource/linked1",
        "http://example.org/resource/linked2"
    ]
    
    # Configure the mock to return specific linked resources
    mock_sparql_service.get_linked_resources.return_value = linked_resources
    
    # Call the method and verify it returns the expected linked resources
    result = resource_lock_manager._get_linked_resources(resource_uri)
    assert result == linked_resources
    
    # Verify the SPARQL service was called with the correct resource URI
    mock_sparql_service.get_linked_resources.assert_called_once_with(resource_uri)


@patch("heritrace.services.resource_lock_manager.current_user")
def test_check_lock_status_with_linked_resources(
    mock_current_user, resource_lock_manager: ResourceLockManager, mock_sparql_service
):
    """Test check_lock_status when a linked resource is locked."""
    resource_uri = "http://example.org/resource/main"
    linked_resource_uri = "http://example.org/resource/linked"
    
    # Set up current user
    mock_current_user.orcid = "0000-0001-2345-6789"
    mock_current_user.name = "Test User"
    
    # Configure the mock to return a linked resource
    mock_sparql_service.get_linked_resources.return_value = [linked_resource_uri]
    
    # Create a lock on the linked resource
    linked_lock_key = resource_lock_manager._generate_lock_key(linked_resource_uri)
    lock_data = {
        "user_id": "other-user-id",  # Different from current user
        "user_name": "Other User",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resource_uri": linked_resource_uri,
        "linked_resources": []
    }
    resource_lock_manager.redis.setex(linked_lock_key, 300, json.dumps(lock_data))
    
    # Check lock status of the main resource
    status, lock_info = resource_lock_manager.check_lock_status(resource_uri)
    
    # Verify the resource is considered locked because of the linked resource
    assert status == LockStatus.LOCKED
    assert lock_info is not None
    assert lock_info.resource_uri == linked_resource_uri
    assert lock_info.user_id == "other-user-id"
    
    # Cleanup
    resource_lock_manager.redis.delete(linked_lock_key)


@patch("heritrace.services.resource_lock_manager.current_user")
def test_acquire_lock_with_linked_resources(
    mock_current_user, resource_lock_manager: ResourceLockManager, mock_sparql_service
):
    """Test acquire_lock when linked resources are present."""
    resource_uri = "http://example.org/resource/main"
    linked_resources = [
        "http://example.org/resource/linked1",
        "http://example.org/resource/linked2"
    ]
    
    # Set up current user
    mock_current_user.orcid = "0000-0001-2345-6789"
    mock_current_user.name = "Test User"
    
    # Configure the mock to return linked resources
    mock_sparql_service.get_linked_resources.return_value = linked_resources
    
    # Acquire lock on the main resource
    assert resource_lock_manager.acquire_lock(resource_uri) is True
    
    # Verify the lock contains the linked resources
    lock_key = resource_lock_manager._generate_lock_key(resource_uri)
    lock_data_json = resource_lock_manager.redis.get(lock_key)
    assert lock_data_json is not None
    
    lock_data = json.loads(lock_data_json)
    assert "linked_resources" in lock_data
    assert set(lock_data["linked_resources"]) == set(linked_resources)
    
    # Cleanup
    resource_lock_manager.redis.delete(lock_key)


@patch("heritrace.services.resource_lock_manager.current_user")
def test_acquire_lock_fails_when_linked_resource_locked(
    mock_current_user, resource_lock_manager: ResourceLockManager, mock_sparql_service
):
    """Test acquire_lock fails when a linked resource is already locked by another user."""
    resource_uri = "http://example.org/resource/main"
    linked_resource_uri = "http://example.org/resource/linked"
    
    # Set up current user
    mock_current_user.orcid = "0000-0001-2345-6789"
    mock_current_user.name = "Test User"
    
    # Configure the mock to return a linked resource
    mock_sparql_service.get_linked_resources.return_value = [linked_resource_uri]
    
    # Create a lock on the linked resource by another user
    linked_lock_key = resource_lock_manager._generate_lock_key(linked_resource_uri)
    lock_data = {
        "user_id": "other-user-id",  # Different from current user
        "user_name": "Other User",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resource_uri": linked_resource_uri,
        "linked_resources": []
    }
    resource_lock_manager.redis.setex(linked_lock_key, 300, json.dumps(lock_data))
    
    # Try to acquire lock on the main resource
    assert resource_lock_manager.acquire_lock(resource_uri) is False
    
    # Verify no lock was created for the main resource
    main_lock_key = resource_lock_manager._generate_lock_key(resource_uri)
    assert resource_lock_manager.redis.get(main_lock_key) is None
    
    # Cleanup
    resource_lock_manager.redis.delete(linked_lock_key)


def test_decode_redis_item_bytes(resource_lock_manager: ResourceLockManager):
    """Test the _decode_redis_item method with bytes input."""
    # Test with bytes
    bytes_item = b"test_bytes"
    result = resource_lock_manager._decode_redis_item(bytes_item)
    assert result == "test_bytes"
    assert isinstance(result, str)


def test_decode_redis_item_string(resource_lock_manager: ResourceLockManager):
    """Test the _decode_redis_item method with string input."""
    # Test with string
    string_item = "test_string"
    result = resource_lock_manager._decode_redis_item(string_item)
    assert result == "test_string"
    assert isinstance(result, str)


def test_lockinfo_post_init():
    """Test the __post_init__ method of LockInfo."""
    # Test with None linked_resources
    lock_info = LockInfo(
        user_id="test_user",
        user_name="Test User",
        timestamp="2023-01-01T00:00:00Z",
        resource_uri="http://example.org/resource"
    )
    assert lock_info.linked_resources == []
    assert isinstance(lock_info.linked_resources, list)

    # Test with provided linked_resources
    provided_resources = ["http://example.org/resource/linked"]
    lock_info_with_resources = LockInfo(
        user_id="test_user",
        user_name="Test User",
        timestamp="2023-01-01T00:00:00Z",
        resource_uri="http://example.org/resource",
        linked_resources=provided_resources
    )
    assert lock_info_with_resources.linked_resources == provided_resources


@patch("heritrace.services.resource_lock_manager.current_user")
def test_check_lock_status_with_reverse_links(
    mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test check_lock_status with reverse links."""
    resource_uri = "http://example.org/resource/target"
    linking_resource_uri = "http://example.org/resource/linking"
    
    # Set up current user
    mock_current_user.orcid = "0000-0001-2345-6789"
    
    # Create a reverse link (resource that links to our target resource)
    reverse_links_key = resource_lock_manager._generate_reverse_links_key(resource_uri)
    resource_lock_manager.redis.sadd(reverse_links_key, linking_resource_uri)
    
    # Create a lock on the linking resource by another user
    linking_lock_key = resource_lock_manager._generate_lock_key(linking_resource_uri)
    lock_data = {
        "user_id": "other-user-id",  # Different from current user
        "user_name": "Other User",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resource_uri": linking_resource_uri,
    }
    resource_lock_manager.redis.setex(linking_lock_key, 300, json.dumps(lock_data))
    
    # Check lock status of the target resource
    status, lock_info = resource_lock_manager.check_lock_status(resource_uri)
    
    # Verify the resource is considered locked because of the reverse link
    assert status == LockStatus.LOCKED
    assert lock_info is not None
    assert lock_info.resource_uri == linking_resource_uri
    assert lock_info.user_id == "other-user-id"
    
    # Cleanup
    resource_lock_manager.redis.delete(reverse_links_key)
    resource_lock_manager.redis.delete(linking_lock_key)


@patch("heritrace.services.resource_lock_manager.current_user")
def test_check_lock_status_with_reverse_links_exception(
    mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test check_lock_status when an exception occurs in the reverse links processing."""
    resource_uri = "http://example.org/resource/target"
    
    # Set up current user
    mock_current_user.orcid = "0000-0001-2345-6789"
    
    # Create a reverse link with a problematic item that will cause an exception
    reverse_links_key = resource_lock_manager._generate_reverse_links_key(resource_uri)
    resource_lock_manager.redis.sadd(reverse_links_key, "valid_link")
    
    # Mock _decode_redis_item to raise an exception for one item
    original_decode = resource_lock_manager._decode_redis_item
    
    def mock_decode(item):
        if item == b"valid_link":
            raise Exception("Test exception")
        return original_decode(item)
    
    with patch.object(resource_lock_manager, "_decode_redis_item", side_effect=mock_decode):
        # Check lock status of the target resource
        status, lock_info = resource_lock_manager.check_lock_status(resource_uri)
        
        # Verify the resource is considered in error state due to the exception
        assert status == LockStatus.ERROR
        assert lock_info is None
    
    # Cleanup
    resource_lock_manager.redis.delete(reverse_links_key)


@patch("heritrace.services.resource_lock_manager.current_user")
def test_release_lock_with_linked_resources(
    mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test release_lock with linked resources."""
    resource_uri = "http://example.org/resource/main"
    linked_resource_uri = "http://example.org/resource/linked"
    
    # Set up current user
    user_id = "0000-0001-2345-6789"
    mock_current_user.orcid = user_id
    
    # Create a lock with linked resources
    lock_key = resource_lock_manager._generate_lock_key(resource_uri)
    lock_data = {
        "user_id": user_id,
        "user_name": "Test User",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resource_uri": resource_uri,
        "linked_resources": [linked_resource_uri]
    }
    resource_lock_manager.redis.setex(lock_key, 300, json.dumps(lock_data))
    
    # Create a reverse link
    reverse_links_key = resource_lock_manager._generate_reverse_links_key(linked_resource_uri)
    resource_lock_manager.redis.sadd(reverse_links_key, resource_uri)
    
    # Release the lock
    success = resource_lock_manager.release_lock(resource_uri)
    
    assert success is True
    
    # Verify lock was deleted
    lock_exists = resource_lock_manager.redis.exists(lock_key)
    assert lock_exists == 0
    
    # Verify reverse link was removed
    reverse_link_exists = resource_lock_manager.redis.sismember(reverse_links_key, resource_uri)
    assert reverse_link_exists == 0
    
    # Cleanup
    resource_lock_manager.redis.delete(reverse_links_key)


def test_get_linked_resources_exception(resource_lock_manager, monkeypatch):
    """Test error handling in _get_linked_resources method."""
    resource_uri = "http://example.org/resource/123"
    
    # Create a mock sparql service that raises an exception
    class MockSparqlService:
        def get_linked_resources(self, uri):
            raise Exception("SPARQL query failed")
    
    # Replace the sparql_service with our mock
    mock_sparql = MockSparqlService()
    original_sparql = resource_lock_manager.sparql_service
    resource_lock_manager.sparql_service = mock_sparql
    
    try:
        # Call the method and verify it handles the exception gracefully
        result = resource_lock_manager._get_linked_resources(resource_uri)
        
        # Verify the method returns an empty list on exception
        assert result == []
    finally:
        # Restore the original sparql_service
        resource_lock_manager.sparql_service = original_sparql


@patch("heritrace.services.resource_lock_manager.current_user")
def test_acquire_lock_linked_resource_locked_by_other(mock_current_user, resource_lock_manager, monkeypatch):
    """Test acquire_lock when a linked resource is locked by another user."""
    resource_uri = "http://example.org/resource/123"
    linked_uri = "http://example.org/resource/linked"
    
    # Set up current user
    user_id = "0000-0001-2345-6789"
    mock_current_user.orcid = user_id
    mock_current_user.name = "Test User"
    
    # Save the original method
    original_get_linked_resources = resource_lock_manager._get_linked_resources
    
    # Replace _get_linked_resources with a function that returns our linked resource
    def mock_get_linked_resources(uri):
        return [linked_uri]
    
    monkeypatch.setattr(resource_lock_manager, '_get_linked_resources', mock_get_linked_resources)
    
    # Create a lock on the linked resource by another user
    other_user_id = "9999-9999-9999-9999"
    other_user_name = "Other User"
    linked_lock_key = resource_lock_manager._generate_lock_key(linked_uri)
    linked_lock_data = {
        "user_id": other_user_id,
        "user_name": other_user_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resource_uri": linked_uri,
        "linked_resources": []
    }
    resource_lock_manager.redis.set(
        linked_lock_key, 
        json.dumps(linked_lock_data),
        ex=resource_lock_manager.lock_duration
    )
    
    # Try to acquire lock on the main resource
    result = resource_lock_manager.acquire_lock(resource_uri)
    
    # Verify the lock acquisition fails
    assert result is False
    
    # Cleanup
    resource_lock_manager.redis.delete(linked_lock_key)


def test_get_linked_resources_no_sparql_service(resource_lock_manager):
    """Test _get_linked_resources when sparql_service is not provided."""
    resource_uri = "http://example.org/resource/123"
    
    # Save the original sparql_service
    original_sparql = resource_lock_manager.sparql_service
    
    try:
        # Set sparql_service to None
        resource_lock_manager.sparql_service = None
        
        # Call the method and verify it returns an empty list
        result = resource_lock_manager._get_linked_resources(resource_uri)
        
        # Verify the method returns an empty list when sparql_service is None
        assert result == []
    finally:
        # Restore the original sparql_service
        resource_lock_manager.sparql_service = original_sparql


@patch("heritrace.services.resource_lock_manager.current_user")
def test_check_lock_status_smembers_exception(mock_current_user, resource_lock_manager, monkeypatch):
    """Test check_lock_status when Redis.smembers raises an exception."""
    resource_uri = "http://example.org/resource/123"
    
    # Set up current user
    mock_current_user.orcid = "0000-0001-2345-6789"
    
    # Save the original method
    original_smembers = resource_lock_manager.redis.smembers
    
    def mock_smembers(key):
        raise Exception("Redis connection error")
    
    # Replace redis.smembers with our mock that raises an exception
    monkeypatch.setattr(resource_lock_manager.redis, 'smembers', mock_smembers)
    
    try:
        # Call the method and verify it handles the exception gracefully
        status, lock_info = resource_lock_manager.check_lock_status(resource_uri)
        
        # Verify the method returns an error status
        assert status == LockStatus.ERROR
        assert lock_info is None
    finally:
        # Restore the original method
        monkeypatch.setattr(resource_lock_manager.redis, 'smembers', original_smembers)


@patch("heritrace.services.resource_lock_manager.current_user")
def test_acquire_lock_with_multiple_linked_resources(mock_current_user, resource_lock_manager, monkeypatch):
    """Test acquire_lock with multiple linked resources, one of which is locked by another user."""
    resource_uri = "http://example.org/resource/123"
    linked_uri_1 = "http://example.org/resource/linked1"
    linked_uri_2 = "http://example.org/resource/linked2"
    
    # Set up current user
    user_id = "0000-0001-2345-6789"
    mock_current_user.orcid = user_id
    mock_current_user.name = "Test User"
    
    # Mock _get_linked_resources to return multiple linked resources
    def mock_get_linked_resources(uri):
        return [linked_uri_1, linked_uri_2]
    
    monkeypatch.setattr(resource_lock_manager, '_get_linked_resources', mock_get_linked_resources)
    
    # Create a lock on the second linked resource by another user
    other_user_id = "9999-9999-9999-9999"
    other_user_name = "Other User"
    linked_lock_key = resource_lock_manager._generate_lock_key(linked_uri_2)
    linked_lock_data = {
        "user_id": other_user_id,
        "user_name": other_user_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resource_uri": linked_uri_2,
        "linked_resources": []
    }
    resource_lock_manager.redis.set(
        linked_lock_key, 
        json.dumps(linked_lock_data),
        ex=resource_lock_manager.lock_duration
    )
    
    # Try to acquire lock on the main resource
    result = resource_lock_manager.acquire_lock(resource_uri)
    
    # Verify the lock acquisition fails
    assert result is False
    
    # Verify no lock was created for the main resource
    main_lock_key = resource_lock_manager._generate_lock_key(resource_uri)
    assert resource_lock_manager.redis.get(main_lock_key) is None
    
    # Cleanup
    resource_lock_manager.redis.delete(linked_lock_key)


@patch("heritrace.services.resource_lock_manager.current_user")
def test_acquire_lock_with_empty_linked_resources(mock_current_user, resource_lock_manager, monkeypatch):
    """Test acquire_lock with an empty list of linked resources."""
    resource_uri = "http://example.org/resource/123"
    
    # Set up current user
    user_id = "0000-0001-2345-6789"
    mock_current_user.orcid = user_id
    mock_current_user.name = "Test User"
    
    # Mock _get_linked_resources to return an empty list
    def mock_get_linked_resources(uri):
        return []
    
    monkeypatch.setattr(resource_lock_manager, '_get_linked_resources', mock_get_linked_resources)
    
    # Try to acquire lock on the main resource
    result = resource_lock_manager.acquire_lock(resource_uri)
    
    # Verify the lock acquisition succeeds
    assert result is True
    
    # Verify lock was created for the main resource
    main_lock_key = resource_lock_manager._generate_lock_key(resource_uri)
    lock_data = resource_lock_manager.redis.get(main_lock_key)
    assert lock_data is not None
    
    # Cleanup
    resource_lock_manager.redis.delete(main_lock_key)


@patch("heritrace.services.resource_lock_manager.current_user")
def test_acquire_lock_with_unlocked_linked_resources(mock_current_user, resource_lock_manager, monkeypatch):
    """Test acquire_lock with linked resources that are not locked."""
    resource_uri = "http://example.org/resource/123"
    linked_uri = "http://example.org/resource/linked"
    
    # Set up current user
    user_id = "0000-0001-2345-6789"
    mock_current_user.orcid = user_id
    mock_current_user.name = "Test User"
    
    # Mock _get_linked_resources to return a linked resource
    def mock_get_linked_resources(uri):
        return [linked_uri]
    
    monkeypatch.setattr(resource_lock_manager, '_get_linked_resources', mock_get_linked_resources)
    
    # Try to acquire lock on the main resource
    result = resource_lock_manager.acquire_lock(resource_uri)
    
    # Verify the lock acquisition succeeds
    assert result is True
    
    # Verify lock was created for the main resource
    main_lock_key = resource_lock_manager._generate_lock_key(resource_uri)
    lock_data = resource_lock_manager.redis.get(main_lock_key)
    assert lock_data is not None
    
    # Parse the lock data and verify it contains the linked resource
    lock_info = json.loads(lock_data)
    assert linked_uri in lock_info["linked_resources"]
    
    # Cleanup
    resource_lock_manager.redis.delete(main_lock_key)


@patch("heritrace.services.resource_lock_manager.current_user")
def test_acquire_lock_line_coverage(mock_current_user, resource_lock_manager, monkeypatch):
    """Test specifically targeting line 238 in the acquire_lock method."""
    resource_uri = "http://example.org/resource/123"
    linked_uri = "http://example.org/resource/linked"
    
    # Set up current user
    user_id = "0000-0001-2345-6789"
    mock_current_user.orcid = user_id
    mock_current_user.name = "Test User"
    
    # Create a custom implementation of _get_linked_resources
    def custom_get_linked_resources(uri):
        # This ensures we have a non-empty list but no locks
        return [linked_uri]
    
    # Create a custom implementation of get_lock_info
    original_get_lock_info = resource_lock_manager.get_lock_info
    def custom_get_lock_info(uri):
        # Return None for all lock info checks
        return None
    
    # Apply our patches
    monkeypatch.setattr(resource_lock_manager, '_get_linked_resources', custom_get_linked_resources)
    monkeypatch.setattr(resource_lock_manager, 'get_lock_info', custom_get_lock_info)
    
    # Try to acquire lock on the main resource
    result = resource_lock_manager.acquire_lock(resource_uri)
    
    # Verify the lock acquisition succeeds
    assert result is True
    
    # Verify lock was created for the main resource with the correct data
    main_lock_key = resource_lock_manager._generate_lock_key(resource_uri)
    lock_data_json = resource_lock_manager.redis.get(main_lock_key)
    assert lock_data_json is not None
    
    lock_data = json.loads(lock_data_json)
    assert lock_data["user_id"] == user_id
    assert lock_data["resource_uri"] == resource_uri
    assert linked_uri in lock_data["linked_resources"]
    
    # Cleanup
    resource_lock_manager.redis.delete(main_lock_key)


@patch("heritrace.services.resource_lock_manager.current_user")
def test_create_resource_lock_exception(mock_current_user, resource_lock_manager, monkeypatch):
    """Test _create_resource_lock when an exception occurs."""
    resource_uri = "http://example.org/resource/123"
    linked_resources = ["http://example.org/resource/linked"]
    
    # Set up current user
    user_id = "0000-0001-2345-6789"
    mock_current_user.orcid = user_id
    mock_current_user.name = "Test User"
    
    # Save the original method
    original_setex = resource_lock_manager.redis.setex
    
    # Replace redis.setex with a function that raises an exception
    def mock_setex(*args, **kwargs):
        raise Exception("Redis connection error")
    
    monkeypatch.setattr(resource_lock_manager.redis, 'setex', mock_setex)
    
    try:
        # Call the method and verify it handles the exception gracefully
        result = resource_lock_manager._create_resource_lock(resource_uri, mock_current_user, linked_resources)
        
        # Verify the method returns False on exception
        assert result is False
    finally:
        # Restore the original method
        monkeypatch.setattr(resource_lock_manager.redis, 'setex', original_setex)


@patch("heritrace.services.resource_lock_manager.current_user")
def test_acquire_lock_exception(mock_current_user, resource_lock_manager, monkeypatch):
    """Test acquire_lock when an exception occurs."""
    resource_uri = "http://example.org/resource/123"
    
    # Set up current user
    user_id = "0000-0001-2345-6789"
    mock_current_user.orcid = user_id
    mock_current_user.name = "Test User"
    
    # Replace check_lock_status with a function that raises an exception
    def mock_check_lock_status(*args, **kwargs):
        raise Exception("Unexpected error")
    
    monkeypatch.setattr(resource_lock_manager, 'check_lock_status', mock_check_lock_status)
    
    # Call the method and verify it handles the exception gracefully
    result = resource_lock_manager.acquire_lock(resource_uri)
    
    # Verify the method returns False on exception
    assert result is False
