# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from pathlib import Path

import yaml
from pyshacl import validate
from rdflib import RDF, Dataset, Graph, Namespace, URIRef

ROOT = Path(__file__).parents[2]
DEMO_ROOT = ROOT / "demo" / "iswc2026"
FABIO = Namespace("http://purl.org/spar/fabio/")
DATACITE = Namespace("http://purl.org/spar/datacite/")
DCTERMS = Namespace("http://purl.org/dc/terms/")
RETAINED_NILSSON = URIRef("https://w3id.org/oc/meta/br/06601213255")
PUBMED_NILSSON = URIRef("https://w3id.org/oc/meta/demo/br/pubmed-15849057")
PUBMED_MALTEZOU = URIRef("https://w3id.org/oc/meta/demo/br/pubmed-15370649")
DOI = URIRef("https://w3id.org/oc/meta/id/06601260376")
NILSSON_PMID = URIRef("https://w3id.org/oc/meta/id/06103979651")
MALTEZOU_PMID = URIRef("https://w3id.org/oc/meta/id/06103979528")


def _load_demo_graph() -> Graph:
    dataset = Dataset()
    dataset.parse(DEMO_ROOT / "data" / "dataset.nq", format="nquads")
    graph = Graph()
    for triple, _contexts in dataset.store.triples((None, None, None)):
        graph.add(triple)
    return graph


def test_iswc2026_demo_exposes_the_two_documented_merge_candidates() -> None:
    graph = _load_demo_graph()
    shacl_graph = Graph().parse(DEMO_ROOT / "config" / "shacl.ttl", format="turtle")
    conforms, _, _ = validate(
        graph,
        shacl_graph=shacl_graph,
    )
    assert conforms is True

    with (DEMO_ROOT / "config" / "display_rules.yaml").open() as stream:
        display_rules = yaml.safe_load(stream)
    article_rule = next(
        rule
        for rule in display_rules["rules"]
        if rule["target"]["class"] == str(FABIO.JournalArticle)
    )
    similarity_properties = [
        URIRef(property_uri) for property_uri in article_rule["similarity_properties"]
    ]

    articles = set(graph.subjects(RDF.type, FABIO.JournalArticle))
    matches = {
        article: {
            property_uri
            for property_uri in similarity_properties
            if set(graph.objects(RETAINED_NILSSON, property_uri))
            & set(graph.objects(article, property_uri))
        }
        for article in articles - {RETAINED_NILSSON}
    }

    assert matches == {
        PUBMED_NILSSON: {DCTERMS.title, DATACITE.hasIdentifier},
        PUBMED_MALTEZOU: {DATACITE.hasIdentifier},
    }
    assert set(graph.objects(RETAINED_NILSSON, DATACITE.hasIdentifier)) == {DOI}
    assert set(graph.objects(PUBMED_NILSSON, DATACITE.hasIdentifier)) == {
        DOI,
        NILSSON_PMID,
    }
    assert set(graph.objects(PUBMED_MALTEZOU, DATACITE.hasIdentifier)) == {
        DOI,
        MALTEZOU_PMID,
    }
