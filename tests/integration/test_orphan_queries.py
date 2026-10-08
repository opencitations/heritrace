# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import pytest
from rdflib import URIRef
from SPARQLWrapper import POST, SPARQLWrapper

from heritrace.utils.sparql_utils import find_orphaned_entities
from tests.test_config import TestConfig


@pytest.mark.parametrize("backend", ["virtuoso", "qlever", "default"])
@pytest.mark.parametrize(
    ("candidate", "expected_orphans", "expected_intermediates"),
    [
        (None, ["backlink", "leaf"], ["proxy"]),
        ("leaf", ["leaf"], []),
        ("shared", [], []),
        ("outgoing", [], []),
        ("backlink", [], []),
        ("proxy", [], ["proxy"]),
    ],
)
def test_orphan_detection(
    app, monkeypatch, backend, candidate, expected_orphans, expected_intermediates
):
    app.config["DATASET_DB_TRIPLESTORE"] = backend
    monkeypatch.setattr(
        "heritrace.utils.sparql_utils.get_display_rules",
        lambda: [
            {
                "target": {"class": "urn:orphan:Source"},
                "displayProperties": [
                    {
                        "intermediateRelation": {"class": "urn:orphan:Proxy"},
                    }
                ],
            }
        ],
    )
    sparql = SPARQLWrapper(TestConfig.DATASET_DB_URL)
    sparql.setMethod(POST)
    sparql.setQuery("""
        PREFIX ex: <urn:orphan:>
        INSERT DATA { GRAPH ex:test {
            ex:source a ex:Source ;
                ex:link ex:leaf, ex:shared, ex:outgoing, ex:backlink, ex:proxy .
            ex:leaf a ex:Entity .
            ex:shared a ex:Entity .
            ex:other ex:link ex:shared .
            ex:outgoing a ex:Entity ; ex:link ex:active .
            ex:active ex:label "active" .
            ex:backlink a ex:Entity ; ex:link ex:source .
            ex:proxy a ex:Proxy .
            ex:unrelated a ex:Entity .
        } }
    """)
    sparql.query()
    try:
        orphans, intermediates = find_orphaned_entities(
            URIRef("urn:orphan:source"),
            "urn:orphan:Source",
            URIRef("urn:orphan:link") if candidate else None,
            f"urn:orphan:{candidate}" if candidate else None,
        )
        assert sorted(orphans, key=lambda item: item["uri"]) == [
            {"uri": f"urn:orphan:{name}", "type": "urn:orphan:Entity"}
            for name in expected_orphans
        ]
        assert intermediates == [
            {"uri": f"urn:orphan:{name}", "type": "urn:orphan:Proxy"}
            for name in expected_intermediates
        ]
    finally:
        sparql.setQuery("CLEAR GRAPH <urn:orphan:test>")
        sparql.query()
