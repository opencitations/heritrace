# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from collections.abc import Collection
from dataclasses import dataclass
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import cast

from pyshacl import validate
from rdflib import RDF, Graph, URIRef
from rdflib.term import Node

from heritrace.configuration.vocabulary import SH, SHUI

# The files in w3c/ come from
# https://github.com/w3c/data-shapes/tree/f881b32ee5b2f96be1b48de576d6fc38c6eaf151/shacl12-ui/widgets
# and keep only the editors that the forms render.
_WIDGETS = Path(__file__).parent.parent / "widgets"


@dataclass(frozen=True, slots=True)
class _Matcher:
    widget: URIRef
    shapes_graph_shapes: tuple[Node, ...]
    data_graph_shapes: tuple[Node, ...]


@dataclass(frozen=True, slots=True)
class _Score:
    matcher: _Matcher
    score: Decimal


@dataclass(frozen=True, slots=True)
class _ScoringGraph:
    graph: Graph
    scores: tuple[_Score, ...]
    accept_matchers: dict[URIRef, tuple[_Matcher, ...]]


def _matcher(graph: Graph, node: Node) -> _Matcher:
    return _Matcher(
        widget=cast("URIRef", graph.value(node, SHUI.widget)),
        shapes_graph_shapes=tuple(graph.objects(node, SHUI.shapesGraphShape)),
        data_graph_shapes=tuple(graph.objects(node, SHUI.dataGraphShape)),
    )


@cache
def _scoring_graph() -> _ScoringGraph:
    graph = Graph()
    for path in sorted(_WIDGETS.rglob("*.ttl")):
        graph.parse(path)
    scores = [
        _Score(
            _matcher(graph, node),
            Decimal(str(graph.value(node, SHUI.score))),
        )
        for node in graph.subjects(RDF.type, SHUI.WidgetScore)
    ]
    scores.sort(key=lambda score: (-score.score, str(score.matcher.widget)))
    accept = [
        _matcher(graph, node)
        for node in graph.subjects(RDF.type, SHUI.WidgetAcceptMatcher)
    ]
    return _ScoringGraph(
        graph=graph,
        scores=tuple(scores),
        accept_matchers={
            score.matcher.widget: tuple(
                matcher for matcher in accept if matcher.widget == score.matcher.widget
            )
            for score in scores
        },
    )


def _conforming_nodes(
    shapes: Graph, scoring: Graph, matcher_shape: Node, nodes: Collection[Node]
) -> set[Node]:
    targeted = Graph()
    targeted += scoring
    for node in nodes:
        targeted.add((matcher_shape, SH.targetNode, node))
    report = cast("Graph", validate(shapes, shacl_graph=targeted)[1])
    return set(nodes) - set(report.objects(None, SH.focusNode))


# Without a value to edit, the matcher function of SHACL 1.2 UI reads only
# shui:shapesGraphShape: a matcher with nothing but shui:dataGraphShape does not
# apply.
def _matches(matcher: _Matcher, node: Node, conforming: dict[Node, set[Node]]) -> bool:
    if not matcher.shapes_graph_shapes:
        return not matcher.data_graph_shapes
    return all(node in conforming[shape] for shape in matcher.shapes_graph_shapes)


def select_editors(shapes: Graph, nodes: Collection[Node]) -> dict[Node, URIRef]:
    scoring = _scoring_graph()
    matcher_shapes = {
        shape for score in scoring.scores for shape in score.matcher.shapes_graph_shapes
    } | {
        shape
        for matchers in scoring.accept_matchers.values()
        for matcher in matchers
        for shape in matcher.shapes_graph_shapes
    }
    conforming = {
        shape: _conforming_nodes(shapes, scoring.graph, shape, nodes)
        for shape in matcher_shapes
    }
    return {
        node: next(
            score.matcher.widget
            for score in scoring.scores
            if _matches(score.matcher, node, conforming)
            and all(
                _matches(matcher, node, conforming)
                for matcher in scoring.accept_matchers[score.matcher.widget]
            )
        )
        for node in nodes
    }
