# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from unittest.mock import MagicMock

import pytest
from rdflib import URIRef

from heritrace.routes.entity import get_object_label
from heritrace.utils.filters import Filter


@pytest.fixture
def mock_custom_filter():
    filter_mock = MagicMock(spec=Filter)
    filter_mock.human_readable_class.return_value = "Person"
    filter_mock.human_readable_entity.return_value = "Human Readable Entity"
    return filter_mock


def test_get_object_label_rdf_type() -> None:
    object_value = "http://example.org/Person"
    predicate = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    entity_type = "http://example.org/Entity"
    mock_custom_filter = MagicMock(spec=Filter)
    mock_custom_filter.human_readable_class.return_value = "Person"

    label = get_object_label(
        object_value,
        predicate,
        None,
        None,
        None,
        mock_custom_filter,
        (entity_type, "http://example.org/EntityShape"),
    )

    assert label == "Person"
    mock_custom_filter.human_readable_class.assert_called_once_with(
        (entity_type, "http://example.org/EntityShape")
    )


def test_get_object_label_uri(mock_custom_filter) -> None:
    object_value = "http://example.org/some-entity"
    predicate = "http://example.org/predicate"

    snapshot = MagicMock()
    snapshot.triples.return_value = [(None, None, URIRef("http://example.org/Person"))]

    label = get_object_label(
        object_value,
        predicate,
        None,
        "http://example.org/Person",
        snapshot,
        mock_custom_filter,
    )

    assert label == "Human Readable Entity"
    mock_custom_filter.human_readable_entity.assert_called_once_with(
        object_value, ("http://example.org/Person", None), snapshot
    )


def test_get_object_label_uri_no_snapshot(mock_custom_filter) -> None:
    object_value = "http://example.org/some-entity"
    predicate = "http://example.org/predicate"

    label = get_object_label(
        object_value, predicate, None, None, None, mock_custom_filter
    )

    assert label == "http://example.org/some-entity"


def test_get_object_label_literal_value(mock_custom_filter) -> None:
    object_value = "Simple text value"
    predicate = "http://example.org/predicate"
    entity_type = "http://example.org/Entity"

    label = get_object_label(
        object_value,
        predicate,
        entity_type,
        "http://example.org/EntityShape",
        None,
        mock_custom_filter,
    )

    assert label == "Simple text value"
    mock_custom_filter.human_readable_predicate.assert_not_called()
    mock_custom_filter.human_readable_entity.assert_not_called()
