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
# nodes of SHACL become skolem IRIs in the stored file. A new node shape gets an
# IRI of its own instead, because the dataset tells its shapes apart by IRI.
ROOT = URIRef("https://w3id.org/heritrace/configuration")
GENID = "https://w3id.org/heritrace/genid/"
SHAPE_NAMESPACE = "https://w3id.org/heritrace/shape/"
SYSTEM_AGENT = URIRef("https://w3id.org/heritrace/system")
PROVENANCE_FILE = "shacl-provenance.trig"
META_DIR = Path(__file__).parent / "meta"
META_SHAPES = META_DIR / "shapes.ttl"
META_DISPLAY_RULES = META_DIR / "display_rules.yaml"


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
    return (
        predicate == RDF.type
        and value == SH.PropertyShape
        and (None, SH.property, subject) in graph
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


def read_shacl(config_dir: Path) -> Graph:
    return canonical(load_rdf_file(config_dir / SHACL_FILE))


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


# A configuration without provenance, such as the one the seed copies, becomes
# the entity's first version, attributed to HERITRACE itself.
def ensure_configuration_entity(config_dir: Path) -> None:
    provenance_path = config_dir / PROVENANCE_FILE
    with configuration_lock(config_dir):
        if provenance_path.exists():
            return
        shacl_path = config_dir / SHACL_FILE
        source = Graph()
        if shacl_path.exists():
            source.parse(shacl_path, format="turtle")
        data = normalize(source)
        check_configuration(data)
        graph = OCDMGraph(InMemoryCounterHandler())
        for triple in data:
            graph.add(triple, resp_agent=SYSTEM_AGENT)
        graph.generate_provenance(
            shacl_path.stat().st_mtime if shacl_path.exists() else time.time()
        )
        write_shacl(config_dir, data)
        Storer(graph.provenance).store_file(provenance_path)
