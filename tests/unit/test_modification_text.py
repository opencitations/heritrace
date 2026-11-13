# SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from unittest.mock import MagicMock, patch

import pytest
from rdflib import Graph, Literal, URIRef

from heritrace.routes.entity import (
    EntityRenderContext,
    HistoryContext,
    build_modifications,
    modification_entry,
)
from heritrace.utils.filters import Filter

PERSON = "http://example.org/person/1"
NAME = "http://example.org/name"
AGE = "http://example.org/age"
MODULE = "heritrace.routes.entity._modifications"


@pytest.fixture
def mock_custom_filter():
    filter_mock = MagicMock(spec=Filter)
    filter_mock.human_readable_predicate.side_effect = lambda p, *_a, **_k: str(p)
    return filter_mock


def _ctx(mock_custom_filter, history=None):
    history = history or {}
    return HistoryContext(
        entity_uri=PERSON,
        highest_priority_class="http://example.org/Person",
        entity_shape="http://example.org/PersonShape",
        history=history,
        sorted_timestamps=sorted(history.get(PERSON, {}).keys()),
        custom_filter=mock_custom_filter,
    )


def _entry(predicate: str, value: str) -> dict:
    return {
        "predicate": predicate,
        "predicate_label": predicate,
        "object": value,
        "object_label": value,
        "position": None,
    }


def _presentation(ordered: list[str], shape_order: list[str] | None = None):
    presentation = MagicMock()
    presentation.predicate_order.return_value = ordered
    presentation.node_order.return_value = shape_order or []
    presentation.ordering.return_value = None
    return presentation


def test_build_modifications_empty(mock_custom_filter) -> None:
    with patch(f"{MODULE}.get_presentation", return_value=_presentation([])):
        result = build_modifications(
            {}, _ctx(mock_custom_filter), Graph(), "2024-01-01T00:00:00"
        )
    assert result == {}


def test_build_modifications_additions_and_deletions(mock_custom_filter) -> None:
    history = {PERSON: {"2024-01-01T00:00:00": Graph(), "2023-12-31T00:00:00": Graph()}}
    modifications = {
        "Additions": [(URIRef(PERSON), URIRef(NAME), "John Doe")],
        "Deletions": [(URIRef(PERSON), URIRef(AGE), "25")],
    }
    with patch.multiple(
        MODULE,
        get_presentation=MagicMock(return_value=_presentation([NAME, AGE])),
    ):
        result = build_modifications(
            modifications,
            _ctx(mock_custom_filter, history),
            Graph(),
            "2024-01-01T00:00:00",
        )

    assert result == {
        "additions": [_entry(NAME, "John Doe")],
        "deletions": [_entry(AGE, "25")],
    }


def test_build_modifications_respects_property_order(mock_custom_filter) -> None:
    modifications = {
        "Additions": [
            (URIRef(PERSON), URIRef(NAME), "John Doe"),
            (URIRef(PERSON), URIRef(AGE), "25"),
            (URIRef(PERSON), URIRef("http://example.org/unordered"), "Value"),
        ]
    }
    with patch.multiple(
        MODULE,
        get_presentation=MagicMock(return_value=_presentation([AGE, NAME])),
    ):
        result = build_modifications(
            modifications, _ctx(mock_custom_filter), Graph(), "2024-01-01T00:00:00"
        )

    assert result == {
        "additions": [
            _entry(AGE, "25"),
            _entry(NAME, "John Doe"),
            _entry("http://example.org/unordered", "Value"),
        ]
    }


def test_build_modifications_orders_groups_by_shape(mock_custom_filter) -> None:
    prop = "http://example.org/property"
    modifications = {
        "Additions": [
            (URIRef(PERSON), URIRef(prop), URIRef("http://example.org/entity1")),
            (URIRef(PERSON), URIRef(prop), URIRef("http://example.org/entity2")),
        ]
    }
    mock_custom_filter.value_label.side_effect = lambda uri, *_a: str(uri)
    snapshot = Graph()
    snapshot.add((URIRef(PERSON), URIRef(NAME), Literal("John Doe")))
    with patch.multiple(
        MODULE,
        get_presentation=MagicMock(
            return_value=_presentation(
                [prop], ["http://example.org/ShapeA", "http://example.org/ShapeB"]
            )
        ),
        determine_object_class_and_shape=MagicMock(
            side_effect=[
                ("ClassA", "http://example.org/ShapeB"),
                ("ClassB", "http://example.org/ShapeA"),
            ]
        ),
    ):
        result = build_modifications(
            modifications, _ctx(mock_custom_filter), snapshot, "2024-01-01T00:00:00"
        )

    assert [entry["object"] for entry in result["additions"]] == [
        "http://example.org/entity2",
        "http://example.org/entity1",
    ]


def test_modification_entry_with_position() -> None:
    mock_custom_filter = MagicMock()
    mock_custom_filter.human_readable_predicate.return_value = "Test Property"

    triple = (
        URIRef("http://example.org/subject"),
        URIRef("http://example.org/predicate"),
        URIRef("http://example.org/object"),
    )
    ctx = EntityRenderContext(
        entity_uri="http://example.org/subject",
        entity_shape="http://example.org/Shape",
        highest_priority_class="http://example.org/Class",
        relevant_snapshot=MagicMock(spec=Graph),
        predicate_ordering_cache={
            "http://example.org/predicate": "http://example.org/next"
        },
        entity_position_cache={
            ("http://example.org/object", "http://example.org/predicate"): 5
        },
        object_shapes_cache={"http://example.org/object": "http://example.org/Shape"},
        object_classes_cache={"http://example.org/object": "http://example.org/Class"},
        custom_filter=mock_custom_filter,
    )

    with patch(f"{MODULE}.get_object_label", return_value="Test Object"):
        result = modification_entry(triple, ctx)

    assert result == {
        "predicate": "http://example.org/predicate",
        "predicate_label": "Test Property",
        "object": "http://example.org/object",
        "object_label": "Test Object",
        "position": 5,
    }


def test_modification_entry_without_position() -> None:
    mock_custom_filter = MagicMock()
    mock_custom_filter.human_readable_predicate.return_value = "Test Property"

    triple = (
        URIRef("http://example.org/subject"),
        URIRef("http://example.org/predicate"),
        URIRef("http://example.org/object"),
    )
    ctx = EntityRenderContext(
        entity_uri="http://example.org/subject",
        entity_shape="http://example.org/Shape",
        highest_priority_class="http://example.org/Class",
        relevant_snapshot=MagicMock(spec=Graph),
        predicate_ordering_cache={},
        entity_position_cache={},
        object_shapes_cache={"http://example.org/object": "http://example.org/Shape"},
        object_classes_cache={"http://example.org/object": "http://example.org/Class"},
        custom_filter=mock_custom_filter,
    )

    with patch(f"{MODULE}.get_object_label", return_value="Test Object"):
        result = modification_entry(triple, ctx)

    assert result["position"] is None
    assert result["object_label"] == "Test Object"
