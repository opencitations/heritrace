# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

"""
Unit tests for the generate_modification_text function in entity.py.
"""

from unittest.mock import MagicMock, patch

import pytest
from rdflib import Graph, URIRef

from heritrace.routes.entity import (
    EntityRenderContext,
    HistoryContext,
    format_triple_modification,
    generate_modification_text,
)
from heritrace.utils.filters import Filter


@pytest.fixture
def mock_custom_filter():
    """Create a mock custom filter."""
    filter_mock = MagicMock(spec=Filter)
    filter_mock.human_readable_predicate.return_value = "Human Readable Predicate"
    return filter_mock


@pytest.fixture
def mock_gettext():
    """Create a mock gettext function."""

    def mock_translate(text):
        return text

    return mock_translate


@pytest.fixture
def mock_format_triple():
    """Create a mock format_triple_modification function."""

    def mock_format(triple, *_args, **_kwargs) -> str:
        return f"""
            <li class='test-class'>
                <span>{triple[1]}: {triple[2]}</span>
            </li>"""

    return mock_format


def test_generate_modification_text_empty_modifications(
    mock_custom_filter,
) -> None:
    """Test generate_modification_text with empty modifications."""
    with (
        patch(
            "heritrace.routes.entity._rendering.get_property_order_from_rules",
            return_value=[],
        ),
        patch("heritrace.routes.entity._rendering.gettext", side_effect=lambda x: x),
    ):
        modifications = {}
        entity_uri = "http://example.org/person/1"
        current_snapshot = Graph()
        current_snapshot_timestamp = "2024-01-01T00:00:00"

        ctx = HistoryContext(
            entity_uri=entity_uri,
            highest_priority_class="http://example.org/Person",
            entity_shape="http://example.org/PersonShape",
            history={},
            sorted_timestamps=[],
            custom_filter=mock_custom_filter,
        )

        result = generate_modification_text(
            modifications,
            ctx,
            current_snapshot,
            current_snapshot_timestamp,
        )

        assert "<p><strong>Modifications</strong></p>" in result
        assert len(result.split("<ul")) == 1  # Only the initial paragraph


def test_generate_modification_text_additions(
    mock_custom_filter, mock_format_triple
) -> None:
    """Test generate_modification_text with additions."""
    with (
        patch(
            "heritrace.routes.entity._rendering.get_property_order_from_rules",
            return_value=["http://example.org/name"],
        ),
        patch("heritrace.routes.entity._rendering.gettext", side_effect=lambda x: x),
        patch(
            "heritrace.routes.entity._rendering.format_triple_modification",
            side_effect=mock_format_triple,
        ),
        patch(
            "heritrace.routes.entity._rendering.get_predicate_ordering_info",
            return_value=None,
        ),
        patch(
            "heritrace.routes.entity._rendering.get_shape_order_from_display_rules",
            return_value=[],
        ),
        patch(
            "heritrace.routes.entity._rendering.determine_object_class_and_shape",
            return_value=(None, None),
        ),
    ):
        modifications = {
            "Additions": [
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/name"),
                    "John Doe",
                )
            ]
        }
        entity_uri = "http://example.org/person/1"
        current_snapshot = Graph()
        current_snapshot_timestamp = "2024-01-01T00:00:00"

        ctx = HistoryContext(
            entity_uri=entity_uri,
            highest_priority_class="http://example.org/Person",
            entity_shape="http://example.org/PersonShape",
            history={},
            sorted_timestamps=[],
            custom_filter=mock_custom_filter,
        )

        result = generate_modification_text(
            modifications,
            ctx,
            current_snapshot,
            current_snapshot_timestamp,
        )

        assert "<p><strong>Modifications</strong></p>" in result
        assert '<i class="bi bi-plus-circle-fill text-success"></i>' in result
        assert "http://example.org/name: John Doe" in result


def test_generate_modification_text_deletions(
    mock_custom_filter, mock_format_triple
) -> None:
    """Test generate_modification_text with deletions."""
    with (
        patch(
            "heritrace.routes.entity._rendering.get_property_order_from_rules",
            return_value=["http://example.org/age"],
        ),
        patch("heritrace.routes.entity._rendering.gettext", side_effect=lambda x: x),
        patch(
            "heritrace.routes.entity._rendering.format_triple_modification",
            side_effect=mock_format_triple,
        ),
        patch(
            "heritrace.routes.entity._rendering.get_predicate_ordering_info",
            return_value=None,
        ),
        patch(
            "heritrace.routes.entity._rendering.get_shape_order_from_display_rules",
            return_value=[],
        ),
        patch(
            "heritrace.routes.entity._rendering.determine_object_class_and_shape",
            return_value=(None, None),
        ),
    ):
        modifications = {
            "Deletions": [
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/age"),
                    "25",
                )
            ]
        }
        history = {
            "http://example.org/person/1": {
                "2024-01-01T00:00:00": Graph(),
                "2023-12-31T00:00:00": Graph(),
            }
        }
        entity_uri = "http://example.org/person/1"
        current_snapshot = Graph()
        current_snapshot_timestamp = "2024-01-01T00:00:00"

        ctx = HistoryContext(
            entity_uri=entity_uri,
            highest_priority_class="http://example.org/Person",
            entity_shape="http://example.org/PersonShape",
            history=history,
            sorted_timestamps=sorted(history[entity_uri].keys()),
            custom_filter=mock_custom_filter,
        )

        result = generate_modification_text(
            modifications,
            ctx,
            current_snapshot,
            current_snapshot_timestamp,
        )

        assert "<p><strong>Modifications</strong></p>" in result
        assert '<i class="bi bi-dash-circle-fill text-danger"></i>' in result
        assert "http://example.org/age: 25" in result


def test_generate_modification_text_mixed_modifications(
    mock_custom_filter, mock_format_triple
) -> None:
    """Test generate_modification_text with both additions and deletions."""
    with (
        patch(
            "heritrace.routes.entity._rendering.get_property_order_from_rules",
            return_value=["http://example.org/name", "http://example.org/age"],
        ),
        patch("heritrace.routes.entity._rendering.gettext", side_effect=lambda x: x),
        patch(
            "heritrace.routes.entity._rendering.format_triple_modification",
            side_effect=mock_format_triple,
        ),
        patch(
            "heritrace.routes.entity._rendering.get_predicate_ordering_info",
            return_value=None,
        ),
        patch(
            "heritrace.routes.entity._rendering.get_shape_order_from_display_rules",
            return_value=[],
        ),
        patch(
            "heritrace.routes.entity._rendering.determine_object_class_and_shape",
            return_value=(None, None),
        ),
    ):
        modifications = {
            "Additions": [
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/name"),
                    "John Doe",
                )
            ],
            "Deletions": [
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/age"),
                    "25",
                )
            ],
        }
        history = {
            "http://example.org/person/1": {
                "2024-01-01T00:00:00": Graph(),
                "2023-12-31T00:00:00": Graph(),
            }
        }
        entity_uri = "http://example.org/person/1"
        current_snapshot = Graph()
        current_snapshot_timestamp = "2024-01-01T00:00:00"

        ctx = HistoryContext(
            entity_uri=entity_uri,
            highest_priority_class="http://example.org/Person",
            entity_shape="http://example.org/PersonShape",
            history=history,
            sorted_timestamps=sorted(history[entity_uri].keys()),
            custom_filter=mock_custom_filter,
        )

        result = generate_modification_text(
            modifications,
            ctx,
            current_snapshot,
            current_snapshot_timestamp,
        )

        assert "<p><strong>Modifications</strong></p>" in result
        assert '<i class="bi bi-plus-circle-fill text-success"></i>' in result
        assert '<i class="bi bi-dash-circle-fill text-danger"></i>' in result
        assert "http://example.org/name: John Doe" in result
        assert "http://example.org/age: 25" in result


def test_generate_modification_text_ordered_properties(
    mock_custom_filter, mock_format_triple
) -> None:
    """Test generate_modification_text respects property ordering."""
    with (
        patch(
            "heritrace.routes.entity._rendering.get_property_order_from_rules",
            return_value=["http://example.org/age", "http://example.org/name"],
        ),
        patch("heritrace.routes.entity._rendering.gettext", side_effect=lambda x: x),
        patch(
            "heritrace.routes.entity._rendering.format_triple_modification",
            side_effect=mock_format_triple,
        ),
        patch(
            "heritrace.routes.entity._rendering.get_predicate_ordering_info",
            return_value=None,
        ),
        patch(
            "heritrace.routes.entity._rendering.get_shape_order_from_display_rules",
            return_value=[],
        ),
        patch(
            "heritrace.routes.entity._rendering.determine_object_class_and_shape",
            return_value=(None, None),
        ),
    ):
        modifications = {
            "Additions": [
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/name"),
                    "John Doe",
                ),
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/age"),
                    "25",
                ),
            ]
        }
        entity_uri = "http://example.org/person/1"
        current_snapshot = Graph()
        current_snapshot_timestamp = "2024-01-01T00:00:00"

        ctx = HistoryContext(
            entity_uri=entity_uri,
            highest_priority_class="http://example.org/Person",
            entity_shape="http://example.org/PersonShape",
            history={},
            sorted_timestamps=[],
            custom_filter=mock_custom_filter,
        )

        result = generate_modification_text(
            modifications,
            ctx,
            current_snapshot,
            current_snapshot_timestamp,
        )

        # Verify that age appears before name in the result
        age_pos = result.find("http://example.org/age: 25")
        name_pos = result.find("http://example.org/name: John Doe")
        assert age_pos < name_pos


def test_generate_modification_text_unordered_properties(
    mock_custom_filter, mock_format_triple
) -> None:
    """Test generate_modification_text handles properties not in ordered list."""
    with (
        patch(
            "heritrace.routes.entity._rendering.get_property_order_from_rules",
            return_value=["http://example.org/name"],
        ),
        patch("heritrace.routes.entity._rendering.gettext", side_effect=lambda x: x),
        patch(
            "heritrace.routes.entity._rendering.format_triple_modification",
            side_effect=mock_format_triple,
        ),
        patch(
            "heritrace.routes.entity._rendering.get_predicate_ordering_info",
            return_value=None,
        ),
        patch(
            "heritrace.routes.entity._rendering.get_shape_order_from_display_rules",
            return_value=[],
        ),
        patch(
            "heritrace.routes.entity._rendering.determine_object_class_and_shape",
            return_value=(None, None),
        ),
    ):
        modifications = {
            "Additions": [
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/unordered"),
                    "Unordered Value",
                ),
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/name"),
                    "John Doe",
                ),
            ]
        }
        entity_uri = "http://example.org/person/1"
        current_snapshot = Graph()
        current_snapshot_timestamp = "2024-01-01T00:00:00"

        ctx = HistoryContext(
            entity_uri=entity_uri,
            highest_priority_class="http://example.org/Person",
            entity_shape="http://example.org/PersonShape",
            history={},
            sorted_timestamps=[],
            custom_filter=mock_custom_filter,
        )

        result = generate_modification_text(
            modifications,
            ctx,
            current_snapshot,
            current_snapshot_timestamp,
        )

        assert "http://example.org/unordered: Unordered Value" in result
        assert "http://example.org/name: John Doe" in result


def test_generate_modification_text_shape_priority_ordering(
    mock_custom_filter, mock_format_triple
) -> None:
    """Test shape priority ordering within predicates."""
    mock_snapshot = MagicMock(spec=Graph)

    with (
        patch(
            "heritrace.routes.entity._rendering.get_property_order_from_rules",
            return_value=["http://example.org/property"],
        ),
        patch(
            "heritrace.routes.entity._rendering.get_shape_order_from_display_rules",
            return_value=["http://example.org/ShapeA", "http://example.org/ShapeB"],
        ) as mock_shape_order,
        patch("heritrace.routes.entity._rendering.gettext", side_effect=lambda x: x),
        patch(
            "heritrace.routes.entity._rendering.format_triple_modification",
            side_effect=mock_format_triple,
        ),
        patch(
            "heritrace.routes.entity._rendering.get_predicate_ordering_info",
            return_value=None,
        ),
        patch(
            "heritrace.routes.entity._rendering.determine_object_class_and_shape",
            side_effect=[
                ("ClassA", "http://example.org/ShapeB"),
                ("ClassB", "http://example.org/ShapeA"),
            ],
        ),
    ):
        modifications = {
            "Additions": [
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/property"),
                    URIRef("http://example.org/entity1"),
                ),
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/property"),
                    URIRef("http://example.org/entity2"),
                ),
            ]
        }

        ctx = HistoryContext(
            entity_uri="http://example.org/person/1",
            highest_priority_class="http://example.org/Person",
            entity_shape="http://example.org/PersonShape",
            history={},
            sorted_timestamps=[],
            custom_filter=mock_custom_filter,
        )

        result = generate_modification_text(
            modifications,
            ctx,
            mock_snapshot,
            "2024-01-01T00:00:00",
        )

        # Verify shape ordering was called
        mock_shape_order.assert_called_with(
            "http://example.org/Person",
            "http://example.org/PersonShape",
            "http://example.org/property",
        )
        assert "http://example.org/property: http://example.org/entity1" in result


def test_generate_modification_text_deletions_with_history(
    mock_custom_filter, mock_format_triple
) -> None:
    """Test deletions with historical snapshots logic."""
    mock_current_snapshot = MagicMock(spec=Graph)
    mock_previous_snapshot = MagicMock(spec=Graph)

    with (
        patch(
            "heritrace.routes.entity._rendering.get_property_order_from_rules",
            return_value=["http://example.org/property"],
        ),
        patch("heritrace.routes.entity._rendering.gettext", side_effect=lambda x: x),
        patch(
            "heritrace.routes.entity._rendering.format_triple_modification",
            side_effect=mock_format_triple,
        ),
        patch(
            "heritrace.routes.entity._rendering.get_predicate_ordering_info",
            return_value=None,
        ),
        patch(
            "heritrace.routes.entity._rendering.get_shape_order_from_display_rules",
            return_value=[],
        ),
        patch(
            "heritrace.routes.entity._rendering.determine_object_class_and_shape",
            return_value=("SomeClass", "SomeShape"),
        ),
    ):
        modifications = {
            "Deletions": [
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/property"),
                    "deleted_value",
                )
            ]
        }

        # Create history with previous snapshot
        history = {
            "http://example.org/person/1": {
                "2023-12-31T00:00:00": mock_previous_snapshot,
                "2024-01-01T00:00:00": mock_current_snapshot,
            }
        }

        ctx = HistoryContext(
            entity_uri="http://example.org/person/1",
            highest_priority_class="http://example.org/Person",
            entity_shape="http://example.org/PersonShape",
            history=history,
            sorted_timestamps=sorted(history["http://example.org/person/1"].keys()),
            custom_filter=mock_custom_filter,
        )

        result = generate_modification_text(
            modifications,
            ctx,
            mock_current_snapshot,
            "2024-01-01T00:00:00",
        )

        # Verify that for deletions, the previous snapshot was used
        assert '<i class="bi bi-dash-circle-fill text-danger"></i>' in result
        assert "http://example.org/property: deleted_value" in result


def test_format_triple_modification_with_order_info() -> None:
    """Test order information display in format_triple_modification."""
    mock_custom_filter = MagicMock()
    mock_custom_filter.human_readable_predicate.return_value = "Test Property"

    mock_snapshot = MagicMock(spec=Graph)

    triple = (
        URIRef("http://example.org/subject"),
        URIRef("http://example.org/predicate"),
        URIRef("http://example.org/object"),
    )

    object_shapes_cache = {"http://example.org/object": "http://example.org/Shape"}
    object_classes_cache = {"http://example.org/object": "http://example.org/Class"}
    predicate_ordering_cache = {
        "http://example.org/predicate": "http://example.org/next"
    }
    entity_position_cache = {
        ("http://example.org/object", "http://example.org/predicate"): 5
    }

    ctx = EntityRenderContext(
        entity_uri="http://example.org/subject",
        entity_shape="http://example.org/Shape",
        highest_priority_class="http://example.org/Class",
        relevant_snapshot=mock_snapshot,
        predicate_ordering_cache=predicate_ordering_cache,
        entity_position_cache=entity_position_cache,
        object_shapes_cache=object_shapes_cache,
        object_classes_cache=object_classes_cache,
        custom_filter=mock_custom_filter,
    )

    with (
        patch(
            "heritrace.routes.entity._rendering.get_object_label",
            return_value="Test Object",
        ),
        patch("heritrace.routes.entity._rendering.is_valid_url", return_value=True),
    ):
        result = format_triple_modification(triple, ctx)

    assert '<span class="order-position-badge">#5</span>' in result
    assert "Test Property" in result
    assert "Test Object" in result


def test_format_triple_modification_without_order_info() -> None:
    mock_custom_filter = MagicMock()
    mock_custom_filter.human_readable_predicate.return_value = "Test Property"

    mock_snapshot = MagicMock(spec=Graph)

    triple = (
        URIRef("http://example.org/subject"),
        URIRef("http://example.org/predicate"),
        URIRef("http://example.org/object"),
    )

    ctx = EntityRenderContext(
        entity_uri="http://example.org/subject",
        entity_shape="http://example.org/Shape",
        highest_priority_class="http://example.org/Class",
        relevant_snapshot=mock_snapshot,
        predicate_ordering_cache={},
        entity_position_cache={},
        object_shapes_cache={"http://example.org/object": "http://example.org/Shape"},
        object_classes_cache={"http://example.org/object": "http://example.org/Class"},
        custom_filter=mock_custom_filter,
    )

    with (
        patch(
            "heritrace.routes.entity._rendering.get_object_label",
            return_value="Test Object",
        ),
        patch("heritrace.routes.entity._rendering.is_valid_url", return_value=True),
    ):
        result = format_triple_modification(triple, ctx)

    assert "order-position-badge" not in result
    assert "Test Property" in result
    assert "Test Object" in result
