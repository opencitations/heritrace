# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import time
from collections import Counter
from pathlib import Path
from typing import cast
from uuid import uuid4

from filelock import FileLock
from pyshacl import validate
from rdflib import DCTERMS, OWL, PROV, RDF, RDFS, BNode, Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.compare import isomorphic
from rdflib.term import Node
from rdflib_ocdm.counter_handler.in_memory_counter_handler import InMemoryCounterHandler
from rdflib_ocdm.ocdm_graph import OCDMGraph
from rdflib_ocdm.storer import Storer

from heritrace.configuration.labels import compact_iri
from heritrace.configuration.shapes import (
    read_shapes,
    shape_subjects,
    unsupported_parts,
)
from heritrace.configuration.store import SHACL_FILE, write_shacl
from heritrace.configuration.validation import validate_shapes
from heritrace.configuration.vocabulary import HT, SH, SHUI
from heritrace.field_errors import FieldError, RejectedError, field_error
from heritrace.language import localize, localized_texts
from heritrace.rdf_files import load_rdf_file
from heritrace.sparql import SPARQLWrapperWithRetry
from heritrace.uri_generator.uri_generator import URIGenerator
from heritrace.utils.shacl_patterns import read_excluded_with

# Admins edit the whole SHACL configuration as one HERITRACE entity: a
# sh:ShapesGraph with a fixed IRI that holds the node shapes through
# dcterms:hasPart. The entity engine needs an IRI for every node, so the blank
# nodes of SHACL become skolem IRIs in the editor's copy of the shapes. A new
# node shape gets an IRI of its own instead, because the dataset tells its
# shapes apart by IRI.
ROOT = URIRef("https://w3id.org/heritrace/configuration")
GENID = "https://w3id.org/heritrace/genid/"
SHAPE_NAMESPACE = "https://w3id.org/heritrace/shape/"
SYSTEM_AGENT = URIRef("https://w3id.org/heritrace/system")
EDITOR_FILE = "shacl-editor.ttl"
PROVENANCE_FILE = "shacl-provenance.trig"
META_DIR = Path(__file__).parent / "meta"
META_SHAPES = META_DIR / "shapes.ttl"


class ConfigurationRejectedError(Exception):
    def __init__(self, issues: list[str]) -> None:
        super().__init__("; ".join(issues))
        self.issues = issues


def skolem_iri() -> URIRef:
    return URIRef(f"{GENID}{uuid4().hex}")


class SkolemURIGenerator(URIGenerator):
    def generate_uri(
        self, entity_type: str | None = None, _context_data: dict | None = None
    ) -> str:
        if entity_type == str(SH.NodeShape):
            return f"{SHAPE_NAMESPACE}{uuid4().hex}"
        return str(skolem_iri())

    def initialize_counters(self, sparql: SPARQLWrapperWithRetry) -> None:
        pass


_HELPER_TYPES = (
    SH.PrefixDeclaration,
    HT.InversePath,
    HT.QualifiedValueShape,
    HT.AllowedValue,
    HT.ValueAlternative,
    HT.PatternRule,
    HT.DuplicateCriterion,
    HT.SelectExpression,
)


def _is_helper_triple(graph: Graph, triple: tuple[Node, Node, Node]) -> bool:
    subject, predicate, value = triple
    if (subject == ROOT and predicate == DCTERMS.hasPart) or predicate in (
        HT.keyProperty,
        HT.labelQuery,
    ):
        return True
    if (
        any((node, RDF.type, HT.PatternRule) in graph for node in (subject, value))
        or (predicate != RDF.rest and (subject, RDF.type, HT.ValueAlternative) in graph)
        or (predicate == SH.hasValue and len(_counted_values(graph, subject)) > 1)
    ):
        return True
    if predicate == SH["in"]:
        return (None, RDF.rest, value) in graph
    if predicate == SH["or"]:
        return (None, RDF.rest, value) in graph or _single_alternative(graph, value)
    if predicate != RDF.type:
        return False
    return value in _HELPER_TYPES or (
        value == SH.PropertyShape and (None, SH.property, subject) in graph
    )


def _list_cells(graph: Graph, head: Node) -> list[Node]:
    cells = []
    while head != RDF.nil:
        cells.append(head)
        head = cast("Node", graph.value(head, RDF.rest))
    return cells


# The editor shows the allowed values of a field as ordered resources: each
# cell of the list belongs to the field and leads to the next one.
def _add_allowed_values(graph: Graph, property_shape: Node) -> None:
    for head in list(graph.objects(property_shape, SH["in"])):
        for cell in _list_cells(graph, head):
            graph.add((property_shape, SH["in"], cell))
            graph.add((cell, RDF.type, HT.AllowedValue))


# The alternatives of a field are ordered in the same way, and each cell of the
# list also takes the constraints of its alternative.
def _add_value_alternatives(graph: Graph, property_shape: Node) -> None:
    for head in list(graph.objects(property_shape, SH["or"])):
        for cell in _list_cells(graph, head):
            alternative = cast("Node", graph.value(cell, RDF.first))
            for predicate, value in list(graph.predicate_objects(alternative)):
                graph.add((cell, predicate, value))
            graph.remove((alternative, None, None))
            graph.remove((cell, RDF.first, alternative))
            graph.add((property_shape, SH["or"], cell))
            graph.add((cell, RDF.type, HT.ValueAlternative))


def _counted_value(graph: Graph, member: Node) -> Node | None:
    pairs = list(graph.predicate_objects(member))
    if len(pairs) == 1 and pairs[0][0] == SH.hasValue:
        return pairs[0][1]
    return None


# The values to count have no order: the editor shows an sh:or of single values
# as several values of the condition.
def _add_counted_values(graph: Graph) -> None:
    for qualified in set(graph.objects(None, SH.qualifiedValueShape)):
        for head in list(graph.objects(qualified, SH["or"])):
            cells = _list_cells(graph, head)
            members = [cast("Node", graph.value(cell, RDF.first)) for cell in cells]
            values = [_counted_value(graph, member) for member in members]
            if None in values:
                continue
            graph.remove((qualified, SH["or"], head))
            for node in (*cells, *members):
                graph.remove((node, None, None))
            for value in cast("list[Node]", values):
                graph.add((qualified, SH.hasValue, value))


def _counted_values(graph: Graph, node: Node) -> list[Node]:
    if (node, RDF.type, HT.QualifiedValueShape) not in graph:
        return []
    return sorted(graph.objects(node, SH.hasValue), key=str)


def _restore_counted_values(graph: Graph, result: Graph) -> None:
    for qualified in graph.subjects(RDF.type, HT.QualifiedValueShape):
        values = _counted_values(graph, qualified)
        if len(values) <= 1:
            continue
        members = []
        for value in values:
            member = BNode()
            result.add((member, SH.hasValue, value))
            members.append(member)
        head = BNode()
        Collection(result, head, members)
        result.add((_restore(qualified), SH["or"], head))


# A rule of a resource type pairs the field that sets the condition with the
# field whose format it checks.
_RULE_CONDITION: dict[Node, URIRef] = {
    SH.path: HT.conditionPath,
    SH.hasValue: HT.conditionValue,
}
_RULE_CHECK: dict[Node, URIRef] = {
    SH.path: HT.checkedPath,
    SH.pattern: SH.pattern,
    SH.message: SH.message,
}
_RULE_REQUIRED = {HT.conditionPath, HT.conditionValue, HT.checkedPath, SH.pattern}


def _pattern_rule(graph: Graph, alternative: Node) -> list[tuple[Node, Node]] | None:
    property_shapes = list(graph.objects(alternative, SH.property))
    conditions = [
        shape for shape in property_shapes if (shape, SH.hasValue, None) in graph
    ]
    checks = [shape for shape in property_shapes if shape not in conditions]
    if (
        set(graph.predicates(alternative)) != {SH.property}
        or len(conditions) != 1
        or len(checks) != 1
    ):
        return None
    rule = []
    for property_shape, fields in (
        (conditions[0], _RULE_CONDITION),
        (checks[0], _RULE_CHECK),
    ):
        pairs = list(graph.predicate_objects(property_shape))
        if not {predicate for predicate, _ in pairs} <= fields.keys():
            return None
        rule.extend((fields[predicate], value) for predicate, value in pairs)
    if _RULE_REQUIRED - {predicate for predicate, _ in rule}:
        return None
    return rule


# The rules of a resource type have no order: the editor shows each one as a
# resource of the type that holds both fields.
def _add_pattern_rules(graph: Graph, shape: Node) -> None:
    for head in list(graph.objects(shape, SH["or"])):
        cells = _list_cells(graph, head)
        alternatives = [cast("Node", graph.value(cell, RDF.first)) for cell in cells]
        rules = [_pattern_rule(graph, alternative) for alternative in alternatives]
        if None in rules:
            continue
        graph.remove((shape, SH["or"], head))
        for cell, alternative, rule in zip(cells, alternatives, rules, strict=True):
            for property_shape in list(graph.objects(alternative, SH.property)):
                graph.remove((property_shape, None, None))
            graph.remove((alternative, None, None))
            graph.remove((cell, None, None))
            for predicate, value in cast("list[tuple[Node, Node]]", rule):
                graph.add((cell, predicate, value))
            graph.add((cell, RDF.type, HT.PatternRule))
            graph.add((shape, SH["or"], cell))


# The properties of a key have no order, so the editor shows each key as a
# criterion that holds them as plain values.
def _add_duplicate_criteria(graph: Graph) -> None:
    for head in set(graph.objects(None, OWL.hasKey)):
        cells = _list_cells(graph, head)
        properties = [graph.value(cell, RDF.first) for cell in cells]
        for cell in cells:
            graph.remove((cell, RDF.first, None))
            graph.remove((cell, RDF.rest, None))
        for prop in properties:
            graph.add((head, HT.keyProperty, cast("Node", prop)))
        graph.add((head, RDF.type, HT.DuplicateCriterion))


_LABEL_FIELD = {SH.path, SHUI.propertyRole, SH.values}


# HERITRACE computes sh:values only for the label of a resource, which is why
# the editor shows the label query on the resource type. A label field written
# by hand in another form stays a field.
def _move_label_queries(graph: Graph) -> None:
    for field in set(graph.subjects(SHUI.propertyRole, SHUI.LabelRole)):
        owners = list(graph.subjects(SH.property, field))
        if (
            len(owners) != 1
            or set(graph.predicates(field)) != _LABEL_FIELD
            or graph.value(field, SH.path) != RDFS.label
        ):
            continue
        graph.add(
            (owners[0], HT.labelQuery, cast("Node", graph.value(field, SH.values)))
        )
        graph.remove((owners[0], SH.property, field))
        graph.remove((field, None, None))


# The meta-shapes reach the blank nodes nested in a field through their type.
def _type_nested_nodes(graph: Graph) -> None:
    for inverse_path in set(graph.subjects(SH.inversePath)):
        graph.add((inverse_path, RDF.type, HT.InversePath))
    for predicate, helper_type in (
        (SH.qualifiedValueShape, HT.QualifiedValueShape),
        (HT.labelQuery, HT.SelectExpression),
    ):
        for node in set(graph.objects(None, predicate)):
            graph.add((node, RDF.type, helper_type))


def normalize(graph: Graph) -> Graph:
    owners = list(graph.subjects(RDF.type, SH.ShapesGraph))
    if len(owners) > 1:
        msg = "The configuration has more than one sh:ShapesGraph"
        raise ConfigurationRejectedError([msg])
    names: dict[Node, URIRef] = dict.fromkeys(owners, ROOT)

    def rename(node: Node) -> Node:
        if isinstance(node, BNode) or node in names:
            return names.setdefault(node, skolem_iri())
        return node

    result = Graph()
    for subject, predicate, value in graph:
        result.add((rename(subject), predicate, rename(value)))
    result.add((ROOT, RDF.type, SH.ShapesGraph))
    for shape in shape_subjects(result):
        result.add((ROOT, DCTERMS.hasPart, shape))
        result.add((shape, RDF.type, SH.NodeShape))
        _add_pattern_rules(result, shape)
    _move_label_queries(result)
    _add_counted_values(result)
    for property_shape in set(result.objects(None, SH.property)):
        result.add((property_shape, RDF.type, SH.PropertyShape))
        _add_allowed_values(result, property_shape)
        _add_value_alternatives(result, property_shape)
    for declaration in set(result.objects(ROOT, SH.declare)):
        result.add((declaration, RDF.type, SH.PrefixDeclaration))
    _type_nested_nodes(result)
    _add_duplicate_criteria(result)
    return result


def _restore(node: Node) -> Node:
    if node == ROOT or str(node).startswith(GENID):
        return BNode(str(node).rsplit("/", 1)[-1])
    return node


def _single_alternative(graph: Graph, cell: Node) -> bool:
    return (
        (cell, RDF.type, HT.ValueAlternative) in graph
        and (cell, RDF.rest, None) not in graph
        and (None, RDF.rest, cell) not in graph
    )


# The cells of the ordered lists end with rdf:nil, and each alternative moves
# back from its cell to a node of its own. A single alternative means the same
# as the constraint it sets, which therefore goes on the field itself.
def _restore_list_cells(graph: Graph, result: Graph) -> None:
    for cell in graph.subjects(RDF.type, HT.AllowedValue):
        if (cell, RDF.rest, None) not in graph:
            result.add((_restore(cell), RDF.rest, RDF.nil))
    for cell in graph.subjects(RDF.type, HT.ValueAlternative):
        if _single_alternative(graph, cell):
            target = cast("Node", graph.value(predicate=SH["or"], object=cell))
        else:
            target = BNode()
            result.add((_restore(cell), RDF.first, target))
            if (cell, RDF.rest, None) not in graph:
                result.add((_restore(cell), RDF.rest, RDF.nil))
        for predicate, value in graph.predicate_objects(cell):
            if predicate not in (RDF.type, RDF.rest):
                result.add((_restore(target), predicate, _restore(value)))


def _restore_pattern_rules(graph: Graph, result: Graph) -> None:
    rules: dict[Node, list[Node]] = {}
    for rule in graph.subjects(RDF.type, HT.PatternRule):
        shape = cast("Node", graph.value(predicate=SH["or"], object=rule))
        rules.setdefault(shape, []).append(rule)
    for shape, shape_rules in rules.items():
        alternatives = []
        for rule in sorted(shape_rules, key=lambda rule: _rule_order(graph, rule)):
            alternative, condition, check = _restore(rule), BNode(), BNode()
            result.add((alternative, SH.property, condition))
            result.add((alternative, SH.property, check))
            for target, fields in ((condition, _RULE_CONDITION), (check, _RULE_CHECK)):
                for predicate, helper in fields.items():
                    for value in graph.objects(rule, helper):
                        result.add((target, predicate, _restore(value)))
            alternatives.append(alternative)
        head = BNode()
        Collection(result, head, alternatives)
        result.add((_restore(shape), SH["or"], head))


def _rule_order(graph: Graph, rule: Node) -> tuple[str, str]:
    return str(graph.value(rule, HT.conditionValue)), str(
        graph.value(rule, HT.checkedPath)
    )


def canonical(graph: Graph) -> Graph:
    result = Graph()
    for triple in graph:
        if _is_helper_triple(graph, triple):
            continue
        subject, predicate, value = triple
        if subject == ROOT and predicate == RDF.type and len(graph.cbd(ROOT)) == 1:
            continue
        result.add((_restore(subject), predicate, _restore(value)))
    _restore_list_cells(graph, result)
    _restore_pattern_rules(graph, result)
    _restore_counted_values(graph, result)
    for criterion in graph.subjects(RDF.type, HT.DuplicateCriterion):
        properties = sorted(graph.objects(criterion, HT.keyProperty), key=str)
        Collection(result, _restore(criterion), properties)
    for shape, query in graph.subject_objects(HT.labelQuery):
        field = BNode()
        result.add((_restore(shape), SH.property, field))
        result.add((field, SH.path, RDFS.label))
        result.add((field, SHUI.propertyRole, SHUI.LabelRole))
        result.add((field, SH.values, _restore(query)))
    return result


def _blank_nodes(graph: Graph) -> set[Node]:
    return {
        node
        for subject, _, value in graph
        for node in (subject, value)
        if isinstance(node, BNode)
    }


# The description of every IRI subject, then what is left of the graph. The
# parts stand for the whole graph only when no blank node belongs to two.
def _independent_parts(graph: Graph) -> tuple[dict[URIRef, Graph], Graph] | None:
    described = {
        subject: graph.cbd(subject)
        for subject in set(graph.subjects())
        if isinstance(subject, URIRef)
    }
    covered = Graph()
    for part in described.values():
        covered += part
    rest = graph - covered
    separate = sum(
        len(_blank_nodes(part)) for part in (*described.values(), rest)
    ) == len(_blank_nodes(graph))
    return (described, rest) if separate else None


# rdflib compares blank nodes in more than linear time, so a large graph is
# compared part by part.
def same_graph(first: Graph, second: Graph) -> bool:
    first_parts = _independent_parts(first)
    second_parts = _independent_parts(second)
    if first_parts is None or second_parts is None:
        return isomorphic(first, second)
    described, rest = first_parts
    other_described, other_rest = second_parts
    return (
        described.keys() == other_described.keys()
        and isomorphic(rest, other_rest)
        and all(
            isomorphic(part, other_described[subject])
            for subject, part in described.items()
        )
    )


def read_shacl(config_dir: Path) -> Graph:
    return load_rdf_file(config_dir / SHACL_FILE)


def shacl_mtime(config_dir: Path) -> int | None:
    path = config_dir / SHACL_FILE
    return path.stat().st_mtime_ns if path.exists() else None


def export_shacl(config_dir: Path, view: Graph) -> None:
    write_shacl(config_dir, canonical(view))


def _meta_field(meta: Graph, shape: Node, path: str) -> tuple[int, str]:
    field = next(
        field
        for field in meta.objects(shape, SH.property)
        if (field, SH.path, URIRef(path)) in meta
    )
    order = cast("Literal", meta.value(field, SH.order))
    return int(order), cast("str", localize(localized_texts(meta, field, SH.name)))


# The meta-shapes declare with sh:or which fields exclude each other, and
# pyshacl reports a broken rule with the whole list. The fields that have a
# value say which rule it is.
def _exclusions(
    graph: Graph, meta: Graph, focus: Node, shape: Node
) -> list[FieldError]:
    pairs = {
        tuple(
            sorted(
                (
                    (_meta_field(meta, shape, path), path),
                    (_meta_field(meta, shape, other), other),
                )
            )
        )
        for (excluding_shape, path), others in read_excluded_with(meta).items()
        if excluding_shape == str(shape)
        for other in others
        if (focus, URIRef(path), None) in graph
        and (focus, URIRef(other), None) in graph
    }
    return [
        field_error("exclusive", str(focus), second_path, first=first, second=second)
        for ((_, first), _), ((_, second), second_path) in sorted(pairs)
    ]


_BOUND_CODES = {
    SH.MinInclusiveConstraintComponent: ("atLeast", SH.minInclusive),
    SH.MaxInclusiveConstraintComponent: ("atMost", SH.maxInclusive),
    SH.MinExclusiveConstraintComponent: ("greaterThan", SH.minExclusive),
    SH.MaxExclusiveConstraintComponent: ("lessThan", SH.maxExclusive),
}
_COUNT_CODES = {
    SH.MinCountConstraintComponent: ("tooFew", "min", SH.minCount),
    SH.MaxCountConstraintComponent: ("tooMany", "max", SH.maxCount),
}
_VALUE_CODES = {
    SH.DatatypeConstraintComponent: ("invalidInput", "expected", SH.datatype),
    SH.ClassConstraintComponent: ("invalidInput", "expected", SH["class"]),
    SH.HasValueConstraintComponent: ("requiredValue", "value", SH.hasValue),
}
_PLAIN_CODES = {
    SH.NodeKindConstraintComponent: "invalidIri",
    SH.UniqueLangConstraintComponent: "languageTaken",
}


# The code of each constraint that the meta-shapes use, with the parameters of
# its message. pyshacl's own message, in English, stands for any other one.
def _meta_error(  # noqa: PLR0911
    graph: Graph, meta: Graph, report: Graph, result: Node
) -> list[FieldError]:
    component = cast("URIRef", report.value(result, SH.sourceConstraintComponent))
    source = cast("Node", report.value(result, SH.sourceShape))
    focus = cast("URIRef", report.value(result, SH.focusNode))
    path = cast("URIRef | None", report.value(result, SH.resultPath))
    namespaces = {str(namespace): prefix for prefix, namespace in meta.namespaces()}

    def constraint(predicate: URIRef) -> Node:
        return cast("Node", meta.value(source, predicate))

    def compact(node: Node) -> str:
        return compact_iri(str(node), namespaces)

    def error(code: str, **params: str | int) -> list[FieldError]:
        return [field_error(code, focus, path, **params)]

    if component == SH.OrConstraintComponent and (
        exclusions := _exclusions(graph, meta, focus, source)
    ):
        return exclusions
    if component in _COUNT_CODES:
        code, limit, predicate = _COUNT_CODES[component]
        return error(
            code,
            name=cast("str", localize(localized_texts(meta, source, SH.name))),
            count=len(set(graph.objects(focus, path))),
            **{limit: int(cast("Literal", constraint(predicate)))},
        )
    if component in _BOUND_CODES:
        code, predicate = _BOUND_CODES[component]
        return error(code, limit=str(constraint(predicate)))
    if component in _VALUE_CODES:
        code, name, predicate = _VALUE_CODES[component]
        return error(code, **{name: compact(constraint(predicate))})
    if component in _PLAIN_CODES:
        return error(_PLAIN_CODES[component])
    if component == SH.InConstraintComponent:
        options = Collection(meta, constraint(SH["in"]))
        return error("notAllowed", values=", ".join(map(compact, options)))
    message = (
        localize(localized_texts(meta, source, SH.message))
        if component == SH.PatternConstraintComponent
        else str(report.value(result, SH.resultMessage))
    )
    return error("message", message=cast("str", message))


def _meta_violations(graph: Graph) -> list[FieldError]:
    meta = load_rdf_file(META_SHAPES)
    conforms, report, _ = validate(graph, shacl_graph=meta)
    if conforms:
        return []
    report = cast("Graph", report)
    results = set(report.subjects(RDF.type, SH.ValidationResult))
    # pyshacl also reports each sh:node that leads to a node with results of its
    # own, which only repeats them.
    checked = {report.value(result, SH.focusNode) for result in results}
    return [
        error
        for result in results
        if not (
            report.value(result, SH.sourceConstraintComponent)
            == SH.NodeConstraintComponent
            and report.value(result, SH.value) in checked
        )
        for error in _meta_error(graph, meta, report, result)
    ]


_ALTERNATIVE_KINDS: dict[frozenset[Node], str] = {
    frozenset({SH.datatype}): "datatype",
    frozenset({SH.node}): "node",
    frozenset({SH.node, SH["class"]}): "node",
    frozenset({SH["class"]}): "class",
    frozenset({SH.hasValue}): "value",
}


# The meta-shapes keep each alternative to one constraint, while the
# alternatives of a field together have to set the same kind.
def _alternative_problems(graph: Graph, field: Node) -> list[str]:
    constraints = [
        frozenset(graph.predicates(cell)) - {RDF.type, RDF.rest}
        for cell in graph.objects(field, SH["or"])
    ]
    kinds = {_ALTERNATIVE_KINDS.get(predicates) for predicates in constraints}
    problems = []
    if frozenset() in constraints:
        problems.append("emptyAlternative")
    if len(kinds - {None}) > 1:
        problems.append("mixedAlternatives")
    return problems


def _alternative_conflicts(graph: Graph) -> list[FieldError]:
    return [
        field_error(problem, str(field), SH["or"])
        for field in set(graph.objects(None, SH.property))
        if (field, SH["or"], None) in graph
        for problem in _alternative_problems(graph, field)
    ]


# The inverse of _restore: the editor IRI of a node of the SHACL graph.
def _editor_iri(node: Node) -> str:
    if not isinstance(node, BNode):
        return str(node)
    return str(ROOT) if node == _restore(ROOT) else f"{GENID}{node}"


def check_configuration(graph: Graph) -> None:
    shapes_graph = canonical(graph)
    shapes = read_shapes(shapes_graph)
    violations = _meta_violations(graph)
    conflicts = _alternative_conflicts(graph)
    # The parts that a violation leaves out would only repeat it less readably.
    unsupported = (
        [] if violations or conflicts else unsupported_parts(shapes_graph, shapes)
    )
    errors = (
        violations
        + conflicts
        + validate_shapes(shapes, _editor_iri)
        + [field_error("unsupported", part=part) for part in unsupported]
    )
    if errors:
        raise RejectedError(errors)


def provenance_counter_handler(provenance_path: Path) -> InMemoryCounterHandler:
    handler = InMemoryCounterHandler()
    counts = Counter(
        str(entity)
        for _, entity in load_rdf_file(provenance_path).subject_objects(
            PROV.specializationOf
        )
    )
    for entity, count in counts.items():
        handler.set_counter(count, entity)
    return handler


def configuration_lock(config_dir: Path) -> FileLock:
    return FileLock(config_dir / f".{SHACL_FILE}.lock")


def _record_version(
    provenance_path: Path, before: Graph, after: Graph, c_time: float
) -> None:
    graph = OCDMGraph(provenance_counter_handler(provenance_path))
    for triple in before:
        graph.add(triple)
    graph.preexisting_finished(SYSTEM_AGENT, None, c_time)
    for triple in before - after:
        graph.remove(triple)
    for subject in set(before.subjects()) - set(after.subjects()):
        graph.mark_as_deleted(cast("URIRef", subject))
    for triple in after - before:
        graph.add(triple, resp_agent=SYSTEM_AGENT)
    graph.generate_provenance(c_time)
    Storer(graph.provenance).store_file(provenance_path)


# shacl.ttl holds the shapes with their blank nodes, and shacl-editor.ttl the
# same shapes with the skolem IRIs the history refers to. A shacl.ttl that
# differs from the editor's copy was edited by hand: its content becomes a new
# version, attributed to HERITRACE itself like the first one. Both sides of
# the comparison take the form the app writes, which leaves out what SHACL
# leaves free, such as the order of the properties of a key.
def ensure_configuration_entity(config_dir: Path) -> None:
    shacl_path = config_dir / SHACL_FILE
    editor_path = config_dir / EDITOR_FILE
    provenance_path = config_dir / PROVENANCE_FILE
    with configuration_lock(config_dir):
        source = Graph()
        if shacl_path.exists():
            source.parse(shacl_path, format="turtle")
        after = normalize(source)
        before = Graph()
        if provenance_path.exists():
            before.parse(editor_path, format="turtle")
            if same_graph(canonical(before), canonical(after)):
                return
        check_configuration(after)
        c_time = shacl_path.stat().st_mtime if shacl_path.exists() else time.time()
        after.serialize(editor_path, format="turtle")
        _record_version(provenance_path, before, after, c_time)
        if not shacl_path.exists():
            write_shacl(config_dir, source)
