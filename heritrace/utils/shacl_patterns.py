# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import re
from collections.abc import Callable
from dataclasses import dataclass

from rdflib import Graph
from rdflib.plugins.sparql import prepareQuery

from heritrace.configuration.vocabulary import SH
from heritrace.field_errors import FieldError, field_error
from heritrace.language import LocalizedText, localize, localized_texts
from heritrace.sparql import select_results

# A field's own sh:pattern applies to each of its values. A pattern in an
# alternative of a node shape's sh:or applies when the resource holds the fixed
# value of the alternative, and a value then needs to match one of them.
_PATTERNS_QUERY = prepareQuery(
    """
    SELECT ?type ?shape ?path ?condition_path ?condition_value ?pattern
           ?value_shape
    WHERE {
        ?shape sh:targetClass ?type .
        {
            ?shape sh:property ?value_shape .
        } UNION {
            ?shape sh:or/rdf:rest*/rdf:first ?alternative .
            ?alternative sh:property ?value_shape, ?condition_shape .
            ?condition_shape sh:path ?condition_path ;
                             sh:hasValue ?condition_value .
        }
        ?value_shape sh:path ?path ;
                     sh:pattern ?pattern .
        FILTER isIRI(?path)
    }
    ORDER BY ?shape ?condition_value ?pattern
    """,
    initNs={
        "sh": "http://www.w3.org/ns/shacl#",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    },
)


@dataclass(frozen=True, slots=True)
class ValuePattern:
    target_class: str
    shape: str
    path: str
    # The field and the value that make the pattern apply, or None for the
    # pattern of the field itself.
    condition: tuple[str, str] | None
    pattern: str
    messages: LocalizedText

    def message(self) -> str | None:
        return localize(self.messages)

    def as_json(self) -> dict[str, object]:
        return {
            "condition": None
            if self.condition is None
            else {"path": self.condition[0], "value": self.condition[1]},
            "pattern": self.pattern,
            "message": self.message(),
        }


def read_value_patterns(shacl: Graph) -> list[ValuePattern]:
    return [
        ValuePattern(
            target_class=str(row.type),
            shape=str(row.shape),
            path=str(row.path),
            condition=None
            if row.condition_path is None
            else (str(row.condition_path), str(row.condition_value)),
            pattern=str(row.pattern),
            messages=localized_texts(shacl, row.value_shape, SH.message),
        )
        for row in select_results(shacl.query(_PATTERNS_QUERY))
    ]


# The pattern that a value breaks among those of its field. The field's own
# patterns apply to every value; among the conditional ones whose condition
# holds, the value needs to match one.
def broken_pattern(
    value: str,
    patterns: list[ValuePattern],
    holds: Callable[[tuple[str, str]], bool],
) -> ValuePattern | None:
    applicable = [
        pattern
        for pattern in patterns
        if pattern.condition is None or holds(pattern.condition)
    ]
    own = [pattern for pattern in applicable if pattern.condition is None]
    conditional = [pattern for pattern in applicable if pattern.condition is not None]
    for pattern in own:
        if not re.search(pattern.pattern, value):
            return pattern
    if conditional and not any(
        re.search(pattern.pattern, value) for pattern in conditional
    ):
        return conditional[0]
    return None


def pattern_error(
    pattern: ValuePattern, subject: str | None, predicate: str, value: str
) -> FieldError:
    message = pattern.message()
    if message is None:
        return field_error(
            "invalidInput", subject, predicate, expected=pattern.pattern, input=value
        )
    return field_error("message", subject, predicate, message=message, input=value)


_SHOWN_WITH_QUERY = prepareQuery(
    """
    SELECT ?shape ?path ?trigger_path
    WHERE {
        ?shape sh:or ?alternatives .
        ?alternatives rdf:rest*/rdf:first ?gated, ?trigger .
        ?gated sh:path ?path ;
               sh:in ( false ) .
        ?trigger sh:path ?trigger_path ;
                 sh:minCount 1 .
    }
    ORDER BY ?shape ?path ?trigger_path
    """,
    initNs={
        "sh": "http://www.w3.org/ns/shacl#",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    },
)


def read_shown_with(shacl: Graph) -> dict[tuple[str, str], list[str]]:
    """Map each (shape, path) to the paths that must have a value to show it.

    A node shape declares that a boolean field applies only when one of some
    other fields has a value with
    sh:or ( [ sh:path P ; sh:in ( false ) ] [ sh:path Q ; sh:minCount 1 ] ... ).
    """
    shown_with: dict[tuple[str, str], list[str]] = {}
    for row in select_results(shacl.query(_SHOWN_WITH_QUERY)):
        shown_with.setdefault((str(row.shape), str(row.path)), []).append(
            str(row.trigger_path)
        )
    return shown_with


_EXCLUDED_WITH_QUERY = prepareQuery(
    """
    SELECT ?shape ?path ?other_path
    WHERE {
        ?shape sh:or ?alternatives .
        ?alternatives rdf:first ?first ;
                      rdf:rest/rdf:first ?second ;
                      rdf:rest/rdf:rest rdf:nil .
        ?first sh:maxCount 0 .
        ?second sh:maxCount 0 .
        {
            ?first sh:path ?path .
            ?second sh:path ?other_path .
        } UNION {
            ?first sh:path ?other_path .
            ?second sh:path ?path .
        }
    }
    ORDER BY ?shape ?path ?other_path
    """,
    initNs={
        "sh": "http://www.w3.org/ns/shacl#",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    },
)


# A node shape declares that two fields cannot both have a value with
# sh:or ( [ sh:path P ; sh:maxCount 0 ] [ sh:path Q ; sh:maxCount 0 ] ). This
# maps each (shape, path) to the paths it excludes.
def read_excluded_with(shacl: Graph) -> dict[tuple[str, str], list[str]]:
    excluded_with: dict[tuple[str, str], list[str]] = {}
    for row in select_results(shacl.query(_EXCLUDED_WITH_QUERY)):
        excluded_with.setdefault((str(row.shape), str(row.path)), []).append(
            str(row.other_path)
        )
    return excluded_with
