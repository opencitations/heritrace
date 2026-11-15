# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import operator
from collections.abc import Callable, Mapping
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from rdflib import XSD
from rdflib.term import Node

if TYPE_CHECKING:
    from rdflib import Literal

Bound = int | float | None

NUMERIC_DATATYPES = frozenset(
    str(datatype)
    for datatype in (
        XSD.integer,
        XSD.int,
        XSD.long,
        XSD.short,
        XSD.byte,
        XSD.positiveInteger,
        XSD.negativeInteger,
        XSD.nonNegativeInteger,
        XSD.nonPositiveInteger,
        XSD.unsignedLong,
        XSD.unsignedInt,
        XSD.unsignedShort,
        XSD.unsignedByte,
        XSD.decimal,
        XSD.float,
        XSD.double,
    )
)

# Each bound with the comparison that breaks it and the code of the error.
_VIOLATIONS: dict[str, tuple[Callable[[Decimal, Decimal], bool], str]] = {
    "minInclusive": (operator.lt, "atLeast"),
    "maxInclusive": (operator.gt, "atMost"),
    "minExclusive": (operator.le, "greaterThan"),
    "maxExclusive": (operator.ge, "lessThan"),
}
BOUND_NAMES = tuple(_VIOLATIONS)


def bound_number(bound: Node | None) -> Bound:
    if bound is None:
        return None
    value = cast("Literal", bound).toPython()
    return value if isinstance(value, int) else float(value)


def broken_bound(
    value: str, bounds: Mapping[str, Bound]
) -> tuple[str, int | float] | None:
    for name, (violates, code) in _VIOLATIONS.items():
        bound = bounds[name]
        if bound is not None and violates(Decimal(value), Decimal(str(bound))):
            return code, bound
    return None
