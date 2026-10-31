# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

"""
Unit tests for the human_readable_predicate method in heritrace/utils/filters.py.
"""

from unittest.mock import MagicMock, patch

import pytest

from heritrace.utils.filters import Filter


@pytest.fixture
def mock_filter():
    """
    Create a mock Filter instance with display rules for testing
    human_readable_predicate.
    """
    context = {"example": "http://example.org/"}
    display_rules = [
        {
            "target": {
                "class": "http://example.org/Class",
                "shape": "http://example.org/Shape",
            },
            "displayName": "Test Class",
            "displayProperties": [
                {
                    "property": "http://example.org/predicate1",
                    "displayRules": [{"displayName": "Predicate 1 Display Name"}],
                },
                {
                    "property": "http://example.org/predicate2",
                    "displayName": "Predicate 2 Display Name",
                },
            ],
        }
    ]
    sparql_endpoint = "http://example.org/sparql"

    # Mock the get_sparql function
    mock_sparql = MagicMock()
    with patch("heritrace.extensions.get_sparql", return_value=mock_sparql):
        return Filter(context, display_rules, sparql_endpoint)


def test_human_readable_predicate_with_display_rules(mock_filter) -> None:
    """Test human_readable_predicate when displayRules is present in the property."""
    predicate_uri = "http://example.org/predicate1"
    entity_key = ("http://example.org/Class", "http://example.org/Shape")

    with patch(
        "heritrace.utils.display_rules_utils.find_matching_rule"
    ) as mock_find_rule:
        mock_find_rule.return_value = mock_filter.display_rules[0]

        with patch.object(
            mock_filter,
            "human_readable_predicate",
            wraps=mock_filter.human_readable_predicate,
        ):
            result = mock_filter.human_readable_predicate(predicate_uri, entity_key)

    assert result == "Predicate 1 Display Name"
    # Verify that find_matching_rule was called with the correct entity_key tuple
    mock_find_rule.assert_called_once_with(
        entity_key[0], entity_key[1], mock_filter.display_rules
    )


def test_human_readable_predicate_with_display_name(mock_filter) -> None:
    """Test human_readable_predicate when displayName is present in the property."""
    predicate_uri = "http://example.org/predicate2"
    entity_key = ("http://example.org/Class", "http://example.org/Shape")

    with patch(
        "heritrace.utils.display_rules_utils.find_matching_rule"
    ) as mock_find_rule:
        mock_find_rule.return_value = mock_filter.display_rules[0]

        result = mock_filter.human_readable_predicate(predicate_uri, entity_key)

    assert result == "Predicate 2 Display Name"
    # Verify that find_matching_rule was called with the correct entity_key tuple
    mock_find_rule.assert_called_once_with(
        entity_key[0], entity_key[1], mock_filter.display_rules
    )


def test_human_readable_predicate_fallback(mock_filter) -> None:
    """Test human_readable_predicate fallback to format_uri_as_readable."""
    predicate_uri = "http://example.org/unknown_predicate"
    entity_key = ("http://example.org/Class", "http://example.org/Shape")

    with patch(
        "heritrace.utils.display_rules_utils.find_matching_rule"
    ) as mock_find_rule:
        mock_find_rule.return_value = mock_filter.display_rules[0]

        with (
            patch(
                "heritrace.utils.filters.format_uri_as_readable",
                return_value="formatted predicate",
            ) as mock_format,
            patch.dict(mock_filter.context, {"http://example.org/": "example"}),
        ):
            result = mock_filter.human_readable_predicate(predicate_uri, entity_key)

    assert result == "formatted predicate"
    # Verify that find_matching_rule was called with the correct entity_key tuple
    mock_find_rule.assert_called_once_with(
        entity_key[0], entity_key[1], mock_filter.display_rules
    )
    mock_format.assert_called_once_with(predicate_uri)


def test_human_readable_predicate_no_rule(mock_filter) -> None:
    """Test human_readable_predicate when no rule is found."""
    predicate_uri = "http://example.org/predicate1"
    entity_key = ("http://example.org/Class", "http://example.org/Shape")

    with patch(
        "heritrace.utils.display_rules_utils.find_matching_rule"
    ) as mock_find_rule:
        mock_find_rule.return_value = None

        with (
            patch(
                "heritrace.utils.filters.format_uri_as_readable",
                return_value="predicate1",
            ) as mock_format,
            patch.dict(mock_filter.context, {"http://example.org/": "example"}),
        ):
            result = mock_filter.human_readable_predicate(predicate_uri, entity_key)

    assert result == "predicate1"
    # Verify that find_matching_rule was called with the correct entity_key tuple
    mock_find_rule.assert_called_once_with(
        entity_key[0], entity_key[1], mock_filter.display_rules
    )
    mock_format.assert_called_once_with(predicate_uri)
