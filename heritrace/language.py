# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from typing import TypeGuard

from flask import has_request_context, request
from rdflib import Graph, Literal, URIRef
from rdflib.term import Node

LANGUAGES = ("en", "it")
NEUTRAL = ""

# The texts of one label, keyed by language tag; NEUTRAL keys the untagged one.
LocalizedText = dict[str, str]


def request_language() -> str:
    # Shapes are also read at startup and from the command line.
    if not has_request_context():
        return LANGUAGES[0]
    return request.accept_languages.best_match(LANGUAGES, default=LANGUAGES[0])


def localized_texts(graph: Graph, subject: Node, predicate: URIRef) -> LocalizedText:
    literals = [
        value
        for value in graph.objects(subject, predicate)
        if isinstance(value, Literal)
    ]
    return {
        value.language or NEUTRAL: str(value)
        for value in sorted(literals, key=lambda value: value.language or NEUTRAL)
    }


def add_localized_texts(
    graph: Graph, subject: Node, predicate: URIRef, texts: LocalizedText
) -> None:
    for language, text in texts.items():
        graph.add((subject, predicate, Literal(text, lang=language or None)))


def pick_text(texts: LocalizedText, language: str) -> str | None:
    for key in (language, NEUTRAL):
        if key in texts:
            return texts[key]
    return next(iter(texts.values()), None)


def localize(texts: LocalizedText) -> str | None:
    return pick_text(texts, request_language())


def is_tagged(value: object) -> TypeGuard[dict[str, str]]:
    """Whether a value sent by a form carries a language tag."""
    return isinstance(value, dict) and "language" in value


def tagged_literal(value: dict[str, str]) -> Literal:
    return Literal(value["value"], lang=value["language"])
