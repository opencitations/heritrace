# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import re
from unittest.mock import MagicMock, patch

import pytest
from rdflib import Graph, URIRef
from SPARQLWrapper.SPARQLExceptions import SPARQLWrapperException

from heritrace.utils.filters import Filter

_FETCH_URI_QUERY = (
    "SELECT ?display WHERE { [[uri]] <http://example.org/name> ?display }"
)
_FETCH_PERSON_QUERY = (
    "SELECT ?display WHERE"
    " { <http://example.org/person/1>"
    " <http://example.org/name> ?display }"
)


@pytest.fixture
def mock_filter():
    context = {"example": "http://example.org/"}
    display_rules = [
        {
            "target": {
                "class": "http://example.org/Person",
                "shape": "http://example.org/PersonShape",
            },
            "displayName": "Person",
            "fetchUriDisplay": _FETCH_URI_QUERY,
        }
    ]
    sparql_endpoint = "http://example.org/sparql"
    return Filter(context, display_rules, sparql_endpoint)


def test_get_fetch_uri_display_with_graph_success(mock_filter) -> None:
    """Test get_fetch_uri_display with a graph that returns results successfully."""
    # Setup
    uri = "http://example.org/person/1"
    rule = {"fetchUriDisplay": _FETCH_PERSON_QUERY}

    # Create a mock graph that returns a result
    mock_graph = MagicMock(spec=Graph)
    mock_results = MagicMock()
    mock_results.__iter__.return_value = [{"display": "John Doe"}]
    mock_graph.query.return_value = mock_results

    result = mock_filter.get_fetch_uri_display(uri, rule, mock_graph)

    # Verify
    assert result == "John Doe"
    mock_graph.query.assert_called_once()


def test_get_fetch_uri_display_with_graph_exception(mock_filter) -> None:
    """Test get_fetch_uri_display with a graph that raises an exception."""
    uri = "http://example.org/person/1"
    rule = {"fetchUriDisplay": _FETCH_PERSON_QUERY}

    mock_graph = MagicMock(spec=Graph)
    mock_graph.query.side_effect = ValueError("Test exception")

    with pytest.raises(ValueError, match="Test exception"):
        mock_filter.get_fetch_uri_display(uri, rule, mock_graph)

    mock_graph.query.assert_called_once()


def test_get_fetch_uri_display_with_sparql_success(mock_filter) -> None:
    """
    Test get_fetch_uri_display with SPARQL endpoint that returns results successfully.
    """
    # Setup
    uri = "http://example.org/person/1"
    rule = {"fetchUriDisplay": _FETCH_PERSON_QUERY}

    # Mock the SPARQL query response
    mock_response = {"results": {"bindings": [{"display": {"value": "John Doe"}}]}}

    # Execute
    mock_sparql = MagicMock()
    mock_sparql.query.return_value.convert.return_value = mock_response
    with patch.object(mock_filter, "_get_sparql", return_value=mock_sparql):
        result = mock_filter.get_fetch_uri_display(uri, rule, None)

    assert result == "John Doe"
    assert mock_sparql.setQuery.call_args.args[0] == _FETCH_PERSON_QUERY
    mock_sparql.query.assert_called_once()


def test_get_fetch_uri_display_with_sparql_exception(mock_filter) -> None:
    """Test get_fetch_uri_display with SPARQL endpoint that raises an exception."""
    uri = "http://example.org/person/1"
    rule = {"fetchUriDisplay": _FETCH_PERSON_QUERY}

    mock_sparql = MagicMock()
    mock_sparql.query.side_effect = SPARQLWrapperException(b"Test exception")
    with (
        patch.object(mock_filter, "_get_sparql", return_value=mock_sparql),
        pytest.raises(SPARQLWrapperException, match="Test exception"),
    ):
        mock_filter.get_fetch_uri_display(uri, rule, None)

    mock_sparql.query.assert_called_once()


def test_get_fetch_uri_display_sparql_no_results(mock_filter) -> None:
    """Test get_fetch_uri_display with SPARQL endpoint that returns no results."""
    # Setup
    uri = "http://example.org/person/1"
    rule = {"fetchUriDisplay": _FETCH_PERSON_QUERY}

    # Mock the SPARQL query response with no bindings
    mock_response = {"results": {"bindings": []}}

    mock_sparql = MagicMock()
    mock_sparql.query.return_value.convert.return_value = mock_response
    with (
        patch.object(mock_filter, "_get_sparql", return_value=mock_sparql),
        pytest.raises(
            ValueError,
            match=re.escape(
                "fetchUriDisplay returned no result for http://example.org/person/1"
            ),
        ),
    ):
        mock_filter.get_fetch_uri_display(uri, rule, None)

    mock_sparql.query.assert_called_once()


def test_get_fetch_uri_display_graph_unbound_result(mock_filter) -> None:
    uri = "http://example.org/person/1"
    rule = {
        "fetchUriDisplay": (
            "SELECT ?display ?subject WHERE {"
            " VALUES ?subject { [[uri]] }"
            " OPTIONAL { ?subject <http://example.org/name> ?display }"
            " }"
        )
    }

    with pytest.raises(
        ValueError,
        match=re.escape(
            "fetchUriDisplay returned no result for http://example.org/person/1"
        ),
    ):
        mock_filter.get_fetch_uri_display(uri, rule, Graph())


def test_format_source_reference_none(mock_filter) -> None:
    assert mock_filter.format_source_reference(None) == {
        "kind": "unknown",
        "url": None,
        "label": "Unknown",
        "extra": None,
        "entity_uri": None,
        "timestamp": None,
    }


def test_format_source_reference_version(mock_filter) -> None:
    result = mock_filter.format_source_reference("http://example.org/br/1/prov/se/3")
    assert result == {
        "kind": "version",
        "url": "http://example.org/br/1/prov/se/3",
        "label": "Version 3",
        "extra": None,
        "entity_uri": "http://example.org/br/1",
        "timestamp": "3",
    }


def test_format_source_reference_generic_url(mock_filter) -> None:
    url = "http://example.org/resource/123"
    assert mock_filter.format_source_reference(url) == {
        "kind": "url",
        "url": url,
        "label": url,
        "extra": None,
        "entity_uri": None,
        "timestamp": None,
    }


def test_format_source_reference_text(mock_filter) -> None:
    assert mock_filter.format_source_reference("not a valid url") == {
        "kind": "text",
        "url": None,
        "label": "not a valid url",
        "extra": None,
        "entity_uri": None,
        "timestamp": None,
    }


def test_format_source_reference_zenodo_url(mock_filter) -> None:
    url = "https://zenodo.org/record/12345"
    zenodo_ref = {
        "kind": "zenodo",
        "url": url,
        "label": "Citation",
        "extra": None,
        "entity_uri": None,
        "timestamp": None,
    }
    with patch(
        "heritrace.utils.filters.zenodo_source", return_value=zenodo_ref
    ) as mock_zenodo:
        assert mock_filter.format_source_reference(url) == zenodo_ref
    mock_zenodo.assert_called_once_with(url)


def test_format_agent_reference_none(mock_filter) -> None:
    assert mock_filter.format_agent_reference(None) == {
        "kind": "unknown",
        "url": None,
        "label": "Unknown",
        "orcid_id": None,
    }


def test_format_agent_reference_orcid_url(mock_filter) -> None:
    url = "https://orcid.org/0000-0001-2345-6789"
    orcid_ref = {
        "kind": "orcid",
        "url": url,
        "label": "Jane Doe",
        "orcid_id": "0000-0001-2345-6789",
    }
    with patch(
        "heritrace.utils.filters.orcid_agent", return_value=orcid_ref
    ) as mock_orcid:
        assert mock_filter.format_agent_reference(url) == orcid_ref
    mock_orcid.assert_called_once_with(url)


def test_format_agent_reference_generic_url(mock_filter) -> None:
    url = "http://example.org/person/123"
    assert mock_filter.format_agent_reference(url) == {
        "kind": "url",
        "url": url,
        "label": url,
        "orcid_id": None,
    }


def test_format_agent_reference_text(mock_filter) -> None:
    assert mock_filter.format_agent_reference("not a valid url") == {
        "kind": "text",
        "url": None,
        "label": "not a valid url",
        "orcid_id": None,
    }


def test_human_readable_entity_with_display_name(mock_filter) -> None:
    """Test human_readable_entity when rule has a displayName property."""
    uri = "http://example.org/person/1"
    entity_key = ("http://example.org/Person", "http://example.org/PersonShape")
    rule = {"displayName": "Custom Person Display Name"}

    with patch(
        "heritrace.utils.display_rules_utils.find_matching_rule"
    ) as mock_find_rule:
        mock_find_rule.return_value = rule
        result = mock_filter.human_readable_entity(uri, entity_key)

    assert result == "Custom Person Display Name"
    mock_find_rule.assert_called_once_with(
        entity_key[0], entity_key[1], mock_filter.display_rules
    )


def test_human_readable_entity_with_fetch_uri_display(mock_filter) -> None:
    """
    Test human_readable_entity when rule has a fetchUriDisplay property and it returns a
    result.
    """
    # Setup
    uri = "http://example.org/person/1"
    entity_key = ("http://example.org/Person", "http://example.org/PersonShape")
    rule = {"fetchUriDisplay": _FETCH_PERSON_QUERY}

    with patch(
        "heritrace.utils.display_rules_utils.find_matching_rule"
    ) as mock_find_rule:
        mock_find_rule.return_value = rule
        with patch.object(
            mock_filter, "get_fetch_uri_display", return_value="John Doe"
        ) as mock_get_fetch:
            result = mock_filter.human_readable_entity(uri, entity_key)

    assert result == "John Doe"
    mock_find_rule.assert_called_once_with(
        entity_key[0], entity_key[1], mock_filter.display_rules
    )
    mock_get_fetch.assert_called_once_with(uri, rule, None)


def test_human_readable_entity_propagates_missing_display(mock_filter) -> None:
    """
    Test human_readable_entity when rule has a fetchUriDisplay property but it returns
    no result.
    """
    uri = "http://example.org/person/1"
    entity_key = ("http://example.org/Person", "http://example.org/PersonShape")
    rule = {
        "fetchUriDisplay": _FETCH_PERSON_QUERY,
        "displayName": "Person Display Name",
    }

    with patch(
        "heritrace.utils.display_rules_utils.find_matching_rule"
    ) as mock_find_rule:
        mock_find_rule.return_value = rule
        with (
            patch.object(
                mock_filter,
                "get_fetch_uri_display",
                side_effect=ValueError("missing display"),
            ) as mock_get_fetch,
            pytest.raises(ValueError, match="missing display"),
        ):
            mock_filter.human_readable_entity(uri, entity_key)

    mock_find_rule.assert_called_once_with(
        entity_key[0], entity_key[1], mock_filter.display_rules
    )
    mock_get_fetch.assert_called_once_with(uri, rule, None)


def test_human_readable_entity_formats_uri_ref(mock_filter) -> None:
    uri = URIRef("http://example.org/person/1")
    entity_key = ("http://example.org/Person", "http://example.org/PersonShape")

    with patch.object(
        mock_filter, "get_fetch_uri_display", return_value="John Doe"
    ) as mock_get_fetch:
        result = mock_filter.human_readable_entity(uri, entity_key)

    assert result == "John Doe"
    mock_get_fetch.assert_called_once_with(str(uri), mock_filter.display_rules[0], None)


def test_human_readable_entity_no_rule(mock_filter) -> None:
    """Test human_readable_entity when no matching rule is found."""
    uri = "http://example.org/person/1"
    entity_key = ("http://example.org/Person", "http://example.org/PersonShape")

    with patch(
        "heritrace.utils.display_rules_utils.find_matching_rule"
    ) as mock_find_rule:
        mock_find_rule.return_value = None
        result = mock_filter.human_readable_entity(uri, entity_key)

    assert result == uri
    mock_find_rule.assert_called_once_with(
        entity_key[0], entity_key[1], mock_filter.display_rules
    )


def test_human_readable_entity_no_matching_rule(mock_filter) -> None:
    """Test human_readable_entity when no matching rule is found."""
    uri = "http://example.org/unknown/1"
    entity_key = ("http://example.org/Unknown", "http://example.org/UnknownShape")

    with patch(
        "heritrace.utils.display_rules_utils.find_matching_rule"
    ) as mock_find_rule:
        mock_find_rule.return_value = None
        result = mock_filter.human_readable_entity(uri, entity_key)

    assert result == uri
    mock_find_rule.assert_called_once_with(
        entity_key[0], entity_key[1], mock_filter.display_rules
    )


def test_human_readable_entity_malformed_rule(mock_filter) -> None:
    """
    Test human_readable_entity when rule exists but has neither displayName nor
    fetchUriDisplay.
    """
    uri = "http://example.org/person/1"
    entity_key = ("http://example.org/Person", "http://example.org/PersonShape")
    # Rule exists but is malformed (missing both displayName and fetchUriDisplay)
    rule = {
        "target": {"class": "http://example.org/Person"},
        "priority": 1,
        "shouldBeDisplayed": True,
    }

    with patch(
        "heritrace.utils.display_rules_utils.find_matching_rule"
    ) as mock_find_rule:
        mock_find_rule.return_value = rule
        result = mock_filter.human_readable_entity(uri, entity_key)

    assert result == uri
    mock_find_rule.assert_called_once_with(
        entity_key[0], entity_key[1], mock_filter.display_rules
    )
