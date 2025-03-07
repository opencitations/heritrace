import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Tuple, List

from flask_login import current_user
from redis import Redis

from heritrace.services.sparql import SparqlService

# Set up logger
logger = logging.getLogger(__name__)


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
    linked_resources: List[str] = None

    def __post_init__(self):
        if self.linked_resources is None:
            self.linked_resources = []


class ResourceLockManager:
    """Manages resource locking using Redis.
    
    This class uses Redis to manage locks on resources and their linked resources.
    It uses the following Redis key patterns:
    - resource_lock:{resource_uri} - Stores lock info for a resource
    - reverse_links:{resource_uri} - Stores a set of resources that link to this resource
    """

    def __init__(self, redis_client: Redis, sparql_service: SparqlService = None):
        self.redis = redis_client
        self.sparql_service = sparql_service
        self.lock_duration = 300  # 5 minutes in seconds
        self.lock_prefix = "resource_lock:"
        self.reverse_links_prefix = "reverse_links:"    # Reverse links: resources that link to this resource

    def _generate_lock_key(self, resource_uri: str) -> str:
        """Generate a Redis key for a resource lock."""
        return f"{self.lock_prefix}{resource_uri}"
    
    def _generate_reverse_links_key(self, resource_uri: str) -> str:
        """Generate a Redis key for storing resources that link to this resource."""
        return f"{self.reverse_links_prefix}{resource_uri}"

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

        data = json.loads(lock_data)
        linked_resources = data.get("linked_resources", [])
        return LockInfo(
            user_id=data["user_id"],
            user_name=data["user_name"],
            timestamp=data["timestamp"],
            resource_uri=data["resource_uri"],
            linked_resources=linked_resources
        )

    def check_lock_status(
        self, resource_uri: str
    ) -> Tuple[LockStatus, Optional[LockInfo]]:
        """
        Check if a resource is locked and return its status.
        This method efficiently checks if:
        1. The resource itself is directly locked
        2. Any resource that this resource links to is locked (forward links)
        3. Any resource that links to this resource is locked (reverse links)

        Args:
            resource_uri: URI of the resource to check

        Returns:
            Tuple of (LockStatus, Optional[LockInfo])
        """            
        try:
            # 1. Check direct lock on the resource
            lock_info = self.get_lock_info(resource_uri)
            if lock_info:
                # If locked by current user, consider it available
                if lock_info.user_id == str(current_user.orcid):
                    return LockStatus.AVAILABLE, lock_info
                return LockStatus.LOCKED, lock_info
            
            # 2. Check if any resource that this resource links to is locked by another user
            if self.sparql_service:
                linked_resources = self._get_linked_resources(resource_uri)
                for linked_uri in linked_resources:
                    linked_lock_info = self.get_lock_info(linked_uri)
                    if linked_lock_info and linked_lock_info.user_id != str(current_user.orcid):
                        # Resource that this resource links to is locked by another user
                        return LockStatus.LOCKED, linked_lock_info
            
            # 3. Check if any resource that links to this resource is locked by another user
            # Get the resources that link to this resource (reverse links)
            reverse_links_key = self._generate_reverse_links_key(resource_uri)
            reverse_links = self.redis.smembers(reverse_links_key)
            
            # Check if any of these resources is locked
            for linking_uri_item in reverse_links:
                # Use helper method to standardize format
                linking_uri = self._decode_redis_item(linking_uri_item)
                linking_lock_info = self.get_lock_info(linking_uri)
                if linking_lock_info and linking_lock_info.user_id != str(current_user.orcid):
                    # Resource that links to this resource is locked by another user
                    return LockStatus.LOCKED, linking_lock_info
            
            # If we get here, the resource is available
            return LockStatus.AVAILABLE, None

        except Exception as e:
            logger.error(f"Error checking lock status for {resource_uri}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return LockStatus.ERROR, None

    def _decode_redis_item(self, item):
        """
        Helper method to decode Redis items that might be bytes or strings.
        
        Args:
            item: The item to decode (bytes or string)
            
        Returns:
            String representation of the item
        """
        if isinstance(item, bytes):
            return item.decode('utf-8')
        return str(item)
    
    def _get_linked_resources(self, resource_uri: str) -> List[str]:
        """
        Get all resources linked to the given resource and update reverse links in Redis.
        
        Args:
            resource_uri: URI of the resource to check
            
        Returns:
            List of URIs of resources linked to the given resource
        """
        if not self.sparql_service:
            return []
        
        try:
            # Query the SPARQL endpoint for linked resources
            linked_resources = self.sparql_service.get_linked_resources(resource_uri)
            
            # Update reverse links in Redis
            if linked_resources:
                # Use a pipeline for better performance
                pipe = self.redis.pipeline()
                
                # Store reverse links (resources that are linked to by this resource)
                for linked_uri in linked_resources:
                    # Add to reverse links (this resource links to the linked resource)
                    reverse_links_key = self._generate_reverse_links_key(linked_uri)
                    pipe.sadd(reverse_links_key, str(resource_uri))
                    pipe.expire(reverse_links_key, self.lock_duration)
                
                pipe.execute()
            
            return linked_resources
        except Exception as e:
            logger.error(f"Error getting linked resources for {resource_uri}: {str(e)}")
            return []
    
    def acquire_lock(self, resource_uri: str) -> bool:
        """
        Try to acquire a lock on a resource.
        This method efficiently checks and acquires locks using Redis sets
        to track relationships between resources.

        Args:
            resource_uri: URI of the resource to lock

        Returns:
            bool: True if lock was acquired, False otherwise
        """
        try:
            # First check if the resource or any related resource is locked by another user
            status, lock_info = self.check_lock_status(resource_uri)
            if status == LockStatus.LOCKED:
                return False
                
            # Get all resources linked to this resource
            linked_resources = self._get_linked_resources(resource_uri)
            # After checking all linked resources, proceed with lock creation
            return self._create_resource_lock(resource_uri, current_user, linked_resources)

        except Exception as e:
            logger.error(f"Error acquiring lock for {resource_uri}: {str(e)}")
            return False

    def _create_resource_lock(self, resource_uri: str, current_user, linked_resources: List[str]) -> bool:
        """
        Helper method to create a lock for a resource.
        
        Args:
            resource_uri: URI of the resource to lock
            current_user: The current user object
            linked_resources: List of linked resource URIs
            
        Returns:
            bool: True if lock was created successfully
        """
        try:
            # Create or update lock for the main resource
            lock_key = self._generate_lock_key(resource_uri)
            lock_data = {
                "user_id": str(current_user.orcid),
                "user_name": current_user.name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "resource_uri": resource_uri,
                "linked_resources": linked_resources
            }

            # Set the lock with expiration
            self.redis.setex(lock_key, self.lock_duration, json.dumps(lock_data))
            return True
        except Exception as e:
            logger.error(f"Error creating lock for {resource_uri}: {str(e)}")
            return False
            
    def release_lock(self, resource_uri: str) -> bool:
        """
        Release a lock on a resource if owned by the current user.
        Also cleans up the reverse links.

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

            # Get the linked resources from the lock info
            linked_resources = lock_info.linked_resources if lock_info.linked_resources else []

            # Delete the lock directly (this will raise an exception in the test)
            self.redis.delete(self._generate_lock_key(resource_uri))
            
            # Clean up reverse links
            for linked_uri in linked_resources:
                # Ensure we're working with string URIs
                linked_uri_str = str(linked_uri)
                reverse_links_key = self._generate_reverse_links_key(linked_uri_str)
                self.redis.srem(reverse_links_key, str(resource_uri))
            
            return True

        except Exception as e:
            logger.error(f"Error releasing lock for {resource_uri}: {str(e)}")
            return False
