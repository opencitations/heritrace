#!/usr/bin/env python3

import argparse
import importlib.util
import logging
import sys
from typing import Union
from urllib.parse import urlparse

from heritrace.extensions import SPARQLWrapperWithRetry
from heritrace.utils.converters import convert_to_datetime
from rdflib import URIRef
from rdflib_ocdm.counter_handler.counter_handler import CounterHandler
from SPARQLWrapper import JSON


class ProvenanceResetter:
    """
    A class to reset the provenance of a specific entity by deleting all snapshots
    after snapshot 1 and resetting the provenance counters.
    """

    def __init__(
        self,
        provenance_endpoint: str,
        counter_handler: CounterHandler,
    ):
        """
        Initialize the ProvenanceResetter.

        Args:
            provenance_endpoint: The SPARQL endpoint for the provenance database
            counter_handler: An instance of a CounterHandler to manage provenance counters
        """
        self.provenance_endpoint = provenance_endpoint
        self.provenance_sparql = SPARQLWrapperWithRetry(provenance_endpoint)
        self.provenance_sparql.setReturnFormat(JSON)
        self.counter_handler = counter_handler
        self.logger = logging.getLogger(__name__)

    def reset_entity_provenance(self, entity_uri: Union[str, URIRef]) -> bool:
        """
        Reset the provenance of a specific entity by deleting all snapshots
        after snapshot 1, removing the invalidatedAtTime property from the first snapshot,
        and resetting the provenance counters.

        Args:
            entity_uri: The URI of the entity to reset

        Returns:
            bool: True if the operation was successful, False otherwise
        """
        if not isinstance(entity_uri, URIRef):
            entity_uri = URIRef(entity_uri)

        # Step 1: Find all snapshots for the entity
        snapshots = self._get_entity_snapshots(entity_uri)
        if not snapshots:
            self.logger.warning(f"No snapshots found for entity {entity_uri}")
            return False

        # Sort snapshots by generation time, converting strings to datetime objects
        sorted_snapshots = sorted(
            snapshots, key=lambda x: convert_to_datetime(x["generation_time"])
        )

        # Keep only the first snapshot
        first_snapshot = sorted_snapshots[0]
        snapshots_to_delete = sorted_snapshots[1:]

        if not snapshots_to_delete:
            self.logger.info(f"Entity {entity_uri} has only one snapshot, nothing to reset")
            # Still remove invalidatedAtTime from the first snapshot
            self._remove_invalidated_time(first_snapshot)
            return True

        # Step 2: Delete all snapshots after the first one
        success = self._delete_snapshots(snapshots_to_delete)
        if not success:
            return False

        # Step 3: Reset the provenance counter for this entity
        self._reset_provenance_counter(entity_uri)

        # Step 4: Remove invalidatedAtTime from the first snapshot
        self._remove_invalidated_time(first_snapshot)

        self.logger.info(f"Successfully reset provenance for entity {entity_uri}")
        return True

    def _get_entity_snapshots(self, entity_uri: URIRef) -> list:
        """
        Get all snapshots for a specific entity.

        Args:
            entity_uri: The URI of the entity

        Returns:
            list: A list of dictionaries containing snapshot information
        """
        query = f"""
        PREFIX prov: <http://www.w3.org/ns/prov#>
        
        SELECT ?snapshot ?generation_time
        WHERE {{
            GRAPH ?g {{
                ?snapshot prov:specializationOf <{entity_uri}> ;
                         prov:generatedAtTime ?generation_time .
            }}
        }}
        ORDER BY ?generation_time
        """
        
        self.provenance_sparql.setQuery(query)
        results = self.provenance_sparql.queryAndConvert()
        
        snapshots = []
        for binding in results["results"]["bindings"]:
            snapshots.append({
                "uri": binding["snapshot"]["value"],
                "generation_time": binding["generation_time"]["value"]
            })
            
        return snapshots

    def _delete_snapshots(self, snapshots: list) -> bool:
        """
        Delete a list of snapshots from the provenance database.

        Args:
            snapshots: A list of snapshot dictionaries to delete

        Returns:
            bool: True if the operation was successful, False otherwise
        """
        if not snapshots:
            return True
            
        # Virtuoso has limitations with DELETE WHERE queries
        # We need to delete each snapshot individually
        success = True
        for snapshot in snapshots:
            snapshot_uri = snapshot['uri']
            
            # Construct the graph name based on the snapshot URI
            # The graph name follows the pattern: snapshot_uri/prov/
            graph_uri = f"{snapshot_uri.split('/prov/se/')[0]}/prov/"
            
            # Delete all triples where the snapshot is the subject
            query = f"""
            PREFIX prov: <http://www.w3.org/ns/prov#>
            
            DELETE {{
                GRAPH <{graph_uri}> {{
                    <{snapshot_uri}> ?p ?o .
                }}
            }}
            WHERE {{
                GRAPH <{graph_uri}> {{
                    <{snapshot_uri}> ?p ?o .
                }}
            }}
            """
            
            try:
                self.provenance_sparql.setQuery(query)
                self.provenance_sparql.method = "POST"
                self.provenance_sparql.query()
                
                # Also delete triples where the snapshot is the object
                query = f"""
                PREFIX prov: <http://www.w3.org/ns/prov#>
                
                DELETE {{
                    GRAPH <{graph_uri}> {{
                        ?s ?p <{snapshot_uri}> .
                    }}
                }}
                WHERE {{
                    GRAPH <{graph_uri}> {{
                        ?s ?p <{snapshot_uri}> .
                    }}
                }}
                """
                
                self.provenance_sparql.setQuery(query)
                self.provenance_sparql.query()
                
                self.logger.debug(f"Successfully deleted snapshot: {snapshot_uri} from graph: {graph_uri}")
            except Exception as e:
                self.logger.error(f"Error deleting snapshot {snapshot_uri}: {e}")
                success = False
                
        return success

    def _reset_provenance_counter(self, entity_uri: URIRef) -> None:
        """
        Reset the provenance counter for a specific entity to 1.

        Args:
            entity_uri: The URI of the entity
        """
        # Extract the entity name from the URI
        parsed_uri = urlparse(str(entity_uri))
        entity_name = parsed_uri.path.split('/')[-1]
        
        # Set the counter to 1 (for the first snapshot)
        self.counter_handler.set_counter(1, entity_name)
        self.logger.info(f"Reset provenance counter for entity {entity_uri} to 1")

    def _remove_invalidated_time(self, snapshot: dict) -> bool:
        """
        Remove the invalidatedAtTime property from a snapshot.

        Args:
            snapshot: A dictionary containing snapshot information

        Returns:
            bool: True if the operation was successful, False otherwise
        """
        snapshot_uri = snapshot['uri']
        
        # Construct the graph name based on the snapshot URI
        graph_uri = f"{snapshot_uri.split('/prov/se/')[0]}/prov/"
        
        # Delete the invalidatedAtTime property
        query = f"""
        PREFIX prov: <http://www.w3.org/ns/prov#>
        
        DELETE {{
            GRAPH <{graph_uri}> {{
                <{snapshot_uri}> prov:invalidatedAtTime ?time .
            }}
        }}
        WHERE {{
            GRAPH <{graph_uri}> {{
                <{snapshot_uri}> prov:invalidatedAtTime ?time .
            }}
        }}
        """
        
        try:
            self.provenance_sparql.setQuery(query)
            self.provenance_sparql.method = "POST"
            self.provenance_sparql.query()
            self.logger.info(f"Successfully removed invalidatedAtTime from snapshot: {snapshot_uri}")
            return True
        except Exception as e:
            self.logger.error(f"Error removing invalidatedAtTime from snapshot {snapshot_uri}: {e}")
            return False


def reset_entity_provenance(
    entity_uri: str,
    provenance_endpoint: str,
    counter_handler: CounterHandler,
) -> bool:
    """
    Reset the provenance of a specific entity by deleting all snapshots
    after snapshot 1, removing the invalidatedAtTime property from the first snapshot,
    and resetting the provenance counters.

    Args:
        entity_uri: The URI of the entity to reset
        provenance_endpoint: The SPARQL endpoint for the provenance database
        counter_handler: An instance of a CounterHandler to manage provenance counters

    Returns:
        bool: True if the operation was successful, False otherwise
    """
    resetter = ProvenanceResetter(
        provenance_endpoint=provenance_endpoint,
        counter_handler=counter_handler,
    )
    
    return resetter.reset_entity_provenance(entity_uri)


def load_config(config_path):
    """
    Load configuration from a Python file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        module: The loaded configuration module
    """
    try:
        spec = importlib.util.spec_from_file_location("config", config_path)
        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)
        return config
    except Exception as e:
        logging.error(f"Error loading configuration file: {e}")
        sys.exit(1)


def main():
    """Main entry point for the script when run from the command line."""
    parser = argparse.ArgumentParser(description="Reset the provenance of a specific entity")
    parser.add_argument("entity_uri", help="URI of the entity to reset")
    parser.add_argument("--config", "-c", required=True, help="Path to the configuration file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Load configuration
    config = load_config(args.config)
    
    # Check if Config class exists
    if not hasattr(config, "Config"):
        logging.error("Configuration file must define a Config class")
        return 1
    
    # Get required configuration from Config class
    if not hasattr(config.Config, "PROVENANCE_DB_URL"):
        logging.error("Config class must define PROVENANCE_DB_URL")
        return 1
    
    provenance_endpoint = config.Config.PROVENANCE_DB_URL
    
    # Get counter handler from Config class
    if not hasattr(config.Config, "COUNTER_HANDLER"):
        logging.error("Config class must define COUNTER_HANDLER")
        return 1
    
    counter_handler = config.Config.COUNTER_HANDLER
    
    success = reset_entity_provenance(
        entity_uri=args.entity_uri,
        provenance_endpoint=provenance_endpoint,
        counter_handler=counter_handler
    )
    
    if success:
        logging.info(f"Successfully reset provenance for entity {args.entity_uri}")
        return 0
    else:
        logging.error(f"Failed to reset provenance for entity {args.entity_uri}")
        return 1


if __name__ == "__main__": # pragma: no cover
    sys.exit(main())