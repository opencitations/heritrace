# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import pytest
from rdflib import URIRef
from SPARQLWrapper import POST, SPARQLWrapper

from heritrace.utils.sparql_utils import find_orphaned_entities
from tests.test_config import TestConfig

COMPOSITE_FORM_FIELDS = {
    ("urn:orphan:Source", "urn:orphan:SourceShape"): {
        "urn:orphan:part": [{"uri": "urn:orphan:part", "composite": True}],
        "^urn:orphan:cites": [
            {
                "uri": "^urn:orphan:cites",
                "composite": True,
                "objectClass": "urn:orphan:Citation",
            }
        ],
        "urn:orphan:link": [{"uri": "urn:orphan:link", "composite": False}],
    }
}


@pytest.mark.parametrize("backend", ["virtuoso", "qlever", "default"])
@pytest.mark.parametrize(
    ("candidate", "expected_orphans", "expected_intermediates"),
    [
        (None, ["backlink", "leaf"], ["citation", "role"]),
        ("leaf", ["leaf"], []),
        ("shared", [], []),
        ("outgoing", [], []),
        ("backlink", [], []),
    ],
)
def test_orphan_detection(
    app, monkeypatch, backend, candidate, expected_orphans, expected_intermediates
):
    app.config["DATASET_DB_TRIPLESTORE"] = backend
    monkeypatch.setattr(
        "heritrace.utils.sparql_utils.get_form_fields",
        lambda: COMPOSITE_FORM_FIELDS,
    )
    sparql = SPARQLWrapper(TestConfig.DATASET_DB_URL)
    sparql.setMethod(POST)
    sparql.setQuery("""
        PREFIX ex: <urn:orphan:>
        INSERT DATA { GRAPH ex:test {
            ex:source a ex:Source ;
                ex:link ex:leaf, ex:shared, ex:outgoing, ex:backlink ;
                ex:part ex:role, ex:sharedRole .
            ex:leaf a ex:Entity .
            ex:shared a ex:Entity .
            ex:other ex:link ex:shared .
            ex:outgoing a ex:Entity ; ex:link ex:active .
            ex:active ex:label "active" .
            ex:backlink a ex:Entity ; ex:link ex:source .
            ex:role a ex:Part .
            ex:sharedRole a ex:Part .
            ex:other ex:part ex:sharedRole .
            ex:citation a ex:Citation ; ex:cites ex:source .
            ex:foreign a ex:Entity ; ex:cites ex:source .
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
        assert sorted(item["uri"] for item in intermediates) == [
            f"urn:orphan:{name}" for name in expected_intermediates
        ]
    finally:
        sparql.setQuery("CLEAR GRAPH <urn:orphan:test>")
        sparql.query()


def test_composite_value_is_a_child_unless_shared(app, monkeypatch):
    monkeypatch.setattr(
        "heritrace.utils.sparql_utils.get_form_fields",
        lambda: COMPOSITE_FORM_FIELDS,
    )
    sparql = SPARQLWrapper(TestConfig.DATASET_DB_URL)
    sparql.setMethod(POST)
    sparql.setQuery("""
        PREFIX ex: <urn:orphan:>
        INSERT DATA { GRAPH ex:test {
            ex:source a ex:Source ; ex:part ex:role, ex:sharedRole .
            ex:role a ex:Part .
            ex:sharedRole a ex:Part .
            ex:other ex:part ex:sharedRole .
        } }
    """)
    sparql.query()
    try:
        subject = URIRef("urn:orphan:source")
        part = URIRef("urn:orphan:part")
        assert find_orphaned_entities(
            subject, "urn:orphan:Source", part, "urn:orphan:role"
        ) == ([], [{"uri": "urn:orphan:role", "type": "urn:orphan:Part"}])
        assert find_orphaned_entities(
            subject, "urn:orphan:Source", part, "urn:orphan:sharedRole"
        ) == ([], [])
    finally:
        sparql.setQuery("CLEAR GRAPH <urn:orphan:test>")
        sparql.query()
