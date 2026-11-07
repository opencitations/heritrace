# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from collections import Counter
from dataclasses import dataclass, field
from typing import Literal as TypingLiteral
from typing import cast

from rdflib import RDF, XSD, BNode, Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.compare import isomorphic
from rdflib.term import Node

from heritrace.configuration.vocabulary import SH, SHUI

ValueKind = TypingLiteral["any", "datatype", "node", "value", "options", "class"]

VALUE_KINDS: tuple[ValueKind, ...] = (
    "any",
    "datatype",
    "node",
    "value",
    "options",
    "class",
)
EDITORS = (str(SHUI.TextFieldEditor), str(SHUI.TextAreaEditor))

_SINGLE_VALUE_PREDICATES: dict[ValueKind, URIRef] = {
    "datatype": SH.datatype,
    "node": SH.node,
    "value": SH.hasValue,
    "class": SH["class"],
}
_ALTERNATIVE_KINDS: tuple[ValueKind, ...] = ("datatype", "node", "value")


@dataclass
class PropertyShape:
    path: str
    name: str | None = None
    order: int | None = None
    min_count: int | None = None
    max_count: int | None = None
    editor: str | None = None
    kind: ValueKind = "any"
    values: list[str] = field(default_factory=list)
    qualified: bool = False
    label: bool = False
    label_query: str | None = None


@dataclass
class PatternRule:
    condition_path: str
    condition_value: str
    path: str
    pattern: str
    message: str | None = None


@dataclass
class NodeShape:
    iri: str
    name: str | None = None
    target_class: str | None = None
    properties: list[PropertyShape] = field(default_factory=list)
    patterns: list[PatternRule] = field(default_factory=list)


@dataclass
class Shapes:
    prefixes: dict[str, str] = field(default_factory=dict)
    shapes: list[NodeShape] = field(default_factory=list)


def _text(graph: Graph, subject: Node, predicate: URIRef) -> str | None:
    value = graph.value(subject, predicate)
    return str(value) if isinstance(value, Literal) else None


def _integer(graph: Graph, subject: Node, predicate: URIRef) -> int | None:
    value = graph.value(subject, predicate)
    if isinstance(value, Literal) and isinstance(value.toPython(), int):
        return cast("int", value.toPython())
    return None


def _iri(graph: Graph, subject: Node, predicate: URIRef) -> str | None:
    value = graph.value(subject, predicate)
    return str(value) if isinstance(value, URIRef) else None


def _only_value(graph: Graph, member: Node, predicate: URIRef) -> str | None:
    pairs = list(graph.predicate_objects(member))
    if len(pairs) == 1 and pairs[0][0] == predicate and isinstance(pairs[0][1], URIRef):
        return str(pairs[0][1])
    return None


def _alternatives(graph: Graph, target: Node) -> tuple[ValueKind, list[str]] | None:
    head = graph.value(target, SH["or"])
    if head is None:
        return None
    members = list(Collection(graph, head))
    for kind in _ALTERNATIVE_KINDS:
        predicate = _SINGLE_VALUE_PREDICATES[kind]
        values = [_only_value(graph, member, predicate) for member in members]
        if members and None not in values:
            return kind, cast("list[str]", values)
    return None


def _value_constraint(graph: Graph, target: Node) -> tuple[ValueKind, list[str]]:
    for kind, predicate in _SINGLE_VALUE_PREDICATES.items():
        value = _iri(graph, target, predicate)
        if value is not None:
            return kind, [value]
    options = graph.value(target, SH["in"])
    if options is not None:
        return "options", [str(option) for option in Collection(graph, options)]
    return _alternatives(graph, target) or ("any", [])


def _read_property(graph: Graph, property_shape: Node) -> PropertyShape | None:
    path = _iri(graph, property_shape, SH.path)
    if path is None:
        return None
    qualified_shape = graph.value(property_shape, SH.qualifiedValueShape)
    prop = PropertyShape(
        path=path,
        name=_text(graph, property_shape, SH.name),
        order=_integer(graph, property_shape, SH.order),
        editor=_iri(graph, property_shape, SHUI.editor),
        label=(property_shape, SHUI.propertyRole, SHUI.LabelRole) in graph,
    )
    if qualified_shape is not None:
        prop.qualified = True
        prop.kind, prop.values = _value_constraint(graph, qualified_shape)
        prop.min_count = _integer(graph, property_shape, SH.qualifiedMinCount)
        prop.max_count = _integer(graph, property_shape, SH.qualifiedMaxCount)
    else:
        prop.kind, prop.values = _value_constraint(graph, property_shape)
        prop.min_count = _integer(graph, property_shape, SH.minCount)
        prop.max_count = _integer(graph, property_shape, SH.maxCount)
    computed = graph.value(property_shape, SH.values)
    if computed is not None:
        prop.label_query = _text(graph, computed, SH.select)
    return prop


def _read_pattern_rule(graph: Graph, alternative: Node) -> PatternRule | None:
    condition = None
    constraint = None
    for property_shape in graph.objects(alternative, SH.property):
        if (property_shape, SH.hasValue, None) in graph:
            condition = property_shape
        elif (property_shape, SH.pattern, None) in graph:
            constraint = property_shape
    if condition is None or constraint is None:
        return None
    condition_path = _iri(graph, condition, SH.path)
    condition_value = _iri(graph, condition, SH.hasValue)
    path = _iri(graph, constraint, SH.path)
    pattern = _text(graph, constraint, SH.pattern)
    if None in (condition_path, condition_value, path, pattern):
        return None
    return PatternRule(
        condition_path=cast("str", condition_path),
        condition_value=cast("str", condition_value),
        path=cast("str", path),
        pattern=cast("str", pattern),
        message=_text(graph, constraint, SH.message),
    )


def _read_patterns(graph: Graph, shape: URIRef) -> list[PatternRule]:
    head = graph.value(shape, SH["or"])
    if head is None:
        return []
    rules = [_read_pattern_rule(graph, item) for item in Collection(graph, head)]
    return [rule for rule in rules if rule is not None]


def _property_sort_key(prop: PropertyShape) -> tuple[bool, int, str]:
    return (prop.order is None, prop.order or 0, prop.name or prop.path)


def shape_subjects(graph: Graph) -> list[URIRef]:
    subjects = set(graph.subjects(SH.targetClass)) | set(
        graph.subjects(RDF.type, SH.NodeShape)
    )
    return sorted(subject for subject in subjects if isinstance(subject, URIRef))


def _declaration_owners(graph: Graph) -> list[Node]:
    return list(graph.subjects(RDF.type, SH.ShapesGraph))


def read_shapes(graph: Graph) -> Shapes:
    prefixes = {
        str(graph.value(declaration, SH.prefix)): str(
            graph.value(declaration, SH.namespace)
        )
        for owner in _declaration_owners(graph)
        for declaration in graph.objects(owner, SH.declare)
    }
    shapes = []
    for subject in shape_subjects(graph):
        properties = [
            prop
            for property_shape in graph.objects(subject, SH.property)
            if (prop := _read_property(graph, property_shape)) is not None
        ]
        shapes.append(
            NodeShape(
                iri=str(subject),
                name=_text(graph, subject, SH.name),
                target_class=_iri(graph, subject, SH.targetClass),
                properties=sorted(properties, key=_property_sort_key),
                patterns=_read_patterns(graph, subject),
            )
        )
    return Shapes(prefixes=dict(sorted(prefixes.items())), shapes=shapes)


def _add_list(graph: Graph, items: list[Node]) -> BNode:
    head = BNode()
    Collection(graph, head, items)
    return head


def _add_value_constraint(graph: Graph, target: Node, prop: PropertyShape) -> None:
    if prop.kind == "any":
        return
    values: list[Node] = [URIRef(value) for value in prop.values]
    if prop.kind == "options":
        graph.add((target, SH["in"], _add_list(graph, values)))
        return
    predicate = _SINGLE_VALUE_PREDICATES[prop.kind]
    if len(values) == 1:
        graph.add((target, predicate, values[0]))
        return
    members: list[Node] = []
    for value in values:
        member = BNode()
        graph.add((member, predicate, value))
        members.append(member)
    graph.add((target, SH["or"], _add_list(graph, members)))


def _add_property(graph: Graph, shape: URIRef, prop: PropertyShape) -> None:
    node = BNode()
    graph.add((shape, SH.property, node))
    graph.add((node, SH.path, URIRef(prop.path)))
    if prop.name is not None:
        graph.add((node, SH.name, Literal(prop.name)))
    if prop.order is not None:
        graph.add((node, SH.order, Literal(prop.order)))
    if prop.editor is not None:
        graph.add((node, SHUI.editor, URIRef(prop.editor)))
    if prop.label:
        graph.add((node, SHUI.propertyRole, SHUI.LabelRole))
    if prop.label_query is not None:
        computed = BNode()
        graph.add((node, SH.values, computed))
        graph.add((computed, SH.select, Literal(prop.label_query)))
    min_predicate, max_predicate = (
        (SH.qualifiedMinCount, SH.qualifiedMaxCount)
        if prop.qualified
        else (SH.minCount, SH.maxCount)
    )
    if prop.min_count is not None:
        graph.add((node, min_predicate, Literal(prop.min_count)))
    if prop.max_count is not None:
        graph.add((node, max_predicate, Literal(prop.max_count)))
    if prop.qualified:
        qualified_shape = BNode()
        graph.add((node, SH.qualifiedValueShape, qualified_shape))
        _add_value_constraint(graph, qualified_shape, prop)
    else:
        _add_value_constraint(graph, node, prop)


def _add_pattern_rules(graph: Graph, shape: URIRef, rules: list[PatternRule]) -> None:
    alternatives: list[Node] = []
    for rule in rules:
        alternative = BNode()
        condition = BNode()
        constraint = BNode()
        graph.add((alternative, SH.property, condition))
        graph.add((alternative, SH.property, constraint))
        graph.add((condition, SH.path, URIRef(rule.condition_path)))
        graph.add((condition, SH.hasValue, URIRef(rule.condition_value)))
        graph.add((constraint, SH.path, URIRef(rule.path)))
        graph.add((constraint, SH.pattern, Literal(rule.pattern)))
        if rule.message is not None:
            graph.add((constraint, SH.message, Literal(rule.message)))
        alternatives.append(alternative)
    graph.add((shape, SH["or"], _add_list(graph, alternatives)))


def shapes_to_graph(shapes: Shapes) -> Graph:
    graph = Graph()
    if shapes.prefixes:
        owner = BNode()
        graph.add((owner, RDF.type, SH.ShapesGraph))
        for prefix, namespace in shapes.prefixes.items():
            declaration = BNode()
            graph.add((owner, SH.declare, declaration))
            graph.add((declaration, SH.prefix, Literal(prefix)))
            graph.add(
                (declaration, SH.namespace, Literal(namespace, datatype=XSD.anyURI))
            )
    for shape in shapes.shapes:
        subject = URIRef(shape.iri)
        graph.add((subject, RDF.type, SH.NodeShape))
        if shape.name is not None:
            graph.add((subject, SH.name, Literal(shape.name)))
        if shape.target_class is not None:
            graph.add((subject, SH.targetClass, URIRef(shape.target_class)))
        for prop in shape.properties:
            _add_property(graph, subject, prop)
        if shape.patterns:
            _add_pattern_rules(graph, subject, shape.patterns)
    return graph


def _predicate_counts(graph: Graph) -> Counter[str]:
    return Counter(
        graph.namespace_manager.normalizeUri(str(p)) for p in graph.predicates()
    )


def _cbd(graph: Graph, subject: Node) -> Graph:
    description = graph.cbd(subject)
    description.namespace_manager = graph.namespace_manager
    return description


def unsupported_parts(graph: Graph, shapes: Shapes) -> list[str]:
    graph.bind("sh", SH)
    graph.bind("shui", SHUI)
    regenerated = shapes_to_graph(shapes)
    warnings = []
    covered = Graph()
    for owner in _declaration_owners(graph):
        covered += _cbd(graph, owner)
    for subject in shape_subjects(graph):
        original = _cbd(graph, subject)
        covered += original
        if isomorphic(original, _cbd(regenerated, subject)):
            continue
        missing = _predicate_counts(original) - _predicate_counts(
            _cbd(regenerated, subject)
        )
        details = ", ".join(
            f"{name} ({count})" for name, count in sorted(missing.items())
        )
        warnings.append(f"{subject}: {details}" if details else str(subject))
    outside = len(graph - covered)
    if outside:
        warnings.append(f"{outside} triples outside any shape")
    return warnings
