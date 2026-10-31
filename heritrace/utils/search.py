# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import re
from dataclasses import dataclass, field

from rdflib import Literal, URIRef

QLEVER_HAS_WORD = "<http://qlever.cs.uni-freiburg.de/builtin-functions/has-word>"
WORD_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class ContextConstraint:
    predicate: str
    value: str
    datatype: str | None


@dataclass(frozen=True, slots=True)
class SearchRequest:
    term: str
    entity_class: str | None
    predicate: str | None
    search_target: str = "self"
    connecting_predicate: str | None = None
    context: list[ContextConstraint] = field(default_factory=list)
    offset: int = 0
    limit: int = 5


def _iri(value: str | None) -> str:
    if value is None:
        msg = "Missing IRI for the search query"
        raise ValueError(msg)
    return URIRef(value).n3()


def _n3(value: str, datatype: str | None) -> str:
    if datatype is None:
        return _iri(value)
    return Literal(value, datatype=URIRef(datatype)).n3()


def _context_patterns(request: SearchRequest) -> str:
    subject = "?nestedEntity" if request.search_target == "parent" else "?entity"
    return "".join(
        f"\n    {subject} {_iri(constraint.predicate)}"
        f" {_n3(constraint.value, constraint.datatype)} ."
        for constraint in request.context
    )


def _virtuoso_query(request: SearchRequest, words: list[str]) -> str:
    if request.search_target == "parent":
        match = f"""
            ?entity a {_iri(request.entity_class)} .
            ?entity {_iri(request.connecting_predicate)} ?nestedEntity .
            ?nestedEntity {_iri(request.predicate)} ?text ."""
    else:
        match = "\n            ?entity ?p ?text ."
        if request.entity_class:
            match += f"\n            ?entity a {_iri(request.entity_class)} ."
        if request.predicate:
            match += f"\n            ?entity {_iri(request.predicate)} ?text ."
    phrase = Literal(f'"{" ".join(words)}"').n3()
    return f"""
        SELECT DISTINCT ?entity ?scoreValue WHERE {{{_context_patterns(request)}{match}
            ?text bif:contains {phrase} OPTION (score ?scoreValue) .
            FILTER(?scoreValue > 0.2)
        }}
        ORDER BY DESC(?scoreValue) ASC(?entity)
        OFFSET {request.offset}
        LIMIT {request.limit + 1}
    """


def _qlever_filter(words: list[str]) -> str:
    patterns = [
        f"?searchValue {QLEVER_HAS_WORD} {Literal(word.lower()).n3()} ."
        for word in words[:-1]
    ]
    last = Literal(words[-1].lower()).n3()
    patterns.append(
        f"?searchValue {QLEVER_HAS_WORD} ?searchWord .\n"
        f"                FILTER(STRSTARTS(?searchWord, {last}))"
    )
    return "\n                ".join(patterns)


def _filter_query(request: SearchRequest, search_filter: str) -> str:
    if request.search_target == "parent":
        match = f"""
            ?nestedEntity {_iri(request.predicate)} ?searchValue .
            {search_filter}
            ?entity {_iri(request.connecting_predicate)} ?nestedEntity .
            ?entity a {_iri(request.entity_class)} ."""
    else:
        match = ""
        if request.entity_class:
            match += f"\n            ?entity a {_iri(request.entity_class)} ."
        if request.predicate:
            match += f"\n            ?entity {_iri(request.predicate)} ?searchValue ."
        else:
            match += "\n            ?entity ?searchPredicate ?searchValue ."
        match += f"\n            {search_filter}"
    return f"""
        SELECT DISTINCT ?entity WHERE {{{_context_patterns(request)}{match}
        }}
        ORDER BY ASC(?entity)
        OFFSET {request.offset}
        LIMIT {request.limit + 1}
    """


def build_search_query(
    request: SearchRequest, triplestore: str, *, text_index_enabled: bool
) -> str:
    if text_index_enabled and triplestore in ("virtuoso", "qlever"):
        words = WORD_PATTERN.findall(request.term)
        if not words:
            return _filter_query(request, "FILTER(false)")
        if triplestore == "virtuoso":
            return _virtuoso_query(request, words)
        return _filter_query(request, _qlever_filter(words))
    regex_filter = (
        f'FILTER(REGEX(STR(?searchValue), {Literal(request.term).n3()}, "i"))'
    )
    return _filter_query(request, regex_filter)
