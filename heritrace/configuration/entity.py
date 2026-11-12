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
from rdflib import DCTERMS, PROV, RDF, BNode, Graph, URIRef
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
from heritrace.configuration.vocabulary import SH
from heritrace.rdf_files import load_rdf_file
from heritrace.sparql import SPARQLWrapperWithRetry
from heritrace.uri_generator.uri_generator import URIGenerator

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


def _is_helper_triple(graph: Graph, triple: tuple[Node, Node, Node]) -> bool:
    subject, predicate, value = triple
    if subject == ROOT and predicate == DCTERMS.hasPart:
        return True
    if predicate != RDF.type:
        return False
    return value == SH.PrefixDeclaration or (
        value == SH.PropertyShape and (None, SH.property, subject) in graph
    )


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
    for property_shape in set(result.objects(None, SH.property)):
        result.add((property_shape, RDF.type, SH.PropertyShape))
    for declaration in set(result.objects(ROOT, SH.declare)):
        result.add((declaration, RDF.type, SH.PrefixDeclaration))
    return result


def canonical(graph: Graph) -> Graph:
    def restore(node: Node) -> Node:
        if node == ROOT or str(node).startswith(GENID):
            return BNode(str(node).rsplit("/", 1)[-1])
        return node

    result = Graph()
    for triple in graph:
        if _is_helper_triple(graph, triple):
            continue
        subject, predicate, value = triple
        if subject == ROOT and predicate == RDF.type and len(graph.cbd(ROOT)) == 1:
            continue
        result.add((restore(subject), predicate, restore(value)))
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


def _meta_violations(graph: Graph) -> list[str]:
    conforms, report, _ = validate(graph, shacl_graph=load_rdf_file(META_SHAPES))
    if conforms:
        return []
    report = cast("Graph", report)
    return sorted(
        f"{report.value(result, SH.focusNode)} {report.value(result, SH.resultPath)}:"
        f" {report.value(result, SH.resultMessage)}"
        for result in report.subjects(RDF.type, SH.ValidationResult)
    )


def check_configuration(graph: Graph) -> None:
    shapes_graph = canonical(graph)
    shapes = read_shapes(shapes_graph)
    issues = (
        _meta_violations(graph)
        + [f"{issue.location}: {issue.message}" for issue in validate_shapes(shapes)]
        + [
            f"HERITRACE cannot represent {part}"
            for part in unsupported_parts(shapes_graph, shapes)
        ]
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
# version, attributed to HERITRACE itself like the first one.
def ensure_configuration_entity(config_dir: Path) -> None:
    shacl_path = config_dir / SHACL_FILE
    editor_path = config_dir / EDITOR_FILE
    provenance_path = config_dir / PROVENANCE_FILE
    with configuration_lock(config_dir):
        source = Graph()
        if shacl_path.exists():
            source.parse(shacl_path, format="turtle")
        before = Graph()
        if provenance_path.exists():
            before.parse(editor_path, format="turtle")
            if same_graph(canonical(before), source):
                return
        after = normalize(source)
        check_configuration(after)
        c_time = shacl_path.stat().st_mtime if shacl_path.exists() else time.time()
        after.serialize(editor_path, format="turtle")
        _record_version(provenance_path, before, after, c_time)
        if not shacl_path.exists():
            write_shacl(config_dir, source)
