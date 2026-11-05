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
