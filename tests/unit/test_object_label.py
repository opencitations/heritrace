"""
Unit tests for the get_object_label function in entity.py.
"""
from unittest.mock import MagicMock, patch

import pytest
from heritrace.routes.entity import get_object_label
from heritrace.utils.filters import Filter
from rdflib import URIRef


@pytest.fixture
def mock_custom_filter():
    """Create a mock custom filter."""
    filter_mock = MagicMock(spec=Filter)
    filter_mock.human_readable_class.return_value = "Person"
    filter_mock.human_readable_entity.return_value = "Human Readable Entity"
    return filter_mock


@patch('heritrace.routes.entity.get_form_fields')
def test_get_object_label_rdf_type(mock_get_form_fields):
    """Test get_object_label with RDF type predicate."""
    # Setup
    object_value = "http://example.org/Person"
    predicate = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    entity_type = "http://example.org/Entity"
    mock_get_form_fields.return_value = {}
    snapshot = None
    mock_custom_filter = MagicMock(spec=Filter)
    mock_custom_filter.human_readable_class.return_value = "Person"
    
    # Execute
    label = get_object_label(object_value, predicate, entity_type, "http://example.org/EntityShape", snapshot, mock_custom_filter)
    
    # Verify
    assert label == "Person"
    mock_custom_filter.human_readable_class.assert_called_once_with((entity_type, "http://example.org/EntityShape"))


@patch('heritrace.routes.entity.get_form_fields')
def test_get_object_label_uri(mock_get_form_fields, mock_custom_filter):
    """Test get_object_label with a URI."""
    # Setup
    object_value = "http://example.org/some-entity"
    predicate = "http://example.org/predicate"
    entity_type = "http://example.org/Entity"
    mock_get_form_fields.return_value = {}
    
    # Create a mock snapshot with type information
    snapshot = MagicMock()
    snapshot.triples.return_value = [
        (None, None, URIRef("http://example.org/Person"))
    ]
    
    # Execute
    label = get_object_label(object_value, predicate, entity_type, "http://example.org/EntityShape", snapshot, mock_custom_filter)
    
    # Verify
    assert label == "Human Readable Entity"
    mock_custom_filter.human_readable_entity.assert_called_once_with(
            object_value, ("http://example.org/Person", None), snapshot
        )


@patch('heritrace.routes.entity.get_form_fields')
def test_get_object_label_uri_no_snapshot(mock_get_form_fields, mock_custom_filter):
    """Test get_object_label with a URI and no snapshot."""
    # Setup
    object_value = "http://example.org/some-entity"
    predicate = "http://example.org/predicate"
    entity_type = "http://example.org/Entity"
    mock_get_form_fields.return_value = {}
    snapshot = None
    
    # Execute
    label = get_object_label(object_value, predicate, entity_type, "http://example.org/EntityShape", snapshot, mock_custom_filter)
    
    # Verify
    assert label == "Human Readable Entity"
    mock_custom_filter.human_readable_entity.assert_called_once_with(
            object_value, (None, None), snapshot
        )


@patch('heritrace.routes.entity.get_form_fields')
def test_get_object_label_literal_value(mock_get_form_fields, mock_custom_filter):
    """Test get_object_label with a literal (non-URL) value."""
    # Setup
    object_value = "Simple text value"
    predicate = "http://example.org/predicate"
    entity_type = "http://example.org/Entity"
    mock_get_form_fields.return_value = {}
    snapshot = None
    
    # Execute
    label = get_object_label(object_value, predicate, entity_type, "http://example.org/EntityShape", snapshot, mock_custom_filter)
    
    # Verify
    assert label == "Simple text value"
    mock_custom_filter.human_readable_predicate.assert_not_called()
    mock_custom_filter.human_readable_entity.assert_not_called()
