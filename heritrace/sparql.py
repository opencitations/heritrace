# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import logging
import time
from collections.abc import Iterator
from typing import TypedDict, cast

from rdflib.query import Result, ResultRow
from SPARQLWrapper import POST, SPARQLWrapper


class SPARQLWrapperWithRetry(SPARQLWrapper):
    def __init__(self, endpoint, **kwargs):
        self.max_attempts = kwargs.pop('max_attempts', 3)
        self.initial_delay = kwargs.pop('initial_delay', 1.0)
        self.backoff_factor = kwargs.pop('backoff_factor', 2.0)
        query_timeout = kwargs.pop('timeout', 5.0)

        super().__init__(endpoint, **kwargs)

        self.setTimeout(int(query_timeout))
        self.setMethod(POST)

    def query(self):
        logger = logging.getLogger(__name__)

        attempt = 1
        delay = self.initial_delay
        last_exception = None

        while attempt <= self.max_attempts:
            try:
                result = super().query()
                return result

            except Exception as e:
                last_exception = e
                logger.warning(f"SPARQL query attempt {attempt}/{self.max_attempts} failed: {str(e)}")

                if attempt < self.max_attempts:
                    logger.info(f"Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                    delay *= self.backoff_factor

                attempt += 1

        logger.error(f"All {self.max_attempts} SPARQL query attempts failed")
        raise last_exception  # type: ignore[misc]


class _SparqlJsonResults(TypedDict):
    bindings: list[dict[str, dict[str, str]]]


class _SparqlJsonResponse(TypedDict):
    results: _SparqlJsonResults


def get_sparql_bindings(result: object) -> list[dict[str, dict[str, str]]]:
    return cast(_SparqlJsonResponse, result)["results"]["bindings"]


def select_results(result: Result) -> Iterator[ResultRow]:
    for row in result:
        yield cast(ResultRow, row)
