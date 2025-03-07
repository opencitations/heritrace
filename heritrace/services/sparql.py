"""
SPARQL service for Heritrace.

This module provides a service for executing SPARQL queries against a triplestore.
"""

import time
import random
import logging
from typing import Dict, Any, Callable, TypeVar

from SPARQLWrapper import SPARQLWrapper, JSON

# Type variable for generic return type
T = TypeVar('T')

# Configure logging
logger = logging.getLogger(__name__)


class SparqlService:
    """Service for executing SPARQL queries against a triplestore with retry capabilities."""

    def __init__(self, endpoint_url: str, max_retries: int = 3, 
                 base_delay: float = 1.0, max_delay: float = 5.0, 
                 jitter: bool = True):
        """
        Initialize the SPARQL service with retry parameters.

        Args:
            endpoint_url: URL of the SPARQL endpoint
            max_retries: Maximum number of retry attempts (default: 3)
            base_delay: Initial delay between retries in seconds (default: 1.0)
            max_delay: Maximum delay between retries in seconds (default: 30.0)
            jitter: Whether to add randomness to the delay (default: True)
        """
        self.endpoint_url = endpoint_url
        self.sparql = SPARQLWrapper(endpoint_url)
        self.sparql.setReturnFormat(JSON)
        
        # Retry configuration
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter

    def _retry_with_backoff(self, operation: Callable[[], T], 
                           error_message: str) -> T:
        """
        Execute an operation with exponential backoff retry logic.

        Args:
            operation: Function to execute
            error_message: Message to log on error

        Returns:
            Result of the operation

        Raises:
            Exception: If all retry attempts fail
        """
        retries = 0

        while retries <= self.max_retries:
            try:
                return operation()
            except Exception as e:
                retries += 1
                
                if retries > self.max_retries:
                    logger.error(f"{error_message}: {str(e)}. Max retries exceeded.")
                    raise
                
                # Calculate delay with exponential backoff
                delay = min(self.max_delay, self.base_delay * (2 ** (retries - 1)))
                
                # Add jitter if enabled (between 75% and 100% of delay)
                if self.jitter:
                    delay = delay * (0.75 + random.random() * 0.25)
                
                time.sleep(delay)


    def query(self, query_string: str) -> Dict[str, Any]:
        """
        Execute a SPARQL query and return the results with retry capability.

        Args:
            query_string: SPARQL query string to execute

        Returns:
            Dict containing the query results in JSON format
        """
        def _execute_query():
            self.sparql.setQuery(query_string)
            return self.sparql.query().convert()
        
        return self._retry_with_backoff(
            _execute_query, 
            f"Error executing SPARQL query on endpoint {self.endpoint_url}"
        )

    def update(self, update_string: str) -> None:
        """
        Execute a SPARQL update query with retry capability.

        Args:
            update_string: SPARQL update query string to execute
        """
        def _execute_update():
            self.sparql.setQuery(update_string)
            self.sparql.method = 'POST'
            result = self.sparql.query()
            self.sparql.method = 'GET'  # Reset to default
            return result
        
        self._retry_with_backoff(
            _execute_update,
            f"Error executing SPARQL update on endpoint {self.endpoint_url}"
        )

    def get_linked_resources(self, resource_uri: str) -> list:
        """
        Get all resources linked to the given resource.
        This includes both resources that this resource links to,
        and resources that link to this resource.
        Only returns valid entities that have at least one predicate and object.
        
        Args:
            resource_uri: URI of the resource to check
            
        Returns:
            List of URIs of linked resources that are valid entities
        """
        candidate_resources = set()
        
        # Get resources that this resource links to (outgoing links)
        query_outgoing = f"""
        SELECT DISTINCT ?o
        WHERE {{
            <{resource_uri}> ?p ?o .
            FILTER(isIRI(?o))
        }}
        """
        
        # Get resources that link to this resource (incoming links)
        query_incoming = f"""
        SELECT DISTINCT ?s
        WHERE {{
            ?s ?p <{resource_uri}> .
        }}
        """
        
        try:
            # Execute outgoing links query with retry capability
            results_outgoing = self.query(query_outgoing)
            for row in results_outgoing["results"]["bindings"]:
                linked_uri = row["o"]["value"]
                candidate_resources.add(linked_uri)
                
            # Execute incoming links query with retry capability
            results_incoming = self.query(query_incoming)
            for row in results_incoming["results"]["bindings"]:
                linked_uri = row["s"]["value"]
                candidate_resources.add(linked_uri)
            
            # Filter to keep only valid entities (with at least one predicate and object)
            valid_entities = []
            for uri in candidate_resources:
                # Query to check if the URI has at least one predicate and object
                validation_query = f"""
                ASK {{
                    <{uri}> ?p ?o .
                }}
                """
                
                try:
                    result = self.query(validation_query)
                    if result.get("boolean", False):
                        valid_entities.append(uri)
                except Exception as e:
                    logger.warning(f"Error validating entity {uri}: {str(e)}")
                    # Skip this URI if validation fails
                    continue
                
            return valid_entities
        except Exception as e:
            logger.error(f"Error getting linked resources for {resource_uri}: {str(e)}")
            return []