from unittest.mock import MagicMock, patch

import pytest
from heritrace.scripts.clean_missing_entities import (MissingEntityCleaner,
                                                    load_config,
                                                    main,
                                                    clean_missing_entities)
from SPARQLWrapper import JSON


@pytest.fixture
def mock_sparql():
    """Fixture for a mock SPARQLWrapper."""
    with patch('heritrace.scripts.clean_missing_entities.SPARQLWrapper') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        mock_instance.queryAndConvert = MagicMock()
        mock_instance.query = MagicMock()
        yield mock, mock_instance


@pytest.fixture
def mock_logger():
    """Fixture for a mock logger."""
    with patch('heritrace.scripts.clean_missing_entities.logging.getLogger') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def cleaner(mock_sparql, mock_logger):
    """Fixture for a MissingEntityCleaner instance with mocked dependencies."""
    _, mock_sparql_instance = mock_sparql
    return MissingEntityCleaner(
        endpoint="http://example.org/sparql",
        is_virtuoso=False  # Non-Virtuoso triplestore by default
    )


def test_init(cleaner, mock_sparql):
    """Test initialization of MissingEntityCleaner."""
    mock_sparql_class, mock_sparql_instance = mock_sparql
    
    assert cleaner.endpoint == "http://example.org/sparql"
    assert cleaner.is_virtuoso is False
    mock_sparql_class.assert_called_once_with("http://example.org/sparql")
    mock_sparql_instance.setReturnFormat.assert_called_once_with(JSON)


def test_find_missing_entities(cleaner, mock_sparql):
    """Test _find_missing_entities method."""
    _, mock_sparql_instance = mock_sparql
    
    # Mock the SPARQL response for missing entities
    mock_response = {
        "results": {
            "bindings": [
                {
                    "entity": {"value": "http://example.org/missing1"},
                    "s": {"value": "http://example.org/entity1"},
                    "p": {"value": "http://example.org/references"}
                },
                {
                    "entity": {"value": "http://example.org/missing2"},
                    "s": {"value": "http://example.org/entity2"},
                    "p": {"value": "http://example.org/mentions"}
                }
            ]
        }
    }
    mock_sparql_instance.queryAndConvert.return_value = mock_response
    
    # Call the method
    missing_entities = cleaner._find_missing_entities_with_references()
    
    # Verify the results
    assert len(missing_entities) == 2
    assert "http://example.org/missing1" in missing_entities
    assert "http://example.org/missing2" in missing_entities
    
    # Verify the SPARQL query was set correctly
    mock_sparql_instance.setQuery.assert_called_once()
    query_arg = mock_sparql_instance.setQuery.call_args[0][0]
    assert "SELECT DISTINCT ?entity" in query_arg
    
    # The query should look for entities with no triples where they are the subject
    assert "NOT EXISTS" in query_arg
    assert "?entity ?anyPredicate ?anyObject" in query_arg


def test_find_missing_entities_empty(cleaner, mock_sparql):
    """Test _find_missing_entities method with no missing entities found."""
    _, mock_sparql_instance = mock_sparql
    
    # Mock an empty SPARQL response
    mock_response = {
        "results": {
            "bindings": []
        }
    }
    mock_sparql_instance.queryAndConvert.return_value = mock_response
    
    # Call the method
    missing_entities = cleaner._find_missing_entities_with_references()
    
    # Verify no missing entities were found
    assert len(missing_entities) == 0


def test_find_references_to_entity(cleaner, mock_sparql):
    """Test _find_references_to_entity method."""
    _, mock_sparql_instance = mock_sparql
    
    # Mock the SPARQL response per una specifica entità
    entity_uri = "http://example.org/missing1"
    mock_response = {
        "results": {
            "bindings": [
                {
                    "entity": {"value": entity_uri},
                    "s": {"value": "http://example.org/entity1"},
                    "p": {"value": "http://example.org/references"}
                },
                {
                    "entity": {"value": entity_uri},
                    "s": {"value": "http://example.org/entity2"},
                    "p": {"value": "http://example.org/cites"}
                }
            ]
        }
    }
    mock_sparql_instance.queryAndConvert.return_value = mock_response
    
    # Call the method
    all_refs = cleaner._find_missing_entities_with_references()
    
    # Check that the entity has references
    assert entity_uri in all_refs
    references = all_refs[entity_uri]
    
    # Verify the results
    assert len(references) == 2
    assert references[0]["subject"] == "http://example.org/entity1"
    assert references[0]["predicate"] == "http://example.org/references"
    assert references[1]["subject"] == "http://example.org/entity2"
    assert references[1]["predicate"] == "http://example.org/cites"


def test_remove_references(cleaner, mock_sparql, mock_logger):
    """Test _remove_references method."""
    _, mock_sparql_instance = mock_sparql
    
    # Mock references
    references = [
        {"subject": "http://example.org/entity1", "predicate": "http://example.org/references"},
        {"subject": "http://example.org/entity2", "predicate": "http://example.org/cites"}
    ]
    
    entity_uri = "http://example.org/missing1"
    
    # Call the method
    success = cleaner._remove_references(entity_uri, references)
    
    # Verify the result
    assert success is True
    
    # Verify SPARQL queries were executed for each reference
    assert mock_sparql_instance.setQuery.call_count == 2
    assert mock_sparql_instance.query.call_count == 2
    
    # Verify method was set to POST
    assert mock_sparql_instance.method == "POST"
    
    # Verify log messages
    assert mock_logger.info.call_count >= 2
    for i, call_args in enumerate(mock_logger.info.call_args_list):
        message = call_args[0][0]
        assert "Removed reference" in message
        assert references[i]["subject"] in message if i < len(references) else True
        assert references[i]["predicate"] in message if i < len(references) else True
        assert entity_uri in message


def test_remove_references_error(cleaner, mock_sparql, mock_logger):
    """Test _remove_references method with an error."""
    _, mock_sparql_instance = mock_sparql
    
    # Mock references
    references = [
        {"subject": "http://example.org/entity1", "predicate": "http://example.org/references"}
    ]
    
    # Make the query method raise an exception
    mock_sparql_instance.query.side_effect = Exception("SPARQL error")
    
    entity_uri = "http://example.org/missing1"
    
    # Call the method
    success = cleaner._remove_references(entity_uri, references)
    
    # Verify the result
    assert success is False
    
    # Verify error was logged
    mock_logger.error.assert_called_once()
    error_msg = mock_logger.error.call_args[0][0]
    assert "Error removing reference" in error_msg
    assert references[0]["subject"] in error_msg
    assert references[0]["predicate"] in error_msg
    assert entity_uri in error_msg


def test_find_missing_entities_with_references(cleaner, mock_sparql):
    """Test _find_missing_entities_with_references method."""
    _, mock_sparql_instance = mock_sparql
    
    # Mock the SPARQL response for missing entities with references
    mock_response = {
        "results": {
            "bindings": [
                {
                    "entity": {"value": "http://example.org/missing1"},
                    "s": {"value": "http://example.org/entity1"},
                    "p": {"value": "http://example.org/references"}
                },
                {
                    "entity": {"value": "http://example.org/missing1"},
                    "s": {"value": "http://example.org/entity2"},
                    "p": {"value": "http://example.org/cites"}
                },
                {
                    "entity": {"value": "http://example.org/missing2"},
                    "s": {"value": "http://example.org/entity3"},
                    "p": {"value": "http://example.org/mentions"}
                }
            ]
        }
    }
    mock_sparql_instance.queryAndConvert.return_value = mock_response
    
    # Call the method
    missing_entities = cleaner._find_missing_entities_with_references()
    
    # Verify the results
    assert len(missing_entities) == 2
    assert len(missing_entities["http://example.org/missing1"]) == 2
    assert len(missing_entities["http://example.org/missing2"]) == 1
    
    # Check references for missing1
    refs1 = missing_entities["http://example.org/missing1"]
    assert {"subject": "http://example.org/entity1", "predicate": "http://example.org/references"} in refs1
    assert {"subject": "http://example.org/entity2", "predicate": "http://example.org/cites"} in refs1
    
    # Check references for missing2
    refs2 = missing_entities["http://example.org/missing2"]
    assert {"subject": "http://example.org/entity3", "predicate": "http://example.org/mentions"} in refs2
    
    # Verify the SPARQL query was set correctly
    mock_sparql_instance.setQuery.assert_called_once()
    query_arg = mock_sparql_instance.setQuery.call_args[0][0]
    assert "SELECT DISTINCT ?entity ?s ?p" in query_arg
    
    # The query should look for entities with no triples where they are the subject
    assert "NOT EXISTS" in query_arg
    assert "?entity ?anyPredicate ?anyObject" in query_arg


def test_find_missing_entities_with_references_empty(cleaner, mock_sparql):
    """Test _find_missing_entities_with_references method with no missing entities found."""
    _, mock_sparql_instance = mock_sparql
    
    # Mock an empty SPARQL response
    mock_response = {
        "results": {
            "bindings": []
        }
    }
    mock_sparql_instance.queryAndConvert.return_value = mock_response
    
    # Call the method
    missing_entities = cleaner._find_missing_entities_with_references()
    
    # Verify no missing entities were found
    assert len(missing_entities) == 0


def test_process_missing_entities(cleaner, mock_sparql, mock_logger):
    """Test process_missing_entities method."""
    with patch.object(cleaner, '_find_missing_entities_with_references') as mock_find_missing_with_refs:
        with patch.object(cleaner, '_remove_references') as mock_remove_refs:
            # Mock finding two missing entities with their references
            mock_find_missing_with_refs.return_value = {
                "http://example.org/missing1": [
                    {"subject": "http://example.org/entity1", "predicate": "http://example.org/references"}
                ],
                "http://example.org/missing2": [
                    {"subject": "http://example.org/entity2", "predicate": "http://example.org/cites"},
                    {"subject": "http://example.org/entity3", "predicate": "http://example.org/knows"}
                ]
            }
            
            # Mock successful reference removal
            mock_remove_refs.return_value = True
            
            # Call the method
            results = cleaner.process_missing_entities()
            
            # Verify the results
            assert isinstance(results, list)
            assert len(results) == 2
            
            # Check first result
            assert results[0]["uri"] == "http://example.org/missing1"
            assert results[0]["success"] is True
            assert len(results[0]["references"]) == 1
            assert results[0]["references"][0]["subject"] == "http://example.org/entity1"
            assert results[0]["references"][0]["predicate"] == "http://example.org/references"
            
            # Check second result
            assert results[1]["uri"] == "http://example.org/missing2"
            assert results[1]["success"] is True
            assert len(results[1]["references"]) == 2
            
            # Verify the methods were called with correct arguments
            assert mock_find_missing_with_refs.call_count == 1
            assert mock_remove_refs.call_count == 2
            
            # Check first remove_references call
            mock_remove_refs.assert_any_call(
                "http://example.org/missing1", 
                [{"subject": "http://example.org/entity1", "predicate": "http://example.org/references"}]
            )
            
            # Check second remove_references call
            mock_remove_refs.assert_any_call(
                "http://example.org/missing2", 
                [
                    {"subject": "http://example.org/entity2", "predicate": "http://example.org/cites"},
                    {"subject": "http://example.org/entity3", "predicate": "http://example.org/knows"}
                ]
            )
            
            # Verify log messages
            assert mock_logger.info.call_count >= 4  # At least 2 for each missing entity
            
            # Verify the summary message
            summary_msg = mock_logger.info.call_args_list[-1][0][0]
            assert "Found 2 missing entities" in summary_msg
            assert "removed 3 references" in summary_msg


def test_process_missing_entities_no_missing(cleaner, mock_sparql, mock_logger):
    """Test process_missing_entities method with no missing entities found."""
    with patch.object(cleaner, '_find_missing_entities_with_references') as mock_find_missing_with_refs:
        # Mock finding no missing entities
        mock_find_missing_with_refs.return_value = {}
        
        # Call the method
        results = cleaner.process_missing_entities()
        
        # Verify the result
        assert isinstance(results, list)
        assert len(results) == 0
        
        # Verify log messages
        assert mock_logger.info.call_count >= 1
        info_msg = mock_logger.info.call_args[0][0]
        assert "No missing entity references found" in info_msg


def test_process_missing_entities_error(cleaner, mock_sparql, mock_logger):
    """Test process_missing_entities method with an error during reference removal."""
    with patch.object(cleaner, '_find_missing_entities_with_references') as mock_find_missing_with_refs:
        with patch.object(cleaner, '_remove_references') as mock_remove_refs:
            # Mock finding one missing entity with references
            mock_find_missing_with_refs.return_value = {
                "http://example.org/missing1": [
                    {"subject": "http://example.org/entity1", "predicate": "http://example.org/references"}
                ]
            }
            
            # Mock error during reference removal
            mock_remove_refs.return_value = False
            
            # Call the method
            results = cleaner.process_missing_entities()
            
            # Verify the result
            assert isinstance(results, list)
            assert len(results) == 1
            assert results[0]["uri"] == "http://example.org/missing1"
            assert results[0]["success"] is False
            assert len(results[0]["references"]) == 1
            
            # Verify error was logged
            assert mock_logger.error.call_count >= 1
            error_msg = mock_logger.error.call_args[0][0]
            assert "Failed to remove references" in error_msg
            assert "http://example.org/missing1" in error_msg


@patch('heritrace.scripts.clean_missing_entities.MissingEntityCleaner')
def test_clean_missing_entities_function(mock_cleaner_class):
    """Test the clean_missing_entities function."""
    # Mock instance of MissingEntityCleaner
    mock_cleaner_instance = mock_cleaner_class.return_value
    
    # Set up return value for process_missing_entities
    mock_cleaner_instance.process_missing_entities.return_value = [
        {"uri": "http://example.org/missing1", "references": [{"subject": "s1", "predicate": "p1"}], "success": True}
    ]
    
    # Call the function
    endpoint = "http://example.org/sparql"
    is_virtuoso = True
    results = clean_missing_entities(endpoint=endpoint, is_virtuoso=is_virtuoso)
    
    # Verify MissingEntityCleaner was created with the correct endpoint and is_virtuoso flag
    mock_cleaner_class.assert_called_once_with(endpoint=endpoint, is_virtuoso=is_virtuoso)
    
    # Verify process_missing_entities was called
    mock_cleaner_instance.process_missing_entities.assert_called_once()
    
    # Verify the results
    assert len(results) == 1
    assert results[0]["uri"] == "http://example.org/missing1"
    assert results[0]["success"] is True


@patch('heritrace.scripts.clean_missing_entities.importlib.util')
def test_load_config_success(mock_importlib_util):
    """Test successful config loading."""
    # Mock successful config loading
    mock_spec = MagicMock()
    mock_module = MagicMock()
    mock_importlib_util.spec_from_file_location.return_value = mock_spec
    mock_importlib_util.module_from_spec.return_value = mock_module
    
    # Call the function
    config = load_config("config.py")
    
    # Verify the result
    assert config == mock_module
    
    # Verify the calls
    mock_importlib_util.spec_from_file_location.assert_called_once_with("config", "config.py")
    mock_importlib_util.module_from_spec.assert_called_once_with(mock_spec)
    mock_spec.loader.exec_module.assert_called_once_with(mock_module)


@patch('heritrace.scripts.clean_missing_entities.importlib.util')
@patch('heritrace.scripts.clean_missing_entities.logging.error')
@patch('heritrace.scripts.clean_missing_entities.sys.exit')
def test_load_config_error(mock_exit, mock_logging_error, mock_importlib_util):
    """Test config loading with an error."""
    # Mock error during config loading
    mock_importlib_util.spec_from_file_location.side_effect = Exception("Config error")
    
    # Call the function
    load_config("config.py")
    
    # Verify error was logged and sys.exit was called
    mock_logging_error.assert_called_once()
    error_msg = mock_logging_error.call_args[0][0]
    assert "Error loading configuration file" in error_msg
    mock_exit.assert_called_once_with(1)


@patch('heritrace.scripts.clean_missing_entities.argparse.ArgumentParser')
@patch('heritrace.scripts.clean_missing_entities.load_config')
@patch('heritrace.scripts.clean_missing_entities.clean_missing_entities')
@patch('heritrace.scripts.clean_missing_entities.logging')
def test_main_success(mock_logging, mock_clean_missing_entities, mock_load_config, mock_argparse):
    """Test main function with successful execution."""
    # Set up mock argument parser
    mock_args = MagicMock()
    mock_args.config = "config.py"
    mock_args.verbose = False
    mock_parser = mock_argparse.return_value
    mock_parser.parse_args.return_value = mock_args
    
    # Set up mock config
    mock_config = MagicMock()
    mock_config.Config.DATASET_DB_URL = "http://test.endpoint/sparql"
    mock_config.Config.DATASET_DB_TRIPLESTORE = "virtuoso"
    mock_load_config.return_value = mock_config
    
    # Set up mock clean_missing_entities
    mock_clean_missing_entities.return_value = [
        {"uri": "http://example.org/missing1", "references": [], "success": True}
    ]
    
    # Call main
    result = main()
    
    # Verify load_config was called with correct args
    mock_load_config.assert_called_once_with("config.py")
    
    # Verify clean_missing_entities was called with correct args
    mock_clean_missing_entities.assert_called_once_with(
        endpoint="http://test.endpoint/sparql", 
        is_virtuoso=True
    )
    
    # Verify result
    assert result == 0
    
    # Verify logging was set up
    mock_logging.basicConfig.assert_called_once()
    
    # Verify config was loaded
    mock_load_config.assert_called_once_with("config.py")
    
    # Verify clean_missing_entities was called with the correct endpoint
    mock_clean_missing_entities.assert_called_once_with(endpoint="http://test.endpoint/sparql", is_virtuoso=True)


@patch('heritrace.scripts.clean_missing_entities.argparse.ArgumentParser')
@patch('heritrace.scripts.clean_missing_entities.load_config')
@patch('heritrace.scripts.clean_missing_entities.clean_missing_entities')
@patch('heritrace.scripts.clean_missing_entities.logging')
def test_main_failure(mock_logging, mock_clean_missing_entities, mock_load_config, mock_argparse):
    """Test main function with missing entity cleanup failure."""
    # Mock argument parsing
    mock_args = MagicMock()
    mock_args.config = "config.py"
    mock_args.verbose = False
    mock_argparse.return_value.parse_args.return_value = mock_args
    
    # Mock config
    mock_config = MagicMock()
    mock_config.Config.DATASET_DB_URL = "http://example.org/sparql"
    mock_load_config.return_value = mock_config
    
    # Mock failed missing entity cleanup with list of dictionaries
    mock_clean_missing_entities.return_value = [
        {
            "uri": "http://example.org/missing1",
            "references": [{"subject": "http://example.org/entity1", "predicate": "http://example.org/references"}],
            "success": False
        }
    ]
    
    # Call the function
    result = main()
    
    # Verify the result
    assert result == 1
    
    # Verify error was logged
    mock_logging.error.assert_called_once()
    error_msg = mock_logging.error.call_args[0][0]
    assert "Failed to clean up some missing entity references from the dataset" in error_msg


@patch('heritrace.scripts.clean_missing_entities.argparse.ArgumentParser')
@patch('heritrace.scripts.clean_missing_entities.load_config')
@patch('heritrace.scripts.clean_missing_entities.logging.error')
@patch('heritrace.scripts.clean_missing_entities.hasattr')
def test_main_missing_dataset_db_url(mock_hasattr, mock_logging_error, mock_load_config, mock_argparse):
    """Test main function with missing DATASET_DB_URL in config."""
    # Mock argument parsing
    mock_args = MagicMock()
    mock_args.config = "config.py"
    mock_args.verbose = False
    mock_argparse.return_value.parse_args.return_value = mock_args
    
    # Mock config
    mock_config = MagicMock()
    mock_load_config.return_value = mock_config
    
    # Mock hasattr to return False for DATASET_DB_URL
    def mock_hasattr_func(obj, name):
        if name == "Config":
            return True
        if name == "DATASET_DB_URL":
            return False
        return True
    
    mock_hasattr.side_effect = mock_hasattr_func
    
    # Call the function
    result = main()
    
    # Verify the result
    assert result == 1
    
    # Verify error was logged
    mock_logging_error.assert_called_once()
    error_msg = mock_logging_error.call_args[0][0]
    assert "Config class must define DATASET_DB_URL" in error_msg


@patch('heritrace.scripts.clean_missing_entities.argparse.ArgumentParser')
@patch('heritrace.scripts.clean_missing_entities.load_config')
@patch('heritrace.scripts.clean_missing_entities.clean_missing_entities')
@patch('heritrace.scripts.clean_missing_entities.logging')
def test_main_no_missing_entities(mock_logging, mock_clean_missing_entities, mock_load_config, mock_argparse):
    """Test main function when no missing entities are found."""
    # Mock argument parsing
    mock_args = MagicMock()
    mock_args.config = "config.py"
    mock_args.verbose = False
    mock_argparse.return_value.parse_args.return_value = mock_args
    
    # Mock config
    mock_config = MagicMock()
    mock_config.Config.DATASET_DB_URL = "http://example.org/sparql"
    # Set DATASET_DB_TRIPLESTORE for is_virtuoso check (optional, but good practice)
    mock_config.Config.DATASET_DB_TRIPLESTORE = "other"  
    mock_load_config.return_value = mock_config
    
    # Mock clean_missing_entities returning an empty list
    mock_clean_missing_entities.return_value = []
    
    # Call the function
    result = main()
    
    # Verify the result is 0
    assert result == 0
    
    # Verify the specific info log message was called
    mock_logging.info.assert_any_call("No missing entity references found")

    # Verify clean_missing_entities was called
    mock_clean_missing_entities.assert_called_once_with(
        endpoint="http://example.org/sparql", 
        is_virtuoso=False  # Based on "other" triplestore type
    ) 