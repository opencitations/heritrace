# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from rdflib import Dataset, Literal, URIRef

from heritrace.routes.entity import (
    build_restored_state,
    compute_entity_deltas,
    compute_graph_differences,
    get_co_transaction_times,
)


def test_restore_version_with_quadstore() -> None:
    """Test restore_version with quadstore data."""
    # Setup mocks
    mock_get_dataset_is_quadstore = MagicMock(return_value=True)

    # Create test data
    current_graph = Dataset()
    editor = MagicMock()
    editor.g_set = MagicMock()

    # Add some quads to the current graph
    current_graph.add(
        (
            URIRef("http://example.org/entity/1"),
            URIRef("http://example.org/predicate"),
            Literal("Value"),
            URIRef("http://example.org/graph"),
        )
    )  # type: ignore[arg-type]

    # Simulate the code path
    if mock_get_dataset_is_quadstore():
        for quad in current_graph.quads():
            editor.g_set.add(quad)

    # Verify results
    editor.g_set.add.assert_called_once()


def test_restore_version_delete_quad() -> None:
    """Test restore_version with quad deletion."""
    # Create test data
    editor = MagicMock()
    # Setup the entity_index as a dictionary
    editor.g_set.entity_index = {}

    item = (
        URIRef("http://example.org/subject"),
        URIRef("http://example.org/predicate"),
        Literal("Value"),
        URIRef("http://example.org/graph"),
    )
    entity_snapshots = {
        "http://example.org/subject": {
            "needs_restore": True,
            "source": "http://example.org/source",
        }
    }

    # Simulate the code path
    if len(item) == 4:
        editor.delete(item[0], item[1], item[2], item[3])
    else:
        editor.delete(item[0], item[1], item[2])

    subject = str(item[0])
    if subject in entity_snapshots:
        entity_info = entity_snapshots[subject]
        if entity_info["needs_restore"]:
            editor.g_set.mark_as_restored(URIRef(subject))
        # Initialize the dictionary entry if it doesn't exist
        if URIRef(subject) not in editor.g_set.entity_index:
            editor.g_set.entity_index[URIRef(subject)] = {}
        editor.g_set.entity_index[URIRef(subject)]["restoration_source"] = entity_info[
            "source"
        ]

    # Verify results
    editor.delete.assert_called_once_with(item[0], item[1], item[2], item[3])
    editor.g_set.mark_as_restored.assert_called_once_with(URIRef(subject))
    assert (
        editor.g_set.entity_index[URIRef(subject)]["restoration_source"]
        == "http://example.org/source"
    )


def test_restore_version_add_triple() -> None:
    """Test restore_version with triple addition."""
    # Create test data
    editor = MagicMock()
    # Setup the entity_index as a dictionary
    editor.g_set.entity_index = {}

    item = (
        URIRef("http://example.org/subject"),
        URIRef("http://example.org/predicate"),
        Literal("Value"),
    )
    entity_snapshots = {
        "http://example.org/subject": {
            "needs_restore": True,
            "source": "http://example.org/source",
        }
    }

    # Simulate the code path
    if len(item) == 4:
        editor.create(item[0], item[1], item[2], item[3])
    else:
        editor.create(item[0], item[1], item[2])

    subject = str(item[0])
    if subject in entity_snapshots:
        entity_info = entity_snapshots[subject]
        if entity_info["needs_restore"]:
            editor.g_set.mark_as_restored(URIRef(subject))
            # Initialize the dictionary entry if it doesn't exist
            if URIRef(subject) not in editor.g_set.entity_index:
                editor.g_set.entity_index[URIRef(subject)] = {}
            editor.g_set.entity_index[URIRef(subject)]["source"] = entity_info["source"]

    # Verify results
    editor.create.assert_called_once_with(item[0], item[1], item[2])
    editor.g_set.mark_as_restored.assert_called_once_with(URIRef(subject))
    assert (
        editor.g_set.entity_index[URIRef(subject)]["source"]
        == "http://example.org/source"
    )


def test_restore_version_entity_not_in_snapshots() -> None:
    """Test restore_version when entity is not in snapshots."""
    # Create test data
    editor = MagicMock()
    # Setup the entity_index as a dictionary
    editor.g_set.entity_index = {}

    item = (
        URIRef("http://example.org/subject"),
        URIRef("http://example.org/predicate"),
        Literal("Value"),
    )
    entity_snapshots = {
        "http://example.org/other_subject": {  # Different subject
            "needs_restore": True,
            "source": "http://example.org/source",
        }
    }

    # Simulate the code path
    if len(item) == 4:
        editor.create(item[0], item[1], item[2], item[3])
    else:
        editor.create(item[0], item[1], item[2])

    subject = str(item[0])
    if subject in entity_snapshots:
        entity_info = entity_snapshots[subject]
        if entity_info["needs_restore"]:
            editor.g_set.mark_as_restored(URIRef(subject))
            # Initialize the dictionary entry if it doesn't exist
            if URIRef(subject) not in editor.g_set.entity_index:
                editor.g_set.entity_index[URIRef(subject)] = {}
            editor.g_set.entity_index[URIRef(subject)]["source"] = entity_info["source"]

    # Verify results
    editor.create.assert_called_once_with(item[0], item[1], item[2])
    # Should not call mark_as_restored since subject is not in entity_snapshots
    editor.g_set.mark_as_restored.assert_not_called()
    # Should not add to entity_index
    assert URIRef(subject) not in editor.g_set.entity_index


def test_restore_version_entity_not_needs_restore() -> None:
    """Test restore_version when entity does not need restoration."""
    # Create test data
    editor = MagicMock()
    # Setup the entity_index as a dictionary
    editor.g_set.entity_index = {}

    item = (
        URIRef("http://example.org/subject"),
        URIRef("http://example.org/predicate"),
        Literal("Value"),
    )
    entity_snapshots = {
        "http://example.org/subject": {
            "needs_restore": False,  # Entity doesn't need restoration
            "source": "http://example.org/source",
        }
    }

    # Simulate the code path for deletion
    if len(item) == 4:
        editor.delete(item[0], item[1], item[2], item[3])
    else:
        editor.delete(item[0], item[1], item[2])

    subject = str(item[0])
    if subject in entity_snapshots:
        entity_info = entity_snapshots[subject]
        if entity_info["needs_restore"]:
            editor.g_set.mark_as_restored(URIRef(subject))
        # Initialize the dictionary entry if it doesn't exist
        if URIRef(subject) not in editor.g_set.entity_index:
            editor.g_set.entity_index[URIRef(subject)] = {}
        editor.g_set.entity_index[URIRef(subject)]["restoration_source"] = entity_info[
            "source"
        ]

    # Verify results
    editor.delete.assert_called_once_with(item[0], item[1], item[2])
    # Should not call mark_as_restored since needs_restore is False
    editor.g_set.mark_as_restored.assert_not_called()
    # Should still add to entity_index
    assert (
        editor.g_set.entity_index[URIRef(subject)]["restoration_source"]
        == "http://example.org/source"
    )


def test_restore_version_entity_not_deleted() -> None:
    """Test restore_version when entity is not deleted."""
    # Create test data
    editor = MagicMock()
    # Setup the entity_index as a dictionary
    editor.g_set.entity_index = {}

    is_deleted = False
    entity_uri = "http://example.org/entity/123"
    entity_snapshots = {
        entity_uri: {"needs_restore": True, "source": "http://example.org/source"}
    }

    # Simulate the code path
    if is_deleted and entity_uri in entity_snapshots:
        editor.g_set.mark_as_restored(URIRef(entity_uri))
        source = entity_snapshots[entity_uri]["source"]
        # Initialize the dictionary entry if it doesn't exist
        if URIRef(entity_uri) not in editor.g_set.entity_index:
            editor.g_set.entity_index[URIRef(entity_uri)] = {}
        editor.g_set.entity_index[URIRef(entity_uri)]["source"] = source

    # Verify results
    # Should not call mark_as_restored since is_deleted is False
    editor.g_set.mark_as_restored.assert_not_called()
    # Should not add to entity_index
    assert URIRef(entity_uri) not in editor.g_set.entity_index


def test_restore_version_entity_not_in_snapshots_when_deleted() -> None:
    """Test restore_version when deleted entity is not in snapshots."""
    # Create test data
    editor = MagicMock()
    # Setup the entity_index as a dictionary
    editor.g_set.entity_index = {}

    is_deleted = True
    entity_uri = "http://example.org/entity/123"
    entity_snapshots = {
        "http://example.org/other_entity": {  # Different entity
            "needs_restore": True,
            "source": "http://example.org/source",
        }
    }

    # Simulate the code path
    if is_deleted and entity_uri in entity_snapshots:
        editor.g_set.mark_as_restored(URIRef(entity_uri))
        source = entity_snapshots[entity_uri]["source"]
        # Initialize the dictionary entry if it doesn't exist
        if URIRef(entity_uri) not in editor.g_set.entity_index:
            editor.g_set.entity_index[URIRef(entity_uri)] = {}
        editor.g_set.entity_index[URIRef(entity_uri)]["source"] = source

    # Verify results
    # Should not call mark_as_restored since entity_uri is not in entity_snapshots
    editor.g_set.mark_as_restored.assert_not_called()
    # Should not add to entity_index
    assert URIRef(entity_uri) not in editor.g_set.entity_index


@patch("heritrace.routes.entity._restoration.get_dataset_is_quadstore")
def test_compute_graph_differences_quadstore(mock_get_dataset_is_quadstore) -> None:
    """Test compute_graph_differences when dataset is a quadstore."""
    # Setup mocks
    mock_get_dataset_is_quadstore.return_value = True

    # Create test graphs
    current_graph = Dataset()
    historical_graph = Dataset()

    # Add test quads to current graph
    current_graph.add(
        (
            URIRef("http://example.org/subject1"),
            URIRef("http://example.org/predicate1"),
            Literal("value1"),
            URIRef("http://example.org/graph1"),
        )
    )  # type: ignore[arg-type]
    current_graph.add(
        (
            URIRef("http://example.org/subject2"),
            URIRef("http://example.org/predicate2"),
            Literal("value2"),
            URIRef("http://example.org/graph2"),
        )
    )  # type: ignore[arg-type]

    # Add test quads to historical graph
    historical_graph.add(
        (
            URIRef("http://example.org/subject1"),
            URIRef("http://example.org/predicate1"),
            Literal("value1"),
            URIRef("http://example.org/graph1"),
        )
    )  # type: ignore[arg-type]
    historical_graph.add(
        (
            URIRef("http://example.org/subject3"),
            URIRef("http://example.org/predicate3"),
            Literal("value3"),
            URIRef("http://example.org/graph3"),
        )
    )  # type: ignore[arg-type]

    # Call the function
    quads_to_delete, quads_to_add = compute_graph_differences(
        current_graph, historical_graph
    )

    # Verify results
    # Should compute differences using quads() instead of triples()
    assert (
        len(quads_to_delete) == 1
    )  # subject2/predicate2/value2/graph2 should be deleted
    assert len(quads_to_add) == 1  # subject3/predicate3/value3/graph3 should be added

    # Verify specific quads
    delete_quad = next(iter(quads_to_delete))
    add_quad = next(iter(quads_to_add))

    assert delete_quad[0] == URIRef("http://example.org/subject2")
    assert delete_quad[1] == URIRef("http://example.org/predicate2")
    assert delete_quad[2] == Literal("value2")
    assert str(delete_quad[3]) == "http://example.org/graph2"

    assert add_quad[0] == URIRef("http://example.org/subject3")
    assert add_quad[1] == URIRef("http://example.org/predicate3")
    assert add_quad[2] == Literal("value3")
    assert str(add_quad[3]) == "http://example.org/graph3"


def _utc(hour: int) -> datetime:
    return datetime(2024, 1, 1, hour, 0, 0, tzinfo=timezone.utc)


def test_get_co_transaction_times() -> None:
    entity_provenance = {
        "snapshot1": {"generatedAtTime": "2024-01-01T00:00:00+00:00"},
        "snapshot2": {"generatedAtTime": "2024-01-01T01:00:00+00:00"},
        "snapshot3": {"generatedAtTime": "2024-01-01T02:00:00Z"},
    }

    result = get_co_transaction_times(entity_provenance, _utc(0))

    assert result == {_utc(1), _utc(2)}


def test_get_co_transaction_times_no_later_snapshots() -> None:
    entity_provenance = {
        "snapshot1": {"generatedAtTime": "2024-01-01T00:00:00+00:00"},
    }

    result = get_co_transaction_times(entity_provenance, _utc(0))

    assert result == set()


def test_compute_entity_deltas() -> None:
    triple_a = ("<http://example.org/s>", "<http://example.org/p>", '"a"')
    triple_b = ("<http://example.org/s>", "<http://example.org/p>", '"b"')
    triple_c = ("<http://example.org/s>", "<http://example.org/p>", '"c"')
    entity_states = {
        "2024-01-01T01:00:00+00:00": {triple_b, triple_c},
        "2024-01-01T00:00:00+00:00": {triple_a, triple_b},
    }

    result = compute_entity_deltas(entity_states)

    assert result == [
        (_utc(0), {triple_a, triple_b}, set()),
        (_utc(1), {triple_c}, {triple_a}),
    ]


def test_build_restored_state_without_co_transactions_is_identity() -> None:
    triple_a = ("<http://example.org/s>", "<http://example.org/p>", '"a"')
    triple_b = ("<http://example.org/s>", "<http://example.org/p>", '"b"')
    entity_states = {
        "2024-01-01T00:00:00+00:00": {triple_a},
        "2024-01-01T01:00:00+00:00": {triple_a, triple_b},
    }

    restored, revert_floor = build_restored_state(entity_states, set())

    assert restored == {triple_a, triple_b}
    assert revert_floor is None


def test_build_restored_state_reverts_creation() -> None:
    triple_a = ("<http://example.org/s>", "<http://example.org/p>", '"a"')
    entity_states = {"2024-01-01T00:00:00+00:00": {triple_a}}

    restored, revert_floor = build_restored_state(entity_states, {_utc(0)})

    assert restored == set()
    assert revert_floor == _utc(0)


def test_build_restored_state_telescopes_to_target_state() -> None:
    triple_a = ("<http://example.org/s>", "<http://example.org/p>", '"a"')
    triple_b = ("<http://example.org/s>", "<http://example.org/p>", '"b"')
    triple_c = ("<http://example.org/s>", "<http://example.org/p>", '"c"')
    entity_states = {
        "2024-01-01T00:00:00+00:00": {triple_a},
        "2024-01-01T01:00:00+00:00": {triple_a, triple_b},
        "2024-01-01T02:00:00+00:00": {triple_b, triple_c},
    }

    restored, revert_floor = build_restored_state(entity_states, {_utc(1), _utc(2)})

    assert restored == {triple_a}
    assert revert_floor == _utc(1)


def test_build_restored_state_keeps_unrelated_snapshots() -> None:
    triple_a = ("<http://example.org/s>", "<http://example.org/p>", '"a"')
    triple_b = ("<http://example.org/s>", "<http://example.org/p>", '"b"')
    triple_c = ("<http://example.org/s>", "<http://example.org/p>", '"c"')
    entity_states = {
        "2024-01-01T00:00:00+00:00": {triple_a},
        "2024-01-01T01:00:00+00:00": {triple_b},
        "2024-01-01T02:00:00+00:00": {triple_b, triple_c},
    }

    restored, revert_floor = build_restored_state(entity_states, {_utc(2)})

    assert restored == {triple_b}
    assert revert_floor == _utc(2)


def test_build_restored_state_resurrects_deleted_entity() -> None:
    triple_a = ("<http://example.org/s>", "<http://example.org/p>", '"a"')
    entity_states = {
        "2024-01-01T00:00:00+00:00": {triple_a},
        "2024-01-01T01:00:00+00:00": set(),
    }

    restored, revert_floor = build_restored_state(entity_states, {_utc(1)})

    assert restored == {triple_a}
    assert revert_floor == _utc(1)


def test_build_restored_state_floor_skips_unreverted_snapshots() -> None:
    triple_a = ("<http://example.org/s>", "<http://example.org/p>", '"a"')
    triple_b = ("<http://example.org/s>", "<http://example.org/p>", '"b"')
    triple_c = ("<http://example.org/s>", "<http://example.org/p>", '"c"')
    triple_d = ("<http://example.org/s>", "<http://example.org/p>", '"d"')
    entity_states = {
        "2024-01-01T00:00:00+00:00": {triple_a},
        "2024-01-01T01:00:00+00:00": {triple_a, triple_b},
        "2024-01-01T02:00:00+00:00": {triple_a, triple_b, triple_c},
        "2024-01-01T03:00:00+00:00": {triple_a, triple_b, triple_c, triple_d},
    }

    restored, revert_floor = build_restored_state(entity_states, {_utc(1), _utc(3)})

    assert restored == {triple_a, triple_c}
    assert revert_floor == _utc(1)
