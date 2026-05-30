# SPDX-FileCopyrightText: 2024-2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from rdflib_ocdm.counter_handler.counter_handler import CounterHandler

    from heritrace.sparql import SPARQLWrapperWithRetry


class URIGenerator(ABC):  # pragma: no cover
    @abstractmethod
    def generate_uri(
        self, entity_type: str | None = None, context_data: dict | None = None
    ) -> str:
        pass

    @abstractmethod
    def initialize_counters(self, sparql: SPARQLWrapperWithRetry) -> None:
        pass


@runtime_checkable
class CounterBasedURIGenerator(Protocol):
    @property
    def counter_handler(self) -> CounterHandler: ...

    def initialize_counters(self, sparql: SPARQLWrapperWithRetry) -> None: ...
