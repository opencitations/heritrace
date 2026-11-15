# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import operator
from collections.abc import Callable, Mapping
from decimal import Decimal
from typing import cast

from rdflib import XSD, Literal
from rdflib.term import Node

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


# The kinds of date that the forms offer, whose values compare by their text.
_DATE_DATATYPES = frozenset(
    str(datatype) for datatype in (XSD.date, XSD.gYearMonth, XSD.gYear)
)


# Whether a value does not exceed a limit. Numbers compare with numbers and
# dates with dates of the same kind; any other pair cannot be compared and
# breaks the rule, as in SHACL.
def at_most(value: Node, limit: Node) -> bool:
    if not (isinstance(value, Literal) and isinstance(limit, Literal)):
        return False
    if {str(value.datatype), str(limit.datatype)} <= NUMERIC_DATATYPES:
        return Decimal(str(value)) <= Decimal(str(limit))
    return (
        value.datatype == limit.datatype
        and str(value.datatype) in _DATE_DATATYPES
        and str(value) <= str(limit)
    )


def broken_bound(
    value: str, bounds: Mapping[str, Bound]
) -> tuple[str, int | float] | None:
    for name, (violates, code) in _VIOLATIONS.items():
        bound = bounds[name]
        if bound is not None and violates(Decimal(value), Decimal(str(bound))):
            return code, bound
    return None
