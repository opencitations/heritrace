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

from heritrace.configuration.shapes import (
    read_shapes,
    shape_subjects,
    unsupported_parts,
)
from heritrace.configuration.store import SHACL_FILE, write_shacl
from heritrace.configuration.validation import validate_shapes
from heritrace.configuration.vocabulary import HT, SH, SHUI
from heritrace.language import localized_texts
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
    if predicate == SH["in"]:
        return (None, RDF.rest, value) in graph
    if predicate == SH["or"]:
        return (None, RDF.rest, value) in graph or _single_alternative(graph, value)
    if predicate != RDF.rest and (subject, RDF.type, HT.ValueAlternative) in graph:
        return True
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
    _move_label_queries(result)
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
    return int(order), localized_texts(meta, field, SH.name)["en"]


# The meta-shapes declare with sh:or which fields exclude each other, and
# pyshacl reports a broken rule with the whole list. The fields that have a
# value say which rule it is.
def _exclusions(graph: Graph, meta: Graph, focus: Node, shape: Node) -> list[str]:
    pairs = [
        sorted((_meta_field(meta, shape, path), _meta_field(meta, shape, other)))
        for (excluding_shape, path), others in read_excluded_with(meta).items()
        if excluding_shape == str(shape)
        for other in others
        if (focus, URIRef(path), None) in graph
        and (focus, URIRef(other), None) in graph
    ]
    return [
        f"{focus}: {first} and {second} cannot be used together"
        for (_, first), (_, second) in pairs
    ]


def _meta_violations(graph: Graph) -> list[str]:
    meta = load_rdf_file(META_SHAPES)
    conforms, report, _ = validate(graph, shacl_graph=meta)
    if conforms:
        return []
    report = cast("Graph", report)
    results = set(report.subjects(RDF.type, SH.ValidationResult))
    # pyshacl also reports each sh:node that leads to a node with results of its
    # own, which only repeats them.
    checked = {report.value(result, SH.focusNode) for result in results}
    issues: set[str] = set()
    for result in results:
        if (
            report.value(result, SH.sourceConstraintComponent)
            == SH.NodeConstraintComponent
            and report.value(result, SH.value) in checked
        ):
            continue
        focus = cast("Node", report.value(result, SH.focusNode))
        exclusions = (
            _exclusions(
                graph, meta, focus, cast("Node", report.value(result, SH.sourceShape))
            )
            if report.value(result, SH.sourceConstraintComponent)
            == SH.OrConstraintComponent
            else []
        )
        issues.update(
            exclusions
            or [
                f"{focus} {report.value(result, SH.resultPath)}:"
                f" {report.value(result, SH.resultMessage)}"
            ]
        )
    return sorted(issues)


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
        problems.append(
            "Each value alternative needs a datatype, SHACL shape, class or value"
        )
    if len(kinds - {None}) > 1:
        problems.append("The value alternatives of a field use the same constraint")
    return problems


def _alternative_conflicts(graph: Graph) -> list[str]:
    return [
        f"{shape}: {problem}"
        for shape, field in graph.subject_objects(SH.property)
        if (field, SH["or"], None) in graph
        for problem in _alternative_problems(graph, field)
    ]


def check_configuration(graph: Graph) -> None:
    shapes_graph = canonical(graph)
    shapes = read_shapes(shapes_graph)
    violations = _meta_violations(graph)
    conflicts = _alternative_conflicts(graph)
    # The parts that a violation leaves out would only repeat it less readably.
    unsupported = (
        [] if violations or conflicts else unsupported_parts(shapes_graph, shapes)
    )
    issues = (
        violations
        + conflicts
        + [f"{issue.location}: {issue.message}" for issue in validate_shapes(shapes)]
        + [f"HERITRACE cannot represent {part}" for part in unsupported]
    )
    if issues:
        raise ConfigurationRejectedError(issues)


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
