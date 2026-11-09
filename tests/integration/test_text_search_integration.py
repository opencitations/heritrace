# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from collections.abc import Generator

import pytest
from SPARQLWrapper import JSON, POST, SPARQLWrapper

from heritrace.sparql import get_sparql_bindings
from heritrace.utils.search import SearchRequest, build_search_query
from tests.conftest import run_isql
from tests.test_config import TestConfig

BASE = "http://example.org/text-search/"
GRAPH = f"{BASE}graph"
PERSON = f"{BASE}Person"
NAME = f"{BASE}name"
HAS_IDENTIFIER = f"{BASE}hasIdentifier"
VALUE = f"{BASE}value"
ADA = f"{BASE}ada"
GRACE = f"{BASE}grace"


def _update(statement: str) -> None:
    sparql = SPARQLWrapper(TestConfig.DATASET_DB_URL)
    sparql.setMethod(POST)
    sparql.setQuery(statement)
    sparql.query()


@pytest.fixture
def indexed_people() -> Generator[None, None, None]:
    run_isql("tests-dataset-db-1", "DB.DBA.RDF_OBJ_FT_RULE_ADD(null, null, 'All');")
    _update(
        f"""
        INSERT DATA {{ GRAPH <{GRAPH}> {{
            <{ADA}> a <{PERSON}> ;
                <{NAME}> "Ada Lovelace" ;
                <{HAS_IDENTIFIER}> <{BASE}ada-id> .
            <{BASE}ada-id> <{VALUE}> "ada-0001-orcid" .
            <{GRACE}> a <{PERSON}> ;
                <{NAME}> "Grace Hopper" .
        }} }}
        """
    )
    run_isql("tests-dataset-db-1", "DB.DBA.VT_INC_INDEX_DB_DBA_RDF_OBJ();")
    yield
    _update(f"CLEAR GRAPH <{GRAPH}>")


@pytest.mark.usefixtures("indexed_people")
@pytest.mark.parametrize(
    ("term", "expected"),
    [("Hopper", [GRACE]), ("orcid", [ADA]), ("Ada", [ADA])],
)
def test_virtuoso_text_search_covers_every_path(term: str, expected: list[str]) -> None:
    request = SearchRequest(
        term=term, entity_class=PERSON, paths=[(NAME,), (HAS_IDENTIFIER, VALUE)]
    )
    sparql = SPARQLWrapper(TestConfig.DATASET_DB_URL)
    sparql.setQuery(build_search_query(request, "virtuoso", text_index_enabled=True))
    sparql.setReturnFormat(JSON)

    bindings = get_sparql_bindings(sparql.query().convert())

    assert [binding["entity"]["value"] for binding in bindings] == expected
