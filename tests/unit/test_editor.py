import pytest
from unittest.mock import MagicMock
from rdflib import URIRef, Literal
from datetime import datetime

from heritrace.editor import Editor

@pytest.fixture
def mock_editor_deps():
    return {
        "dataset_endpoint": "http://localhost:9999/blazegraph/sparql",
        "provenance_endpoint": "http://localhost:9998/blazegraph/sparql",
        "counter_handler": MagicMock(),
        "resp_agent": URIRef("http://example.com/agent"),
        "source": URIRef("http://initial.source"), # Initial source
        "c_time": datetime.now()
    }

def test_set_primary_source_string(mock_editor_deps):
    """Test setting primary source using a string URI."""
    editor = Editor(**mock_editor_deps)
    new_source_str = "http://new.string.source"
    expected_source_uri = URIRef(new_source_str)
    
    editor.set_primary_source(new_source_str)
    
    assert isinstance(editor.source, URIRef)
    assert editor.source == expected_source_uri

def test_set_primary_source_uriref(mock_editor_deps):
    """Test setting primary source using a URIRef object."""
    editor = Editor(**mock_editor_deps)
    new_source_uri = URIRef("http://new.uriref.source")
    
    editor.set_primary_source(new_source_uri)
    
    assert isinstance(editor.source, URIRef)
    assert editor.source == new_source_uri

def test_set_primary_source_none(mock_editor_deps):
    """Test setting primary source with None doesn't change it."""
    initial_source = mock_editor_deps["source"]
    editor = Editor(**mock_editor_deps)
    
    editor.set_primary_source(None)
    
    assert editor.source == initial_source # Source should remain unchanged

def test_set_primary_source_empty_string(mock_editor_deps):
    """Test setting primary source with an empty string doesn't change it."""
    initial_source = mock_editor_deps["source"]
    editor = Editor(**mock_editor_deps)
    
    editor.set_primary_source("")
    
    assert editor.source == initial_source # Source should remain unchanged 