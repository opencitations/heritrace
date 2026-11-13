# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from unittest.mock import MagicMock, patch

from flask.testing import FlaskClient
from rdflib import XSD

from heritrace.utils.search import SearchRequest, build_search_query, text_paths

TITLE = "http://purl.org/dc/terms/title"
NAME = "http://xmlns.com/foaf/0.1/name"
ARTICLE = "http://purl.org/spar/fabio/JournalArticle"
AGENT = "http://xmlns.com/foaf/0.1/Agent"
AGENT_SHAPE = "http://example.org/AgentShape"
HAS_IDENTIFIER = "http://purl.org/spar/datacite/hasIdentifier"
VALUE = "http://www.essepuntato.it/2010/06/literalreification/hasLiteralValue"
HAS_WORD = "<http://qlever.cs.uni-freiburg.de/builtin-functions/has-word>"


def _normalize(query: str) -> str:
    return " ".join(query.split())


def _text_field(uri: str) -> dict:
    return {
        "uri": uri,
        "datatypes": [str(XSD.string)],
        "hasValue": None,
        "optionalValues": [],
    }


def test_text_paths_cover_the_shape_and_its_nested_shapes() -> None:
    date = {**_text_field("urn:date"), "datatypes": [str(XSD.date)]}
    fixed = {**_text_field("urn:fixed"), "hasValue": "urn:value"}
    choice = {**_text_field("urn:choice"), "optionalValues": ["urn:a"]}
    identifier = {
        "uri": HAS_IDENTIFIER,
        "datatypes": [],
        "hasValue": None,
        "optionalValues": [],
        "nestedShape": [_text_field(VALUE), date],
    }

    paths = text_paths(
        {
            NAME: [_text_field(NAME)],
            HAS_IDENTIFIER: [identifier],
            "urn:date": [date],
            "urn:fixed": [fixed],
            "urn:choice": [choice],
            "^urn:cites": [{"nestedShape": [_text_field(TITLE)]}],
        }
    )

    assert paths == [(NAME,), (HAS_IDENTIFIER, VALUE)]


def test_virtuoso_query_searches_the_words_of_the_term_as_a_phrase() -> None:
    request = SearchRequest(
        term="Gabriele D'Annunzio", entity_class=ARTICLE, paths=[(TITLE,)]
    )

    query = build_search_query(request, "virtuoso", text_index_enabled=True)

    assert _normalize(query) == _normalize(
        f"""
        SELECT DISTINCT ?entity ?scoreValue WHERE {{
            ?entity a <{ARTICLE}> .
            {{
                ?entity <{TITLE}> ?text .
                ?text bif:contains "\\"Gabriele D Annunzio\\""
                    OPTION (score ?scoreValue) .
            }}
            FILTER(?scoreValue > 0.2)
        }}
        ORDER BY DESC(?scoreValue) ASC(?entity)
        OFFSET 0
        LIMIT 6
        """
    )


def test_qlever_query_needs_every_word_as_a_prefix_in_any_path() -> None:
    request = SearchRequest(
        term="Élan-vital",
        entity_class=AGENT,
        paths=[(NAME,), (HAS_IDENTIFIER, VALUE)],
        offset=5,
        limit=5,
    )

    query = build_search_query(request, "qlever", text_index_enabled=True)

    assert _normalize(query) == _normalize(
        f"""
        SELECT DISTINCT ?entity WHERE {{
            {{
                {{
                    ?searchValue0 {HAS_WORD} ?searchWord0 .
                    FILTER(STRSTARTS(?searchWord0, "élan"))
                    ?entity <{NAME}> ?searchValue0 .
                }}
                UNION
                {{
                    ?searchValue0 {HAS_WORD} ?searchWord0 .
                    FILTER(STRSTARTS(?searchWord0, "élan"))
                    ?entity <{HAS_IDENTIFIER}> ?nested0 .
                    ?nested0 <{VALUE}> ?searchValue0 .
                }}
            }}
            {{
                {{
                    ?searchValue1 {HAS_WORD} ?searchWord1 .
                    FILTER(STRSTARTS(?searchWord1, "vital"))
                    ?entity <{NAME}> ?searchValue1 .
                }}
                UNION
                {{
                    ?searchValue1 {HAS_WORD} ?searchWord1 .
                    FILTER(STRSTARTS(?searchWord1, "vital"))
                    ?entity <{HAS_IDENTIFIER}> ?nested1 .
                    ?nested1 <{VALUE}> ?searchValue1 .
                }}
            }}
            ?entity a <{AGENT}> .
        }}
        ORDER BY ASC(?entity)
        OFFSET 5
        LIMIT 6
        """
    )


def test_text_index_query_matches_nothing_for_a_term_without_words() -> None:
    request = SearchRequest(term="?!", entity_class=AGENT, paths=[(NAME,)])

    query = build_search_query(request, "virtuoso", text_index_enabled=True)

    assert "FILTER(false)" in query


def test_regex_query_without_text_index() -> None:
    request = SearchRequest(term="smith", entity_class=AGENT, paths=[(NAME,)])

    query = build_search_query(request, "virtuoso", text_index_enabled=False)

    assert 'FILTER(REGEX(STR(?searchValue), "smith", "i"))' in query


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
    custom_filter.value_label.side_effect = lambda uri, _key: f"Label {uri[-1]}"
    with (
        patch("heritrace.routes.search.get_sparql", return_value=sparql),
        patch("heritrace.routes.search.get_custom_filter", return_value=custom_filter),
        patch(
            "heritrace.routes.search.get_form_fields",
            return_value={(AGENT, AGENT_SHAPE): {NAME: [_text_field(NAME)]}},
        ),
    ):
        response = logged_in_client.post(
            "/api/search",
            json={
                "term": "doe",
                "entity_class": AGENT,
                "shape": AGENT_SHAPE,
                "offset": 0,
                "limit": 2,
            },
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
    custom_filter.value_label.assert_any_call(
        "http://example.org/ra/0", (AGENT, AGENT_SHAPE)
    )


def test_search_endpoint_requires_a_term(logged_in_client: FlaskClient) -> None:
    response = logged_in_client.post("/api/search", json={"term": ""})

    assert response.status_code == 400
    assert response.get_json() == {
        "status": "error",
        "message": "A search term is required",
    }


def test_search_endpoint_rejects_an_unknown_entity_type(
    logged_in_client: FlaskClient,
) -> None:
    with patch("heritrace.routes.search.get_form_fields", return_value={}):
        response = logged_in_client.post(
            "/api/search",
            json={"term": "doe", "entity_class": AGENT, "shape": AGENT_SHAPE},
        )

    assert response.status_code == 400
    assert response.get_json() == {
        "status": "error",
        "message": "Unknown entity type",
    }
