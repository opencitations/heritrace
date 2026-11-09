# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import re
from dataclasses import dataclass

from rdflib import XSD, Literal, URIRef

QLEVER_HAS_WORD = "<http://qlever.cs.uni-freiburg.de/builtin-functions/has-word>"
WORD_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class SearchRequest:
    term: str
    entity_class: str
    paths: list[tuple[str, ...]]
    offset: int = 0
    limit: int = 5


def _is_text_field(field: dict) -> bool:
    return (
        "datatypes" in field
        and str(XSD.string) in field["datatypes"]
        and field["hasValue"] is None
        and not field["optionalValues"]
    )


def text_paths(fields: dict[str, list[dict]]) -> list[tuple[str, ...]]:
    paths: dict[tuple[str, ...], None] = {}
    for predicate, definitions in fields.items():
        for definition in definitions:
            if "is_virtual" in definition:
                continue
            if _is_text_field(definition):
                paths[(predicate,)] = None
            if "nestedShape" in definition:
                for nested in definition["nestedShape"]:
                    if _is_text_field(nested):
                        paths[(predicate, nested["uri"])] = None
    return list(paths)


def _path_pattern(path: tuple[str, ...], text: str, nested: str) -> str:
    predicates = [URIRef(predicate).n3() for predicate in path]
    if len(predicates) == 1:
        return f"?entity {predicates[0]} {text} ."
    return f"?entity {predicates[0]} {nested} . {nested} {predicates[1]} {text} ."


def _match_patterns(request: SearchRequest, text: str) -> str:
    alternatives = " UNION ".join(
        f"{{ {_path_pattern(path, text, '?nested')} }}" for path in request.paths
    )
    return f"?entity a {URIRef(request.entity_class).n3()} .\n{alternatives}"


def _virtuoso_query(request: SearchRequest, words: list[str]) -> str:
    phrase = Literal(f'"{" ".join(words)}"').n3()
    text_match = f"?text bif:contains {phrase} OPTION (score ?scoreValue) ."
    branches = " UNION ".join(
        f"{{ {_path_pattern(path, '?text', '?nested')} {text_match} }}"
        for path in request.paths
    )
    return f"""
        SELECT DISTINCT ?entity ?scoreValue WHERE {{
            ?entity a {URIRef(request.entity_class).n3()} .
            {branches}
            FILTER(?scoreValue > 0.2)
        }}
        ORDER BY DESC(?scoreValue) ASC(?entity)
        OFFSET {request.offset}
        LIMIT {request.limit + 1}
    """


def _entity_query(request: SearchRequest, patterns: str) -> str:
    return f"""
        SELECT DISTINCT ?entity WHERE {{
            {patterns}
        }}
        ORDER BY ASC(?entity)
        OFFSET {request.offset}
        LIMIT {request.limit + 1}
    """


def _filter_query(request: SearchRequest, search_filter: str) -> str:
    return _entity_query(
        request, f"{_match_patterns(request, '?searchValue')}\n{search_filter}"
    )


def _qlever_word_group(request: SearchRequest, word: str, index: int) -> str:
    value = f"?searchValue{index}"
    word_variable = f"?searchWord{index}"
    prefix = Literal(word.lower()).n3()
    word_match = (
        f"{value} {QLEVER_HAS_WORD} {word_variable} . "
        f"FILTER(STRSTARTS({word_variable}, {prefix}))"
    )
    # Outside the branches, QLever sorts every value of the paths before filtering.
    branches = " UNION ".join(
        f"{{ {word_match} {_path_pattern(path, value, f'?nested{index}')} }}"
        for path in request.paths
    )
    return f"{{ {branches} }}"


def _qlever_query(request: SearchRequest, words: list[str]) -> str:
    groups = "\n".join(
        _qlever_word_group(request, word, index) for index, word in enumerate(words)
    )
    return _entity_query(
        request, f"{groups}\n?entity a {URIRef(request.entity_class).n3()} ."
    )


def build_search_query(
    request: SearchRequest, triplestore: str, *, text_index_enabled: bool
) -> str:
    if text_index_enabled and triplestore in ("virtuoso", "qlever"):
        words = WORD_PATTERN.findall(request.term)
        if not words:
            return _filter_query(request, "FILTER(false)")
        if triplestore == "virtuoso":
            return _virtuoso_query(request, words)
        return _qlever_query(request, words)
    regex_filter = (
        f'FILTER(REGEX(STR(?searchValue), {Literal(request.term).n3()}, "i"))'
    )
    return _filter_query(request, regex_filter)
