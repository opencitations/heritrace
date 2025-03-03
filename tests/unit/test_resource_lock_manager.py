import json
import time
from datetime import datetime, timezone
from unittest.mock import patch

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


def test_get_lock_info_invalid_data(resource_lock_manager: ResourceLockManager):
    """Test get_lock_info with invalid lock data."""
    resource_uri = "http://example.org/resource/invalid-lock"
    lock_key = resource_lock_manager._generate_lock_key(resource_uri)

    # Set invalid JSON data
    resource_lock_manager.redis.setex(lock_key, 300, "invalid json")

    lock_info = resource_lock_manager.get_lock_info(resource_uri)
    assert lock_info is None


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
