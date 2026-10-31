# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from heritrace.routes.entity._about import (
    about,
    build_entity_view,
    get_deleted_entity_context_info,
)
from heritrace.routes.entity._blueprint import entity_bp
from heritrace.routes.entity._creation import (
    CreationContext,
    create_entity,
    create_nested_entity,
    determine_datatype,
    entity_types,
    process_entity_value,
    process_ordered_properties,
    process_unordered_properties,
)
from heritrace.routes.entity._history import (
    _format_snapshot_description,
    entity_history,
    entity_version,
)
from heritrace.routes.entity._modifications import (
    build_modifications,
    determine_object_class_and_shape,
    get_object_label,
    modification_entry,
)
from heritrace.routes.entity._operations import (
    apply_modifications,
    get_predicate_count,
    process_modification_data,
    validate_modification,
)
from heritrace.routes.entity._restoration import (
    build_restored_state,
    compute_entity_deltas,
    compute_graph_differences,
    find_appropriate_snapshot,
    get_co_transaction_times,
    get_entities_to_restore,
    prepare_entity_snapshots,
    restore_entity_version,
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
    "build_entity_view",
    "build_modifications",
    "build_restored_state",
    "compute_entity_deltas",
    "compute_graph_differences",
    "create_entity",
    "create_nested_entity",
    "determine_datatype",
    "determine_object_class_and_shape",
    "entity_bp",
    "entity_history",
    "entity_types",
    "entity_version",
    "find_appropriate_snapshot",
    "generate_unique_uri",
    "get_co_transaction_times",
    "get_deleted_entity_context_info",
    "get_entities_to_restore",
    "get_object_label",
    "get_predicate_count",
    "modification_entry",
    "prepare_entity_snapshots",
    "process_entity_value",
    "process_modification_data",
    "process_ordered_properties",
    "process_unordered_properties",
    "restore_entity_version",
    "restore_version",
    "validate_entity_data",
    "validate_modification",
]
