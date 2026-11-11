# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from dataclasses import dataclass

from rdflib import Graph
from rdflib.plugins.sparql import prepareQuery

from heritrace.sparql import select_results

_ALTERNATIVES_QUERY = prepareQuery(
    """
    SELECT ?type ?shape ?path ?condition_path ?condition_value ?pattern ?message
    WHERE {
        ?shape sh:targetClass ?type ;
               sh:or/rdf:rest*/rdf:first ?alternative .
        ?alternative sh:property ?value_shape, ?condition_shape .
        ?value_shape sh:path ?path ;
                     sh:pattern ?pattern .
        OPTIONAL { ?value_shape sh:message ?message . }
        ?condition_shape sh:path ?condition_path ;
                         sh:hasValue ?condition_value .
    }
    ORDER BY ?shape ?condition_value ?pattern
    """,
    initNs={
        "sh": "http://www.w3.org/ns/shacl#",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    },
)


@dataclass(frozen=True, slots=True)
class PatternAlternative:
    target_class: str
    shape: str
    path: str
    condition_path: str
    condition_value: str
    pattern: str
    message: str

    def as_condition(self) -> dict[str, object]:
        return {
            "condition": {"path": self.condition_path, "value": self.condition_value},
            "pattern": self.pattern,
            "message": self.message,
        }


def read_pattern_alternatives(shacl: Graph) -> list[PatternAlternative]:
    return [
        PatternAlternative(
            target_class=str(row.type),
            shape=str(row.shape),
            path=str(row.path),
            condition_path=str(row.condition_path),
            condition_value=str(row.condition_value),
            pattern=str(row.pattern),
            message=(
                str(row.message)
                if row.message
                else f"Value must match pattern: {row.pattern}"
            ),
        )
        for row in select_results(shacl.query(_ALTERNATIVES_QUERY))
    ]


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
