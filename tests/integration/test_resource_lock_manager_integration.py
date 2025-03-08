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


@pytest.fixture
def resource_lock_manager(redis_client) -> ResourceLockManager:
    """Create a ResourceLockManager instance with a real Redis client."""
    return ResourceLockManager(redis_client)


def test_generate_lock_key(resource_lock_manager: ResourceLockManager):
    """Test the _generate_lock_key method."""
    resource_uri = "http://example.org/resource/123"
    expected_key = "resource_lock:http://example.org/resource/123"
    assert resource_lock_manager._generate_lock_key(resource_uri) == expected_key


def test_get_lock_info_no_lock(resource_lock_manager: ResourceLockManager):
    """Test get_lock_info when no lock exists."""
    resource_uri = "http://example.org/resource/no-lock"
    lock_key = resource_lock_manager._generate_lock_key(resource_uri)
    
    # Ensure no lock exists
    resource_lock_manager.redis.delete(lock_key)
    
    # Call the method
    lock_info = resource_lock_manager.get_lock_info(resource_uri)
    
    # Verify the result
    assert lock_info is None


def test_get_lock_info_with_lock(resource_lock_manager: ResourceLockManager):
    """Test get_lock_info when a lock exists."""
    resource_uri = "http://example.org/resource/with-lock"
    lock_key = resource_lock_manager._generate_lock_key(resource_uri)
    
    # Create a lock
    lock_data = {
        "user_id": "user123",
        "user_name": "Test User",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resource_uri": resource_uri,
        "linked_resources": ["http://example.org/resource/linked1", "http://example.org/resource/linked2"]
    }
    resource_lock_manager.redis.setex(
        lock_key, resource_lock_manager.lock_duration, json.dumps(lock_data)
    )
    
    # Call the method
    lock_info = resource_lock_manager.get_lock_info(resource_uri)
    
    # Verify the result
    assert lock_info is not None
    assert lock_info.user_id == "user123"
    assert lock_info.user_name == "Test User"
    assert lock_info.resource_uri == resource_uri
    assert lock_info.linked_resources == ["http://example.org/resource/linked1", "http://example.org/resource/linked2"]


@patch("heritrace.services.resource_lock_manager.current_user")
def test_check_lock_status_available(
    mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test check_lock_status when resource is available."""
    resource_uri = "http://example.org/resource/available"
    lock_key = resource_lock_manager._generate_lock_key(resource_uri)
    
    # Ensure no lock exists
    resource_lock_manager.redis.delete(lock_key)
    
    # Call the method
    status, lock_info = resource_lock_manager.check_lock_status(resource_uri)
    
    # Verify the result
    assert status == LockStatus.AVAILABLE
    assert lock_info is None


@patch("heritrace.services.resource_lock_manager.current_user")
def test_check_lock_status_locked_by_other(
    mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test check_lock_status when resource is locked by another user."""
    resource_uri = "http://example.org/resource/locked-by-other"
    lock_key = resource_lock_manager._generate_lock_key(resource_uri)
    
    # Set current user
    mock_current_user.orcid = "current-user"
    
    # Create a lock by another user
    lock_data = {
        "user_id": "other-user",
        "user_name": "Other User",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resource_uri": resource_uri,
        "linked_resources": []
    }
    resource_lock_manager.redis.setex(
        lock_key, resource_lock_manager.lock_duration, json.dumps(lock_data)
    )
    
    # Call the method
    status, lock_info = resource_lock_manager.check_lock_status(resource_uri)
    
    # Verify the result
    assert status == LockStatus.LOCKED
    assert lock_info is not None
    assert lock_info.user_id == "other-user"


@patch("heritrace.services.resource_lock_manager.current_user")
def test_check_lock_status_locked_by_self(
    mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test check_lock_status when resource is locked by the current user."""
    resource_uri = "http://example.org/resource/locked-by-self"
    lock_key = resource_lock_manager._generate_lock_key(resource_uri)
    
    # Set current user
    mock_current_user.orcid = "current-user"
    
    # Create a lock by the current user
    lock_data = {
        "user_id": "current-user",
        "user_name": "Current User",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resource_uri": resource_uri,
        "linked_resources": []
    }
    resource_lock_manager.redis.setex(
        lock_key, resource_lock_manager.lock_duration, json.dumps(lock_data)
    )
    
    # Call the method
    status, lock_info = resource_lock_manager.check_lock_status(resource_uri)
    
    # Verify the result
    assert status == LockStatus.AVAILABLE
    assert lock_info is not None
    assert lock_info.user_id == "current-user"


@patch("heritrace.services.resource_lock_manager.current_user")
@patch("heritrace.services.resource_lock_manager.logger")
def test_check_lock_status_exception(
    mock_logger, mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test check_lock_status when an exception occurs."""
    resource_uri = "http://example.org/resource/error"
    
    # Mock get_lock_info to raise an exception
    with patch.object(
        resource_lock_manager, 'get_lock_info', side_effect=Exception("Test exception")
    ):
        # Call the method
        status, lock_info = resource_lock_manager.check_lock_status(resource_uri)
        
        # Verify the result
        assert status == LockStatus.ERROR
        assert lock_info is None
        
        # Verify that the error was logged
        mock_logger.error.assert_any_call(f"Error checking lock status for {resource_uri}: Test exception")
        # The second call to logger.error is with traceback.format_exc(), which we can't easily verify


@patch("heritrace.services.resource_lock_manager.current_user")
def test_check_lock_status_reverse_link_locked(
    mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test check_lock_status when a resource that links to the requested resource is locked by another user."""
    # Set up the resources
    resource_uri = "http://example.org/resource/target"
    linking_resource_uri = "http://example.org/resource/linking"
    
    # Set current user
    mock_current_user.orcid = "current-user"
    
    # Ensure the target resource is not locked
    target_lock_key = resource_lock_manager._generate_lock_key(resource_uri)
    resource_lock_manager.redis.delete(target_lock_key)
    
    # Create a lock on the linking resource by another user
    linking_lock_key = resource_lock_manager._generate_lock_key(linking_resource_uri)
    lock_data = {
        "user_id": "other-user",
        "user_name": "Other User",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resource_uri": linking_resource_uri,
        "linked_resources": []
    }
    resource_lock_manager.redis.setex(
        linking_lock_key, resource_lock_manager.lock_duration, json.dumps(lock_data)
    )
    
    # Set up the reverse link (linking_resource links to resource)
    reverse_links_key = resource_lock_manager._generate_reverse_links_key(resource_uri)
    resource_lock_manager.redis.sadd(reverse_links_key, linking_resource_uri)
    
    # Call the method
    status, lock_info = resource_lock_manager.check_lock_status(resource_uri)
    
    # Verify the result
    assert status == LockStatus.LOCKED
    assert lock_info is not None
    assert lock_info.user_id == "other-user"
    assert lock_info.resource_uri == linking_resource_uri


@patch("heritrace.services.resource_lock_manager.current_user")
def test_check_lock_status_reverse_link_locked_by_self(
    mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test check_lock_status when a resource that links to the requested resource is locked by the current user."""
    # Set up the resources
    resource_uri = "http://example.org/resource/target-self"
    linking_resource_uri = "http://example.org/resource/linking-self"
    
    # Set current user
    mock_current_user.orcid = "current-user"
    
    # Ensure the target resource is not locked
    target_lock_key = resource_lock_manager._generate_lock_key(resource_uri)
    resource_lock_manager.redis.delete(target_lock_key)
    
    # Create a lock on the linking resource by the current user
    linking_lock_key = resource_lock_manager._generate_lock_key(linking_resource_uri)
    lock_data = {
        "user_id": "current-user",
        "user_name": "Current User",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resource_uri": linking_resource_uri,
        "linked_resources": []
    }
    resource_lock_manager.redis.setex(
        linking_lock_key, resource_lock_manager.lock_duration, json.dumps(lock_data)
    )
    
    # Set up the reverse link (linking_resource links to resource)
    reverse_links_key = resource_lock_manager._generate_reverse_links_key(resource_uri)
    resource_lock_manager.redis.sadd(reverse_links_key, linking_resource_uri)
    
    # Call the method
    status, lock_info = resource_lock_manager.check_lock_status(resource_uri)
    
    # Verify the result - should be AVAILABLE since the linking resource is locked by the current user
    assert status == LockStatus.AVAILABLE
    assert lock_info is None


@patch("heritrace.services.resource_lock_manager.current_user")
def test_acquire_lock_success(
    mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test acquire_lock when the resource is not locked."""
    # Setup
    resource_uri = "http://example.org/resource/not-locked"
    linked_resources = ["http://example.org/resource/linked1", "http://example.org/resource/linked2"]
    mock_current_user.orcid = "user123"
    mock_current_user.name = "Test User"

    # Ensure no lock exists
    lock_key = resource_lock_manager._generate_lock_key(resource_uri)
    resource_lock_manager.redis.delete(lock_key)

    # Call the method
    result = resource_lock_manager.acquire_lock(resource_uri, linked_resources)

    # Verify the result
    assert result is True

    # Verify the lock was created
    lock_data = resource_lock_manager.redis.get(lock_key)
    assert lock_data is not None
    lock_info = json.loads(lock_data)
    assert lock_info["user_id"] == "user123"
    assert lock_info["user_name"] == "Test User"
    assert lock_info["resource_uri"] == resource_uri
    assert lock_info["linked_resources"] == linked_resources


@patch("heritrace.services.resource_lock_manager.current_user")
@patch("heritrace.services.resource_lock_manager.logger")
def test_acquire_lock_exception(
    mock_logger, mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test acquire_lock when an exception occurs."""
    resource_uri = "http://example.org/resource/error"
    linked_resources = ["http://example.org/resource/linked1"]
    
    # Mock check_lock_status to raise an exception
    with patch.object(
        resource_lock_manager, 'check_lock_status', side_effect=Exception("Test exception")
    ):
        # Call the method
        result = resource_lock_manager.acquire_lock(resource_uri, linked_resources)
        
        # Verify the result
        assert result is False
        
        # Verify that the error was logged
        mock_logger.error.assert_called_once_with(f"Error acquiring lock for {resource_uri}: Test exception")


@patch("heritrace.services.resource_lock_manager.current_user")
@patch("heritrace.services.resource_lock_manager.logger")
def test_create_resource_lock_exception(
    mock_logger, mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test _create_resource_lock when an exception occurs."""
    resource_uri = "http://example.org/resource/error"
    linked_resources = ["http://example.org/resource/linked1"]
    
    # Set up current user
    mock_current_user.orcid = "user123"
    mock_current_user.name = "Test User"
    
    # Mock redis.setex to raise an exception
    with patch.object(
        resource_lock_manager.redis, 'setex', side_effect=Exception("Test exception")
    ):
        # Call the method
        result = resource_lock_manager._create_resource_lock(
            resource_uri, mock_current_user, linked_resources
        )
        
        # Verify the result
        assert result is False
        
        # Verify that the error was logged
        mock_logger.error.assert_called_once_with(f"Error creating lock for {resource_uri}: Test exception")


@patch("heritrace.services.resource_lock_manager.current_user")
def test_release_lock_success(
    mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test release_lock when the resource is locked by the current user."""
    # Setup
    resource_uri = "http://example.org/resource/locked-by-self-for-release"
    linked_resources = ["http://example.org/resource/linked1", "http://example.org/resource/linked2"]
    mock_current_user.orcid = "user123"
    
    # Create a lock by the current user
    lock_key = resource_lock_manager._generate_lock_key(resource_uri)
    lock_data = {
        "user_id": "user123",
        "user_name": "Test User",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resource_uri": resource_uri,
        "linked_resources": linked_resources
    }
    resource_lock_manager.redis.setex(
        lock_key, resource_lock_manager.lock_duration, json.dumps(lock_data)
    )
    
    # Set up reverse links
    for linked_uri in linked_resources:
        reverse_links_key = resource_lock_manager._generate_reverse_links_key(linked_uri)
        resource_lock_manager.redis.sadd(reverse_links_key, resource_uri)
    
    # Call the method
    result = resource_lock_manager.release_lock(resource_uri)
    
    # Verify the result
    assert result is True
    
    # Verify the lock was released
    assert resource_lock_manager.redis.get(lock_key) is None
    
    # Verify reverse links were cleaned up
    for linked_uri in linked_resources:
        reverse_links_key = resource_lock_manager._generate_reverse_links_key(linked_uri)
        assert not resource_lock_manager.redis.sismember(reverse_links_key, resource_uri)


@patch("heritrace.services.resource_lock_manager.current_user")
@patch("heritrace.services.resource_lock_manager.logger")
def test_release_lock_exception(
    mock_logger, mock_current_user, resource_lock_manager: ResourceLockManager
):
    """Test release_lock when an exception occurs."""
    resource_uri = "http://example.org/resource/error"
    
    # Mock get_lock_info to raise an exception
    with patch.object(
        resource_lock_manager, 'get_lock_info', side_effect=Exception("Test exception")
    ):
        # Call the method
        result = resource_lock_manager.release_lock(resource_uri)
        
        # Verify the result
        assert result is False
        
        # Verify that the error was logged
        mock_logger.error.assert_called_once_with(f"Error releasing lock for {resource_uri}: Test exception")


def test_decode_redis_item_bytes(resource_lock_manager: ResourceLockManager):
    """Test _decode_redis_item with bytes input."""
    bytes_item = b"test-bytes"
    result = resource_lock_manager._decode_redis_item(bytes_item)
    assert result == "test-bytes"
    assert isinstance(result, str)


def test_decode_redis_item_string(resource_lock_manager: ResourceLockManager):
    """Test _decode_redis_item with string input."""
    string_item = "test-string"
    result = resource_lock_manager._decode_redis_item(string_item)
    assert result == "test-string"
    assert isinstance(result, str)


def test_lockinfo_post_init():
    """Test LockInfo.__post_init__ initializes linked_resources as empty list if None."""
    # Test with None linked_resources
    lock_info = LockInfo(
        user_id="user123",
        user_name="Test User",
        timestamp=datetime.now(timezone.utc).isoformat(),
        resource_uri="http://example.org/resource/123",
        linked_resources=None
    )
    assert lock_info.linked_resources == []
    
    # Test with provided linked_resources
    linked_resources = ["http://example.org/resource/linked1"]
    lock_info = LockInfo(
        user_id="user123",
        user_name="Test User",
        timestamp=datetime.now(timezone.utc).isoformat(),
        resource_uri="http://example.org/resource/123",
        linked_resources=linked_resources
    )
    assert lock_info.linked_resources == linked_resources 