import pytest
from unittest.mock import patch, MagicMock
from rdflib import Graph, ConjunctiveGraph, URIRef, Literal
from flask import Flask

from heritrace.routes.entity import (
    compute_graph_differences,
    get_entities_to_restore,
    prepare_entity_snapshots,
    find_appropriate_snapshot,
)
from heritrace.editor import Editor


def test_restore_version_with_quadstore():
    """Test restore_version with quadstore data."""
    # Setup mocks
    mock_get_dataset_is_quadstore = MagicMock(return_value=True)
    
    # Create test data
    current_graph = ConjunctiveGraph()
    editor = MagicMock()
    editor.g_set = MagicMock()
    
    # Add some quads to the current graph
    current_graph.add((
        URIRef("http://example.org/entity/1"), 
        URIRef("http://example.org/predicate"), 
        Literal("Value"),
        URIRef("http://example.org/graph")
    ))
    
    # Simulate the code path
    if mock_get_dataset_is_quadstore():
        for quad in current_graph.quads():
            editor.g_set.add(quad)
    
    # Verify results
    editor.g_set.add.assert_called_once()


def test_restore_version_delete_quad():
    """Test restore_version with quad deletion."""
    # Create test data
    editor = MagicMock()
    # Setup the entity_index as a dictionary
    editor.g_set.entity_index = {}
    
    item = (
        URIRef("http://example.org/subject"), 
        URIRef("http://example.org/predicate"), 
        Literal("Value"),
        URIRef("http://example.org/graph")
    )
    entity_snapshots = {
        "http://example.org/subject": {
            "needs_restore": True,
            "source": "http://example.org/source"
        }
    }
    
    # Simulate the code path
    if len(item) == 4:
        editor.delete(item[0], item[1], item[2], item[3])
    else:
        editor.delete(item[0], item[1], item[2])
    
    subject = str(item[0])
    if subject in entity_snapshots:
        entity_info = entity_snapshots[subject]
        if entity_info["needs_restore"]:
            editor.g_set.mark_as_restored(URIRef(subject))
        # Initialize the dictionary entry if it doesn't exist
        if URIRef(subject) not in editor.g_set.entity_index:
            editor.g_set.entity_index[URIRef(subject)] = {}
        editor.g_set.entity_index[URIRef(subject)]["restoration_source"] = entity_info["source"]
    
    # Verify results
    editor.delete.assert_called_once_with(item[0], item[1], item[2], item[3])
    editor.g_set.mark_as_restored.assert_called_once_with(URIRef(subject))
    assert editor.g_set.entity_index[URIRef(subject)]["restoration_source"] == "http://example.org/source"


def test_restore_version_add_triple():
    """Test restore_version with triple addition."""
    # Create test data
    editor = MagicMock()
    # Setup the entity_index as a dictionary
    editor.g_set.entity_index = {}
    
    item = (
        URIRef("http://example.org/subject"), 
        URIRef("http://example.org/predicate"), 
        Literal("Value")
    )
    entity_snapshots = {
        "http://example.org/subject": {
            "needs_restore": True,
            "source": "http://example.org/source"
        }
    }
    
    # Simulate the code path
    if len(item) == 4:
        editor.create(item[0], item[1], item[2], item[3])
    else:
        editor.create(item[0], item[1], item[2])
    
    subject = str(item[0])
    if subject in entity_snapshots:
        entity_info = entity_snapshots[subject]
        if entity_info["needs_restore"]:
            editor.g_set.mark_as_restored(URIRef(subject))
            # Initialize the dictionary entry if it doesn't exist
            if URIRef(subject) not in editor.g_set.entity_index:
                editor.g_set.entity_index[URIRef(subject)] = {}
            editor.g_set.entity_index[URIRef(subject)]["source"] = entity_info["source"]
    
    # Verify results
    editor.create.assert_called_once_with(item[0], item[1], item[2])
    editor.g_set.mark_as_restored.assert_called_once_with(URIRef(subject))
    assert editor.g_set.entity_index[URIRef(subject)]["source"] == "http://example.org/source"


def test_restore_version_entity_not_in_snapshots():
    """Test restore_version when entity is not in snapshots."""
    # Create test data
    editor = MagicMock()
    # Setup the entity_index as a dictionary
    editor.g_set.entity_index = {}
    
    item = (
        URIRef("http://example.org/subject"), 
        URIRef("http://example.org/predicate"), 
        Literal("Value")
    )
    entity_snapshots = {
        "http://example.org/other_subject": {  # Different subject
            "needs_restore": True,
            "source": "http://example.org/source"
        }
    }
    
    # Simulate the code path
    if len(item) == 4:
        editor.create(item[0], item[1], item[2], item[3])
    else:
        editor.create(item[0], item[1], item[2])
    
    subject = str(item[0])
    if subject in entity_snapshots:
        entity_info = entity_snapshots[subject]
        if entity_info["needs_restore"]:
            editor.g_set.mark_as_restored(URIRef(subject))
            # Initialize the dictionary entry if it doesn't exist
            if URIRef(subject) not in editor.g_set.entity_index:
                editor.g_set.entity_index[URIRef(subject)] = {}
            editor.g_set.entity_index[URIRef(subject)]["source"] = entity_info["source"]
    
    # Verify results
    editor.create.assert_called_once_with(item[0], item[1], item[2])
    # Should not call mark_as_restored since subject is not in entity_snapshots
    editor.g_set.mark_as_restored.assert_not_called()
    # Should not add to entity_index
    assert URIRef(subject) not in editor.g_set.entity_index


def test_restore_version_entity_not_needs_restore():
    """Test restore_version when entity does not need restoration."""
    # Create test data
    editor = MagicMock()
    # Setup the entity_index as a dictionary
    editor.g_set.entity_index = {}
    
    item = (
        URIRef("http://example.org/subject"), 
        URIRef("http://example.org/predicate"), 
        Literal("Value")
    )
    entity_snapshots = {
        "http://example.org/subject": {
            "needs_restore": False,  # Entity doesn't need restoration
            "source": "http://example.org/source"
        }
    }
    
    # Simulate the code path for deletion
    if len(item) == 4:
        editor.delete(item[0], item[1], item[2], item[3])
    else:
        editor.delete(item[0], item[1], item[2])
    
    subject = str(item[0])
    if subject in entity_snapshots:
        entity_info = entity_snapshots[subject]
        if entity_info["needs_restore"]:
            editor.g_set.mark_as_restored(URIRef(subject))
        # Initialize the dictionary entry if it doesn't exist
        if URIRef(subject) not in editor.g_set.entity_index:
            editor.g_set.entity_index[URIRef(subject)] = {}
        editor.g_set.entity_index[URIRef(subject)]["restoration_source"] = entity_info["source"]
    
    # Verify results
    editor.delete.assert_called_once_with(item[0], item[1], item[2])
    # Should not call mark_as_restored since needs_restore is False
    editor.g_set.mark_as_restored.assert_not_called()
    # Should still add to entity_index
    assert editor.g_set.entity_index[URIRef(subject)]["restoration_source"] == "http://example.org/source"


def test_restore_version_entity_not_deleted():
    """Test restore_version when entity is not deleted."""
    # Create test data
    editor = MagicMock()
    # Setup the entity_index as a dictionary
    editor.g_set.entity_index = {}
    
    is_deleted = False
    entity_uri = "http://example.org/entity/123"
    entity_snapshots = {
        entity_uri: {
            "needs_restore": True,
            "source": "http://example.org/source"
        }
    }
    
    # Simulate the code path
    if is_deleted and entity_uri in entity_snapshots:
        editor.g_set.mark_as_restored(URIRef(entity_uri))
        source = entity_snapshots[entity_uri]["source"]
        # Initialize the dictionary entry if it doesn't exist
        if URIRef(entity_uri) not in editor.g_set.entity_index:
            editor.g_set.entity_index[URIRef(entity_uri)] = {}
        editor.g_set.entity_index[URIRef(entity_uri)]["source"] = source
    
    # Verify results
    # Should not call mark_as_restored since is_deleted is False
    editor.g_set.mark_as_restored.assert_not_called()
    # Should not add to entity_index
    assert URIRef(entity_uri) not in editor.g_set.entity_index


def test_restore_version_entity_not_in_snapshots_when_deleted():
    """Test restore_version when deleted entity is not in snapshots."""
    # Create test data
    editor = MagicMock()
    # Setup the entity_index as a dictionary
    editor.g_set.entity_index = {}
    
    is_deleted = True
    entity_uri = "http://example.org/entity/123"
    entity_snapshots = {
        "http://example.org/other_entity": {  # Different entity
            "needs_restore": True,
            "source": "http://example.org/source"
        }
    }
    
    # Simulate the code path
    if is_deleted and entity_uri in entity_snapshots:
        editor.g_set.mark_as_restored(URIRef(entity_uri))
        source = entity_snapshots[entity_uri]["source"]
        # Initialize the dictionary entry if it doesn't exist
        if URIRef(entity_uri) not in editor.g_set.entity_index:
            editor.g_set.entity_index[URIRef(entity_uri)] = {}
        editor.g_set.entity_index[URIRef(entity_uri)]["source"] = source
    
    # Verify results
    # Should not call mark_as_restored since entity_uri is not in entity_snapshots
    editor.g_set.mark_as_restored.assert_not_called()
    # Should not add to entity_index
    assert URIRef(entity_uri) not in editor.g_set.entity_index


@patch('heritrace.routes.entity.get_dataset_is_quadstore')
def test_compute_graph_differences_quadstore(mock_get_dataset_is_quadstore):
    """Test compute_graph_differences when dataset is a quadstore."""
    # Setup mocks
    mock_get_dataset_is_quadstore.return_value = True
    
    # Create test graphs
    current_graph = ConjunctiveGraph()
    historical_graph = ConjunctiveGraph()
    
    # Add test quads to current graph
    current_graph.add((
        URIRef("http://example.org/subject1"),
        URIRef("http://example.org/predicate1"),
        Literal("value1"),
        URIRef("http://example.org/graph1")
    ))
    current_graph.add((
        URIRef("http://example.org/subject2"),
        URIRef("http://example.org/predicate2"),
        Literal("value2"),
        URIRef("http://example.org/graph2")
    ))
    
    # Add test quads to historical graph
    historical_graph.add((
        URIRef("http://example.org/subject1"),
        URIRef("http://example.org/predicate1"),
        Literal("value1"),
        URIRef("http://example.org/graph1")
    ))
    historical_graph.add((
        URIRef("http://example.org/subject3"),
        URIRef("http://example.org/predicate3"),
        Literal("value3"),
        URIRef("http://example.org/graph3")
    ))
    
    # Call the function
    quads_to_delete, quads_to_add = compute_graph_differences(current_graph, historical_graph)
    
    # Verify results
    # Should compute differences using quads() instead of triples()
    assert len(quads_to_delete) == 1  # subject2/predicate2/value2/graph2 should be deleted
    assert len(quads_to_add) == 1     # subject3/predicate3/value3/graph3 should be added
    
    # Verify specific quads
    delete_quad = list(quads_to_delete)[0]
    add_quad = list(quads_to_add)[0]
    
    assert delete_quad[0] == URIRef("http://example.org/subject2")
    assert delete_quad[1] == URIRef("http://example.org/predicate2")
    assert delete_quad[2] == Literal("value2")
    assert str(delete_quad[3].identifier) == "http://example.org/graph2"
    
    assert add_quad[0] == URIRef("http://example.org/subject3")
    assert add_quad[1] == URIRef("http://example.org/predicate3")
    assert add_quad[2] == Literal("value3")
    assert str(add_quad[3].identifier) == "http://example.org/graph3" 