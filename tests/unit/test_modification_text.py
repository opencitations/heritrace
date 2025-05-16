"""
Unit tests for the generate_modification_text function in entity.py.
"""
import pytest
from unittest.mock import MagicMock, patch
from rdflib import Graph, URIRef
from heritrace.routes.entity import generate_modification_text
from heritrace.utils.filters import Filter


@pytest.fixture
def mock_custom_filter():
    """Create a mock custom filter."""
    filter_mock = MagicMock(spec=Filter)
    filter_mock.human_readable_predicate.return_value = "Human Readable Predicate"
    return filter_mock


@pytest.fixture
def mock_display_rules():
    """Create mock display rules."""
    return {
        "http://example.org/Person": {
            "properties": [
                "http://example.org/name",
                "http://example.org/age"
            ]
        }
    }


@pytest.fixture
def mock_gettext():
    """Create a mock gettext function."""
    def mock_translate(text):
        return text
    return mock_translate


@pytest.fixture
def mock_format_triple():
    """Create a mock format_triple_modification function."""
    def mock_format(triple, *args, **kwargs):
        return f"""
            <li class='test-class'>
                <span>{triple[1]}: {triple[2]}</span>
            </li>"""
    return mock_format


def test_generate_modification_text_empty_modifications(mock_custom_filter, mock_display_rules):
    """Test generate_modification_text with empty modifications."""
    with patch('heritrace.routes.entity.get_display_rules', return_value=mock_display_rules), \
         patch('heritrace.routes.entity.get_property_order_from_rules', 
               return_value=[]), \
         patch('heritrace.routes.entity.gettext', side_effect=lambda x: x), \
         patch('heritrace.routes.entity.get_form_fields', return_value={}):
        
        modifications = {}
        subject_classes = ["http://example.org/Person"]
        history = {}
        entity_uri = "http://example.org/person/1"
        current_snapshot = Graph()
        current_snapshot_timestamp = "2024-01-01T00:00:00"

        result = generate_modification_text(
            modifications,
            subject_classes,
            history,
            entity_uri,
            current_snapshot,
            current_snapshot_timestamp,
            mock_custom_filter
        )

        assert "<p><strong>Modifications</strong></p>" in result
        assert len(result.split("<ul")) == 1  # Only the initial paragraph


def test_generate_modification_text_additions(
    mock_custom_filter, mock_display_rules, mock_format_triple
):
    """Test generate_modification_text with additions."""
    with patch('heritrace.routes.entity.get_display_rules', return_value=mock_display_rules), \
         patch('heritrace.routes.entity.get_property_order_from_rules', 
               return_value=["http://example.org/name"]), \
         patch('heritrace.routes.entity.gettext', side_effect=lambda x: x), \
         patch('heritrace.routes.entity.format_triple_modification', 
               side_effect=mock_format_triple), \
         patch('heritrace.routes.entity.get_form_fields', return_value={}):
        
        modifications = {
            "Additions": [
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/name"),
                    "John Doe"
                )
            ]
        }
        subject_classes = ["http://example.org/Person"]
        history = {}
        entity_uri = "http://example.org/person/1"
        current_snapshot = Graph()
        current_snapshot_timestamp = "2024-01-01T00:00:00"

        result = generate_modification_text(
            modifications,
            subject_classes,
            history,
            entity_uri,
            current_snapshot,
            current_snapshot_timestamp,
            mock_custom_filter
        )

        assert "<p><strong>Modifications</strong></p>" in result
        assert '<i class="bi bi-plus-circle-fill text-success"></i>' in result
        assert "http://example.org/name: John Doe" in result


def test_generate_modification_text_deletions(
    mock_custom_filter, mock_display_rules, mock_format_triple
):
    """Test generate_modification_text with deletions."""
    with patch('heritrace.routes.entity.get_display_rules', return_value=mock_display_rules), \
         patch('heritrace.routes.entity.get_property_order_from_rules', 
               return_value=["http://example.org/age"]), \
         patch('heritrace.routes.entity.gettext', side_effect=lambda x: x), \
         patch('heritrace.routes.entity.format_triple_modification', 
               side_effect=mock_format_triple), \
         patch('heritrace.routes.entity.get_form_fields', return_value={}):
        
        modifications = {
            "Deletions": [
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/age"),
                    "25"
                )
            ]
        }
        subject_classes = ["http://example.org/Person"]
        history = {
            "http://example.org/person/1": {
                "2024-01-01T00:00:00": Graph(),
                "2023-12-31T00:00:00": Graph()
            }
        }
        entity_uri = "http://example.org/person/1"
        current_snapshot = Graph()
        current_snapshot_timestamp = "2024-01-01T00:00:00"

        result = generate_modification_text(
            modifications,
            subject_classes,
            history,
            entity_uri,
            current_snapshot,
            current_snapshot_timestamp,
            mock_custom_filter
        )

        assert "<p><strong>Modifications</strong></p>" in result
        assert '<i class="bi bi-dash-circle-fill text-danger"></i>' in result
        assert "http://example.org/age: 25" in result


def test_generate_modification_text_mixed_modifications(
    mock_custom_filter, mock_display_rules, mock_format_triple
):
    """Test generate_modification_text with both additions and deletions."""
    with patch('heritrace.routes.entity.get_display_rules', return_value=mock_display_rules), \
         patch('heritrace.routes.entity.get_property_order_from_rules', 
               return_value=["http://example.org/name", "http://example.org/age"]), \
         patch('heritrace.routes.entity.gettext', side_effect=lambda x: x), \
         patch('heritrace.routes.entity.format_triple_modification', 
               side_effect=mock_format_triple), \
         patch('heritrace.routes.entity.get_form_fields', return_value={}):
        
        modifications = {
            "Additions": [
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/name"),
                    "John Doe"
                )
            ],
            "Deletions": [
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/age"),
                    "25"
                )
            ]
        }
        subject_classes = ["http://example.org/Person"]
        history = {
            "http://example.org/person/1": {
                "2024-01-01T00:00:00": Graph(),
                "2023-12-31T00:00:00": Graph()
            }
        }
        entity_uri = "http://example.org/person/1"
        current_snapshot = Graph()
        current_snapshot_timestamp = "2024-01-01T00:00:00"

        result = generate_modification_text(
            modifications,
            subject_classes,
            history,
            entity_uri,
            current_snapshot,
            current_snapshot_timestamp,
            mock_custom_filter
        )

        assert "<p><strong>Modifications</strong></p>" in result
        assert '<i class="bi bi-plus-circle-fill text-success"></i>' in result
        assert '<i class="bi bi-dash-circle-fill text-danger"></i>' in result
        assert "http://example.org/name: John Doe" in result
        assert "http://example.org/age: 25" in result


def test_generate_modification_text_ordered_properties(
    mock_custom_filter, mock_display_rules, mock_format_triple
):
    """Test generate_modification_text respects property ordering."""
    with patch('heritrace.routes.entity.get_display_rules', return_value=mock_display_rules), \
         patch('heritrace.routes.entity.get_property_order_from_rules', 
               return_value=["http://example.org/age", "http://example.org/name"]), \
         patch('heritrace.routes.entity.gettext', side_effect=lambda x: x), \
         patch('heritrace.routes.entity.format_triple_modification', 
               side_effect=mock_format_triple), \
         patch('heritrace.routes.entity.get_form_fields', return_value={}):
        
        modifications = {
            "Additions": [
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/name"),
                    "John Doe"
                ),
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/age"),
                    "25"
                )
            ]
        }
        subject_classes = ["http://example.org/Person"]
        history = {}
        entity_uri = "http://example.org/person/1"
        current_snapshot = Graph()
        current_snapshot_timestamp = "2024-01-01T00:00:00"

        result = generate_modification_text(
            modifications,
            subject_classes,
            history,
            entity_uri,
            current_snapshot,
            current_snapshot_timestamp,
            mock_custom_filter
        )

        # Verify that age appears before name in the result
        age_pos = result.find("http://example.org/age: 25")
        name_pos = result.find("http://example.org/name: John Doe")
        assert age_pos < name_pos


def test_generate_modification_text_unordered_properties(
    mock_custom_filter, mock_display_rules, mock_format_triple
):
    """Test generate_modification_text handles properties not in ordered list."""
    with patch('heritrace.routes.entity.get_display_rules', return_value=mock_display_rules), \
         patch('heritrace.routes.entity.get_property_order_from_rules', 
               return_value=["http://example.org/name"]), \
         patch('heritrace.routes.entity.gettext', side_effect=lambda x: x), \
         patch('heritrace.routes.entity.format_triple_modification', 
               side_effect=mock_format_triple), \
         patch('heritrace.routes.entity.get_form_fields', return_value={}):
        
        modifications = {
            "Additions": [
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/unordered"),
                    "Unordered Value"
                ),
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/name"),
                    "John Doe"
                )
            ]
        }
        subject_classes = ["http://example.org/Person"]
        history = {}
        entity_uri = "http://example.org/person/1"
        current_snapshot = Graph()
        current_snapshot_timestamp = "2024-01-01T00:00:00"

        result = generate_modification_text(
            modifications,
            subject_classes,
            history,
            entity_uri,
            current_snapshot,
            current_snapshot_timestamp,
            mock_custom_filter
        )

        assert "http://example.org/unordered: Unordered Value" in result
        assert "http://example.org/name: John Doe" in result
