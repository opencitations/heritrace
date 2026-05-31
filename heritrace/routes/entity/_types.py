# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from dataclasses import dataclass
from datetime import datetime, timezone

from rdflib import Graph

from heritrace.utils.filters import Filter

_QUAD_LENGTH = 4
_DATETIME_MIN_UTC = datetime.min.replace(tzinfo=timezone.utc)


@dataclass(frozen=True, slots=True)
class EntityRenderContext:
    entity_uri: str
    entity_shape: str | None
    highest_priority_class: str | None
    relevant_snapshot: Graph | None
    predicate_ordering_cache: dict[str, str | None]
    entity_position_cache: dict[tuple[str, str], int | None]
    object_shapes_cache: dict[str, str | None]
    object_classes_cache: dict[str, str | None]
    custom_filter: Filter


@dataclass(frozen=True, slots=True)
class EntityIdentity:
    entity_uri: str
    highest_priority_class: str | None
    entity_shape: str | None
    relevant_snapshot: Graph | None


@dataclass(frozen=True, slots=True)
class HistoryContext:
    entity_uri: str
    highest_priority_class: str | None
    entity_shape: str | None
    history: dict[str, dict[str, Graph]]
    sorted_timestamps: list[str]
    custom_filter: Filter
