# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from heritrace.routes.entity._about import (
    about,
    get_deleted_entity_context_info,
)
from heritrace.routes.entity._blueprint import entity_bp
from heritrace.routes.entity._creation import (
    CreationContext,
    create_entity,
    create_nested_entity,
    determine_datatype,
    process_entity_value,
    process_ordered_properties,
    process_unordered_properties,
)
from heritrace.routes.entity._history import (
    _format_snapshot_description,
    entity_history,
    entity_version,
)
from heritrace.routes.entity._operations import (
    apply_modifications,
    get_predicate_count,
    process_modification_data,
    validate_modification,
)
from heritrace.routes.entity._rendering import (
    determine_object_class_and_shape,
    format_triple_modification,
    generate_modification_text,
    get_object_label,
)
from heritrace.routes.entity._restoration import (
    compute_graph_differences,
    find_appropriate_snapshot,
    get_entities_to_restore,
    prepare_entity_snapshots,
    restore_version,
)
from heritrace.routes.entity._types import (
    EntityIdentity,
    EntityRenderContext,
    HistoryContext,
)
from heritrace.routes.entity._validation import validate_entity_data
from heritrace.utils.uri_utils import generate_unique_uri

__all__ = [
    "CreationContext",
    "EntityIdentity",
    "EntityRenderContext",
    "HistoryContext",
    "_format_snapshot_description",
    "about",
    "apply_modifications",
    "compute_graph_differences",
    "create_entity",
    "create_nested_entity",
    "determine_datatype",
    "determine_object_class_and_shape",
    "entity_bp",
    "entity_history",
    "entity_version",
    "find_appropriate_snapshot",
    "format_triple_modification",
    "generate_modification_text",
    "generate_unique_uri",
    "get_deleted_entity_context_info",
    "get_entities_to_restore",
    "get_object_label",
    "get_predicate_count",
    "prepare_entity_snapshots",
    "process_entity_value",
    "process_modification_data",
    "process_ordered_properties",
    "process_unordered_properties",
    "restore_version",
    "validate_entity_data",
    "validate_modification",
]
