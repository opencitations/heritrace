# SPDX-FileCopyrightText: 2024-2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from __future__ import annotations

import os
import uuid
from typing import TYPE_CHECKING

from rdflib import URIRef

from heritrace.uri_generator.uri_generator import URIGenerator

if TYPE_CHECKING:
    from heritrace.sparql import SPARQLWrapperWithRetry


class DefaultURIGenerator(URIGenerator):
    def __init__(self, base_iri: str | None = None) -> None:
        self.base_iri = base_iri if base_iri is not None else os.environ["BASE_IRI"]

    def generate_uri(
        self, _entity_type: str | None = None, _context_data: dict | None = None
    ) -> str:
        return URIRef(f"{self.base_iri}/{uuid.uuid4().hex}")

    def initialize_counters(self, sparql: SPARQLWrapperWithRetry) -> None:
        """
        Initialize counters for entity types supported by this URI generator.
        Since DefaultURIGenerator uses UUIDs, no counter initialization is needed.

        :param sparql: SPARQLWrapper instance to execute queries on the dataset
        :return: None
        """
