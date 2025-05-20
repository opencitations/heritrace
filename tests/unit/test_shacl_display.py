"""
Tests for the shacl_display module.
"""

from heritrace.utils.shacl_display import order_form_fields


class TestShaclDisplay:
    """Test class for shacl_display module."""

    def test_unordered_properties_are_preserved_exact_match(self):
        """Test that properties not in ordered_properties are included in the result with exact match (class and shape)."""
        entity_class = "http://example.org/Person"
        entity_shape = "http://example.org/PersonShape"
        entity_key = (entity_class, entity_shape)

        form_fields = {
            entity_key: {
                "http://example.org/name": [{"label": "Name"}],
                "http://example.org/unordered": [{"label": "Unordered"}],
                "http://example.org/another": [{"label": "Another"}]
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

        # Verify all properties are preserved
        assert "http://example.org/name" in result[entity_key]
        assert "http://example.org/unordered" in result[entity_key]
        assert "http://example.org/another" in result[entity_key]
        
        # Verify the order (ordered properties first, then unordered)
        ordered_props = list(result[entity_key].keys())
        assert ordered_props[0] == "http://example.org/name"
        assert set(ordered_props[1:]) == {"http://example.org/unordered", "http://example.org/another"}
        
        # Verify the content is preserved
        assert result[entity_key]["http://example.org/name"] == form_fields[entity_key]["http://example.org/name"]
        assert result[entity_key]["http://example.org/unordered"] == form_fields[entity_key]["http://example.org/unordered"]
        assert result[entity_key]["http://example.org/another"] == form_fields[entity_key]["http://example.org/another"]

    def test_unordered_properties_are_preserved_class_only(self):
        """Test that properties not in ordered_properties are included in the result with class-only match."""
        entity_class = "http://example.org/Person"
        entity_shape1 = "http://example.org/PersonShape1"
        entity_shape2 = "http://example.org/PersonShape2"
        entity_key1 = (entity_class, entity_shape1)
        entity_key2 = (entity_class, entity_shape2)

        form_fields = {
            entity_key1: {
                "http://example.org/name": [{"label": "Name"}],
                "http://example.org/unordered": [{"label": "Unordered"}]
            },
            entity_key2: {
                "http://example.org/email": [{"label": "Email"}],
                "http://example.org/phone": [{"label": "Phone"}]
            }
        }

        display_rules = [
            {
                "target": {
                    "class": entity_class
                },
                "displayProperties": [
                    {"property": "http://example.org/name"},
                    {"property": "http://example.org/email"}
                ]
            }
        ]

        result = order_form_fields(form_fields, display_rules)

        # Check both entity keys are in the result
        assert entity_key1 in result
        assert entity_key2 in result
        
        # Check all properties for entity_key1
        assert "http://example.org/name" in result[entity_key1]
        assert "http://example.org/unordered" in result[entity_key1]
        
        # Check all properties for entity_key2
        assert "http://example.org/email" in result[entity_key2]
        assert "http://example.org/phone" in result[entity_key2]
        
        # Verify the content is preserved for unordered properties
        assert result[entity_key1]["http://example.org/unordered"] == form_fields[entity_key1]["http://example.org/unordered"]
        assert result[entity_key2]["http://example.org/phone"] == form_fields[entity_key2]["http://example.org/phone"]

    def test_unordered_properties_are_preserved_shape_only(self):
        """Test that properties not in ordered_properties are included in the result with shape-only match."""
        entity_class1 = "http://example.org/Person"
        entity_class2 = "http://example.org/Organization"
        entity_shape = "http://example.org/CommonShape"
        entity_key1 = (entity_class1, entity_shape)
        entity_key2 = (entity_class2, entity_shape)

        form_fields = {
            entity_key1: {
                "http://example.org/name": [{"label": "Name"}],
                "http://example.org/address": [{"label": "Address"}]
            },
            entity_key2: {
                "http://example.org/name": [{"label": "OrgName"}],
                "http://example.org/taxCode": [{"label": "TaxCode"}]
            }
        }

        display_rules = [
            {
                "target": {
                    "shape": entity_shape
                },
                "displayProperties": [
                    {"property": "http://example.org/name"}
                ]
            }
        ]

        result = order_form_fields(form_fields, display_rules)

        # Check both entity keys are in the result
        assert entity_key1 in result
        assert entity_key2 in result
        
        # Check all properties for entity_key1
        assert "http://example.org/name" in result[entity_key1]
        assert "http://example.org/address" in result[entity_key1]
        
        # Check all properties for entity_key2
        assert "http://example.org/name" in result[entity_key2]
        assert "http://example.org/taxCode" in result[entity_key2]
        
        # Verify the content is preserved for unordered properties
        assert result[entity_key1]["http://example.org/address"] == form_fields[entity_key1]["http://example.org/address"]
        assert result[entity_key2]["http://example.org/taxCode"] == form_fields[entity_key2]["http://example.org/taxCode"]
