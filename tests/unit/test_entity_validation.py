# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

"""
Unit tests for entity validation functionality.
These tests focus on validating entity data against form fields and SHACL shapes.
"""

from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from rdflib import XSD

from heritrace.field_errors import field_error
from heritrace.routes.entity import validate_entity_data
from heritrace.utils.filters import Filter
from heritrace.utils.shacl_patterns import ValuePattern


@patch("heritrace.routes.entity._validation.get_custom_filter")
@patch("heritrace.routes.entity._validation.get_form_fields")
def test_validate_entity_data_valid(
    mock_get_form_fields, mock_get_custom_filter
) -> None:
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
            "http://example.org/description": ["Test Description"],
        },
    }

    form_fields = {
        ("http://example.org/Document", None): {
            "http://example.org/title": [
                {
                    "label": "Title",
                    "datatype": str(XSD.string),
                    "patterns": [],
                    "required": True,
                    "min": 1,
                    "max": 1,
                    "minCount": 1,
                    "maxCount": 1,
                }
            ],
            "http://example.org/description": [
                {
                    "label": "Description",
                    "datatype": str(XSD.string),
                    "patterns": [],
                    "required": False,
                    "min": 0,
                    "max": 1,
                    "minCount": 0,
                    "maxCount": 1,
                }
            ],
        }
    }

    mock_get_form_fields.return_value = form_fields

    errors = validate_entity_data(entity_data)

    assert errors == []


@patch("heritrace.routes.entity._validation.get_custom_filter")
@patch("heritrace.routes.entity._validation.get_form_fields")
def test_validate_entity_data_missing_required(
    mock_get_form_fields, mock_get_custom_filter
) -> None:
    """Test validate_entity_data with missing required field."""
    # Setup mock filter
    mock_filter = MagicMock(spec=Filter)
    mock_get_custom_filter.return_value = mock_filter
    mock_filter.human_readable_predicate.return_value = "Title"

    # Create test data
    entity_data = {
        "entity_type": "http://example.org/Document",
        "properties": {"http://example.org/description": ["Test Description"]},
    }

    form_fields = {
        ("http://example.org/Document", None): {
            "http://example.org/title": [
                {
                    "label": "Title",
                    "datatype": str(XSD.string),
                    "patterns": [],
                    "required": True,
                    "min": 1,
                    "max": 1,
                    "minCount": 1,
                    "maxCount": 1,
                }
            ],
            "http://example.org/description": [
                {
                    "label": "Description",
                    "datatype": str(XSD.string),
                    "patterns": [],
                    "required": False,
                    "min": 0,
                    "max": 1,
                    "minCount": 0,
                    "maxCount": 1,
                }
            ],
        }
    }

    mock_get_form_fields.return_value = form_fields

    errors = validate_entity_data(entity_data)

    assert errors == [
        field_error(
            "tooFew", None, "http://example.org/title", name="Title", count=0, min=1
        )
    ]


@patch("heritrace.routes.entity._validation.get_custom_filter")
@patch("heritrace.routes.entity._validation.get_form_fields")
def test_validate_entity_data_invalid_entity_type(
    mock_get_form_fields, mock_get_custom_filter
) -> None:
    """Test validate_entity_data with invalid entity type."""
    # Setup mock filter
    mock_filter = MagicMock(spec=Filter)
    mock_get_custom_filter.return_value = mock_filter

    # Create test data
    entity_data = {
        "entity_type": "http://example.org/InvalidType",
        "properties": {"http://example.org/title": ["Test Title"]},
    }

    form_fields = {
        ("http://example.org/Document", None): {
            "http://example.org/title": [
                {
                    "label": "Title",
                    "datatype": str(XSD.string),
                    "patterns": [],
                    "required": True,
                    "min": 1,
                    "max": 1,
                    "minCount": 1,
                    "maxCount": 1,
                }
            ]
        }
    }

    mock_get_form_fields.return_value = form_fields

    with pytest.raises(ValueError, match="No form fields found for entity type"):
        validate_entity_data(entity_data)


@patch("heritrace.routes.entity._validation.get_custom_filter")
@patch("heritrace.routes.entity._validation.get_form_fields")
def test_validate_entity_data_with_shape(
    mock_get_form_fields, mock_get_custom_filter
) -> None:
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
                    "datatypes": [str(XSD.string)],
                    "patterns": [],
                },
                {
                    "subjectShape": "business",
                    "min": 0,
                    "max": 1,
                    "datatypes": [str(XSD.string)],
                    "patterns": [],
                },
            ]
        }
    }

    mock_get_form_fields.return_value = form_fields

    # Test data with shape specified
    entity_data = {
        "entity_type": "http://example.org/Person",
        "properties": {
            "http://example.org/hasAddress": [
                {"shape": "residential", "value": "123 Main St"}
            ]
        },
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
                    "max": None,
                    "patterns": [],
                }
            ],
            "http://example.org/hasResidentialAddress": [
                {
                    "subjectShape": "residential",
                    "min": 1,  # This makes residential address required
                    "max": 1,
                    "datatypes": [str(XSD.string)],
                    "patterns": [],
                }
            ],
        }
    }

    mock_get_form_fields.return_value = form_fields

    # Entity data missing the required residential address
    entity_data = {
        "entity_type": "http://example.org/Person",
        "properties": {
            "http://example.org/hasAddress": [
                {"shape": "business", "value": "456 Business Ave"}
            ]
            # Missing http://example.org/hasResidentialAddress
        },
    }

    errors = validate_entity_data(entity_data)

    assert errors == [
        field_error(
            "tooFew",
            None,
            "http://example.org/hasResidentialAddress",
            name="Human Readable Property",
            count=0,
            min=1,
        )
    ]


@pytest.mark.parametrize(
    ("bounds", "values", "errors"),
    [
        (
            {"minInclusive": 0, "maxInclusive": 10},
            ["-1", "0", "10", "11"],
            [("atLeast", "0", "-1"), ("atMost", "10", "11")],
        ),
        (
            {"minExclusive": 0, "maxExclusive": 2.5},
            ["0", "1", "2.5"],
            [("greaterThan", "0", "0"), ("lessThan", "2.5", "2.5")],
        ),
    ],
)
@patch("heritrace.routes.entity._validation.get_custom_filter")
@patch("heritrace.routes.entity._validation.get_form_fields")
def test_validate_entity_data_values_outside_bounds(
    mock_get_form_fields,
    mock_get_custom_filter,
    bounds: dict[str, float],
    values: list[str],
    errors: list[tuple[str, str, str]],
) -> None:
    mock_filter = MagicMock(spec=Filter)
    mock_get_custom_filter.return_value = mock_filter
    mock_filter.human_readable_predicate.return_value = "Count"
    mock_get_form_fields.return_value = {
        ("http://example.org/Document", None): {
            "http://example.org/count": [
                {"datatypes": [str(XSD.decimal)], "min": 0, "patterns": [], **bounds}
            ],
        }
    }

    assert validate_entity_data(
        {
            "entity_type": "http://example.org/Document",
            "properties": {"http://example.org/count": values},
        }
    ) == [
        field_error(code, None, "http://example.org/count", limit=limit, input=value)
        for code, limit, value in errors
    ]


@patch("heritrace.routes.entity._validation.get_custom_filter")
@patch("heritrace.routes.entity._validation.get_form_fields")
def test_validate_entity_data_values_that_break_a_pattern(
    mock_get_form_fields, mock_get_custom_filter, app: Flask
) -> None:
    mock_get_custom_filter.return_value = MagicMock(spec=Filter)
    scheme = "http://example.org/scheme"
    code = "http://example.org/code"

    def pattern(
        condition: tuple[str, str] | None, regex: str, messages: dict[str, str]
    ) -> ValuePattern:
        return ValuePattern(
            "http://example.org/Document", "shape", code, condition, regex, messages
        )

    mock_get_form_fields.return_value = {
        ("http://example.org/Document", None): {
            scheme: [{"patterns": []}],
            code: [
                {
                    "patterns": [
                        pattern(None, r"^\S+$", {}),
                        pattern((scheme, "doi"), r"^10\.", {"en": "Not a DOI"}),
                    ],
                }
            ],
        }
    }

    with app.test_request_context():
        errors = validate_entity_data(
            {
                "entity_type": "http://example.org/Document",
                "properties": {scheme: ["doi"], code: ["a b", "x", "10.1/x"]},
            }
        )

    assert errors == [
        field_error("invalidInput", None, code, expected=r"^\S+$", input="a b"),
        field_error("message", None, code, message="Not a DOI", input="x"),
    ]
