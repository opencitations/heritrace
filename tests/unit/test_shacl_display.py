"""
Tests for the shacl_display module.
"""

from heritrace.utils.shacl_display import order_form_fields


class TestShaclDisplay:
    """Test class for shacl_display module."""

    def test_unordered_properties_are_preserved(self):
        """Test that properties not in ordered_properties are included in the result."""
        entity_class = "http://example.org/Person"
        entity_shape = "http://example.org/PersonShape"
        entity_key = (entity_class, entity_shape)

        form_fields = {
            entity_key: {
                "http://example.org/name": [{"label": "Name"}],
                "http://example.org/unordered": [{"label": "Unordered"}]
            }
        }

        display_rules = [
            {
                "target": {
                    "class": entity_class,
                    "shape": entity_shape
                },
                "displayProperties": [
                    {"property": "http://example.org/name"}
                ]
            }
        ]

        result = order_form_fields(form_fields, display_rules)

        assert "http://example.org/name" in result[entity_key]
        assert "http://example.org/unordered" in result[entity_key]
        ordered_props = list(result[entity_key].keys())
        assert ordered_props[0] == "http://example.org/name"
        assert ordered_props[1] == "http://example.org/unordered"
