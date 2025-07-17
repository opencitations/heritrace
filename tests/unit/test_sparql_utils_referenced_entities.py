"""
Tests for referenced entities functions in sparql_utils module.
"""

from unittest.mock import MagicMock, patch

from heritrace.utils.sparql_utils import (collect_referenced_entities,
                                          import_referenced_entities)


class TestCollectReferencedEntities:
    """Tests for the collect_referenced_entities function."""

    def test_collect_simple_existing_entity_reference(self):
        """Test collecting a simple existing entity reference."""
        data = {
            "is_existing_entity": True,
            "entity_uri": "http://example.org/person1"
        }
        
        result = collect_referenced_entities(data)
        
        assert len(result) == 1
        assert "http://example.org/person1" in result

    def test_collect_nested_entity_references(self):
        """Test collecting references from nested entity structure."""
        data = {
            "entity_type": "http://example.org/Document",
            "properties": {
                "http://example.org/hasAuthor": [
                    {
                        "is_existing_entity": True,
                        "entity_uri": "http://example.org/person1"
                    }
                ],
                "http://example.org/hasEditor": [
                    {
                        "is_existing_entity": True,
                        "entity_uri": "http://example.org/person2"
                    }
                ]
            }
        }
        
        result = collect_referenced_entities(data)
        
        assert len(result) == 2
        assert "http://example.org/person1" in result
        assert "http://example.org/person2" in result

    def test_collect_empty_structure(self):
        """Test collecting from empty or non-entity structures."""
        assert len(collect_referenced_entities({})) == 0
        assert len(collect_referenced_entities([])) == 0
        assert len(collect_referenced_entities("string")) == 0

    def test_collect_mixed_with_new_entities(self):
        """Test that new entities don't get collected but their references do."""
        data = {
            "entity_type": "http://example.org/Document",
            "properties": {
                "http://example.org/hasAuthor": [
                    {
                        "entity_type": "http://example.org/Person",
                        "properties": {
                            "http://example.org/knows": [
                                {
                                    "is_existing_entity": True,
                                    "entity_uri": "http://example.org/person1"
                                }
                            ]
                        }
                    }
                ]
            }
        }
        
        result = collect_referenced_entities(data)
        
        assert len(result) == 1
        assert "http://example.org/person1" in result


class TestImportReferencedEntities:
    """Tests for the import_referenced_entities function."""

    @patch('heritrace.utils.sparql_utils.collect_referenced_entities')
    def test_import_referenced_entities_success(self, mock_collect):
        """Test successful import of referenced entities."""
        mock_editor = MagicMock()
        structured_data = {"test": "data"}
        referenced_entities = {
            "http://example.org/person1",
            "http://example.org/person2"
        }
        
        mock_collect.return_value = referenced_entities
        
        import_referenced_entities(mock_editor, structured_data)
        
        mock_collect.assert_called_once_with(structured_data)
        assert mock_editor.import_entity.call_count == 2

    @patch('heritrace.utils.sparql_utils.collect_referenced_entities')
    @patch('builtins.print')
    def test_import_referenced_entities_with_error(self, mock_print, mock_collect):
        """Test import when one entity fails to import."""
        mock_editor = MagicMock()
        structured_data = {"test": "data"}
        referenced_entities = {"http://example.org/person1"}
        
        mock_collect.return_value = referenced_entities
        mock_editor.import_entity.side_effect = Exception("Import failed")
        
        # Should not raise exception, should continue
        import_referenced_entities(mock_editor, structured_data)
        
        mock_editor.import_entity.assert_called_once()
        mock_print.assert_called_once()

    @patch('heritrace.utils.sparql_utils.collect_referenced_entities')
    def test_import_referenced_entities_empty_set(self, mock_collect):
        """Test import when no referenced entities are found."""
        mock_editor = MagicMock()
        structured_data = {"test": "data"}
        
        mock_collect.return_value = set()
        
        import_referenced_entities(mock_editor, structured_data)
        
        mock_collect.assert_called_once_with(structured_data)
        mock_editor.import_entity.assert_not_called()