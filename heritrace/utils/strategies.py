# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

"""
Strategies for handling orphaned entities and entities that depend on another.
"""

from enum import Enum


class OrphanHandlingStrategy(Enum):
    """Strategy for handling orphaned entities."""

    DELETE = "delete"  # Automatically delete orphaned entities
    ASK = "ask"  # Ask the user before deleting orphaned entities
    KEEP = "keep"  # Keep orphaned entities (do nothing)


class CompositeHandlingStrategy(Enum):
    """Strategy for handling entities that depend on another (dash:composite)."""

    DELETE = "delete"  # Automatically delete dependent entities
    ASK = "ask"  # Ask the user before deleting dependent entities
    KEEP = "keep"  # Keep dependent entities (do nothing)
