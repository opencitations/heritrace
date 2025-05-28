"""
Unit tests for entity validation functionality.
These tests focus on validating entity data against form fields and SHACL shapes.
"""
import pytest
from unittest.mock import MagicMock, patch
from rdflib import XSD
from heritrace.routes.entity import validate_entity_data
from heritrace.utils.filters import Filter


@patch('heritrace.routes.entity.get_custom_filter')
@patch('heritrace.routes.entity.get_form_fields')
def test_validate_entity_data_valid(mock_get_form_fields, mock_get_custom_filter):
    """Test validate_entity_data with valid data."""
    # Setup mock filter
    mock_filter = MagicMock(spec=Filter)
    mock_get_custom_filter.return_value = mock_filter
    mock_filter.human_readable_predicate.return_value = "Title"
    
    # Create test data
    entity_data = {
        "entity_type": "http://example.org/Document",
        "properties": {
            "http://example.org/title": ["Test Title"],
            "http://example.org/description": ["Test Description"]
        }
    }
    
    form_fields = {
        ("http://example.org/Document", None): {
            "http://example.org/title": [
                {
                    "label": "Title",
                    "datatype": str(XSD.string),
                    "required": True,
                    "min": 1,
                    "max": 1,
                    "minCount": 1,
                    "maxCount": 1
                }
            ],
            "http://example.org/description": [
                {
                    "label": "Description",
                    "datatype": str(XSD.string),
                    "required": False,
                    "min": 0,
                    "max": 1,
                    "minCount": 0,
                    "maxCount": 1
                }
            ]
        }
    }
    
    mock_get_form_fields.return_value = form_fields
    
    errors = validate_entity_data(entity_data)
    
    assert errors == []


@patch('heritrace.routes.entity.get_custom_filter')
@patch('heritrace.routes.entity.get_form_fields')
def test_validate_entity_data_missing_required(mock_get_form_fields, mock_get_custom_filter):
    """Test validate_entity_data with missing required field."""
    # Setup mock filter
    mock_filter = MagicMock(spec=Filter)
    mock_get_custom_filter.return_value = mock_filter
    mock_filter.human_readable_predicate.return_value = "Title"
    
    # Create test data
    entity_data = {
        "entity_type": "http://example.org/Document",
        "properties": {
            "http://example.org/description": ["Test Description"]
        }
    }
    
    form_fields = {
        ("http://example.org/Document", None): {
            "http://example.org/title": [
                {
                    "label": "Title",
                    "datatype": str(XSD.string),
                    "required": True,
                    "min": 1,
                    "max": 1,
                    "minCount": 1,
                    "maxCount": 1
                }
            ],
            "http://example.org/description": [
                {
                    "label": "Description",
                    "datatype": str(XSD.string),
                    "required": False,
                    "min": 0,
                    "max": 1,
                    "minCount": 0,
                    "maxCount": 1
                }
            ]
        }
    }
    
    mock_get_form_fields.return_value = form_fields
    
    errors = validate_entity_data(entity_data)
    
    assert len(errors) == 1
    assert "Missing required property" in errors[0]
    assert "Title" in errors[0]


@patch('heritrace.routes.entity.get_custom_filter')
@patch('heritrace.routes.entity.get_form_fields')
def test_validate_entity_data_invalid_entity_type(mock_get_form_fields, mock_get_custom_filter):
    """Test validate_entity_data with invalid entity type."""
    # Setup mock filter
    mock_filter = MagicMock(spec=Filter)
    mock_get_custom_filter.return_value = mock_filter
    
    # Create test data
    entity_data = {
        "entity_type": "http://example.org/InvalidType",
        "properties": {
            "http://example.org/title": ["Test Title"]
        }
    }
    
    form_fields = {
        ("http://example.org/Document", None): {
            "http://example.org/title": [
                {
                    "label": "Title",
                    "datatype": str(XSD.string),
                    "required": True,
                    "min": 1,
                    "max": 1,
                    "minCount": 1,
                    "maxCount": 1
                }
            ]
        }
    }
    
    mock_get_form_fields.return_value = form_fields
    
    # Call the function
    errors = validate_entity_data(entity_data)
    
    # Verify results
    assert len(errors) == 1
    assert "No form fields found for entity type" in errors[0]


@patch('heritrace.routes.entity.get_custom_filter')
@patch('heritrace.routes.entity.get_form_fields')
def test_validate_entity_data_with_shape(mock_get_form_fields, mock_get_custom_filter):
    """Test validate_entity_data with property shapes."""
    # Setup mock filter
    mock_filter = MagicMock()
    mock_filter.human_readable_predicate.return_value = "Human Readable Property"
    mock_get_custom_filter.return_value = mock_filter
    
    # Create form fields with shape definitions
    form_fields = {
        ("http://example.org/Person", None): {
            "http://example.org/hasAddress": [
                {
                    "subjectShape": "residential",
                    "min": 1,
                    "max": 1,
                    "datatypes": [str(XSD.string)]
                },
                {
                    "subjectShape": "business",
                    "min": 0,
                    "max": 1,
                    "datatypes": [str(XSD.string)]
                }
            ]
        }
    }
    
    mock_get_form_fields.return_value = form_fields
    
    # Test data with shape specified
    entity_data = {
        "entity_type": "http://example.org/Person",
        "properties": {
            "http://example.org/hasAddress": [
                {
                    "shape": "residential",
                    "value": "123 Main St"
                }
            ]
        }
    }
    
    errors = validate_entity_data(entity_data)
    
    # Should be no errors
    assert errors == []
    
    # Test with missing required shape
    # We need to create a new form fields structure where residential is required
    # and business is optional
    form_fields = {
        ("http://example.org/Person", None): {
            "http://example.org/hasAddress": [
                {
                    "min": 1,  # This makes the property required
                    "max": None
                }
            ],
            "http://example.org/hasResidentialAddress": [
                {
                    "subjectShape": "residential",
                    "min": 1,  # This makes residential address required
                    "max": 1,
                    "datatypes": [str(XSD.string)]
                }
            ]
        }
    }
    
    mock_get_form_fields.return_value = form_fields
    
    # Entity data missing the required residential address
    entity_data = {
        "entity_type": "http://example.org/Person",
        "properties": {
            "http://example.org/hasAddress": [
                {
                    "shape": "business",
                    "value": "456 Business Ave"
                }
            ]
            # Missing http://example.org/hasResidentialAddress
        }
    }
    
    errors = validate_entity_data(entity_data)
    
    # Should have one error about missing required property
    assert len(errors) == 1
    assert "residential" in str(errors[0]) or "required" in str(errors[0])
