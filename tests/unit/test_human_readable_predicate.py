"""
Unit tests for the human_readable_predicate method in heritrace/utils/filters.py.
"""
from unittest.mock import patch

import pytest
from heritrace.utils.filters import Filter


@pytest.fixture
def mock_filter():
    """Create a mock Filter instance with display rules for testing human_readable_predicate."""
    context = {"example": "http://example.org/"}
    display_rules = [
        {
            "target": {
                "class": "http://example.org/Class",
                "shape": "http://example.org/Shape"
            },
            "displayName": "Test Class",
            "displayProperties": [
                {
                    "property": "http://example.org/predicate1",
                    "displayRules": [
                        {
                            "displayName": "Predicate 1 Display Name"
                        }
                    ]
                },
                {
                    "property": "http://example.org/predicate2",
                    "displayName": "Predicate 2 Display Name"
                }
            ]
        }
    ]
    sparql_endpoint = "http://example.org/sparql"
    return Filter(context, display_rules, sparql_endpoint)


def test_human_readable_predicate_with_display_rules(mock_filter):
    """Test human_readable_predicate when displayRules is present in the property."""
    entity_key = ("http://example.org/predicate1", "http://example.org/Shape")
    
    with patch('heritrace.utils.display_rules_utils.find_matching_rule') as mock_find_rule:
        mock_find_rule.return_value = mock_filter.display_rules[0]
        
        result = mock_filter.human_readable_predicate(entity_key)
    
    assert result == "Predicate 1 Display Name"
    mock_find_rule.assert_called_once_with(
        "http://example.org/predicate1", 
        "http://example.org/Shape", 
        mock_filter.display_rules
    )


def test_human_readable_predicate_with_display_name(mock_filter):
    """Test human_readable_predicate when displayName is present in the property."""
    entity_key = ("http://example.org/predicate2", "http://example.org/Shape")
    
    with patch('heritrace.utils.display_rules_utils.find_matching_rule') as mock_find_rule:
        mock_find_rule.return_value = mock_filter.display_rules[0]
        
        result = mock_filter.human_readable_predicate(entity_key)
    
    assert result == "Predicate 2 Display Name"
    mock_find_rule.assert_called_once_with(
        "http://example.org/predicate2", 
        "http://example.org/Shape", 
        mock_filter.display_rules
    )


def test_human_readable_predicate_fallback(mock_filter):
    """Test human_readable_predicate fallback to _format_uri_as_readable."""
    entity_key = ("http://example.org/unknown_predicate", "http://example.org/Shape")
    
    with patch('heritrace.utils.display_rules_utils.find_matching_rule') as mock_find_rule:
        mock_find_rule.return_value = mock_filter.display_rules[0]
        
        with patch.object(mock_filter, '_format_uri_as_readable', return_value="Formatted URI") as mock_format:
            result = mock_filter.human_readable_predicate(entity_key)
    
    assert result == "Formatted URI"
    mock_find_rule.assert_called_once_with(
        "http://example.org/unknown_predicate", 
        "http://example.org/Shape", 
        mock_filter.display_rules
    )
    mock_format.assert_called_once_with("http://example.org/unknown_predicate", False)


def test_human_readable_predicate_no_rule(mock_filter):
    """Test human_readable_predicate when no rule is found."""
    entity_key = ("http://example.org/predicate1", "http://example.org/Shape")
    
    with patch('heritrace.utils.display_rules_utils.find_matching_rule') as mock_find_rule:
        mock_find_rule.return_value = None
        
        with patch.object(mock_filter, '_format_uri_as_readable', return_value="Formatted URI") as mock_format:
            result = mock_filter.human_readable_predicate(entity_key)
    
    assert result == "Formatted URI"
    mock_find_rule.assert_called_once_with(
        "http://example.org/predicate1", 
        "http://example.org/Shape", 
        mock_filter.display_rules
    )
    mock_format.assert_called_once_with("http://example.org/predicate1", False)


def test_format_uri_as_readable_with_link(mock_filter):
    """Test _format_uri_as_readable when uri is a valid URL and is_link is True."""
    uri = "http://example.org/resource/123"
    
    with patch('heritrace.utils.filters.validators.url', return_value=True) as mock_validators:
        with patch('heritrace.utils.filters.url_for', return_value="/entity/about") as mock_url_for:
            with patch('heritrace.utils.filters.quote', return_value="quoted_uri") as mock_quote:
                with patch('heritrace.utils.filters.gettext', return_value="Link to the entity test") as mock_gettext:
                    result = mock_filter._format_uri_as_readable(uri, is_link=True)
    
    expected = "<a href='/entity/about' alt='Link to the entity test'>http://example.org/resource/123</a>"
    assert result == expected
    mock_validators.assert_called_once_with(uri)
    mock_url_for.assert_called_once_with('entity.about', subject="quoted_uri")
    mock_quote.assert_called_once_with(uri)
    mock_gettext.assert_called_once_with('Link to the entity %(entity)s', entity=uri)
