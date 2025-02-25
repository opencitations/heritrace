import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Tuple

from flask_login import current_user
from redis import Redis


class LockStatus(Enum):
    """Possible states of a resource lock."""

    AVAILABLE = "available"
    LOCKED = "locked"
    ERROR = "error"


@dataclass
class LockInfo:
    """Information about a resource lock."""

    user_id: str
    user_name: str
    timestamp: str
    resource_uri: str


class ResourceLockManager:
    """Manages resource locking using Redis."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.lock_duration = 300  # 5 minutes in seconds
        self.lock_prefix = "resource_lock:"

    def _generate_lock_key(self, resource_uri: str) -> str:
        """Generate a Redis key for a resource lock."""
        return f"{self.lock_prefix}{resource_uri}"

    def get_lock_info(self, resource_uri: str) -> Optional[LockInfo]:
        """
        Get information about the current lock on a resource.

        Args:
            resource_uri: URI of the resource to check

        Returns:
            LockInfo if resource is locked, None otherwise
        """
        lock_key = self._generate_lock_key(resource_uri)
        lock_data = self.redis.get(lock_key)

        if not lock_data:
            return None

        try:
            data = json.loads(lock_data)
            return LockInfo(
                user_id=data["user_id"],
                user_name=data["user_name"],
                timestamp=data["timestamp"],
                resource_uri=data["resource_uri"],
            )
        except (json.JSONDecodeError, KeyError):
            print(f"Invalid lock data format for resource {resource_uri}")
            return None

    def check_lock_status(
        self, resource_uri: str
    ) -> Tuple[LockStatus, Optional[LockInfo]]:
        """
        Check if a resource is locked and return its status.

        Args:
            resource_uri: URI of the resource to check

        Returns:
            Tuple of (LockStatus, Optional[LockInfo])
        """
        try:
            lock_info = self.get_lock_info(resource_uri)

            if not lock_info:
                return LockStatus.AVAILABLE, None

            # If locked by current user, consider it available
            if lock_info.user_id == str(current_user.orcid):
                return LockStatus.AVAILABLE, lock_info

            return LockStatus.LOCKED, lock_info

        except Exception as e:
            print(f"Error checking lock status: {str(e)}")
            return LockStatus.ERROR, None

    def acquire_lock(self, resource_uri: str) -> bool:
        """
        Try to acquire a lock on a resource.

        Args:
            resource_uri: URI of the resource to lock

        Returns:
            bool: True if lock was acquired, False otherwise
        """
        try:
            lock_key = self._generate_lock_key(resource_uri)
            lock_info = self.get_lock_info(resource_uri)

            # If already locked by another user
            if lock_info and lock_info.user_id != str(current_user.orcid):
                return False

            # Create or update lock
            lock_data = {
                "user_id": str(current_user.orcid),
                "user_name": current_user.name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "resource_uri": resource_uri,
            }

            self.redis.setex(lock_key, self.lock_duration, json.dumps(lock_data))
            return True

        except Exception as e:
            print(f"Error acquiring lock: {str(e)}")
            return False

    def release_lock(self, resource_uri: str) -> bool:
        """
        Release a lock on a resource if owned by the current user.

        Args:
            resource_uri: URI of the resource to unlock

        Returns:
            bool: True if lock was released, False otherwise
        """
        try:
            lock_info = self.get_lock_info(resource_uri)

            # If not locked or locked by another user
            if not lock_info or lock_info.user_id != str(current_user.orcid):
                return False

            self.redis.delete(self._generate_lock_key(resource_uri))
            return True

        except Exception as e:
            print(f"Error releasing lock: {str(e)}")
            return False
