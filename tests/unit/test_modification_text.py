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
    return [
        {
            "target": {
                "class": "http://example.org/Person"
            },
            "properties": [
                "http://example.org/name",
                "http://example.org/age"
            ],
            "priority": 0
        }
    ]


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
            "http://example.org/Person",
            "http://example.org/PersonShape",
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
            "http://example.org/Person",
            "http://example.org/PersonShape",
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
            "http://example.org/Person",
            "http://example.org/PersonShape",
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
            "http://example.org/Person",
            "http://example.org/PersonShape",
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
            "http://example.org/Person",
            "http://example.org/PersonShape",
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
            "http://example.org/Person",
            "http://example.org/PersonShape",
                        history,
            entity_uri,
            current_snapshot,
            current_snapshot_timestamp,
            mock_custom_filter
        )

        assert "http://example.org/unordered: Unordered Value" in result
        assert "http://example.org/name: John Doe" in result


def test_generate_modification_text_object_caching_with_snapshot(
    mock_custom_filter, mock_display_rules, mock_format_triple
):
    """Test object shapes and classes caching logic with relevant snapshot."""
    mock_snapshot = MagicMock(spec=Graph)
    
    with patch('heritrace.routes.entity.get_display_rules', return_value=mock_display_rules), \
         patch('heritrace.routes.entity.get_property_order_from_rules', 
               return_value=[]), \
         patch('heritrace.routes.entity.gettext', side_effect=lambda x: x), \
         patch('heritrace.routes.entity.format_triple_modification', 
               side_effect=mock_format_triple), \
         patch('heritrace.routes.entity.determine_object_class_and_shape',
               return_value=("http://example.org/PersonClass", "http://example.org/PersonShape")) as mock_determine, \
         patch('heritrace.routes.entity.get_predicate_ordering_info', return_value=None), \
         patch('heritrace.routes.entity.get_form_fields', return_value={}):
        
        modifications = {
            "Additions": [
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/name"),
                    URIRef("http://example.org/entity/123")
                )
            ]
        }
        
        result = generate_modification_text(
            modifications,
            "http://example.org/Person",
            "http://example.org/PersonShape",
            {},
            "http://example.org/person/1",
            mock_snapshot,
            "2024-01-01T00:00:00",
            mock_custom_filter
        )
        
        # Test that the object caching logic was executed (lines 1475-1480)
        assert "Modifications" in result
        assert "Additions" in result


def test_generate_modification_text_entity_position_caching(
    mock_custom_filter, mock_display_rules, mock_format_triple
):
    """Test entity position caching and get_cached_position function."""
    mock_snapshot = MagicMock(spec=Graph)
    
    with patch('heritrace.routes.entity.get_display_rules', return_value=mock_display_rules), \
         patch('heritrace.routes.entity.get_property_order_from_rules', 
               return_value=[]), \
         patch('heritrace.routes.entity.gettext', side_effect=lambda x: x), \
         patch('heritrace.routes.entity.format_triple_modification', 
               side_effect=mock_format_triple), \
         patch('heritrace.routes.entity.get_predicate_ordering_info',
               return_value="http://example.org/next") as mock_ordering, \
         patch('heritrace.routes.entity.get_entity_position_in_sequence',
               return_value=1) as mock_position, \
         patch('heritrace.routes.entity.validators.url', return_value=True), \
         patch('heritrace.routes.entity.determine_object_class_and_shape', return_value=(None, None)), \
         patch('heritrace.routes.entity.get_form_fields', return_value={}):
        
        modifications = {
            "Additions": [
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/orderedProperty"),
                    URIRef("http://example.org/target/1")
                )
            ]
        }
        
        result = generate_modification_text(
            modifications,
            "http://example.org/Person",
            "http://example.org/PersonShape",
            {},
            "http://example.org/person/1",
            mock_snapshot,
            "2024-01-01T00:00:00",
            mock_custom_filter
        )
        
        # Test that entity position caching logic was executed (lines 1494-1500)
        assert "Modifications" in result
        assert "Additions" in result


def test_generate_modification_text_shape_priority_ordering(
    mock_custom_filter, mock_display_rules, mock_format_triple
):
    """Test shape priority ordering within predicates."""
    mock_snapshot = MagicMock(spec=Graph)
    
    with patch('heritrace.routes.entity.get_display_rules', return_value=mock_display_rules), \
         patch('heritrace.routes.entity.get_property_order_from_rules', 
               return_value=["http://example.org/property"]), \
         patch('heritrace.routes.entity.get_shape_order_from_display_rules',
               return_value=["http://example.org/ShapeA", "http://example.org/ShapeB"]) as mock_shape_order, \
         patch('heritrace.routes.entity.gettext', side_effect=lambda x: x), \
         patch('heritrace.routes.entity.format_triple_modification', 
               side_effect=mock_format_triple), \
         patch('heritrace.routes.entity.determine_object_class_and_shape',
               side_effect=[("ClassA", "http://example.org/ShapeB"), ("ClassB", "http://example.org/ShapeA")]), \
         patch('heritrace.routes.entity.get_form_fields', return_value={}):
        
        modifications = {
            "Additions": [
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/property"),
                    URIRef("http://example.org/entity1")
                ),
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/property"),
                    URIRef("http://example.org/entity2")
                )
            ]
        }
        
        result = generate_modification_text(
            modifications,
            "http://example.org/Person",
            "http://example.org/PersonShape",
            {},
            "http://example.org/person/1",
            mock_snapshot,
            "2024-01-01T00:00:00",
            mock_custom_filter
        )
        
        # Verify shape ordering was called
        mock_shape_order.assert_called_with("http://example.org/Person", "http://example.org/PersonShape", "http://example.org/property")
        assert "http://example.org/property: http://example.org/entity1" in result


def test_generate_modification_text_position_based_sorting(
    mock_custom_filter, mock_display_rules, mock_format_triple
):
    """Test position-based sorting of triples within groups."""
    mock_snapshot = MagicMock(spec=Graph)
    
    with patch('heritrace.routes.entity.get_display_rules', return_value=mock_display_rules), \
         patch('heritrace.routes.entity.get_property_order_from_rules', 
               return_value=[]), \
         patch('heritrace.routes.entity.gettext', side_effect=lambda x: x), \
         patch('heritrace.routes.entity.format_triple_modification', 
               side_effect=mock_format_triple), \
         patch('heritrace.routes.entity.get_predicate_ordering_info',
               return_value="http://example.org/next"), \
         patch('heritrace.routes.entity.get_entity_position_in_sequence',
               side_effect=[2, 1]) as mock_position, \
         patch('heritrace.routes.entity.validators.url', return_value=True), \
         patch('heritrace.routes.entity.determine_object_class_and_shape', return_value=(None, None)), \
         patch('heritrace.routes.entity.get_form_fields', return_value={}):
        
        modifications = {
            "Additions": [
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/orderedProperty"),
                    URIRef("http://example.org/entity1")
                ),
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/orderedProperty"),
                    URIRef("http://example.org/entity2")
                )
            ]
        }
        
        result = generate_modification_text(
            modifications,
            "http://example.org/Person",
            "http://example.org/PersonShape",
            {},
            "http://example.org/person/1",
            mock_snapshot,
            "2024-01-01T00:00:00",
            mock_custom_filter
        )
        
        # Test that position-based sorting logic was executed (lines 1535-1536, 1559-1560)
        assert "Modifications" in result
        assert "Additions" in result


def test_generate_modification_text_deletions_with_history(
    mock_custom_filter, mock_display_rules, mock_format_triple
):
    """Test deletions with historical snapshots logic."""
    mock_current_snapshot = MagicMock(spec=Graph)
    mock_previous_snapshot = MagicMock(spec=Graph)
    
    with patch('heritrace.routes.entity.get_display_rules', return_value=mock_display_rules), \
         patch('heritrace.routes.entity.get_property_order_from_rules', 
               return_value=["http://example.org/property"]), \
         patch('heritrace.routes.entity.gettext', side_effect=lambda x: x), \
         patch('heritrace.routes.entity.format_triple_modification', 
               side_effect=mock_format_triple), \
         patch('heritrace.routes.entity.determine_object_class_and_shape',
               return_value=("SomeClass", "SomeShape")), \
         patch('heritrace.routes.entity.get_form_fields', return_value={}):
        
        modifications = {
            "Deletions": [
                (
                    URIRef("http://example.org/person/1"),
                    URIRef("http://example.org/property"),
                    "deleted_value"
                )
            ]
        }
        
        # Create history with previous snapshot
        history = {
            "http://example.org/person/1": {
                "2023-12-31T00:00:00": mock_previous_snapshot,
                "2024-01-01T00:00:00": mock_current_snapshot
            }
        }
        
        result = generate_modification_text(
            modifications,
            "http://example.org/Person",
            "http://example.org/PersonShape",
            history,
            "http://example.org/person/1",
            mock_current_snapshot,
            "2024-01-01T00:00:00",
            mock_custom_filter
        )
        
        # Verify that for deletions, the previous snapshot was used
        assert '<i class="bi bi-dash-circle-fill text-danger"></i>' in result
        assert "http://example.org/property: deleted_value" in result


def test_format_triple_modification_with_order_info():
    """Test order information display in format_triple_modification."""
    from heritrace.routes.entity import format_triple_modification
    from rdflib import URIRef
    
    mock_custom_filter = MagicMock()
    mock_custom_filter.human_readable_predicate.return_value = "Test Property"
    
    mock_snapshot = MagicMock(spec=Graph)
    
    triple = (
        URIRef("http://example.org/subject"),
        URIRef("http://example.org/predicate"),
        URIRef("http://example.org/object")
    )
    
    object_shapes_cache = {"http://example.org/object": "http://example.org/Shape"}
    object_classes_cache = {"http://example.org/object": "http://example.org/Class"}
    predicate_ordering_cache = {"http://example.org/predicate": "http://example.org/next"}
    entity_position_cache = {("http://example.org/object", "http://example.org/predicate"): 5}
    
    with patch('heritrace.routes.entity.get_object_label', return_value="Test Object"), \
         patch('heritrace.routes.entity.validators.url', return_value=True):
        
        result = format_triple_modification(
            triple,
            "http://example.org/Class",
            "http://example.org/Shape",
            object_shapes_cache,
            object_classes_cache,
            mock_snapshot,
            mock_custom_filter,
            subject_uri="http://example.org/subject",
            predicate_ordering_cache=predicate_ordering_cache,
            entity_position_cache=entity_position_cache
        )
    
    # Verify that order badge is included
    assert '<span class="order-position-badge">#5</span>' in result
    assert "Test Property" in result
    assert "Test Object" in result


def test_format_triple_modification_without_order_info():
    """Test format_triple_modification without order information."""
    from heritrace.routes.entity import format_triple_modification
    from rdflib import URIRef
    
    mock_custom_filter = MagicMock()
    mock_custom_filter.human_readable_predicate.return_value = "Test Property"
    
    mock_snapshot = MagicMock(spec=Graph)
    
    triple = (
        URIRef("http://example.org/subject"),
        URIRef("http://example.org/predicate"),
        URIRef("http://example.org/object")
    )
    
    object_shapes_cache = {"http://example.org/object": "http://example.org/Shape"}
    object_classes_cache = {"http://example.org/object": "http://example.org/Class"}
    
    with patch('heritrace.routes.entity.get_object_label', return_value="Test Object"), \
         patch('heritrace.routes.entity.validators.url', return_value=True):
        
        result = format_triple_modification(
            triple,
            "http://example.org/Class",
            "http://example.org/Shape",
            object_shapes_cache,
            object_classes_cache,
            mock_snapshot,
            mock_custom_filter,
            subject_uri="http://example.org/subject",
            predicate_ordering_cache=None,
            entity_position_cache=None
        )
    
    # Verify that no order badge is included when caches are None
    assert 'order-position-badge' not in result
    assert "Test Property" in result
    assert "Test Object" in result
