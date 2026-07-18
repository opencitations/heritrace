# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from typing import Protocol, runtime_checkable


@runtime_checkable
class CounterInitializationPolicy(Protocol):
    def should_initialize_from_triplestore(self) -> bool: ...
