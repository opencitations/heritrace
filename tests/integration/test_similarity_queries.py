# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from collections import defaultdict

import pytest
from rdflib import XSD, Literal, URIRef
from SPARQLWrapper import JSON, POST, SPARQLWrapper

from heritrace.routes.merge import _build_union_blocks
from tests.test_config import TestConfig


@pytest.mark.parametrize(
    ("value", "matching", "different"),
    [
        (
            Literal("doi value"),
            Literal("doi value"),
            Literal("other"),
        ),
        (
            Literal("doi value", datatype=XSD.string),
            Literal("doi value", datatype=XSD.string),
            Literal("other", datatype=XSD.string),
        ),
        (
            Literal("title", lang="en"),
            Literal("title", lang="en"),
            Literal("title", lang="it"),
        ),
        (
            URIRef("urn:scheme:doi"),
            URIRef("urn:scheme:doi"),
            URIRef("urn:scheme:orcid"),
        ),
        (
            Literal("1", datatype=XSD.integer),
            Literal("1", datatype=XSD.integer),
            Literal(2),
        ),
    ],
)
def test_similarity_matches_configured_values(app, value, matching, different):
    predicate = "urn:similarity:property"
    graph_uri = "urn:similarity:test"
    sparql = SPARQLWrapper(TestConfig.DATASET_DB_URL)
    sparql.setMethod(POST)
    sparql.setReturnFormat(JSON)
    sparql.setQuery(f"""
        INSERT DATA {{ GRAPH <{graph_uri}> {{
            <urn:matching> <{predicate}> {matching.n3()} .
            <urn:different> <{predicate}> {different.n3()} .
        }} }}
    """)
    sparql.query()
    try:
        blocks = _build_union_blocks(
            [[predicate]], defaultdict(list, {predicate: [value.n3()]})
        )
        sparql.setQuery(
            f"SELECT DISTINCT ?similar FROM <{graph_uri}> WHERE {{ "
            + " UNION ".join(blocks)
            + " }"
        )
        results = sparql.query().convert()
        assert results["results"]["bindings"] == [
            {"similar": {"type": "uri", "value": "urn:matching"}}
        ]
    finally:
        sparql.setQuery(f"CLEAR GRAPH <{graph_uri}>")
        sparql.query()
