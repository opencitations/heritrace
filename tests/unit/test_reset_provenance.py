from unittest.mock import MagicMock, patch

import pytest
from heritrace.scripts.reset_provenance import (ProvenanceResetter,
                                                load_config,
                                                main,
                                                reset_entity_provenance)
from rdflib import URIRef
from SPARQLWrapper import JSON


@pytest.fixture
def mock_counter_handler():
    """Fixture for a mock counter handler."""
    handler = MagicMock()
    handler.set_counter = MagicMock()
    return handler


@pytest.fixture
def mock_sparql():
    """Fixture for a mock SPARQLWrapper."""
    with patch('heritrace.scripts.reset_provenance.SPARQLWrapper') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        mock_instance.queryAndConvert = MagicMock()
        mock_instance.query = MagicMock()
        yield mock, mock_instance


@pytest.fixture
def mock_logger():
    """Fixture for a mock logger."""
    with patch('heritrace.scripts.reset_provenance.logging.getLogger') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def resetter(mock_counter_handler, mock_sparql, mock_logger):
    """Fixture for a ProvenanceResetter instance with mocked dependencies."""
    _, mock_sparql_instance = mock_sparql
    return ProvenanceResetter(
        provenance_endpoint="http://example.org/sparql",
        counter_handler=mock_counter_handler
    )


def test_init(resetter, mock_counter_handler, mock_sparql):
    """Test initialization of ProvenanceResetter."""
    mock_sparql_class, mock_sparql_instance = mock_sparql
    
    assert resetter.provenance_endpoint == "http://example.org/sparql"
    assert resetter.counter_handler == mock_counter_handler
    mock_sparql_class.assert_called_once_with("http://example.org/sparql")
    mock_sparql_instance.setReturnFormat.assert_called_once_with(JSON)


def test_get_entity_snapshots(resetter, mock_sparql):
    """Test _get_entity_snapshots method."""
    _, mock_sparql_instance = mock_sparql
    
    # Mock the SPARQL response
    mock_response = {
        "results": {
            "bindings": [
                {
                    "snapshot": {"value": "http://example.org/snapshot/1"},
                    "generation_time": {"value": "2023-01-01T00:00:00Z"}
                },
                {
                    "snapshot": {"value": "http://example.org/snapshot/2"},
                    "generation_time": {"value": "2023-01-02T00:00:00Z"}
                }
            ]
        }
    }
    mock_sparql_instance.queryAndConvert.return_value = mock_response
    
    # Call the method
    entity_uri = URIRef("http://example.org/entity/1")
    snapshots = resetter._get_entity_snapshots(entity_uri)
    
    # Verify the results
    assert len(snapshots) == 2
    assert snapshots[0]["uri"] == "http://example.org/snapshot/1"
    assert snapshots[0]["generation_time"] == "2023-01-01T00:00:00Z"
    assert snapshots[1]["uri"] == "http://example.org/snapshot/2"
    assert snapshots[1]["generation_time"] == "2023-01-02T00:00:00Z"
    
    # Verify the SPARQL query was set correctly
    mock_sparql_instance.setQuery.assert_called_once()
    query_arg = mock_sparql_instance.setQuery.call_args[0][0]
    assert f"<{entity_uri}>" in query_arg
    assert "prov:specializationOf" in query_arg
    assert "prov:generatedAtTime" in query_arg


def test_delete_snapshots_empty(resetter, mock_sparql):
    """Test _delete_snapshots method with empty list."""
    _, mock_sparql_instance = mock_sparql
    
    result = resetter._delete_snapshots([])
    
    assert result is True
    mock_sparql_instance.setQuery.assert_not_called()


def test_delete_snapshots_success(resetter, mock_sparql):
    """Test _delete_snapshots method with successful deletion."""
    _, mock_sparql_instance = mock_sparql
    
    snapshots = [
        {"uri": "http://example.org/snapshot/1", "generation_time": "2023-01-01T00:00:00Z"},
        {"uri": "http://example.org/snapshot/2", "generation_time": "2023-01-02T00:00:00Z"}
    ]
    
    result = resetter._delete_snapshots(snapshots)
    
    assert result is True
    # The method calls setQuery multiple times (twice per snapshot)
    assert mock_sparql_instance.setQuery.call_count == 4
    
    # Check that the first call contains the first snapshot
    first_query = mock_sparql_instance.setQuery.call_args_list[0][0][0]
    assert "<http://example.org/snapshot/1>" in first_query
    
    # Check that the third call contains the second snapshot
    third_query = mock_sparql_instance.setQuery.call_args_list[2][0][0]
    assert "<http://example.org/snapshot/2>" in third_query
    
    # Verify method was set to POST and query was called
    assert mock_sparql_instance.method == "POST"
    assert mock_sparql_instance.query.call_count == 4


def test_delete_snapshots_error(resetter, mock_sparql, mock_logger):
    """Test _delete_snapshots method with error during deletion."""
    _, mock_sparql_instance = mock_sparql
    
    snapshots = [
        {"uri": "http://example.org/snapshot/1", "generation_time": "2023-01-01T00:00:00Z"}
    ]
    
    # Make the query method raise an exception
    mock_sparql_instance.query.side_effect = Exception("SPARQL error")
    
    result = resetter._delete_snapshots(snapshots)
    
    assert result is False
    mock_logger.error.assert_called_once()
    error_msg = mock_logger.error.call_args[0][0]
    assert "Error deleting snapshot" in error_msg
    assert "http://example.org/snapshot/1" in error_msg
    assert "SPARQL error" in error_msg


def test_reset_provenance_counter(resetter, mock_counter_handler, mock_logger):
    """Test _reset_provenance_counter method."""
    entity_uri = URIRef("http://example.org/entity/123")
    
    resetter._reset_provenance_counter(entity_uri)
    
    mock_counter_handler.set_counter.assert_called_once_with(1, "123")
    mock_logger.info.assert_called_once()
    info_msg = mock_logger.info.call_args[0][0]
    assert "Reset provenance counter" in info_msg
    assert str(entity_uri) in info_msg


@patch('heritrace.scripts.reset_provenance.convert_to_datetime')
def test_reset_entity_provenance_no_snapshots(mock_convert, resetter, mock_sparql, mock_logger):
    """Test reset_entity_provenance method when no snapshots are found."""
    _, mock_sparql_instance = mock_sparql
    
    # Mock empty snapshots
    mock_sparql_instance.queryAndConvert.return_value = {"results": {"bindings": []}}
    
    entity_uri = "http://example.org/entity/1"
    result = resetter.reset_entity_provenance(entity_uri)
    
    assert result is False
    mock_logger.warning.assert_called_once()
    warning_msg = mock_logger.warning.call_args[0][0]
    assert "No snapshots found" in warning_msg
    assert entity_uri in warning_msg


@patch('heritrace.scripts.reset_provenance.convert_to_datetime')
def test_reset_entity_provenance_single_snapshot(mock_convert, resetter, mock_sparql, mock_logger, mock_counter_handler):
    """Test reset_entity_provenance method with only one snapshot."""
    _, mock_sparql_instance = mock_sparql
    
    # Mock a single snapshot
    mock_response = {
        "results": {
            "bindings": [
                {
                    "snapshot": {"value": "http://example.org/snapshot/1"},
                    "generation_time": {"value": "2023-01-01T00:00:00Z"}
                }
            ]
        }
    }
    mock_sparql_instance.queryAndConvert.return_value = mock_response
    
    # Mock datetime conversion
    mock_convert.return_value = "2023-01-01T00:00:00Z"
    
    entity_uri = "http://example.org/entity/1"
    result = resetter.reset_entity_provenance(entity_uri)
    
    assert result is True
    # Check that info was called at least once
    assert mock_logger.info.call_count >= 1
    
    # Verify the first info message
    first_info_msg = mock_logger.info.call_args_list[0][0][0]
    assert "has only one snapshot" in first_info_msg
    
    # Verify that invalidatedAtTime was removed
    assert any("removed invalidatedAtTime" in call[0][0] for call in mock_logger.info.call_args_list)
    
    # Counter should not be reset for a single snapshot
    mock_counter_handler.set_counter.assert_not_called()


@patch('heritrace.scripts.reset_provenance.convert_to_datetime')
def test_reset_entity_provenance_multiple_snapshots(mock_convert, resetter, mock_sparql, mock_logger, mock_counter_handler):
    """Test reset_entity_provenance method with multiple snapshots."""
    _, mock_sparql_instance = mock_sparql
    
    # Mock multiple snapshots
    mock_response = {
        "results": {
            "bindings": [
                {
                    "snapshot": {"value": "http://example.org/snapshot/1"},
                    "generation_time": {"value": "2023-01-01T00:00:00Z"}
                },
                {
                    "snapshot": {"value": "http://example.org/snapshot/2"},
                    "generation_time": {"value": "2023-01-02T00:00:00Z"}
                },
                {
                    "snapshot": {"value": "http://example.org/snapshot/3"},
                    "generation_time": {"value": "2023-01-03T00:00:00Z"}
                }
            ]
        }
    }
    mock_sparql_instance.queryAndConvert.return_value = mock_response
    
    # Mock datetime conversion to ensure proper sorting
    mock_convert.side_effect = lambda x: x
    
    entity_uri = "http://example.org/entity/1"
    result = resetter.reset_entity_provenance(entity_uri)
    
    assert result is True
    
    # Verify snapshots 2 and 3 were deleted (each snapshot gets 2 setQuery calls)
    assert mock_sparql_instance.setQuery.call_count >= 4
    
    # Check that snapshot 2 was deleted
    snapshot2_deleted = False
    for call_args in mock_sparql_instance.setQuery.call_args_list:
        if "<http://example.org/snapshot/2>" in call_args[0][0]:
            snapshot2_deleted = True
            break
    assert snapshot2_deleted, "Snapshot 2 was not deleted"
    
    # Check that snapshot 3 was deleted
    snapshot3_deleted = False
    for call_args in mock_sparql_instance.setQuery.call_args_list:
        if "<http://example.org/snapshot/3>" in call_args[0][0]:
            snapshot3_deleted = True
            break
    assert snapshot3_deleted, "Snapshot 3 was not deleted"
    
    # Verify counter was reset
    mock_counter_handler.set_counter.assert_called_once_with(1, "1")
    
    # Verify success was logged
    success_logged = False
    for call_args in mock_logger.info.call_args_list:
        if "Successfully reset provenance" in call_args[0][0]:
            success_logged = True
            break
    assert success_logged, "Success message was not logged"


@patch('heritrace.scripts.reset_provenance.convert_to_datetime')
def test_reset_entity_provenance_delete_failure(mock_convert, resetter, mock_sparql, mock_counter_handler):
    """Test reset_entity_provenance method when deletion fails."""
    _, mock_sparql_instance = mock_sparql
    
    # Mock multiple snapshots
    mock_response = {
        "results": {
            "bindings": [
                {
                    "snapshot": {"value": "http://example.org/snapshot/1"},
                    "generation_time": {"value": "2023-01-01T00:00:00Z"}
                },
                {
                    "snapshot": {"value": "http://example.org/snapshot/2"},
                    "generation_time": {"value": "2023-01-02T00:00:00Z"}
                }
            ]
        }
    }
    mock_sparql_instance.queryAndConvert.return_value = mock_response
    
    # Mock datetime conversion
    mock_convert.side_effect = lambda x: x
    
    # Make deletion fail
    mock_sparql_instance.query.side_effect = Exception("SPARQL error")
    
    entity_uri = "http://example.org/entity/1"
    result = resetter.reset_entity_provenance(entity_uri)
    
    assert result is False
    mock_counter_handler.set_counter.assert_not_called()


def test_reset_entity_provenance_string_uri(resetter, mock_sparql):
    """Test reset_entity_provenance method with string URI."""
    _, mock_sparql_instance = mock_sparql
    
    # Mock empty snapshots for simplicity
    mock_sparql_instance.queryAndConvert.return_value = {"results": {"bindings": []}}
    
    # Call with string URI
    entity_uri = "http://example.org/entity/1"
    resetter.reset_entity_provenance(entity_uri)
    
    # Verify URI was converted to URIRef
    query_arg = mock_sparql_instance.setQuery.call_args[0][0]
    assert f"<{entity_uri}>" in query_arg


@patch('heritrace.scripts.reset_provenance.ProvenanceResetter')
def test_reset_entity_provenance_function(mock_resetter_class):
    """Test the reset_entity_provenance function."""
    # Mock the ProvenanceResetter instance
    mock_resetter_instance = MagicMock()
    mock_resetter_class.return_value = mock_resetter_instance
    mock_resetter_instance.reset_entity_provenance.return_value = True
    
    # Mock the counter handler
    mock_counter_handler = MagicMock()
    
    # Call the function
    entity_uri = "http://example.org/entity/1"
    provenance_endpoint = "http://example.org/sparql"
    result = reset_entity_provenance(
        entity_uri=entity_uri,
        provenance_endpoint=provenance_endpoint,
        counter_handler=mock_counter_handler
    )
    
    # Verify the results
    assert result is True
    mock_resetter_class.assert_called_once_with(
        provenance_endpoint=provenance_endpoint,
        counter_handler=mock_counter_handler
    )
    mock_resetter_instance.reset_entity_provenance.assert_called_once_with(entity_uri)


@patch('heritrace.scripts.reset_provenance.importlib.util')
def test_load_config_success(mock_importlib_util):
    """Test load_config function with successful loading."""
    # Mock the importlib.util functions
    mock_spec = MagicMock()
    mock_importlib_util.spec_from_file_location.return_value = mock_spec
    
    mock_config = MagicMock()
    mock_importlib_util.module_from_spec.return_value = mock_config
    
    # Call the function
    config_path = "/path/to/config.py"
    result = load_config(config_path)
    
    # Verify the results
    assert result == mock_config
    mock_importlib_util.spec_from_file_location.assert_called_once_with("config", config_path)
    mock_importlib_util.module_from_spec.assert_called_once_with(mock_spec)
    mock_spec.loader.exec_module.assert_called_once_with(mock_config)


@patch('heritrace.scripts.reset_provenance.importlib.util')
@patch('heritrace.scripts.reset_provenance.logging.error')
@patch('heritrace.scripts.reset_provenance.sys.exit')
def test_load_config_error(mock_exit, mock_logging_error, mock_importlib_util):
    """Test load_config function with error during loading."""
    # Make importlib.util.spec_from_file_location raise an exception
    mock_importlib_util.spec_from_file_location.side_effect = Exception("Import error")
    
    # Call the function
    config_path = "/path/to/config.py"
    load_config(config_path)
    
    # Verify the results
    mock_logging_error.assert_called_once()
    error_msg = mock_logging_error.call_args[0][0]
    assert "Error loading configuration file" in error_msg
    mock_exit.assert_called_once_with(1)


@patch('heritrace.scripts.reset_provenance.argparse.ArgumentParser')
@patch('heritrace.scripts.reset_provenance.load_config')
@patch('heritrace.scripts.reset_provenance.reset_entity_provenance')
@patch('heritrace.scripts.reset_provenance.logging')
def test_main_success(mock_logging, mock_reset_entity_provenance, mock_load_config, mock_argparse):
    """Test main function with successful execution."""
    # Mock the ArgumentParser
    mock_parser = MagicMock()
    mock_argparse.return_value = mock_parser
    
    mock_args = MagicMock()
    mock_args.entity_uri = "http://example.org/entity/1"
    mock_args.config = "/path/to/config.py"
    mock_args.verbose = False
    mock_parser.parse_args.return_value = mock_args
    
    # Mock the config with Config class
    mock_config = MagicMock()
    mock_config_class = MagicMock()
    mock_config_class.PROVENANCE_DB_URL = "http://example.org/sparql"
    mock_config_class.COUNTER_HANDLER = MagicMock()
    mock_config.Config = mock_config_class
    mock_load_config.return_value = mock_config
    
    # Mock reset_entity_provenance to return True (success)
    mock_reset_entity_provenance.return_value = True
    
    # Call the function
    result = main()
    
    # Verify the results
    assert result == 0
    mock_reset_entity_provenance.assert_called_once_with(
        entity_uri="http://example.org/entity/1",
        provenance_endpoint="http://example.org/sparql",
        counter_handler=mock_config_class.COUNTER_HANDLER
    )
    mock_logging.info.assert_called()
    info_msg = mock_logging.info.call_args[0][0]
    assert "Successfully reset provenance" in info_msg


@patch('heritrace.scripts.reset_provenance.argparse.ArgumentParser')
@patch('heritrace.scripts.reset_provenance.load_config')
@patch('heritrace.scripts.reset_provenance.reset_entity_provenance')
@patch('heritrace.scripts.reset_provenance.logging')
def test_main_failure(mock_logging, mock_reset_entity_provenance, mock_load_config, mock_argparse):
    """Test main function with failure during execution."""
    # Mock the ArgumentParser
    mock_parser = MagicMock()
    mock_argparse.return_value = mock_parser
    
    mock_args = MagicMock()
    mock_args.entity_uri = "http://example.org/entity/1"
    mock_args.config = "/path/to/config.py"
    mock_args.verbose = False
    mock_parser.parse_args.return_value = mock_args
    
    # Mock the config with Config class
    mock_config = MagicMock()
    mock_config_class = MagicMock()
    mock_config_class.PROVENANCE_DB_URL = "http://example.org/sparql"
    mock_config_class.COUNTER_HANDLER = MagicMock()
    mock_config.Config = mock_config_class
    mock_load_config.return_value = mock_config
    
    # Mock reset_entity_provenance to return False (failure)
    mock_reset_entity_provenance.return_value = False
    
    # Call the function
    result = main()
    
    # Verify the results
    assert result == 1
    mock_reset_entity_provenance.assert_called_once_with(
        entity_uri="http://example.org/entity/1",
        provenance_endpoint="http://example.org/sparql",
        counter_handler=mock_config_class.COUNTER_HANDLER
    )
    mock_logging.error.assert_called()
    error_msg = mock_logging.error.call_args[0][0]
    assert "Failed to reset provenance" in error_msg


@patch('heritrace.scripts.reset_provenance.argparse.ArgumentParser')
@patch('heritrace.scripts.reset_provenance.load_config')
@patch('heritrace.scripts.reset_provenance.logging.error')
@patch('heritrace.scripts.reset_provenance.hasattr')
def test_main_missing_config_class(mock_hasattr, mock_logging_error, mock_load_config, mock_argparse):
    """Test main function with missing Config class in config."""
    # Mock the ArgumentParser
    mock_parser = MagicMock()
    mock_argparse.return_value = mock_parser
    
    mock_args = MagicMock()
    mock_args.entity_uri = "http://example.org/entity/1"
    mock_args.config = "/path/to/config.py"
    mock_args.verbose = False
    mock_parser.parse_args.return_value = mock_args
    
    # Mock the config
    mock_config = MagicMock()
    mock_load_config.return_value = mock_config
    
    # Mock hasattr to return False for Config
    def mock_hasattr_func(obj, name):
        if obj == mock_config and name == "Config":
            return False
        return True
    
    mock_hasattr.side_effect = mock_hasattr_func
    
    # Call the function
    result = main()
    
    # Verify the results
    assert result == 1
    mock_logging_error.assert_called_once()
    error_msg = mock_logging_error.call_args[0][0]
    assert "Configuration file must define a Config class" in error_msg


@patch('heritrace.scripts.reset_provenance.argparse.ArgumentParser')
@patch('heritrace.scripts.reset_provenance.load_config')
@patch('heritrace.scripts.reset_provenance.logging.error')
@patch('heritrace.scripts.reset_provenance.hasattr')
def test_main_missing_provenance_endpoint(mock_hasattr, mock_logging_error, mock_load_config, mock_argparse):
    """Test main function with missing PROVENANCE_DB_URL in Config class."""
    # Mock the ArgumentParser
    mock_parser = MagicMock()
    mock_argparse.return_value = mock_parser
    
    mock_args = MagicMock()
    mock_args.entity_uri = "http://example.org/entity/1"
    mock_args.config = "/path/to/config.py"
    mock_args.verbose = False
    mock_parser.parse_args.return_value = mock_args
    
    # Mock the config with Config class
    mock_config = MagicMock()
    mock_config_class = MagicMock()
    mock_config.Config = mock_config_class
    mock_load_config.return_value = mock_config
    
    # Mock hasattr to return False for PROVENANCE_DB_URL
    def mock_hasattr_func(obj, name):
        if obj == mock_config_class and name == "PROVENANCE_DB_URL":
            return False
        return True
    
    mock_hasattr.side_effect = mock_hasattr_func
    
    # Call the function
    result = main()
    
    # Verify the results
    assert result == 1
    mock_logging_error.assert_called_once()
    error_msg = mock_logging_error.call_args[0][0]
    assert "Config class must define PROVENANCE_DB_URL" in error_msg


@patch('heritrace.scripts.reset_provenance.argparse.ArgumentParser')
@patch('heritrace.scripts.reset_provenance.load_config')
@patch('heritrace.scripts.reset_provenance.logging.error')
@patch('heritrace.scripts.reset_provenance.hasattr')
def test_main_missing_counter_handler(mock_hasattr, mock_logging_error, mock_load_config, mock_argparse):
    """Test main function with missing COUNTER_HANDLER in Config class."""
    # Mock the ArgumentParser
    mock_parser = MagicMock()
    mock_argparse.return_value = mock_parser
    
    mock_args = MagicMock()
    mock_args.entity_uri = "http://example.org/entity/1"
    mock_args.config = "/path/to/config.py"
    mock_args.verbose = False
    mock_parser.parse_args.return_value = mock_args
    
    # Mock the config with Config class and PROVENANCE_DB_URL
    mock_config = MagicMock()
    mock_config_class = MagicMock()
    mock_config_class.PROVENANCE_DB_URL = "http://example.org/sparql"
    mock_config.Config = mock_config_class
    mock_load_config.return_value = mock_config
    
    # Mock hasattr to return True for PROVENANCE_DB_URL but False for COUNTER_HANDLER
    def mock_hasattr_func(obj, name):
        if obj == mock_config_class and name == "COUNTER_HANDLER":
            return False
        return True
    
    mock_hasattr.side_effect = mock_hasattr_func
    
    # Call the function
    result = main()
    
    # Verify the results
    assert result == 1
    mock_logging_error.assert_called_once()
    error_msg = mock_logging_error.call_args[0][0]
    assert "Config class must define COUNTER_HANDLER" in error_msg


def test_remove_invalidated_time_error(resetter, mock_sparql, mock_logger):
    """Test _remove_invalidated_time method when an error occurs."""
    _, mock_sparql_instance = mock_sparql
    
    # Make the query method raise an exception
    mock_sparql_instance.query.side_effect = Exception("SPARQL error")
    
    snapshot = {
        "uri": "http://example.org/snapshot/1",
        "generation_time": "2023-01-01T00:00:00Z"
    }
    
    result = resetter._remove_invalidated_time(snapshot)
    
    # Verify the result is False
    assert result is False
    
    # Verify error was logged
    mock_logger.error.assert_called_once()
    error_msg = mock_logger.error.call_args[0][0]
    assert "Error removing invalidatedAtTime from snapshot" in error_msg
    assert "http://example.org/snapshot/1" in error_msg
    assert "SPARQL error" in error_msg
    
    # Verify the query was set correctly
    mock_sparql_instance.setQuery.assert_called_once()
    query = mock_sparql_instance.setQuery.call_args[0][0]
    assert "DELETE" in query
    assert "prov:invalidatedAtTime" in query
    assert "<http://example.org/snapshot/1>" in query


def test_remove_invalidated_time_success(resetter, mock_sparql, mock_logger):
    """Test _remove_invalidated_time method when successful."""
    _, mock_sparql_instance = mock_sparql
    
    snapshot = {
        "uri": "http://example.org/snapshot/1",
        "generation_time": "2023-01-01T00:00:00Z"
    }
    
    result = resetter._remove_invalidated_time(snapshot)
    
    # Verify the result is True
    assert result is True
    
    # Verify success was logged
    mock_logger.info.assert_called_once()
    info_msg = mock_logger.info.call_args[0][0]
    assert "Successfully removed invalidatedAtTime from snapshot" in info_msg
    assert "http://example.org/snapshot/1" in info_msg
    
    # Verify the query was set correctly
    mock_sparql_instance.setQuery.assert_called_once()
    query = mock_sparql_instance.setQuery.call_args[0][0]
    assert "DELETE" in query
    assert "prov:invalidatedAtTime" in query
    assert "<http://example.org/snapshot/1>" in query
    
    # Verify method was set to POST and query was called
    assert mock_sparql_instance.method == "POST"
    mock_sparql_instance.query.assert_called_once() 