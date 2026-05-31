# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import argparse
import importlib.util
import logging
import sys
import types
from datetime import datetime, timezone
from urllib.parse import urlparse

from rdflib import URIRef
from rdflib_ocdm.counter_handler.counter_handler import CounterHandler
from SPARQLWrapper import JSON
from SPARQLWrapper.SPARQLExceptions import SPARQLWrapperException

from heritrace.sparql import SPARQLWrapperWithRetry, get_sparql_bindings
from heritrace.utils.converters import convert_to_datetime

logger = logging.getLogger(__name__)


class ProvenanceResetter:
    """
    A class to reset the provenance of a specific entity by deleting all snapshots
    after snapshot 1 and resetting the provenance counters.
    """

    def __init__(
        self,
        provenance_endpoint: str,
        counter_handler: CounterHandler,
    ) -> None:
        """
        Initialize the ProvenanceResetter.

        Args:
            provenance_endpoint: The SPARQL endpoint for the provenance database
            counter_handler: An instance of a CounterHandler to manage provenance
            counters
        """
        self.provenance_endpoint = provenance_endpoint
        self.provenance_sparql = SPARQLWrapperWithRetry(provenance_endpoint)
        self.provenance_sparql.setReturnFormat(JSON)
        self.counter_handler = counter_handler
        self.logger = logging.getLogger(__name__)

    def reset_entity_provenance(self, entity_uri: URIRef) -> bool:

        # Step 1: Find all snapshots for the entity
        snapshots = self.get_entity_snapshots(entity_uri)
        if not snapshots:
            self.logger.warning("No snapshots found for entity %s", entity_uri)
            return False

        # Sort snapshots by generation time, converting strings to datetime objects
        sorted_snapshots = sorted(
            snapshots,
            key=lambda x: (
                convert_to_datetime(x["generation_time"])
                or datetime.min.replace(tzinfo=timezone.utc)
            ),
        )

        # Keep only the first snapshot
        first_snapshot = sorted_snapshots[0]
        snapshots_to_delete = sorted_snapshots[1:]

        if not snapshots_to_delete:
            self.logger.info(
                "Entity %s has only one snapshot, nothing to reset", entity_uri
            )
            # Still remove invalidatedAtTime from the first snapshot
            self.remove_invalidated_time(first_snapshot)
            return True

        # Step 2: Delete all snapshots after the first one
        success = self.delete_snapshots(snapshots_to_delete)
        if not success:
            return False

        # Step 3: Reset the provenance counter for this entity
        self.reset_provenance_counter(entity_uri)

        # Step 4: Remove invalidatedAtTime from the first snapshot
        self.remove_invalidated_time(first_snapshot)

        self.logger.info("Successfully reset provenance for entity %s", entity_uri)
        return True

    def get_entity_snapshots(self, entity_uri: URIRef) -> list:
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
        bindings = get_sparql_bindings(self.provenance_sparql.queryAndConvert())

        return [
            {
                "uri": binding["snapshot"]["value"],
                "generation_time": binding["generation_time"]["value"],
            }
            for binding in bindings
        ]

    def delete_snapshots(self, snapshots: list) -> bool:
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
            snapshot_uri = snapshot["uri"]

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

                self.logger.debug(
                    "Successfully deleted snapshot: %s from graph: %s",
                    snapshot_uri,
                    graph_uri,
                )
            except SPARQLWrapperException:
                self.logger.exception("Error deleting snapshot %s", snapshot_uri)
                success = False

        return success

    def reset_provenance_counter(self, entity_uri: URIRef) -> None:
        """
        Reset the provenance counter for a specific entity to 1.

        Args:
            entity_uri: The URI of the entity
        """
        # Extract the entity name from the URI
        parsed_uri = urlparse(str(entity_uri))
        entity_name = parsed_uri.path.split("/")[-1]

        # Set the counter to 1 (for the first snapshot)
        self.counter_handler.set_counter(1, entity_name)
        self.logger.info("Reset provenance counter for entity %s to 1", entity_uri)

    def remove_invalidated_time(self, snapshot: dict) -> bool:
        """
        Remove the invalidatedAtTime property from a snapshot.

        Args:
            snapshot: A dictionary containing snapshot information

        Returns:
            bool: True if the operation was successful, False otherwise
        """
        snapshot_uri = snapshot["uri"]

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
            self.logger.info(
                "Successfully removed invalidatedAtTime from snapshot: %s",
                snapshot_uri,
            )
        except SPARQLWrapperException:
            self.logger.exception(
                "Error removing invalidatedAtTime from snapshot %s", snapshot_uri
            )
            return False
        else:
            return True


def reset_entity_provenance(
    entity_uri: URIRef,
    provenance_endpoint: str,
    counter_handler: CounterHandler,
) -> bool:
    resetter = ProvenanceResetter(
        provenance_endpoint=provenance_endpoint,
        counter_handler=counter_handler,
    )

    return resetter.reset_entity_provenance(entity_uri)


def load_config(config_path: str) -> types.ModuleType:
    """
    Load configuration from a Python file.

    Args:
        config_path: Path to the configuration file

    Returns:
        module: The loaded configuration module
    """
    try:
        spec = importlib.util.spec_from_file_location("config", config_path)
        if spec is None or spec.loader is None:
            logger.error("Failed to create module spec from %s", config_path)
            sys.exit(1)
        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)
    except SystemExit:
        raise
    except (FileNotFoundError, ImportError, AttributeError):
        logger.exception("Error loading configuration file: %s", config_path)
        sys.exit(1)
    else:
        return config


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reset the provenance of a specific entity"
    )
    parser.add_argument("entity_uri", help="URI of the entity to reset")
    parser.add_argument(
        "--config", "-c", required=True, help="Path to the configuration file"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Load configuration
    config = load_config(args.config)

    # Check if Config class exists
    if not hasattr(config, "Config"):
        logger.error("Configuration file must define a Config class")
        return 1

    # Get required configuration from Config class
    if not hasattr(config.Config, "PROVENANCE_DB_URL"):
        logger.error("Config class must define PROVENANCE_DB_URL")
        return 1

    provenance_endpoint = config.Config.PROVENANCE_DB_URL

    # Get counter handler from Config class
    if not hasattr(config.Config, "COUNTER_HANDLER"):
        logger.error("Config class must define COUNTER_HANDLER")
        return 1

    counter_handler = config.Config.COUNTER_HANDLER

    success = reset_entity_provenance(
        entity_uri=URIRef(args.entity_uri),
        provenance_endpoint=provenance_endpoint,
        counter_handler=counter_handler,
    )

    if success:
        logger.info("Successfully reset provenance for entity %s", args.entity_uri)
        return 0
    logger.error("Failed to reset provenance for entity %s", args.entity_uri)
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
