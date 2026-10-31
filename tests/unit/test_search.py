# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from unittest.mock import MagicMock, patch

from flask.testing import FlaskClient

from heritrace.utils.search import (
    ContextConstraint,
    SearchRequest,
    build_search_query,
)

TITLE = "http://purl.org/dc/terms/title"
NAME = "http://xmlns.com/foaf/0.1/name"
ARTICLE = "http://purl.org/spar/fabio/JournalArticle"
AGENT = "http://xmlns.com/foaf/0.1/Agent"
HELD_BY = "http://purl.org/spar/pro/isHeldBy"
XSD_STRING = "http://www.w3.org/2001/XMLSchema#string"
HAS_WORD = "<http://qlever.cs.uni-freiburg.de/builtin-functions/has-word>"


def _normalize(query: str) -> str:
    return " ".join(query.split())


def test_virtuoso_query_searches_the_words_of_the_term_as_a_phrase() -> None:
    request = SearchRequest(
        term="Gabriele D'Annunzio", entity_class=ARTICLE, predicate=TITLE
    )

    query = build_search_query(request, "virtuoso", text_index_enabled=True)

    assert _normalize(query) == _normalize(
        f"""
        SELECT DISTINCT ?entity ?scoreValue WHERE {{
            ?entity ?p ?text .
            ?entity a <{ARTICLE}> .
            ?entity <{TITLE}> ?text .
            ?text bif:contains "\\"Gabriele D Annunzio\\"" OPTION (score ?scoreValue) .
            FILTER(?scoreValue > 0.2)
        }}
        ORDER BY DESC(?scoreValue) ASC(?entity)
        OFFSET 0
        LIMIT 6
        """
    )


def test_qlever_query_matches_words_and_prefix_of_the_last_one() -> None:
    request = SearchRequest(
        term="Élan vital", entity_class=AGENT, predicate=NAME, offset=5, limit=5
    )

    query = build_search_query(request, "qlever", text_index_enabled=True)

    assert _normalize(query) == _normalize(
        f"""
        SELECT DISTINCT ?entity WHERE {{
            ?entity a <{AGENT}> .
            ?entity <{NAME}> ?searchValue .
            ?searchValue {HAS_WORD} "élan" .
            ?searchValue {HAS_WORD} ?searchWord .
            FILTER(STRSTARTS(?searchWord, "vital"))
        }}
        ORDER BY ASC(?entity)
        OFFSET 5
        LIMIT 6
        """
    )


def test_text_index_query_matches_nothing_for_a_term_without_words() -> None:
    request = SearchRequest(term="?!", entity_class=None, predicate=None)

    query = build_search_query(request, "virtuoso", text_index_enabled=True)

    assert _normalize(query) == _normalize(
        """
        SELECT DISTINCT ?entity WHERE {
            ?entity ?searchPredicate ?searchValue .
            FILTER(false)
        }
        ORDER BY ASC(?entity)
        OFFSET 0
        LIMIT 6
        """
    )


def test_regex_query_without_text_index_and_without_predicate() -> None:
    request = SearchRequest(term="smith", entity_class=None, predicate=None)

    query = build_search_query(request, "virtuoso", text_index_enabled=False)

    assert _normalize(query) == _normalize(
        """
        SELECT DISTINCT ?entity WHERE {
            ?entity ?searchPredicate ?searchValue .
            FILTER(REGEX(STR(?searchValue), "smith", "i"))
        }
        ORDER BY ASC(?entity)
        OFFSET 0
        LIMIT 6
        """
    )


def test_parent_search_adds_context_to_the_nested_entity() -> None:
    request = SearchRequest(
        term="Doe",
        entity_class=ARTICLE,
        predicate=NAME,
        search_target="parent",
        connecting_predicate=HELD_BY,
        context=[
            ContextConstraint(predicate=TITLE, value="A title", datatype=XSD_STRING),
            ContextConstraint(
                predicate=HELD_BY, value="http://example.org/ra/1", datatype=None
            ),
        ],
    )

    query = build_search_query(request, "qlever", text_index_enabled=False)

    assert _normalize(query) == _normalize(
        f"""
        SELECT DISTINCT ?entity WHERE {{
            ?nestedEntity <{TITLE}> "A title"^^<{XSD_STRING}> .
            ?nestedEntity <{HELD_BY}> <http://example.org/ra/1> .
            ?nestedEntity <{NAME}> ?searchValue .
            FILTER(REGEX(STR(?searchValue), "Doe", "i"))
            ?entity <{HELD_BY}> ?nestedEntity .
            ?entity a <{ARTICLE}> .
        }}
        ORDER BY ASC(?entity)
        OFFSET 0
        LIMIT 6
        """
    )


def test_search_endpoint_returns_labels_and_has_more(
    logged_in_client: FlaskClient,
) -> None:
    sparql = MagicMock()
    sparql.query.return_value.convert.return_value = {
        "results": {
            "bindings": [
                {"entity": {"value": f"http://example.org/ra/{i}"}} for i in range(3)
            ]
        }
    }
    custom_filter = MagicMock()
    custom_filter.human_readable_entity.side_effect = lambda uri, _key: (
        f"Label {uri[-1]}"
    )
    with (
        patch("heritrace.routes.search.get_sparql", return_value=sparql),
        patch("heritrace.routes.search.get_custom_filter", return_value=custom_filter),
        patch(
            "heritrace.routes.search.determine_shape_for_classes",
            return_value="http://example.org/AgentShape",
        ),
    ):
        response = logged_in_client.post(
            "/api/search",
            json={"term": "doe", "entity_class": AGENT, "predicate": NAME, "limit": 2},
        )

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "success",
        "results": [
            {"uri": "http://example.org/ra/0", "label": "Label 0"},
            {"uri": "http://example.org/ra/1", "label": "Label 1"},
        ],
        "has_more": True,
    }
    assert "LIMIT 3" in sparql.setQuery.call_args.args[0]
    custom_filter.human_readable_entity.assert_any_call(
        "http://example.org/ra/0", (AGENT, "http://example.org/AgentShape")
    )


def test_search_endpoint_requires_a_term(logged_in_client: FlaskClient) -> None:
    response = logged_in_client.post("/api/search", json={"term": ""})

    assert response.status_code == 400
    assert response.get_json() == {
        "status": "error",
        "message": "A search term is required",
    }


def test_parent_search_endpoint_requires_the_connecting_predicate(
    logged_in_client: FlaskClient,
) -> None:
    response = logged_in_client.post(
        "/api/search",
        json={"term": "doe", "entity_class": ARTICLE, "search_target": "parent"},
    )

    assert response.status_code == 400
    assert response.get_json()["status"] == "error"


def test_search_endpoint_rejects_invalid_iris(logged_in_client: FlaskClient) -> None:
    response = logged_in_client.post(
        "/api/search",
        json={"term": "doe", "predicate": f"{NAME}> . ?s ?p ?o }} #"},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "status": "error",
        "message": "Invalid IRI in request",
    }
