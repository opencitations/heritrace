"""
Unit tests for entity modification functions in entity.py.
These tests focus on the apply_modifications and validate_modification functionality.
"""
import pytest
from unittest.mock import MagicMock, patch
from rdflib import URIRef, Literal, XSD
from heritrace.routes.entity import (
    apply_modifications,
    validate_modification,
    get_entity_types,
    get_highest_priority_class,
    get_predicate_count,
    get_sparql,
    process_modification_data
)


def test_apply_modifications_remove():
    """Test apply_modifications with remove operation."""
    # Setup
    editor = MagicMock()
    subject_uri = "http://example.org/entity"
    predicate = "http://example.org/predicate"
    graph_uri = "http://example.org/graph"
    
    modifications = [{
        "operation": "remove",
        "predicate": predicate
    }]
    
    # Execute
    apply_modifications(editor, modifications, subject_uri, graph_uri)
    
    # Verify
    editor.delete.assert_called_once_with(
        URIRef(subject_uri),
        URIRef(predicate),
        graph_uri=graph_uri
    )


def test_apply_modifications_add_uri():
    """Test apply_modifications with add operation for URI value."""
    # Setup
    editor = MagicMock()
    subject_uri = "http://example.org/entity"
    predicate = "http://example.org/predicate"
    value = "http://example.org/value"
    graph_uri = "http://example.org/graph"
    
    modifications = [{
        "operation": "add",
        "predicate": predicate,
        "value": value
    }]
    
    # Execute
    apply_modifications(editor, modifications, subject_uri, graph_uri)
    
    # Verify
    editor.create.assert_called_once_with(
        URIRef(subject_uri),
        URIRef(predicate),
        URIRef(value),
        graph_uri
    )


def test_apply_modifications_add_literal():
    """Test apply_modifications with add operation for Literal value."""
    # Setup
    editor = MagicMock()
    subject_uri = "http://example.org/entity"
    predicate = "http://example.org/predicate"
    value = "test value"
    datatype = str(XSD.integer)
    graph_uri = "http://example.org/graph"
    
    modifications = [{
        "operation": "add",
        "predicate": predicate,
        "value": value,
        "datatype": datatype
    }]
    
    # Execute
    apply_modifications(editor, modifications, subject_uri, graph_uri)
    
    # Verify
    editor.create.assert_called_once_with(
        URIRef(subject_uri),
        URIRef(predicate),
        Literal(value, datatype=URIRef(datatype)),
        graph_uri
    )


def test_apply_modifications_update_uri():
    """Test apply_modifications with update operation for URI values."""
    # Setup
    editor = MagicMock()
    subject_uri = "http://example.org/entity"
    predicate = "http://example.org/predicate"
    old_value = "http://example.org/oldValue"
    new_value = "http://example.org/newValue"
    graph_uri = "http://example.org/graph"
    
    modifications = [{
        "operation": "update",
        "predicate": predicate,
        "oldValue": old_value,
        "newValue": new_value
    }]
    
    # Execute
    apply_modifications(editor, modifications, subject_uri, graph_uri)
    
    # Verify
    editor.update.assert_called_once_with(
        URIRef(subject_uri),
        URIRef(predicate),
        URIRef(old_value),
        URIRef(new_value),
        graph_uri
    )


def test_apply_modifications_update_literal():
    """Test apply_modifications with update operation for Literal values."""
    # Setup
    editor = MagicMock()
    subject_uri = "http://example.org/entity"
    predicate = "http://example.org/predicate"
    old_value = "old test value"
    new_value = "new test value"
    datatype = str(XSD.string)
    graph_uri = "http://example.org/graph"
    
    modifications = [{
        "operation": "update",
        "predicate": predicate,
        "oldValue": old_value,
        "newValue": new_value,
        "datatype": datatype
    }]
    
    # Execute
    apply_modifications(editor, modifications, subject_uri, graph_uri)
    
    # Verify
    editor.update.assert_called_once_with(
        URIRef(subject_uri),
        URIRef(predicate),
        Literal(old_value, datatype=URIRef(datatype)),
        Literal(new_value, datatype=URIRef(datatype)),
        graph_uri
    )


def test_apply_modifications_multiple():
    """Test apply_modifications with multiple modifications."""
    # Setup
    editor = MagicMock()
    subject_uri = "http://example.org/entity"
    predicate1 = "http://example.org/predicate1"
    predicate2 = "http://example.org/predicate2"
    value = "test value"
    graph_uri = "http://example.org/graph"
    
    modifications = [
        {
            "operation": "remove",
            "predicate": predicate1
        },
        {
            "operation": "add",
            "predicate": predicate2,
            "value": value
        }
    ]
    
    # Execute
    apply_modifications(editor, modifications, subject_uri, graph_uri)
    
    # Verify
    editor.delete.assert_called_once_with(
        URIRef(subject_uri),
        URIRef(predicate1),
        graph_uri=graph_uri
    )
    editor.create.assert_called_once_with(
        URIRef(subject_uri),
        URIRef(predicate2),
        Literal(value, datatype=URIRef(str(XSD.string))),
        graph_uri
    )


def test_validate_modification_no_operation():
    """Test validate_modification when no operation is specified."""
    # Setup
    modification = {
        "predicate": "http://example.org/predicate"
    }
    subject_uri = "http://example.org/entity"
    form_fields = {}
    
    # Execute
    is_valid, error_message = validate_modification(modification, subject_uri, form_fields)
    
    # Verify
    assert not is_valid
    assert "No operation specified in modification" == error_message


def test_validate_modification_no_predicate():
    """Test validate_modification when no predicate is specified."""
    # Setup
    modification = {
        "operation": "add"
    }
    subject_uri = "http://example.org/entity"
    form_fields = {}
    
    # Execute
    is_valid, error_message = validate_modification(modification, subject_uri, form_fields)
    
    # Verify
    assert not is_valid
    assert "No predicate specified in modification" == error_message


def test_validate_modification_invalid_operation():
    """Test validate_modification with an invalid operation."""
    # Setup
    modification = {
        "operation": "invalid",
        "predicate": "http://example.org/predicate"
    }
    subject_uri = "http://example.org/entity"
    form_fields = {}
    
    # Execute
    is_valid, error_message = validate_modification(modification, subject_uri, form_fields)
    
    # Verify
    assert not is_valid
    assert "Invalid operation: invalid" == error_message


@patch('heritrace.routes.entity.get_predicate_count')
@patch('heritrace.routes.entity.get_entity_types')
@patch('heritrace.routes.entity.get_highest_priority_class')
def test_validate_modification_remove_required(mock_get_highest_priority, mock_get_entity_types, mock_get_predicate_count):
    """Test validate_modification when trying to remove a required predicate."""
    # Setup mocks
    mock_get_highest_priority.return_value = "http://example.org/Document"
    mock_get_entity_types.return_value = ["http://example.org/Document"]
    
    # Setup test data
    modification = {
        "operation": "remove",
        "predicate": "http://example.org/title"
    }
    subject_uri = "http://example.org/entity"
    form_fields = {
        "http://example.org/Document": {
            "http://example.org/title": [
                {
                    "minCount": 1  # This makes it required
                }
            ]
        }
    }
    
    # Execute
    is_valid, error_message = validate_modification(modification, subject_uri, form_fields)
    
    # Verify
    assert not is_valid
    assert "Cannot remove required predicate: http://example.org/title" == error_message


@patch('heritrace.routes.entity.get_predicate_count')
@patch('heritrace.routes.entity.get_entity_types')
@patch('heritrace.routes.entity.get_highest_priority_class')
def test_validate_modification_exceed_max_count(mock_get_highest_priority, mock_get_entity_types, mock_get_predicate_count):
    """Test validate_modification when exceeding maxCount for a predicate."""
    # Setup mocks
    mock_get_highest_priority.return_value = "http://example.org/Document"
    mock_get_entity_types.return_value = ["http://example.org/Document"]
    mock_get_predicate_count.return_value = 2  # Current count
    
    # Setup test data
    modification = {
        "operation": "add",
        "predicate": "http://example.org/title"
    }
    subject_uri = "http://example.org/entity"
    form_fields = {
        "http://example.org/Document": {
            "http://example.org/title": [
                {
                    "maxCount": 2  # Maximum allowed
                }
            ]
        }
    }
    
    # Execute
    is_valid, error_message = validate_modification(modification, subject_uri, form_fields)
    
    # Verify
    assert not is_valid
    assert "Maximum count exceeded for predicate: http://example.org/title" == error_message


@patch('heritrace.routes.entity.get_sparql')
def test_get_predicate_count_single_value(mock_get_sparql):
    """Test get_predicate_count when there is a single value for the predicate."""
    # Setup mock SPARQL endpoint
    mock_sparql = MagicMock()
    mock_get_sparql.return_value = mock_sparql
    
    # Mock query results
    mock_results = {
        "results": {
            "bindings": [
                {
                    "count": {"value": "1"}
                }
            ]
        }
    }
    mock_query = MagicMock()
    mock_query.convert.return_value = mock_results
    mock_sparql.query.return_value = mock_query
    
    # Test data
    subject_uri = "http://example.org/entity"
    predicate = "http://example.org/predicate"
    
    # Execute
    count = get_predicate_count(subject_uri, predicate)
    
    # Verify
    assert count == 1
    mock_sparql.setQuery.assert_called_once()
    mock_sparql.setReturnFormat.assert_called_once()
    mock_sparql.query.assert_called_once()
    
    # Verify query format
    query = mock_sparql.setQuery.call_args[0][0]
    assert subject_uri in query
    assert predicate in query
    assert "COUNT(?o)" in query


@patch('heritrace.routes.entity.get_sparql')
def test_get_predicate_count_multiple_values(mock_get_sparql):
    """Test get_predicate_count when there are multiple values for the predicate."""
    # Setup mock SPARQL endpoint
    mock_sparql = MagicMock()
    mock_get_sparql.return_value = mock_sparql
    
    # Mock query results
    mock_results = {
        "results": {
            "bindings": [
                {
                    "count": {"value": "3"}
                }
            ]
        }
    }
    mock_query = MagicMock()
    mock_query.convert.return_value = mock_results
    mock_sparql.query.return_value = mock_query
    
    # Test data
    subject_uri = "http://example.org/entity"
    predicate = "http://example.org/predicate"
    
    # Execute
    count = get_predicate_count(subject_uri, predicate)
    
    # Verify
    assert count == 3
    mock_sparql.setQuery.assert_called_once()
    mock_sparql.setReturnFormat.assert_called_once()
    mock_sparql.query.assert_called_once()


@patch('heritrace.routes.entity.get_sparql')
def test_get_predicate_count_no_values(mock_get_sparql):
    """Test get_predicate_count when there are no values for the predicate."""
    # Setup mock SPARQL endpoint
    mock_sparql = MagicMock()
    mock_get_sparql.return_value = mock_sparql
    
    # Mock query results
    mock_results = {
        "results": {
            "bindings": [
                {
                    "count": {"value": "0"}
                }
            ]
        }
    }
    mock_query = MagicMock()
    mock_query.convert.return_value = mock_results
    mock_sparql.query.return_value = mock_query
    
    # Test data
    subject_uri = "http://example.org/entity"
    predicate = "http://example.org/predicate"
    
    # Execute
    count = get_predicate_count(subject_uri, predicate)
    
    # Verify
    assert count == 0
    mock_sparql.setQuery.assert_called_once()
    mock_sparql.setReturnFormat.assert_called_once()
    mock_sparql.query.assert_called_once()


@patch('heritrace.utils.sparql_utils.get_sparql')
def test_get_entity_types_single_type(mock_get_sparql):
    """Test get_entity_types when the entity has a single type."""
    # Setup mock SPARQL endpoint
    mock_sparql = MagicMock()
    mock_get_sparql.return_value = mock_sparql
    
    # Mock query results
    mock_results = {
        "results": {
            "bindings": [
                {
                    "type": {"value": "http://example.org/Person"}
                }
            ]
        }
    }
    mock_query = MagicMock()
    mock_query.convert.return_value = mock_results
    mock_sparql.query.return_value = mock_query
    
    # Test data
    subject_uri = "http://example.org/entity"
    
    # Execute
    types = get_entity_types(subject_uri)
    
    # Verify
    assert types == ["http://example.org/Person"]
    mock_sparql.setQuery.assert_called_once()
    mock_sparql.setReturnFormat.assert_called_once()
    mock_sparql.query.assert_called_once()
    
    # Verify query format
    query = mock_sparql.setQuery.call_args[0][0]
    assert subject_uri in query
    assert "a ?type" in query


@patch('heritrace.utils.sparql_utils.get_sparql')
def test_get_entity_types_multiple_types(mock_get_sparql):
    """Test get_entity_types when the entity has multiple types."""
    # Setup mock SPARQL endpoint
    mock_sparql = MagicMock()
    mock_get_sparql.return_value = mock_sparql
    
    # Mock query results
    mock_results = {
        "results": {
            "bindings": [
                {
                    "type": {"value": "http://example.org/Person"}
                },
                {
                    "type": {"value": "http://example.org/Author"}
                },
                {
                    "type": {"value": "http://example.org/Researcher"}
                }
            ]
        }
    }
    mock_query = MagicMock()
    mock_query.convert.return_value = mock_results
    mock_sparql.query.return_value = mock_query
    
    # Test data
    subject_uri = "http://example.org/entity"
    
    # Execute
    types = get_entity_types(subject_uri)
    
    # Verify
    assert types == [
        "http://example.org/Person",
        "http://example.org/Author",
        "http://example.org/Researcher"
    ]
    mock_sparql.setQuery.assert_called_once()
    mock_sparql.setReturnFormat.assert_called_once()
    mock_sparql.query.assert_called_once()


@patch('heritrace.utils.sparql_utils.get_sparql')
def test_get_entity_types_no_types(mock_get_sparql):
    """Test get_entity_types when the entity has no types."""
    # Setup mock SPARQL endpoint
    mock_sparql = MagicMock()
    mock_get_sparql.return_value = mock_sparql
    
    # Mock query results with no types
    mock_results = {
        "results": {
            "bindings": []
        }
    }
    mock_query = MagicMock()
    mock_query.convert.return_value = mock_results
    mock_sparql.query.return_value = mock_query
    
    # Test data
    subject_uri = "http://example.org/entity"
    
    # Execute
    types = get_entity_types(subject_uri)
    
    # Verify
    assert types == []
    mock_sparql.setQuery.assert_called_once()
    mock_sparql.setReturnFormat.assert_called_once()
    mock_sparql.query.assert_called_once()


def test_process_modification_data_no_subject():
    """Test process_modification_data when no subject URI is provided."""
    # Setup
    data = {
        "modifications": [
            {
                "operation": "add",
                "predicate": "http://example.org/predicate",
                "value": "test value"
            }
        ]
    }
    
    # Execute and verify
    with pytest.raises(ValueError) as exc_info:
        process_modification_data(data)
    
    assert str(exc_info.value) == "No subject URI provided in modification data"
