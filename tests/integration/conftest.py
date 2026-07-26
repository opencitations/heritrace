# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import uuid
from collections.abc import Generator

import pytest
from flask import Flask
from SPARQLWrapper import SPARQLWrapper

from heritrace import create_app
from tests.test_config import TestConfig


@pytest.fixture(scope="session")
def _shared_app(docker_services) -> Flask:
    return create_app(TestConfig)


@pytest.fixture
def app(_shared_app: Flask) -> Generator[Flask, None, None]:
    config = dict(_shared_app.config)
    exts = dict(_shared_app.extensions)
    login_mgr = getattr(_shared_app, "login_manager", None)
    before_fns = {k: list(v) for k, v in _shared_app.before_request_funcs.items()}
    teardown_fns = list(_shared_app.teardown_appcontext_funcs)

    with _shared_app.app_context():
        yield _shared_app

    _shared_app.config.clear()
    _shared_app.config.update(config)
    _shared_app.extensions.clear()
    _shared_app.extensions.update(exts)
    if login_mgr is not None:
        _shared_app.login_manager = login_mgr
    _shared_app.before_request_funcs.clear()
    _shared_app.before_request_funcs.update(before_fns)
    _shared_app.teardown_appcontext_funcs[:] = teardown_fns
    _shared_app._got_first_request = False  # noqa: SLF001


@pytest.fixture
def setup_test_data(app):
    dataset_endpoint = app.config["DATASET_DB_URL"]

    sparql = SPARQLWrapper(dataset_endpoint)
    sparql.setMethod("POST")

    test_id = str(uuid.uuid4())
    graph_uri = f"http://example.org/test-graph-{test_id}"
    person1_uri = f"http://example.org/person1-{test_id}"
    person2_uri = f"http://example.org/person2-{test_id}"
    document1_uri = f"http://example.org/document1-{test_id}"
    relationship1_uri = f"http://example.org/relationship1-{test_id}"

    clear_all_query = """
    DELETE {
        GRAPH ?g {
            ?s a <http://example.org/Person> .
            ?s ?p ?o .
        }
    }
    WHERE {
        GRAPH ?g {
            ?s a <http://example.org/Person> .
            ?s ?p ?o .
        }
    };

    DELETE {
        GRAPH ?g {
            ?s a <http://example.org/Document> .
            ?s ?p ?o .
        }
    }
    WHERE {
        GRAPH ?g {
            ?s a <http://example.org/Document> .
            ?s ?p ?o .
        }
    };

    DELETE {
        GRAPH ?g {
            ?s a <http://example.org/Relationship> .
            ?s ?p ?o .
        }
    }
    WHERE {
        GRAPH ?g {
            ?s a <http://example.org/Relationship> .
            ?s ?p ?o .
        }
    }
    """
    sparql.setQuery(clear_all_query)
    sparql.query()

    clear_query = f"""
    CLEAR GRAPH <{graph_uri}>;
    """
    sparql.setQuery(clear_query)
    sparql.query()

    insert_query = f"""
    INSERT DATA {{
        GRAPH <{graph_uri}> {{
            <{person1_uri}> a <http://example.org/Person> ;
                <http://example.org/name> "John Doe {test_id}" ;
                <http://example.org/age>
                "30"^^<http://www.w3.org/2001/XMLSchema#integer> ;
                <http://example.org/knows> <{person2_uri}> .

            <{person2_uri}> a <http://example.org/Person> ;
                <http://example.org/name> "Jane Smith {test_id}" ;
                <http://example.org/age>
                "28"^^<http://www.w3.org/2001/XMLSchema#integer> .

            <{document1_uri}> a <http://example.org/Document> ;
                <http://example.org/title> "Test Document {test_id}" ;
                <http://example.org/author> <{person1_uri}> .

            <{relationship1_uri}> a <http://example.org/Relationship> ;
                <http://example.org/from> <{person1_uri}> ;
                <http://example.org/to> <{person2_uri}> ;
                <http://example.org/type> "Friend" .
        }}
    }}
    """
    sparql.setQuery(insert_query)
    sparql.query()

    yield {
        "graph_uri": graph_uri,
        "person1_uri": person1_uri,
        "person2_uri": person2_uri,
        "document1_uri": document1_uri,
        "relationship1_uri": relationship1_uri,
        "test_id": test_id,
    }

    sparql.setQuery(clear_query)
    sparql.query()


@pytest.fixture(autouse=True)
def _cleanup_test_meta_entities() -> Generator[None, None, None]:
    # Leftover test_ entities under the meta base IRI break
    # MetaURIGenerator.initialize_counters() for later tests/sessions
    # reusing the shared dataset/provenance stores.
    yield

    dataset = SPARQLWrapper(TestConfig.DATASET_DB_URL)
    dataset.setMethod("POST")
    dataset.setQuery("""
    DELETE { GRAPH ?g { ?s ?p ?o } }
    WHERE {
        GRAPH ?g {
            ?s ?p ?o .
            FILTER(
                STRSTARTS(str(?s), "https://w3id.org/oc/meta/")
                && CONTAINS(str(?s), "/test_")
            )
        }
    }
    """)
    dataset.query()

    provenance = SPARQLWrapper(TestConfig.PROVENANCE_DB_URL)
    provenance.setMethod("POST")
    provenance.setQuery("""
    DELETE { GRAPH ?g { ?snapshot ?p ?o } }
    WHERE {
        GRAPH ?g {
            ?snapshot <http://www.w3.org/ns/prov#specializationOf> ?entity ;
                      ?p ?o .
            FILTER(
                STRSTARTS(str(?entity), "https://w3id.org/oc/meta/")
                && CONTAINS(str(?entity), "/test_")
            )
        }
    }
    """)
    provenance.query()
