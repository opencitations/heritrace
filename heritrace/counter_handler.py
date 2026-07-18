# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from typing import Protocol, runtime_checkable


@runtime_checkable
class CounterInitializationPolicy(Protocol):
    def should_initialize_from_triplestore(self) -> bool: ...


@runtime_checkable
class TransactionalCounterHandler(Protocol):
    def begin_counter_transaction(self) -> None: ...

    def commit_counter_transaction(self) -> None: ...

    def rollback_counter_transaction(self) -> None: ...
