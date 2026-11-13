# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from collections import Counter
from dataclasses import dataclass, field
from typing import Literal as TypingLiteral
from typing import cast

from rdflib import OWL, RDF, RDFS, XSD, BNode, Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.compare import isomorphic
from rdflib.term import Node

from heritrace.configuration.vocabulary import DASH, HT, SH, SHUI
from heritrace.language import (
    LANGUAGES,
    LocalizedText,
    add_localized_texts,
    localized_texts,
    pick_text,
)

ValueKind = TypingLiteral["any", "datatype", "node", "value", "options", "class"]

VALUE_KINDS: tuple[ValueKind, ...] = (
    "any",
    "datatype",
    "node",
    "value",
    "options",
    "class",
)
EDITORS = (
    str(SHUI.TextFieldEditor),
    str(SHUI.TextAreaEditor),
    str(SHUI.TextFieldWithLangEditor),
    str(SHUI.TextAreaWithLangEditor),
    str(SHUI.AutoCompleteEditor),
    str(SHUI.DetailsEditor),
)
VIEWERS = (str(SHUI.DetailsViewer),)

_SINGLE_VALUE_PREDICATES: dict[ValueKind, URIRef] = {
    "datatype": SH.datatype,
    "node": SH.node,
    "value": SH.hasValue,
    "class": SH["class"],
}
_ALTERNATIVE_KINDS: tuple[ValueKind, ...] = ("datatype", "node", "value", "class")


@dataclass
class PropertyShape:
    path: str
    inverse: bool = False
    names: LocalizedText = field(default_factory=dict)
    descriptions: LocalizedText = field(default_factory=dict)
    order: int | None = None
    min_count: int | None = None
    max_count: int | None = None
    min_inclusive: Literal | None = None
    max_inclusive: Literal | None = None
    min_exclusive: Literal | None = None
    max_exclusive: Literal | None = None
    editor: str | None = None
    viewer: str | None = None
    composite: bool | None = None
    hidden: bool | None = None
    unique_lang: bool | None = None
    ordered_by: str | None = None
    kind: ValueKind = "any"
    values: list[str] = field(default_factory=list)
    node_classes: dict[str, str] = field(default_factory=dict)
    qualified: bool = False
    label: bool = False
    label_query: str | None = None
    details: list[str] = field(default_factory=list)


@dataclass
class PatternRule:
    condition_path: str
    condition_value: str
    path: str
    pattern: str
    messages: LocalizedText = field(default_factory=dict)


@dataclass
class NodeShape:
    iri: str
    names: LocalizedText = field(default_factory=dict)
    target_class: str | None = None
    hidden: bool | None = None
    properties: list[PropertyShape] = field(default_factory=list)
    patterns: list[PatternRule] = field(default_factory=list)
    duplicate_keys: list[list[str]] = field(default_factory=list)


@dataclass
class ValueTexts:
    names: LocalizedText
    descriptions: LocalizedText


@dataclass
class Shapes:
    prefixes: dict[str, str] = field(default_factory=dict)
    shapes: list[NodeShape] = field(default_factory=list)
    # The rdfs:label and rdfs:comment that name and explain IRIs used as values.
    value_texts: dict[str, ValueTexts] = field(default_factory=dict)


def _text(graph: Graph, subject: Node, predicate: URIRef) -> str | None:
    value = graph.value(subject, predicate)
    return str(value) if isinstance(value, Literal) else None


def _integer(graph: Graph, subject: Node, predicate: URIRef) -> int | None:
    value = graph.value(subject, predicate)
    if isinstance(value, Literal) and isinstance(value.toPython(), int):
        return cast("int", value.toPython())
    return None


def _literal(graph: Graph, subject: Node, predicate: URIRef) -> Literal | None:
    value = graph.value(subject, predicate)
    return value if isinstance(value, Literal) else None


def _boolean(graph: Graph, subject: Node, predicate: URIRef) -> bool | None:
    value = graph.value(subject, predicate)
    if isinstance(value, Literal) and isinstance(value.toPython(), bool):
        return cast("bool", value.toPython())
    return None


def _iri(graph: Graph, subject: Node, predicate: URIRef) -> str | None:
    value = graph.value(subject, predicate)
    return str(value) if isinstance(value, URIRef) else None


def _only_value(graph: Graph, member: Node, predicate: URIRef) -> str | None:
    pairs = [
        (member_predicate, value)
        for member_predicate, value in graph.predicate_objects(member)
        if not (predicate == SH.node and member_predicate == SH["class"])
    ]
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


def _node_classes(graph: Graph, target: Node) -> dict[str, str]:
    head = graph.value(target, SH["or"])
    members = [target, *(Collection(graph, head) if head is not None else [])]
    return {
        str(node): str(node_class)
        for member in members
        if isinstance(node := graph.value(member, SH.node), URIRef)
        and isinstance(node_class := graph.value(member, SH["class"]), URIRef)
    }


def _read_property(graph: Graph, property_shape: Node) -> PropertyShape | None:
    path = graph.value(property_shape, SH.path)
    inverse_of = graph.value(path, SH.inversePath)
    if not isinstance(inverse_of or path, URIRef):
        return None
    qualified_shape = graph.value(property_shape, SH.qualifiedValueShape)
    prop = PropertyShape(
        path=str(inverse_of or path),
        inverse=inverse_of is not None,
        names=localized_texts(graph, property_shape, SH.name),
        descriptions=localized_texts(graph, property_shape, SH.description),
        order=_integer(graph, property_shape, SH.order),
        editor=_iri(graph, property_shape, SHUI.editor),
        viewer=_iri(graph, property_shape, SHUI.viewer),
        composite=_boolean(graph, property_shape, DASH.composite),
        hidden=_boolean(graph, property_shape, DASH.hidden),
        unique_lang=_boolean(graph, property_shape, SH.uniqueLang),
        ordered_by=_iri(graph, property_shape, HT.orderedBy),
        label=(property_shape, SHUI.propertyRole, SHUI.LabelRole) in graph,
        min_inclusive=_literal(graph, property_shape, SH.minInclusive),
        max_inclusive=_literal(graph, property_shape, SH.maxInclusive),
        min_exclusive=_literal(graph, property_shape, SH.minExclusive),
        max_exclusive=_literal(graph, property_shape, SH.maxExclusive),
    )
    if qualified_shape is not None:
        prop.qualified = True
        prop.kind, prop.values = _value_constraint(graph, qualified_shape)
        prop.node_classes = _node_classes(graph, qualified_shape)
        prop.min_count = _integer(graph, property_shape, SH.qualifiedMinCount)
        prop.max_count = _integer(graph, property_shape, SH.qualifiedMaxCount)
    else:
        prop.kind, prop.values = _value_constraint(graph, property_shape)
        prop.node_classes = _node_classes(graph, property_shape)
        prop.min_count = _integer(graph, property_shape, SH.minCount)
        prop.max_count = _integer(graph, property_shape, SH.maxCount)
    computed = graph.value(property_shape, SH.values)
    if computed is not None:
        prop.label_query = _text(graph, computed, SH.select)
    prop.details = sorted(
        str(detail_path)
        for detail in graph.objects(property_shape, SH.property)
        if isinstance(detail_path := graph.value(detail, SH.path), URIRef)
    )
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
        messages=localized_texts(graph, constraint, SH.message),
    )


def _read_patterns(graph: Graph, shape: URIRef) -> list[PatternRule]:
    head = graph.value(shape, SH["or"])
    if head is None:
        return []
    rules = [_read_pattern_rule(graph, item) for item in Collection(graph, head)]
    return [rule for rule in rules if rule is not None]


def read_duplicate_keys(graph: Graph, shape: Node) -> list[list[str]]:
    return sorted(
        [str(prop) for prop in Collection(graph, head)]
        for head in graph.objects(shape, OWL.hasKey)
    )


def _property_sort_key(prop: PropertyShape) -> tuple[bool, int, str]:
    return (
        prop.order is None,
        prop.order or 0,
        pick_text(prop.names, LANGUAGES[0]) or prop.path,
    )


def shape_subjects(graph: Graph) -> list[URIRef]:
    subjects = set(graph.subjects(SH.targetClass)) | set(
        graph.subjects(RDF.type, SH.NodeShape)
    )
    return sorted(subject for subject in subjects if isinstance(subject, URIRef))


def _declaration_owners(graph: Graph) -> list[Node]:
    return list(graph.subjects(RDF.type, SH.ShapesGraph))


def read_value_texts(graph: Graph) -> dict[str, ValueTexts]:
    subjects = {
        subject
        for predicate in (RDFS.label, RDFS.comment)
        for subject, text in graph.subject_objects(predicate)
        if isinstance(subject, URIRef) and isinstance(text, Literal)
    }
    return {
        str(subject): ValueTexts(
            names=localized_texts(graph, subject, RDFS.label),
            descriptions=localized_texts(graph, subject, RDFS.comment),
        )
        for subject in sorted(subjects)
    }


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
                names=localized_texts(graph, subject, SH.name),
                target_class=_iri(graph, subject, SH.targetClass),
                hidden=_boolean(graph, subject, DASH.hidden),
                properties=sorted(properties, key=_property_sort_key),
                patterns=_read_patterns(graph, subject),
                duplicate_keys=read_duplicate_keys(graph, subject),
            )
        )
    return Shapes(
        prefixes=dict(sorted(prefixes.items())),
        shapes=shapes,
        value_texts=read_value_texts(graph),
    )


def _add_list(graph: Graph, items: list[Node]) -> BNode:
    head = BNode()
    Collection(graph, head, items)
    return head


def _add_value(graph: Graph, target: Node, prop: PropertyShape, value: URIRef) -> None:
    graph.add((target, _SINGLE_VALUE_PREDICATES[prop.kind], value))
    if str(value) in prop.node_classes:
        graph.add((target, SH["class"], URIRef(prop.node_classes[str(value)])))


def _add_value_constraint(graph: Graph, target: Node, prop: PropertyShape) -> None:
    if prop.kind == "any":
        return
    values = [URIRef(value) for value in prop.values]
    if prop.kind == "options":
        graph.add((target, SH["in"], _add_list(graph, list(values))))
        return
    if len(values) == 1:
        _add_value(graph, target, prop, values[0])
        return
    members: list[Node] = []
    for value in values:
        member = BNode()
        _add_value(graph, member, prop, value)
        members.append(member)
    graph.add((target, SH["or"], _add_list(graph, members)))


def _add_path(graph: Graph, node: Node, prop: PropertyShape) -> None:
    if prop.inverse:
        path = BNode()
        graph.add((path, SH.inversePath, URIRef(prop.path)))
        graph.add((node, SH.path, path))
    else:
        graph.add((node, SH.path, URIRef(prop.path)))


def _add_widgets(graph: Graph, node: Node, prop: PropertyShape) -> None:
    if prop.editor is not None:
        graph.add((node, SHUI.editor, URIRef(prop.editor)))
    if prop.viewer is not None:
        graph.add((node, SHUI.viewer, URIRef(prop.viewer)))
    if prop.composite is not None:
        graph.add((node, DASH.composite, Literal(prop.composite)))
    if prop.hidden is not None:
        graph.add((node, DASH.hidden, Literal(prop.hidden)))
    if prop.unique_lang is not None:
        graph.add((node, SH.uniqueLang, Literal(prop.unique_lang)))
    if prop.ordered_by is not None:
        graph.add((node, HT.orderedBy, URIRef(prop.ordered_by)))
    for detail_path in prop.details:
        detail = BNode()
        graph.add((node, SH.property, detail))
        graph.add((detail, SH.path, URIRef(detail_path)))


def _add_property(graph: Graph, shape: URIRef, prop: PropertyShape) -> None:
    node = BNode()
    graph.add((shape, SH.property, node))
    _add_path(graph, node, prop)
    _add_widgets(graph, node, prop)
    add_localized_texts(graph, node, SH.name, prop.names)
    add_localized_texts(graph, node, SH.description, prop.descriptions)
    for predicate, value in (
        (SH.order, prop.order),
        (SH.minInclusive, prop.min_inclusive),
        (SH.maxInclusive, prop.max_inclusive),
        (SH.minExclusive, prop.min_exclusive),
        (SH.maxExclusive, prop.max_exclusive),
    ):
        if value is not None:
            graph.add((node, predicate, Literal(value)))
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
        add_localized_texts(graph, constraint, SH.message, rule.messages)
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
        add_localized_texts(graph, subject, SH.name, shape.names)
        if shape.target_class is not None:
            graph.add((subject, SH.targetClass, URIRef(shape.target_class)))
        if shape.hidden is not None:
            graph.add((subject, DASH.hidden, Literal(shape.hidden)))
        for key in shape.duplicate_keys:
            properties: list[Node] = [URIRef(prop) for prop in key]
            graph.add((subject, OWL.hasKey, _add_list(graph, properties)))
        for prop in shape.properties:
            _add_property(graph, subject, prop)
        if shape.patterns:
            _add_pattern_rules(graph, subject, shape.patterns)
    for value, texts in shapes.value_texts.items():
        add_localized_texts(graph, URIRef(value), RDFS.label, texts.names)
        add_localized_texts(graph, URIRef(value), RDFS.comment, texts.descriptions)
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
    for value in shapes.value_texts:
        for predicate in (RDFS.label, RDFS.comment):
            for text in graph.objects(URIRef(value), predicate):
                if isinstance(text, Literal):
                    covered.add((URIRef(value), predicate, text))
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
