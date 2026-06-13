# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import uuid
from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from dateutil import parser
from flask import Flask
from flask.testing import FlaskClient
from SPARQLWrapper import JSON, POST, SPARQLWrapper

from heritrace.sparql import get_sparql_bindings
from tests.test_config import TestConfig

PRO_IS_DOCUMENT_CONTEXT_FOR = "http://purl.org/spar/pro/isDocumentContextFor"
PRO_IS_HELD_BY = "http://purl.org/spar/pro/isHeldBy"
PRO_WITH_ROLE = "http://purl.org/spar/pro/withRole"
PRO_AUTHOR = "http://purl.org/spar/pro/author"
OCO_HAS_NEXT = "https://w3id.org/oc/ontology/hasNext"
AUTHOR_COUNT = 5


@pytest.fixture
def ordered_authors_article(app: Flask) -> Generator[dict, None, None]:
    test_id = uuid.uuid4().hex
    base = "https://w3id.org/oc/meta"
    br = f"{base}/br/test{test_id}"
    ars = [f"{base}/ar/test{test_id}n{i}" for i in range(1, AUTHOR_COUNT + 1)]
    ras = [f"{base}/ra/test{test_id}n{i}" for i in range(1, AUTHOR_COUNT + 1)]

    br_triples = [
        f"<{br}> a <http://purl.org/spar/fabio/JournalArticle> .",
        f'<{br}> <http://purl.org/dc/terms/title> "Test Article {test_id}" .',
    ]
    ar_triples = []
    ra_triples = []
    for i in range(AUTHOR_COUNT):
        br_triples.append(f"<{br}> <{PRO_IS_DOCUMENT_CONTEXT_FOR}> <{ars[i]}> .")
        ar_triples.append(f"<{ars[i]}> a <http://purl.org/spar/pro/RoleInTime> .")
        ar_triples.append(f"<{ars[i]}> <{PRO_WITH_ROLE}> <{PRO_AUTHOR}> .")
        ar_triples.append(f"<{ars[i]}> <{PRO_IS_HELD_BY}> <{ras[i]}> .")
        if i < AUTHOR_COUNT - 1:
            ar_triples.append(f"<{ars[i]}> <{OCO_HAS_NEXT}> <{ars[i + 1]}> .")
        ra_triples.append(f"<{ras[i]}> a <http://xmlns.com/foaf/0.1/Agent> .")
        ra_triples.append(
            f'<{ras[i]}> <http://xmlns.com/foaf/0.1/givenName> "Given{i + 1}" .'
        )
        ra_triples.append(
            f"<{ras[i]}> <http://xmlns.com/foaf/0.1/familyName>"
            f' "Family{i + 1}x{test_id}" .'
        )

    sparql = SPARQLWrapper(app.config["DATASET_DB_URL"])
    sparql.setMethod(POST)
    sparql.setQuery(f"""
    INSERT DATA {{
        GRAPH <{base}/br/> {{ {" ".join(br_triples)} }}
        GRAPH <{base}/ar/> {{ {" ".join(ar_triples)} }}
        GRAPH <{base}/ra/> {{ {" ".join(ra_triples)} }}
    }}
    """)
    sparql.query()

    yield {"test_id": test_id, "br": br, "ars": ars, "ras": ras}

    entities = [br, *ars, *ras]
    values = " ".join(f"<{entity}>" for entity in entities)

    cleanup_data = SPARQLWrapper(app.config["DATASET_DB_URL"])
    cleanup_data.setMethod(POST)
    cleanup_data.setQuery(f"""
    DELETE {{ GRAPH ?g {{ ?s ?p ?o }} }}
    WHERE {{ GRAPH ?g {{ ?s ?p ?o . VALUES ?s {{ {values} }} }} }}
    """)
    cleanup_data.query()

    cleanup_prov = SPARQLWrapper(app.config["PROVENANCE_DB_URL"])
    cleanup_prov.setMethod(POST)
    cleanup_prov.setQuery(f"""
    DELETE {{ GRAPH ?g {{ ?snapshot ?p ?o }} }}
    WHERE {{
        GRAPH ?g {{
            ?snapshot <http://www.w3.org/ns/prov#specializationOf> ?entity ;
                      ?p ?o .
            VALUES ?entity {{ {values} }}
        }}
    }}
    """)
    cleanup_prov.query()


def _provenance_generation_times(entity_uri: str) -> list[datetime]:
    sparql = SPARQLWrapper(TestConfig.PROVENANCE_DB_URL)
    sparql.setMethod(POST)
    sparql.setReturnFormat(JSON)
    sparql.setQuery(f"""
    SELECT ?t WHERE {{
        GRAPH ?g {{
            ?snapshot <http://www.w3.org/ns/prov#specializationOf> <{entity_uri}> ;
                      <http://www.w3.org/ns/prov#generatedAtTime> ?t .
        }}
    }}
    """)
    bindings = get_sparql_bindings(sparql.queryAndConvert())
    return [parser.isoparse(b["t"]["value"]).astimezone(timezone.utc) for b in bindings]


def test_reorder_backfills_provenance_for_all_chained_authors(
    logged_in_client: FlaskClient, ordered_authors_article: dict
) -> None:
    data = ordered_authors_article
    new_order = [data["ars"][-1], *data["ars"][:-1]]

    response = logged_in_client.post(
        "/api/apply_changes",
        json=[
            {
                "action": "order",
                "subject": data["br"],
                "predicate": PRO_IS_DOCUMENT_CONTEXT_FOR,
                "object": new_order,
                "newObject": OCO_HAS_NEXT,
            }
        ],
    )
    assert response.status_code == 200
    assert response.get_json()["status"] == "success"

    backdated_time = datetime(2023, 12, 31, 23, 59, 55, tzinfo=timezone.utc)
    for ra in data["ras"]:
        assert _provenance_generation_times(ra) == [backdated_time]

    history_response = logged_in_client.get(f"/entity-history/{data['br']}")
    assert history_response.status_code == 200
    history_page = history_response.data.decode()
    for i in range(1, AUTHOR_COUNT + 1):
        assert f"Given{i} Family{i}x{data['test_id']}" in history_page
        assert f"ra/test{data['test_id']}n{i}<" not in history_page
