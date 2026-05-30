#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import argparse
import importlib.util
import logging
import sys
import types
from typing import TypedDict

from SPARQLWrapper import JSON

from heritrace.sparql import SPARQLWrapperWithRetry, get_sparql_bindings
from heritrace.utils.sparql_utils import VIRTUOSO_EXCLUDED_GRAPHS

logger = logging.getLogger(__name__)


class MissingEntityResult(TypedDict):
    uri: str
    references: list[dict[str, str]]
    success: bool


class MissingEntityCleaner:
    """
    A class to detect and clean up references to missing entities from the dataset.

    Missing entities are URIs that are referenced by triples but don't actually exist
    in the dataset (they have no triples where they are the subject). The script
    identifies
    these missing references and removes all triples that reference them.
    """

    def __init__(self, endpoint: str, *, is_virtuoso: bool = False) -> None:
        """
        Initialize the MissingEntityCleaner.

        Args:
            endpoint: The SPARQL endpoint for the database
            is_virtuoso: Boolean indicating if the endpoint is Virtuoso
        """
        self.endpoint = endpoint
        self.is_virtuoso = is_virtuoso
        self.sparql = SPARQLWrapperWithRetry(endpoint)
        self.sparql.setReturnFormat(JSON)
        self.logger = logging.getLogger(__name__)

    def find_missing_entities_with_references(self) -> dict[str, list[dict[str, str]]]:
        """
        Find missing entity references in the dataset along with their references.

        A missing entity is one that:
        1. Is referenced as an object in at least one triple
        2. Has no triples where it is the subject (completely missing)

        The following are excluded from being considered missing entities:
        - Objects of rdf:type triples (types are not considered entities)
        - Objects of ProWithRole triples
        - Objects of datacite:usesIdentifierScheme triples

        Returns:
            Dictionary mapping missing entity URIs to lists of reference dictionaries
        """
        is_quad_store = self.is_virtuoso

        # Define predicates to exclude
        rdf_type = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
        pro_with_role = "http://purl.org/spar/pro/withRole"
        datacite_uses_identifier_scheme = (
            "http://purl.org/spar/datacite/usesIdentifierScheme"
        )

        # Combine all predicates to exclude
        excluded_predicates = [rdf_type, pro_with_role, datacite_uses_identifier_scheme]

        # Format the excluded predicates for SPARQL
        excluded_predicates_filter = " && ".join(
            [f"?p != <{pred}>" for pred in excluded_predicates]
        )

        if is_quad_store:
            query = f"""
            SELECT DISTINCT ?entity ?s ?p
            WHERE {{
                GRAPH ?g1 {{
                    ?s ?p ?entity .
                    FILTER(isIRI(?entity))
                    FILTER({excluded_predicates_filter})
                }}
                FILTER NOT EXISTS {{
                    GRAPH ?g2 {{
                        ?entity ?anyPredicate ?anyObject .
                    }}
                }}
                FILTER(?g1 NOT IN (<{">, <".join(VIRTUOSO_EXCLUDED_GRAPHS)}>))
            }}
            """
        else:
            query = f"""
            SELECT DISTINCT ?entity ?s ?p
            WHERE {{
                ?s ?p ?entity .
                FILTER(isIRI(?entity))
                FILTER({excluded_predicates_filter})
                FILTER NOT EXISTS {{
                    ?entity ?anyPredicate ?anyObject .
                }}
            }}
            """

        self.sparql.setQuery(query)
        bindings = get_sparql_bindings(self.sparql.queryAndConvert())

        missing_entities: dict[str, list[dict[str, str]]] = {}

        for result in bindings:
            entity_uri = result["entity"]["value"]
            subject = result["s"]["value"]
            predicate = result["p"]["value"]

            if entity_uri not in missing_entities:
                missing_entities[entity_uri] = []

            missing_entities[entity_uri].append(
                {"subject": subject, "predicate": predicate}
            )

        return missing_entities

    def remove_references(
        self, entity_uri: str, references: list[dict[str, str]]
    ) -> bool:
        """
        Remove all references to a missing entity.

        Args:
            entity_uri: The URI of the missing entity
            references: List of references to the missing entity

        Returns:
            bool: True if all references were successfully removed, False otherwise
        """
        success = True

        for reference in references:
            subject = reference["subject"]
            predicate = reference["predicate"]

            is_quad_store = self.is_virtuoso

            if is_quad_store:
                query = f"""
                DELETE {{
                    GRAPH ?g {{
                        <{subject}> <{predicate}> <{entity_uri}> .
                    }}
                }}
                WHERE {{
                    GRAPH ?g {{
                        <{subject}> <{predicate}> <{entity_uri}> .
                    }}
                    FILTER(?g NOT IN (<{">, <".join(VIRTUOSO_EXCLUDED_GRAPHS)}>))
                }}
                """
            else:
                query = f"""
                DELETE {{
                    <{subject}> <{predicate}> <{entity_uri}> .
                }}
                WHERE {{
                    <{subject}> <{predicate}> <{entity_uri}> .
                }}
                """

            try:
                self.sparql.setQuery(query)
                self.sparql.method = "POST"
                self.sparql.query()
                self.logger.info(
                    f"Removed reference from {subject} to {entity_uri} via {predicate}"
                )
            except Exception as e:
                self.logger.error(
                    f"Error removing reference from {subject} to {entity_uri} via {predicate}: {e}"
                )
                success = False

        return success

    def process_missing_entities(self) -> list[MissingEntityResult]:
        """
        Process all missing entity references in the dataset.

        This method:
        1. Finds all missing entity references along with their references
        2. For each missing entity, removes all references to it

        Returns:
            List[Dict]: A list of dictionaries containing results for each missing
            entity processed
            Each dictionary includes:
                - uri: the URI of the missing entity
                - references: list of references that were processed
                - success: boolean indicating if all references were successfully
                removed
        """
        missing_entities_with_refs = self.find_missing_entities_with_references()

        if not missing_entities_with_refs:
            self.logger.info("No missing entity references found.")
            return []

        num_missing_entities = len(missing_entities_with_refs)
        self.logger.info(f"Found {num_missing_entities} missing entity references.")

        total_references = sum(
            len(refs) for refs in missing_entities_with_refs.values()
        )
        results = []

        for entity_uri, references in missing_entities_with_refs.items():
            self.logger.info(f"Processing missing entity: {entity_uri}")

            self.logger.info(
                f"Found {len(references)} references to missing entity {entity_uri}"
            )

            success = self.remove_references(entity_uri, references)

            if not success:
                self.logger.error(
                    f"Failed to remove references to missing entity {entity_uri}"
                )

            results.append(
                {"uri": entity_uri, "references": references, "success": success}
            )

        successful = all(result["success"] for result in results)
        if successful:
            self.logger.info(
                f"Successfully processed all missing"
                f" entities. Found {num_missing_entities} missing entities"
                f" and removed {total_references} references."
            )

        return results


def clean_missing_entities(
    endpoint: str, *, is_virtuoso: bool = False
) -> list[MissingEntityResult]:
    """
    Clean up references to missing entities from the dataset.

    Args:
        endpoint: The SPARQL endpoint for the database
        is_virtuoso: Boolean indicating if the endpoint is Virtuoso

    Returns:
        List[Dict]: Results of processing each missing entity
    """
    cleaner = MissingEntityCleaner(endpoint=endpoint, is_virtuoso=is_virtuoso)
    return cleaner.process_missing_entities()


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
            logging.error("Failed to create module spec from %s", config_path)
            sys.exit(1)
        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)
    except SystemExit:
        raise
    except Exception:
        logging.error(f"Error loading configuration file: {config_path}")
        sys.exit(1)
    else:
        return config


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Detect and clean up references to missing entities from the dataset"
        )
    )
    parser.add_argument(
        "--config", "-c", required=True, help="Path to the configuration file"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    config = load_config(args.config)

    if not hasattr(config.Config, "DATASET_DB_URL"):
        logging.error("Config class must define DATASET_DB_URL")
        return 1

    endpoint = config.Config.DATASET_DB_URL

    is_virtuoso = False
    if hasattr(config.Config, "DATASET_DB_TRIPLESTORE"):
        is_virtuoso = config.Config.DATASET_DB_TRIPLESTORE.lower() == "virtuoso"

    logging.info(
        f"Starting missing entity detection and cleanup using endpoint: {endpoint}"
    )

    results = clean_missing_entities(endpoint=endpoint, is_virtuoso=is_virtuoso)

    successful = all(result["success"] for result in results)
    if not results:
        logging.info("No missing entity references found")
        return 0
    if successful:
        logging.info(
            f"Successfully cleaned up missing entity"
            f" references from the dataset."
            f" Processed {len(results)} missing entities."
        )
        return 0
    logging.error(
        f"Failed to clean up some missing entity"
        f" references from the dataset."
        f" {len([r for r in results if not r['success']])} entities had errors."
    )
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
