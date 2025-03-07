"""
Tests for the SPARQL service module.
"""

import random
import time
from unittest.mock import MagicMock, patch, call

import pytest
from SPARQLWrapper import JSON

from heritrace.services.sparql import SparqlService


class TestSparqlService:
    """Tests for the SparqlService class."""

    def test_init(self):
        """Test initialization of the SparqlService."""
        endpoint_url = "http://example.org/sparql"
        service = SparqlService(endpoint_url)

        assert service.endpoint_url == endpoint_url
        assert service.sparql.endpoint == endpoint_url
        assert service.sparql.returnFormat == JSON
        assert service.max_retries == 3
        assert service.base_delay == 1.0
        assert service.max_delay == 5.0
        assert service.jitter is True

    def test_init_with_custom_params(self):
        """Test initialization of the SparqlService with custom parameters."""
        endpoint_url = "http://example.org/sparql"
        service = SparqlService(
            endpoint_url, max_retries=5, base_delay=2.0, max_delay=10.0, jitter=False
        )

        assert service.endpoint_url == endpoint_url
        assert service.sparql.endpoint == endpoint_url
        assert service.sparql.returnFormat == JSON
        assert service.max_retries == 5
        assert service.base_delay == 2.0
        assert service.max_delay == 10.0
        assert service.jitter is False

    @patch("time.sleep")
    def test_retry_with_backoff_success_first_try(self, mock_sleep):
        """Test _retry_with_backoff when operation succeeds on first try."""
        service = SparqlService("http://example.org/sparql")
        operation = MagicMock(return_value="success")
        
        result = service._retry_with_backoff(operation, "Error message")
        
        assert result == "success"
        operation.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("time.sleep")
    def test_retry_with_backoff_success_after_retry(self, mock_sleep):
        """Test _retry_with_backoff when operation succeeds after retry."""
        service = SparqlService("http://example.org/sparql")
        
        # Operation fails once, then succeeds
        operation = MagicMock(side_effect=[Exception("Test error"), "success"])
        
        result = service._retry_with_backoff(operation, "Error message")
        
        assert result == "success"
        assert operation.call_count == 2
        mock_sleep.assert_called_once()

    @patch("time.sleep")
    @patch("random.random", return_value=0.5)
    def test_retry_with_backoff_with_jitter(self, mock_random, mock_sleep):
        """Test _retry_with_backoff with jitter enabled."""
        service = SparqlService("http://example.org/sparql", jitter=True)
        
        # Operation fails twice, then succeeds
        operation = MagicMock(side_effect=[
            Exception("Test error 1"), 
            Exception("Test error 2"),
            "success"
        ])
        
        result = service._retry_with_backoff(operation, "Error message")
        
        assert result == "success"
        assert operation.call_count == 3
        assert mock_sleep.call_count == 2
        
        # First delay should be base_delay * (0.75 + 0.5 * 0.25) = 1.0 * 0.875 = 0.875
        # Second delay should be min(max_delay, base_delay * 2^1) * (0.75 + 0.5 * 0.25) = 2.0 * 0.875 = 1.75
        mock_sleep.assert_has_calls([call(0.875), call(1.75)])

    @patch("time.sleep")
    def test_retry_with_backoff_without_jitter(self, mock_sleep):
        """Test _retry_with_backoff with jitter disabled."""
        service = SparqlService("http://example.org/sparql", jitter=False)
        
        # Operation fails twice, then succeeds
        operation = MagicMock(side_effect=[
            Exception("Test error 1"), 
            Exception("Test error 2"),
            "success"
        ])
        
        result = service._retry_with_backoff(operation, "Error message")
        
        assert result == "success"
        assert operation.call_count == 3
        assert mock_sleep.call_count == 2
        
        # First delay should be base_delay = 1.0
        # Second delay should be min(max_delay, base_delay * 2^1) = 2.0
        mock_sleep.assert_has_calls([call(1.0), call(2.0)])

    @patch("time.sleep")
    def test_retry_with_backoff_max_retries_exceeded(self, mock_sleep):
        """Test _retry_with_backoff when max retries are exceeded."""
        service = SparqlService("http://example.org/sparql", max_retries=2)
        
        # Operation always fails
        operation = MagicMock(side_effect=Exception("Test error"))
        
        with pytest.raises(Exception, match="Test error"):
            service._retry_with_backoff(operation, "Error message")
        
        assert operation.call_count == 3  # Initial try + 2 retries
        assert mock_sleep.call_count == 2

    @patch("time.sleep")
    def test_retry_with_backoff_max_delay_cap(self, mock_sleep):
        """Test _retry_with_backoff with max delay cap."""
        service = SparqlService(
            "http://example.org/sparql", 
            max_retries=3, 
            base_delay=2.0, 
            max_delay=3.0,
            jitter=False
        )
        
        # Operation fails three times, then succeeds
        operation = MagicMock(side_effect=[
            Exception("Test error 1"), 
            Exception("Test error 2"),
            Exception("Test error 3"),
            "success"
        ])
        
        result = service._retry_with_backoff(operation, "Error message")
        
        assert result == "success"
        assert operation.call_count == 4
        assert mock_sleep.call_count == 3
        
        # First delay should be base_delay = 2.0
        # Second delay should be min(max_delay, base_delay * 2^1) = min(3.0, 4.0) = 3.0
        # Third delay should be min(max_delay, base_delay * 2^2) = min(3.0, 8.0) = 3.0
        mock_sleep.assert_has_calls([call(2.0), call(3.0), call(3.0)])

    def test_query_success(self):
        """Test successful query execution."""
        service = SparqlService("http://example.org/sparql")
        
        # Mock the SPARQLWrapper instance
        mock_sparql = MagicMock()
        service.sparql = mock_sparql
        
        # Configure the mock to return a valid response
        expected_result = {"results": {"bindings": []}}
        mock_sparql.query.return_value.convert.return_value = expected_result
        
        # Execute the query
        query_string = "SELECT * WHERE { ?s ?p ?o }"
        result = service.query(query_string)
        
        # Verify the result
        assert result == expected_result
        mock_sparql.setQuery.assert_called_once_with(query_string)
        mock_sparql.query.assert_called_once()

    @patch("time.sleep")
    def test_query_with_retry(self, mock_sleep):
        """Test query execution with retry."""
        service = SparqlService("http://example.org/sparql")
        
        # Mock the SPARQLWrapper instance
        mock_sparql = MagicMock()
        service.sparql = mock_sparql
        
        # Configure the mock to fail once, then succeed
        expected_result = {"results": {"bindings": []}}
        mock_sparql.query.side_effect = [
            Exception("Connection error"),
            MagicMock(convert=MagicMock(return_value=expected_result))
        ]
        
        # Execute the query
        query_string = "SELECT * WHERE { ?s ?p ?o }"
        result = service.query(query_string)
        
        # Verify the result
        assert result == expected_result
        assert mock_sparql.setQuery.call_count == 2
        assert mock_sparql.query.call_count == 2
        mock_sleep.assert_called_once()

    def test_update_success(self):
        """Test successful update execution."""
        service = SparqlService("http://example.org/sparql")
        
        # Mock the SPARQLWrapper instance
        mock_sparql = MagicMock()
        service.sparql = mock_sparql
        
        # Execute the update
        update_string = "INSERT DATA { <http://example.org/s> <http://example.org/p> <http://example.org/o> }"
        service.update(update_string)
        
        # Verify the method calls
        mock_sparql.setQuery.assert_called_once_with(update_string)
        assert mock_sparql.method == 'GET'  # Should be reset to GET after update
        mock_sparql.query.assert_called_once()

    @patch("time.sleep")
    def test_update_with_retry(self, mock_sleep):
        """Test update execution with retry."""
        service = SparqlService("http://example.org/sparql")
        
        # Mock the SPARQLWrapper instance
        mock_sparql = MagicMock()
        service.sparql = mock_sparql
        
        # Configure the mock to fail once, then succeed
        mock_sparql.query.side_effect = [
            Exception("Connection error"),
            MagicMock()
        ]
        
        # Execute the update
        update_string = "INSERT DATA { <http://example.org/s> <http://example.org/p> <http://example.org/o> }"
        service.update(update_string)
        
        # Verify the method calls
        assert mock_sparql.setQuery.call_count == 2
        assert mock_sparql.query.call_count == 2
        assert mock_sparql.method == 'GET'  # Should be reset to GET after update
        mock_sleep.assert_called_once()

    def test_get_linked_resources_success(self):
        """Test successful retrieval of linked resources."""
        service = SparqlService("http://example.org/sparql")
        
        # Mock the query method
        with patch.object(service, 'query') as mock_query:
            # Configure mock for outgoing links query
            mock_query.side_effect = [
                # Outgoing links result
                {
                    "results": {
                        "bindings": [
                            {"o": {"value": "http://example.org/resource1"}},
                            {"o": {"value": "http://example.org/resource2"}}
                        ]
                    }
                },
                # Incoming links result
                {
                    "results": {
                        "bindings": [
                            {"s": {"value": "http://example.org/resource2"}},
                            {"s": {"value": "http://example.org/resource3"}}
                        ]
                    }
                },
                # Validation for resource1 - valid
                {"boolean": True},
                # Validation for resource2 - valid
                {"boolean": True},
                # Validation for resource3 - valid
                {"boolean": True}
            ]
            
            # Execute the method
            resource_uri = "http://example.org/target"
            result = service.get_linked_resources(resource_uri)
            
            # Verify the result
            assert set(result) == {
                "http://example.org/resource1",
                "http://example.org/resource2",
                "http://example.org/resource3"
            }
            
            # Verify the queries
            assert mock_query.call_count == 5

    def test_get_linked_resources_with_invalid_entities(self):
        """Test retrieval of linked resources with some invalid entities."""
        service = SparqlService("http://example.org/sparql")
        
        # Use a dictionary to map URIs to their validation results
        validation_results = {
            "http://example.org/resource1": {"boolean": False},  # Invalid
            "http://example.org/resource2": {"boolean": True},   # Valid
            "http://example.org/resource3": {"boolean": True}    # Valid
        }
        
        # Mock the query method with a custom side effect function
        def query_side_effect(query_string):
            if "SELECT DISTINCT ?o" in query_string:
                return {
                    "results": {
                        "bindings": [
                            {"o": {"value": "http://example.org/resource1"}},
                            {"o": {"value": "http://example.org/resource2"}}
                        ]
                    }
                }
            elif "SELECT DISTINCT ?s" in query_string:
                return {
                    "results": {
                        "bindings": [
                            {"s": {"value": "http://example.org/resource3"}}
                        ]
                    }
                }
            elif "ASK" in query_string:
                # Extract the URI from the query
                uri = query_string.split('<')[1].split('>')[0]
                # Return the appropriate validation result
                return validation_results.get(uri, {"boolean": False})
            
            return {}
        
        with patch.object(service, 'query', side_effect=query_side_effect):
            # Execute the method
            resource_uri = "http://example.org/target"
            result = service.get_linked_resources(resource_uri)
            
            # Verify the result - resource1 should be excluded since boolean: False
            # The implementation only adds resources to valid_entities if boolean is True
            assert set(result) == {
                "http://example.org/resource2",
                "http://example.org/resource3"
            }

    def test_get_linked_resources_with_validation_error(self):
        """Test retrieval of linked resources with a validation error."""
        service = SparqlService("http://example.org/sparql")
        
        # Define which URI should raise an exception during validation
        error_uri = "http://example.org/resource2"
        
        # Mock the query method with a custom side effect function
        def query_side_effect(query_string):
            if "SELECT DISTINCT ?o" in query_string:
                return {
                    "results": {
                        "bindings": [
                            {"o": {"value": "http://example.org/resource1"}},
                            {"o": {"value": "http://example.org/resource2"}}
                        ]
                    }
                }
            elif "SELECT DISTINCT ?s" in query_string:
                return {
                    "results": {
                        "bindings": [
                            {"s": {"value": "http://example.org/resource3"}}
                        ]
                    }
                }
            elif "ASK" in query_string:
                # Extract the URI from the query
                uri = query_string.split('<')[1].split('>')[0]
                # Raise an exception for the specified URI
                if uri == error_uri:
                    raise Exception("Validation error")
                # Return valid for other URIs
                return {"boolean": True}
            
            return {}
        
        with patch.object(service, 'query', side_effect=query_side_effect):
            # Execute the method
            resource_uri = "http://example.org/target"
            result = service.get_linked_resources(resource_uri)
            
            # Verify the result - resource2 should be excluded due to validation error
            # The implementation skips URIs when validation raises an exception
            assert set(result) == {
                "http://example.org/resource1",
                "http://example.org/resource3"
            }

    def test_get_linked_resources_with_query_error(self):
        """Test retrieval of linked resources with a query error."""
        service = SparqlService("http://example.org/sparql")
        
        # Mock the query method to raise an exception
        with patch.object(service, 'query', side_effect=Exception("Query error")):
            # Execute the method
            resource_uri = "http://example.org/target"
            result = service.get_linked_resources(resource_uri)
            
            # Verify the result - should be empty due to error
            assert result == []
    
    def test_retry_with_backoff_unreachable_code(self):
        """Test the unreachable code path in _retry_with_backoff."""
        service = SparqlService("http://example.org/sparql", max_retries=0)
        
        # Create a test exception
        test_exception = ValueError("Test exception")
        
        # Create a custom operation that manipulates the service to force the unreachable code path
        def operation():
            # Set retries to -1 to bypass the while loop condition
            service.max_retries = -1
            raise test_exception
        
        # Execute and verify exception is raised
        with pytest.raises(ValueError) as context:
            service._retry_with_backoff(operation, "Error message")
        
        # Verify it's the same exception
        assert str(context.value) == "Test exception"
