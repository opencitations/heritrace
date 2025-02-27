"""
Strategies for handling orphaned entities and proxy relationships.
"""

from enum import Enum


class OrphanHandlingStrategy(Enum):
    """Strategy for handling orphaned entities."""

    DELETE = "delete"  # Automatically delete orphaned entities
    ASK = "ask"  # Ask the user before deleting orphaned entities
    KEEP = "keep"  # Keep orphaned entities (do nothing)


class ProxyHandlingStrategy(Enum):
    """Strategy for handling proxy entities."""

    DELETE = "delete"  # Automatically delete proxy entities
    ASK = "ask"  # Ask the user before deleting proxy entities
    KEEP = "keep"  # Keep proxy entities (do nothing)
