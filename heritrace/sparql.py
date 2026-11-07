# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import json
import logging
import time
from collections.abc import Callable, Iterator
from typing import Protocol, TypedDict, cast

from rdflib import Graph
from rdflib.query import Result, ResultRow
from SPARQLWrapper import POST, QueryResult, SPARQLWrapper
from SPARQLWrapper.SPARQLExceptions import SPARQLWrapperException


class SPARQLWrapperWithRetry(SPARQLWrapper):
    def __init__(
        self,
        endpoint: str,
        *,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        timeout: float = 5.0,
    ) -> None:
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor

        super().__init__(endpoint)

        self.setTimeout(int(timeout))
        self.setMethod(POST)

    def query(self) -> QueryResult:
        return self._query_with_retry()

    def _query_with_retry(self) -> QueryResult:
        logger = logging.getLogger(__name__)

        delay = self.initial_delay
        last_exception = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                return super().query()
            except (SPARQLWrapperException, OSError) as e:  # noqa: PERF203
                last_exception = e
                logger.warning(
                    "SPARQL query attempt %d/%d failed: %s",
                    attempt,
                    self.max_attempts,
                    e,
                )

                if attempt < self.max_attempts:
                    logger.info("Retrying in %.2f seconds...", delay)
                    time.sleep(delay)
                    delay *= self.backoff_factor

        logger.error("All %d SPARQL query attempts failed", self.max_attempts)
        raise last_exception  # type: ignore[misc]


class _ConvertibleResult(Protocol):
    def convert(self) -> object: ...


class SparqlEndpoint(Protocol):
    def setQuery(self, query: str) -> None: ...  # noqa: N802

    def setReturnFormat(self, format: str) -> None: ...  # noqa: N802, A002

    def query(self) -> _ConvertibleResult: ...

    def queryAndConvert(self) -> object: ...  # noqa: N802


class _LocalResult:
    def __init__(self, result: Result) -> None:
        self._result = result

    def convert(self) -> object:
        return json.loads(cast("bytes", self._result.serialize(format="json")))


# Answers like a SPARQL endpoint, with SPARQL JSON results, from an rdflib graph
# that the callable returns afresh for every query.
class LocalSparql:
    def __init__(self, graph: Callable[[], Graph]) -> None:
        self._graph = graph
        self._query = ""

    def setQuery(self, query: str) -> None:  # noqa: N802
        self._query = query

    def setReturnFormat(self, format: str) -> None:  # noqa: N802, A002
        pass

    def query(self) -> _LocalResult:
        return _LocalResult(self._graph().query(self._query))

    def queryAndConvert(self) -> object:  # noqa: N802
        return self.query().convert()


class _SparqlJsonResults(TypedDict):
    bindings: list[dict[str, dict[str, str]]]


class _SparqlJsonResponse(TypedDict):
    results: _SparqlJsonResults


def get_sparql_bindings(result: object) -> list[dict[str, dict[str, str]]]:
    return cast("_SparqlJsonResponse", result)["results"]["bindings"]


def select_results(result: Result) -> Iterator[ResultRow]:
    for row in result:
        yield cast("ResultRow", row)
