# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import logging
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import cast

from pyparsing.exceptions import ParseException
from rdflib import OWL, RDF, XSD, BNode, Graph, Literal, URIRef
from rdflib.plugins.sparql.algebra import translateQuery, traverse
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.term import Node

from heritrace.configuration.shapes import read_duplicate_keys
from heritrace.configuration.vocabulary import DASH, HT, SH, SHUI

_THIS_VARIABLE = re.compile(r"[?$]this\b")

_INVERSE_PROBE = URIRef("urn:heritrace:inverse-probe")

_INVERSE_PATH_MARK = "^"

_TRUE = Literal("true", datatype=XSD.boolean)


def inverse_path_key(predicate: str) -> str:
    return f"{_INVERSE_PATH_MARK}{predicate}"


def inverse_predicate(path: str) -> str | None:
    return path.removeprefix(_INVERSE_PATH_MARK) if is_inverse_path(path) else None


def is_inverse_path(path: str) -> bool:
    return path.startswith(_INVERSE_PATH_MARK)


@dataclass(frozen=True, slots=True)
class PropertyPresentation:
    path: str
    node: str | None
    name: str | None
    order: Decimal | None
    editor: str | None
    ordered_by: str | None
    identifier: str


@dataclass(frozen=True, slots=True)
class ShapesPresentation:
    shape_names: dict[str, str]
    properties: dict[str, list[PropertyPresentation]]
    label_queries: dict[str, str]
    fixed_type_counts: dict[str, int]
    hidden_shapes: frozenset[str]
    duplicate_keys: dict[str, list[list[str]]]

    def is_hidden(self, shape: str | None) -> bool:
        return str(shape) in self.hidden_shapes

    def shape_duplicate_keys(self, shape: str | None) -> list[list[str]]:
        return self.duplicate_keys.get(str(shape), [])

    def fixed_type_count(self, shape: str | None) -> int:
        return self.fixed_type_counts.get(str(shape), 0)

    def shape_name(self, shape: str | None) -> str | None:
        return self.shape_names.get(str(shape)) if shape else None

    def shape_properties(self, shape: str | None) -> list[PropertyPresentation]:
        return self.properties.get(str(shape), []) if shape else []

    def property_presentation(
        self, shape: str | None, predicate: str, object_shape: str | None
    ) -> PropertyPresentation | None:
        candidates = [
            prop for prop in self.shape_properties(shape) if prop.path == predicate
        ]
        for prop in candidates:
            if prop.node == object_shape:
                return prop
        return candidates[0] if candidates else None

    def property_name(
        self, shape: str | None, predicate: str, object_shape: str | None
    ) -> str | None:
        prop = self.property_presentation(shape, predicate, object_shape)
        return prop.name if prop else None

    def ordered_by(self, shape: str | None, predicate: str) -> str | None:
        for prop in self.shape_properties(shape):
            if prop.path == predicate and prop.ordered_by is not None:
                return prop.ordered_by
        return None

    def predicate_order(self, shape: str | None) -> list[str]:
        ordered: list[str] = []
        for prop in self.shape_properties(shape):
            if prop.path not in ordered:
                ordered.append(prop.path)
        return ordered

    def node_order(self, shape: str | None, predicate: str) -> list[str]:
        return [
            prop.node
            for prop in self.shape_properties(shape)
            if prop.path == predicate and prop.node
        ]

    def label_query(self, shape: str | None, focus_node: str) -> str | None:
        query = self.label_queries.get(str(shape)) if shape else None
        if query is None:
            return None
        return _THIS_VARIABLE.sub(URIRef(focus_node).n3(), query)


def _literal_text(graph: Graph, subject: Node, predicate: URIRef) -> str | None:
    value = graph.value(subject, predicate)
    return str(value) if isinstance(value, Literal) else None


def _prefix_block(graph: Graph, select_expression: Node) -> str:
    declaration_owners = list(graph.objects(select_expression, SH.prefixes))
    if not declaration_owners:
        declaration_owners = [
            owner
            for graph_type in (
                OWL.Ontology,
                SH.DataGraph,
                SH.ShapesGraph,
                SH.RulesGraph,
            )
            for owner in graph.subjects(RDF.type, graph_type)
        ]
    declarations = {
        str(graph.value(declaration, SH.prefix)): str(
            graph.value(declaration, SH.namespace)
        )
        for owner in declaration_owners
        for declaration in graph.objects(owner, SH.declare)
    }
    return "".join(
        f"PREFIX {prefix}: <{namespace}>\n"
        for prefix, namespace in sorted(declarations.items())
    )


def _label_query(graph: Graph, property_shape: Node, path: URIRef) -> str:
    select_expression = graph.value(property_shape, SH.values)
    if select_expression is None:
        return f"SELECT ?label WHERE {{ $this {path.n3()} ?label }}"
    select = graph.value(select_expression, SH.select)
    return _prefix_block(graph, select_expression) + str(select)


def _property_presentation(
    graph: Graph, property_shape: Node, path: str
) -> PropertyPresentation:
    order = graph.value(property_shape, SH.order)
    node = graph.value(property_shape, SH.node)
    editor = graph.value(property_shape, SHUI.editor)
    ordered_by = graph.value(property_shape, HT.orderedBy)
    return PropertyPresentation(
        path=path,
        node=str(node) if isinstance(node, URIRef) else None,
        name=_literal_text(graph, property_shape, SH.name),
        order=Decimal(str(order)) if isinstance(order, Literal) else None,
        editor=str(editor) if editor else None,
        ordered_by=str(ordered_by) if ordered_by else None,
        identifier=str(property_shape),
    )


def _presentation_sort_key(
    prop: PropertyPresentation,
) -> tuple[bool, Decimal, str, str]:
    return (
        prop.order is None,
        prop.order if prop.order is not None else Decimal(0),
        prop.name or prop.path,
        prop.identifier,
    )


def _fixed_values(graph: Graph, property_shape: Node) -> set[Node]:
    fixed = set(graph.objects(property_shape, SH.hasValue))
    for qualified_shape in graph.objects(property_shape, SH.qualifiedValueShape):
        fixed |= set(graph.objects(qualified_shape, SH.hasValue))
    return fixed


def is_computed_property(graph: Graph, property_shape: Node) -> bool:
    return (property_shape, SH.values, None) in graph


def read_presentation(graph: Graph) -> ShapesPresentation:
    shape_names: dict[str, str] = {}
    properties: dict[str, list[PropertyPresentation]] = {}
    label_queries: dict[str, str] = {}
    fixed_type_counts: dict[str, int] = {}
    shapes = {
        shape
        for shape in set(graph.subjects(SH.targetClass))
        | set(graph.subjects(RDF.type, SH.NodeShape))
        if not isinstance(shape, BNode)
    }
    for shape in shapes:
        name = _literal_text(graph, shape, SH.name)
        if name is not None:
            shape_names[str(shape)] = name
        shape_properties = []
        fixed_types: set[Node] = set()
        for property_shape in graph.objects(shape, SH.property):
            path = graph.value(property_shape, SH.path)
            inverse_of = graph.value(path, SH.inversePath)
            if inverse_of is not None:
                shape_properties.append(
                    _property_presentation(
                        graph, property_shape, inverse_path_key(str(inverse_of))
                    )
                )
                continue
            if not isinstance(path, URIRef):
                continue
            if path == RDF.type:
                fixed_types |= _fixed_values(graph, property_shape)
            if (property_shape, SHUI.propertyRole, SHUI.LabelRole) in graph:
                label_queries[str(shape)] = _label_query(graph, property_shape, path)
            if is_computed_property(graph, property_shape):
                continue
            shape_properties.append(
                _property_presentation(graph, property_shape, str(path))
            )
        properties[str(shape)] = sorted(shape_properties, key=_presentation_sort_key)
        fixed_type_counts[str(shape)] = len(fixed_types)
    return ShapesPresentation(
        shape_names=shape_names,
        properties=properties,
        label_queries=label_queries,
        fixed_type_counts=fixed_type_counts,
        hidden_shapes=frozenset(
            str(shape) for shape in shapes if (shape, DASH.hidden, _TRUE) in graph
        ),
        duplicate_keys={
            str(shape): keys
            for shape in shapes
            if (keys := read_duplicate_keys(graph, shape))
        },
    )


def _binds_focus_node_as_object(query: str) -> bool:
    try:
        algebra = translateQuery(parseQuery(query)).algebra
    except ParseException:
        # rdflib evaluates label queries against snapshot graphs with this same
        # parser, so a query it cannot parse cannot produce a label there and
        # cannot need incoming references either.
        logging.getLogger(__name__).warning(
            "Label query is not valid SPARQL and will not render in entity history: %s",
            query,
        )
        return False
    found = False

    def visit(node: object) -> None:
        nonlocal found
        triples = getattr(node, "triples", None)
        if triples is None:
            return
        for triple in triples:
            if triple[2] == _INVERSE_PROBE:
                found = True

    traverse(algebra, visitPre=visit)
    return found


# A label query that binds the focus node as an object resolves the label from
# entities pointing at the current one, so history retrieval must collect
# reverse relations to render it. That means reconstructing the history of every
# referring entity, so it is done only when a label query actually needs it.
def labels_use_inverse_relations(presentation: ShapesPresentation) -> bool:
    return any(
        _binds_focus_node_as_object(
            cast("str", presentation.label_query(shape, str(_INVERSE_PROBE)))
        )
        for shape in presentation.label_queries
    )
