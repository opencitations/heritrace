# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from unittest.mock import MagicMock

import pytest
from rdflib import URIRef

from heritrace.routes.entity import EntityRenderContext, get_object_label
from heritrace.utils.filters import Filter


@pytest.fixture
def mock_custom_filter():
    filter_mock = MagicMock(spec=Filter)
    filter_mock.human_readable_class.return_value = "Person"
    filter_mock.human_readable_entity.return_value = "Human Readable Entity"
    return filter_mock


@pytest.mark.parametrize(
    ("object_value", "expected_label"),
    [
        ("http://example.org/Expression", "Expression"),
        ("http://example.org/JournalArticle", "Journal Article"),
    ],
)
def test_get_object_label_rdf_type(object_value: str, expected_label: str) -> None:
    predicate = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    entity_type = "http://example.org/Entity"
    mock_custom_filter = MagicMock(spec=Filter)
    mock_custom_filter.human_readable_class.return_value = expected_label

    ctx = EntityRenderContext(
        entity_uri="http://example.org/entity/1",
        entity_shape="http://example.org/EntityShape",
        highest_priority_class=entity_type,
        relevant_snapshot=None,
        predicate_ordering_cache={},
        entity_position_cache={},
        object_shapes_cache={},
        object_classes_cache={},
        custom_filter=mock_custom_filter,
    )

    label = get_object_label(
        object_value,
        predicate,
        None,
        None,
        ctx,
    )

    assert label == expected_label
    mock_custom_filter.human_readable_class.assert_called_once_with(
        (object_value, None)
    )


def test_get_object_label_uri(mock_custom_filter) -> None:
    object_value = "http://example.org/some-entity"
    predicate = "http://example.org/predicate"

    snapshot = MagicMock()
    snapshot.triples.return_value = [(None, None, URIRef("http://example.org/Person"))]

    ctx = EntityRenderContext(
        entity_uri="http://example.org/entity/1",
        entity_shape=None,
        highest_priority_class=None,
        relevant_snapshot=snapshot,
        predicate_ordering_cache={},
        entity_position_cache={},
        object_shapes_cache={},
        object_classes_cache={},
        custom_filter=mock_custom_filter,
    )

    label = get_object_label(
        object_value,
        predicate,
        None,
        "http://example.org/Person",
        ctx,
    )

    assert label == "Human Readable Entity"
    mock_custom_filter.human_readable_entity.assert_called_once_with(
        object_value, ("http://example.org/Person", None), snapshot
    )


def test_get_object_label_uri_no_snapshot(mock_custom_filter) -> None:
    object_value = "http://example.org/some-entity"
    predicate = "http://example.org/predicate"

    ctx = EntityRenderContext(
        entity_uri="http://example.org/entity/1",
        entity_shape=None,
        highest_priority_class=None,
        relevant_snapshot=None,
        predicate_ordering_cache={},
        entity_position_cache={},
        object_shapes_cache={},
        object_classes_cache={},
        custom_filter=mock_custom_filter,
    )

    label = get_object_label(object_value, predicate, None, None, ctx)

    assert label == "http://example.org/some-entity"


def test_get_object_label_literal_value(mock_custom_filter) -> None:
    object_value = "Simple text value"
    predicate = "http://example.org/predicate"

    ctx = EntityRenderContext(
        entity_uri="http://example.org/entity/1",
        entity_shape="http://example.org/EntityShape",
        highest_priority_class="http://example.org/Entity",
        relevant_snapshot=None,
        predicate_ordering_cache={},
        entity_position_cache={},
        object_shapes_cache={},
        object_classes_cache={},
        custom_filter=mock_custom_filter,
    )

    label = get_object_label(
        object_value,
        predicate,
        "http://example.org/Entity",
        "http://example.org/EntityShape",
        ctx,
    )

    assert label == "Simple text value"
    mock_custom_filter.human_readable_predicate.assert_not_called()
    mock_custom_filter.human_readable_entity.assert_not_called()
