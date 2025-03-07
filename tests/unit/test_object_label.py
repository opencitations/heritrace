"""
Unit tests for the get_object_label function in entity.py.
"""
import pytest
from unittest.mock import MagicMock, patch
from rdflib import RDF, URIRef
from heritrace.routes.entity import get_object_label
from heritrace.utils.filters import Filter


@pytest.fixture
def mock_custom_filter():
    """Create a mock custom filter."""
    filter_mock = MagicMock(spec=Filter)
    filter_mock.human_readable_predicate.return_value = "Human Readable Predicate"
    filter_mock.human_readable_entity.return_value = "Human Readable Entity"
    return filter_mock


def test_get_object_label_rdf_type():
    """Test get_object_label with RDF type predicate."""
    # Setup
    object_value = "http://example.org/Person"
    predicate = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    entity_type = "http://example.org/Entity"
    form_fields = {}
    snapshot = None
    custom_filter = MagicMock(spec=Filter)
    custom_filter.human_readable_predicate.return_value = "person"
    
    # Execute
    label = get_object_label(object_value, predicate, entity_type, form_fields, snapshot, custom_filter)
    
    # Verify
    assert label == "Person"
    custom_filter.human_readable_predicate.assert_called_once_with(object_value, [entity_type])


def test_get_object_label_node_shape(mock_custom_filter):
    """Test get_object_label when field has nodeShape and object_value is a URL."""
    # Setup
    object_value = "http://example.org/referenced-entity"
    predicate = "http://example.org/predicate"
    entity_type = "http://example.org/Entity"
    form_fields = {
        "http://example.org/Entity": {
            "http://example.org/predicate": [
                {"nodeShape": "http://example.org/shape"}
            ]
        }
    }
    
    # Create a mock snapshot with type information
    snapshot = MagicMock()
    snapshot.triples.return_value = [
        (None, None, URIRef("http://example.org/Person"))
    ]
    
    # Execute
    label = get_object_label(object_value, predicate, entity_type, form_fields, snapshot, mock_custom_filter)
    
    # Verify
    assert label == "Human Readable Entity"
    mock_custom_filter.human_readable_entity.assert_called_once_with(
        object_value, ["http://example.org/Person"], snapshot
    )


def test_get_object_label_object_class_no_snapshot(mock_custom_filter):
    """Test get_object_label when field has objectClass but no snapshot is provided."""
    # Setup
    object_value = "http://example.org/referenced-entity"
    predicate = "http://example.org/predicate"
    entity_type = "http://example.org/Entity"
    form_fields = {
        "http://example.org/Entity": {
            "http://example.org/predicate": [
                {"objectClass": "http://example.org/Person"}
            ]
        }
    }
    snapshot = None
    
    # Execute
    label = get_object_label(object_value, predicate, entity_type, form_fields, snapshot, mock_custom_filter)
    
    # Verify
    assert label == "Human Readable Entity"
    mock_custom_filter.human_readable_entity.assert_called_once_with(
        object_value, ["http://example.org/Person"], None
    )


def test_get_object_label_has_value(mock_custom_filter):
    """Test get_object_label when field has hasValue matching object_value."""
    # Setup
    object_value = "http://example.org/specific-value"
    predicate = "http://example.org/predicate"
    entity_type = "http://example.org/Entity"
    form_fields = {
        "http://example.org/Entity": {
            "http://example.org/predicate": [
                {"hasValue": "http://example.org/specific-value"}
            ]
        }
    }
    snapshot = None
    
    # Execute
    label = get_object_label(object_value, predicate, entity_type, form_fields, snapshot, mock_custom_filter)
    
    # Verify
    assert label == "Human Readable Predicate"
    mock_custom_filter.human_readable_predicate.assert_called_once_with(object_value, [entity_type])


def test_get_object_label_optional_values(mock_custom_filter):
    """Test get_object_label when object_value is in optionalValues."""
    # Setup
    object_value = "http://example.org/optional-value"
    predicate = "http://example.org/predicate"
    entity_type = "http://example.org/Entity"
    form_fields = {
        "http://example.org/Entity": {
            "http://example.org/predicate": [
                {"optionalValues": ["http://example.org/optional-value"]}
            ]
        }
    }
    snapshot = None
    
    # Execute
    label = get_object_label(object_value, predicate, entity_type, form_fields, snapshot, mock_custom_filter)
    
    # Verify
    assert label == "Human Readable Predicate"
    mock_custom_filter.human_readable_predicate.assert_called_once_with(object_value, [entity_type])


def test_get_object_label_literal_value(mock_custom_filter):
    """Test get_object_label with a literal (non-URL) value."""
    # Setup
    object_value = "Simple text value"
    predicate = "http://example.org/predicate"
    entity_type = "http://example.org/Entity"
    form_fields = {}
    snapshot = None
    
    # Execute
    label = get_object_label(object_value, predicate, entity_type, form_fields, snapshot, mock_custom_filter)
    
    # Verify
    assert label == "Simple text value"
    mock_custom_filter.human_readable_predicate.assert_not_called()
    mock_custom_filter.human_readable_entity.assert_not_called()


def test_get_object_label_uri_no_special_handling(mock_custom_filter):
    """Test get_object_label with a URI that doesn't match any special cases."""
    # Setup
    object_value = "http://example.org/some-uri"
    predicate = "http://example.org/predicate"
    entity_type = "http://example.org/Entity"
    form_fields = {
        "http://example.org/Entity": {
            "http://example.org/predicate": [
                {"someOtherField": "value"}
            ]
        }
    }
    snapshot = None
    
    # Execute
    label = get_object_label(object_value, predicate, entity_type, form_fields, snapshot, mock_custom_filter)
    
    # Verify
    assert label == "Human Readable Predicate"
    mock_custom_filter.human_readable_predicate.assert_called_once_with(object_value, [entity_type])
