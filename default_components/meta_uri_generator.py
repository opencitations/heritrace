# SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import re
from collections import defaultdict

from rdflib import URIRef
from SPARQLWrapper import JSON, SPARQLWrapper

from default_components.meta_entities import (
    META_URI_ENTITY_TYPE_ABBR,
    MetaCounterHandlerProtocol,
)
from heritrace.sparql import get_sparql_bindings
from heritrace.uri_generator.uri_generator import URIGenerator


class InvalidURIFormatError(Exception):
    """Exception raised when an URI has an invalid format."""


def _process_data_bindings(
    bindings: list[dict],
    max_numbers_by_prefix: defaultdict,
    entity_type_abbr: dict[str, str],
    supplier_prefix_regex: str,
) -> None:
    for result in bindings:
        entity_type = result["type"]["value"]
        entity_uri = result["s"]["value"]

        if entity_type in entity_type_abbr:
            try:
                numeric_part = entity_uri.rsplit("/", 1)[-1]
                match = re.search(supplier_prefix_regex, numeric_part)
                if match:
                    supplier_prefix = match.group()
                    number_str = numeric_part[match.end() :]
                    if number_str:
                        number = int(number_str)
                        abbr = entity_type_abbr[entity_type]
                        old_max = max_numbers_by_prefix[supplier_prefix][abbr]
                        max_numbers_by_prefix[supplier_prefix][abbr] = max(
                            old_max, number
                        )
            except (ValueError, IndexError) as err:
                msg = f"Invalid URI format found for entity: {entity_uri}"
                raise InvalidURIFormatError(msg) from err


def _process_prov_bindings(
    bindings: list[dict],
    max_numbers_by_prefix: defaultdict,
    entity_type_abbr: dict[str, str],
    supplier_prefix_regex: str,
) -> None:
    for result in bindings:
        entity_uri = result["entity"]["value"]

        numeric_part = entity_uri.rsplit("/", 1)[-1]
        match = re.search(supplier_prefix_regex, numeric_part)
        if match:
            supplier_prefix = match.group()
            for abbr in set(entity_type_abbr.values()):
                if f"/{abbr}/" in entity_uri:
                    try:
                        number_str = numeric_part[match.end() :]
                        if number_str:
                            number = int(number_str)
                            max_numbers_by_prefix[supplier_prefix][abbr] = max(
                                max_numbers_by_prefix[supplier_prefix][abbr], number
                            )
                    except (ValueError, IndexError) as err:
                        msg = (
                            "Invalid URI format found"
                            f" in provenance for entity: {entity_uri}"
                        )
                        raise InvalidURIFormatError(msg) from err
                    break


def _set_counters_from_prefix_map(
    max_numbers_by_prefix: defaultdict,
    counter_handler: MetaCounterHandlerProtocol,
    entity_type_abbr: dict[str, str],
) -> None:
    for supplier_prefix, max_numbers in max_numbers_by_prefix.items():
        original_prefix = counter_handler.supplier_prefix
        counter_handler.supplier_prefix = supplier_prefix

        for entity_type, abbr in entity_type_abbr.items():
            counter_value = max_numbers[abbr]
            counter_handler.set_counter(counter_value, entity_type)

        counter_handler.supplier_prefix = original_prefix


class MetaURIGenerator(URIGenerator):
    def __init__(
        self,
        counter_handler: MetaCounterHandlerProtocol,
        supplier_prefix_regex: str = r"0[69][1-9]*0",
    ) -> None:
        self.base_iri = counter_handler.base_iri.rstrip("/")
        self.supplier_prefix_regex = supplier_prefix_regex
        self.new_supplier_prefix = counter_handler.supplier_prefix

        self.counter_handler = counter_handler
        self.counter_handler.supplier_prefix = self.new_supplier_prefix
        self.entity_type_abbr = META_URI_ENTITY_TYPE_ABBR

    def generate_uri(self, entity_type: str, _context_data: dict | None = None) -> str:
        next_number = self.counter_handler.increment_counter(entity_type)
        return URIRef(
            f"{self.base_iri}/{self.entity_type_abbr[entity_type]}/{self.new_supplier_prefix}{next_number}"
        )

    def initialize_counters(self, sparql: SPARQLWrapper) -> None:
        """
        Initialize counters for entity types supported by this URI generator.
        Extracts sequential numbers from both data and provenance for each abbreviation,
        grouping by supplier prefix to maintain separate counters.

        :param sparql: SPARQLWrapper instance to execute queries on the dataset
        :raises InvalidURIFormatError: If an URI with invalid format is found
        """
        max_numbers_by_prefix = defaultdict(lambda: defaultdict(int))

        data_query = f"""
            SELECT ?s ?type
            WHERE {{
                ?s a ?type .
                FILTER(STRSTARTS(str(?s), "{self.base_iri}/"))
            }}
        """

        sparql.setQuery(data_query)
        sparql.setReturnFormat(JSON)
        data_bindings = get_sparql_bindings(sparql.query().convert())

        _process_data_bindings(
            data_bindings,
            max_numbers_by_prefix,
            self.entity_type_abbr,
            self.supplier_prefix_regex,
        )

        prov_query = """
            SELECT ?entity
            WHERE {
                ?snapshot <http://www.w3.org/ns/prov#specializationOf> ?entity .
            }
        """

        sparql.setQuery(prov_query)
        prov_bindings = get_sparql_bindings(sparql.query().convert())

        _process_prov_bindings(
            prov_bindings,
            max_numbers_by_prefix,
            self.entity_type_abbr,
            self.supplier_prefix_regex,
        )

        _set_counters_from_prefix_map(
            max_numbers_by_prefix, self.counter_handler, self.entity_type_abbr
        )
