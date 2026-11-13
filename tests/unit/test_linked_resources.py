# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from dataclasses import replace
from unittest.mock import MagicMock, patch

import pytest
from SPARQLWrapper.SPARQLExceptions import SPARQLWrapperException

from heritrace.routes.linked_resources import (
    _resolve_parent_entity,
    get_paginated_inverse_references,
)
from heritrace.utils.virtuoso_utils import VIRTUOSO_EXCLUDED_GRAPHS

SAMPLE_SUBJECT_URI = "http://example.org/entity1"
COMPOSITE_SHAPE = "http://example.org/CompositeShape"
SAMPLE_REFERRING_SUBJECT_1 = "http://example.org/ref1"
SAMPLE_REFERRING_SUBJECT_2 = "http://example.org/ref2"
SAMPLE_REFERRING_SUBJECT_3 = "http://example.org/ref3"
SAMPLE_PREDICATE_1 = "http://example.org/pred1"
SAMPLE_PREDICATE_2 = "http://example.org/pred2"
SAMPLE_TYPE_1 = "http://example.org/TypeA"


def mock_sparql_query_results(results_bindings=None, limit=None, offset=None):
    """Helper to mock SPARQLWrapper query results for the limit+1 strategy."""
    mock_sparql = MagicMock()
    mock_convert = MagicMock()

    if results_bindings is None:
        results_bindings = []

    if limit is not None:
        query_limit = limit + 1
        fetched_bindings = (
            results_bindings[offset : offset + query_limit]
            if offset is not None
            else results_bindings[:query_limit]
        )
    else:
        fetched_bindings = results_bindings

    data_results = {"results": {"bindings": fetched_bindings}}

    mock_convert.return_value = data_results
    mock_sparql.query.return_value.convert = mock_convert
    return mock_sparql


@patch("heritrace.routes.linked_resources.get_entity_types")
@patch("heritrace.routes.linked_resources.get_custom_filter")
@patch("heritrace.routes.linked_resources.get_sparql")
@patch("heritrace.routes.linked_resources.is_virtuoso", new=lambda: False)
def test_get_paginated_inverse_references_basic(
    mock_get_sparql, mock_get_filter, mock_get_types, app
) -> None:
    """Test basic functionality with results."""
    limit = 5
    offset = 0
    mock_bindings = [
        {
            "s": {"value": SAMPLE_REFERRING_SUBJECT_1},
            "p": {"value": SAMPLE_PREDICATE_1},
        },
        {
            "s": {"value": SAMPLE_REFERRING_SUBJECT_2},
            "p": {"value": SAMPLE_PREDICATE_2},
        },
    ]
    mock_sparql_instance = mock_sparql_query_results(
        mock_bindings, limit=limit, offset=offset
    )
    mock_get_sparql.return_value = mock_sparql_instance
    mock_get_filter.return_value.value_label.side_effect = lambda s, _t: f"{s}_label"
    # Updated to match the new tuple-based structure
    mock_get_filter.return_value.human_readable_predicate.side_effect = lambda p, _: (
        f"{p}_label"
    )
    mock_get_filter.return_value.human_readable_class.return_value = "Type A"
    mock_get_types.return_value = [SAMPLE_TYPE_1]

    with app.app_context():
        refs, has_more = get_paginated_inverse_references(
            SAMPLE_SUBJECT_URI, limit=limit, offset=offset
        )

    assert not has_more
    assert len(refs) == 2
    assert refs[0]["subject"] == SAMPLE_REFERRING_SUBJECT_1
    assert refs[0]["predicate"] == SAMPLE_PREDICATE_1
    assert refs[0]["label"] == f"{SAMPLE_REFERRING_SUBJECT_1}_label"
    assert refs[0]["predicate_label"] == f"{SAMPLE_PREDICATE_1}_label"
    assert refs[0]["type_label"] == "Type A"
    assert refs[1]["subject"] == SAMPLE_REFERRING_SUBJECT_2


@patch("heritrace.routes.linked_resources.get_entity_types")
@patch("heritrace.routes.linked_resources.get_custom_filter")
@patch("heritrace.routes.linked_resources.get_sparql")
@patch("heritrace.routes.linked_resources.is_virtuoso", new=lambda: False)
def test_get_paginated_inverse_references_pagination_has_more(
    mock_get_sparql, mock_get_filter, mock_get_types, app
) -> None:
    """Test pagination where more results exist."""
    limit = 2
    offset = 0
    mock_bindings = [
        {
            "s": {"value": SAMPLE_REFERRING_SUBJECT_1},
            "p": {"value": SAMPLE_PREDICATE_1},
        },
        {
            "s": {"value": SAMPLE_REFERRING_SUBJECT_2},
            "p": {"value": SAMPLE_PREDICATE_2},
        },
        {
            "s": {"value": SAMPLE_REFERRING_SUBJECT_3},
            "p": {"value": SAMPLE_PREDICATE_1},
        },
    ]
    mock_sparql_instance = mock_sparql_query_results(
        mock_bindings, limit=limit, offset=offset
    )
    mock_get_sparql.return_value = mock_sparql_instance
    mock_get_filter.return_value.value_label.side_effect = lambda s, _t: f"{s}_label"
    # Updated to match the new tuple-based structure
    mock_get_filter.return_value.human_readable_predicate.side_effect = lambda p, _: (
        f"{p}_label"
    )
    mock_get_filter.return_value.human_readable_class.return_value = "Type A"
    mock_get_types.return_value = [SAMPLE_TYPE_1]

    with app.app_context():
        refs, has_more = get_paginated_inverse_references(
            SAMPLE_SUBJECT_URI, limit=limit, offset=offset
        )

    assert has_more
    assert len(refs) == 2
    assert refs[0]["subject"] == SAMPLE_REFERRING_SUBJECT_1
    assert refs[0]["label"] == f"{SAMPLE_REFERRING_SUBJECT_1}_label"
    assert refs[0]["predicate"] == SAMPLE_PREDICATE_1
    assert refs[0]["predicate_label"] == f"{SAMPLE_PREDICATE_1}_label"
    assert refs[0]["type_label"] == "Type A"
    assert refs[1]["subject"] == SAMPLE_REFERRING_SUBJECT_2


@patch("heritrace.routes.linked_resources.get_entity_types")
@patch("heritrace.routes.linked_resources.get_custom_filter")
@patch("heritrace.routes.linked_resources.get_sparql")
@patch("heritrace.routes.linked_resources.is_virtuoso", new=lambda: False)
def test_get_paginated_inverse_references_pagination_no_more(
    mock_get_sparql, mock_get_filter, mock_get_types, app
) -> None:
    """Test pagination where no more results exist."""
    limit = 2
    offset = 2
    all_bindings = [
        {
            "s": {"value": SAMPLE_REFERRING_SUBJECT_1},
            "p": {"value": SAMPLE_PREDICATE_1},
        },
        {
            "s": {"value": SAMPLE_REFERRING_SUBJECT_2},
            "p": {"value": SAMPLE_PREDICATE_2},
        },
        {
            "s": {"value": SAMPLE_REFERRING_SUBJECT_3},
            "p": {"value": SAMPLE_PREDICATE_1},
        },
    ]
    mock_sparql_instance = mock_sparql_query_results(
        all_bindings, limit=limit, offset=offset
    )
    mock_get_sparql.return_value = mock_sparql_instance
    mock_get_filter.return_value.value_label.side_effect = lambda s, _t: f"{s}_label"
    # Updated to match the new tuple-based structure
    mock_get_filter.return_value.human_readable_predicate.side_effect = lambda p, _: (
        f"{p}_label"
    )
    mock_get_filter.return_value.human_readable_class.return_value = "Type A"
    mock_get_types.return_value = [SAMPLE_TYPE_1]

    with app.app_context():
        refs, has_more = get_paginated_inverse_references(
            SAMPLE_SUBJECT_URI, limit=limit, offset=offset
        )

    assert not has_more
    assert len(refs) == 1
    assert refs[0]["subject"] == SAMPLE_REFERRING_SUBJECT_3
    assert refs[0]["label"] == f"{SAMPLE_REFERRING_SUBJECT_3}_label"
    assert refs[0]["predicate"] == SAMPLE_PREDICATE_1
    assert refs[0]["predicate_label"] == f"{SAMPLE_PREDICATE_1}_label"
    assert refs[0]["type_label"] == "Type A"


@patch("heritrace.routes.linked_resources.get_entity_types")
@patch("heritrace.routes.linked_resources.get_custom_filter")
@patch("heritrace.routes.linked_resources.get_sparql")
@patch("heritrace.routes.linked_resources.is_virtuoso", new=lambda: False)
def test_get_paginated_inverse_references_no_results(
    mock_get_sparql, mock_get_filter, mock_get_types, app
) -> None:
    """Test the case with no inverse references."""
    limit = 5
    offset = 0
    mock_sparql_instance = mock_sparql_query_results([], limit=limit, offset=offset)
    mock_get_sparql.return_value = mock_sparql_instance

    with app.app_context():
        refs, has_more = get_paginated_inverse_references(
            SAMPLE_SUBJECT_URI, limit=limit, offset=offset
        )

    assert not has_more
    assert len(refs) == 0


@patch("heritrace.routes.linked_resources.get_entity_types")
@patch("heritrace.routes.linked_resources.get_custom_filter")
@patch("heritrace.routes.linked_resources.get_sparql")
@pytest.mark.parametrize("backend", ["virtuoso", "qlever", "default"])
def test_get_paginated_inverse_references_backend(
    mock_get_sparql, mock_get_filter, mock_get_types, app, backend
) -> None:
    app.config["DATASET_DB_TRIPLESTORE"] = backend
    app.extensions["heritrace"] = replace(
        app.extensions["heritrace"], is_virtuoso=backend == "virtuoso"
    )
    limit = 5
    offset = 0
    mock_sparql_instance = mock_sparql_query_results([], limit=limit, offset=offset)
    mock_get_sparql.return_value = mock_sparql_instance

    with app.app_context():
        get_paginated_inverse_references(SAMPLE_SUBJECT_URI, limit=limit, offset=offset)

    call_args_list = mock_sparql_instance.setQuery.call_args_list
    assert len(call_args_list) == 1
    main_query = call_args_list[0].args[0]
    patterns = {
        "virtuoso": [
            "    GRAPH ?g { ?s ?p ?o . }",
            f"    FILTER(?g NOT IN (<{'>, <'.join(VIRTUOSO_EXCLUDED_GRAPHS)}>))",
            f"    FILTER(?o = <{SAMPLE_SUBJECT_URI}>)",
        ],
        "qlever": [f"    ?s ?p <{SAMPLE_SUBJECT_URI}> ."],
        "default": [f"    ?s ?p <{SAMPLE_SUBJECT_URI}> ."],
    }
    assert main_query.splitlines() == [
        "SELECT DISTINCT ?s ?p WHERE {",
        *patterns[backend],
        "    FILTER(?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)",
        "} ORDER BY ?s OFFSET 0 LIMIT 6",
    ]


@patch("heritrace.routes.linked_resources.get_sparql")
def test_get_paginated_inverse_references_exception(mock_get_sparql, app) -> None:
    """Test exception handling during SPARQL query."""
    mock_sparql_instance = MagicMock()
    mock_sparql_instance.query.side_effect = RuntimeError("SPARQL Error")
    mock_get_sparql.return_value = mock_sparql_instance

    with app.app_context(), pytest.raises(RuntimeError, match="SPARQL Error"):
        get_paginated_inverse_references(SAMPLE_SUBJECT_URI, limit=5, offset=0)


@patch("heritrace.routes.linked_resources.get_paginated_inverse_references")
def test_get_linked_resources_api_success(mock_get_paginated, logged_in_client) -> None:
    """Test successful API call."""
    limit = 5
    offset = 0
    mock_data = [
        {
            "subject": SAMPLE_REFERRING_SUBJECT_1,
            "predicate": SAMPLE_PREDICATE_1,
            "label": "Ref1",
            "type_label": "Type A",
            "predicate_label": "Pred1",
        },
    ]
    mock_get_paginated.return_value = (mock_data, False)

    response = logged_in_client.get(
        f"/api/linked-resources/?subject_uri={SAMPLE_SUBJECT_URI}&limit={limit}&offset={offset}"
    )

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "success"
    assert json_data["results"] == mock_data
    assert not json_data["has_more"]
    mock_get_paginated.assert_called_once_with(SAMPLE_SUBJECT_URI, limit, offset)


@patch("heritrace.routes.linked_resources.get_paginated_inverse_references")
def test_get_linked_resources_api_success_no_results(
    mock_get_paginated, logged_in_client
) -> None:
    """Test successful API call with no results."""
    mock_get_paginated.return_value = ([], False)

    response = logged_in_client.get(
        f"/api/linked-resources/?subject_uri={SAMPLE_SUBJECT_URI}"
    )

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "success"
    assert json_data["results"] == []
    assert not json_data["has_more"]
    mock_get_paginated.assert_called_once_with(SAMPLE_SUBJECT_URI, 5, 0)


def test_get_linked_resources_api_missing_subject(logged_in_client) -> None:
    """Test API call with missing subject_uri."""
    response = logged_in_client.get("/api/linked-resources/")
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["status"] == "error"
    assert "Missing subject_uri" in json_data["message"]


def test_get_linked_resources_api_invalid_limit(logged_in_client) -> None:
    """Test API call with invalid limit."""
    response = logged_in_client.get(
        f"/api/linked-resources/?subject_uri={SAMPLE_SUBJECT_URI}&limit=abc"
    )
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["status"] == "error"
    assert "Invalid limit or offset" in json_data["message"]


def test_get_linked_resources_api_invalid_offset(logged_in_client) -> None:
    """Test API call with invalid offset."""
    response = logged_in_client.get(
        f"/api/linked-resources/?subject_uri={SAMPLE_SUBJECT_URI}&offset=xyz"
    )
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["status"] == "error"
    assert "Invalid limit or offset" in json_data["message"]


def test_get_linked_resources_api_negative_limit(logged_in_client) -> None:
    """Test API call with negative limit."""
    response = logged_in_client.get(
        f"/api/linked-resources/?subject_uri={SAMPLE_SUBJECT_URI}&limit=-1"
    )
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["status"] == "error"
    assert "Limit must be positive" in json_data["message"]


def test_get_linked_resources_api_negative_offset(logged_in_client) -> None:
    """Test API call with negative offset."""
    response = logged_in_client.get(
        f"/api/linked-resources/?subject_uri={SAMPLE_SUBJECT_URI}&offset=-5"
    )
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["status"] == "error"
    assert "offset non-negative" in json_data["message"]


@patch("heritrace.routes.linked_resources.get_paginated_inverse_references")
def test_get_linked_resources_api_internal_error(
    mock_get_paginated, logged_in_client, app
) -> None:
    """Test API call when get_paginated_inverse_references handles an internal error."""
    mock_get_paginated.return_value = ([], False)

    response = logged_in_client.get(
        f"/api/linked-resources/?subject_uri={SAMPLE_SUBJECT_URI}"
    )

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "success"
    assert json_data["results"] == []
    assert not json_data["has_more"]
    mock_get_paginated.assert_called_once_with(SAMPLE_SUBJECT_URI, 5, 0)


@patch("heritrace.routes.linked_resources.get_sparql")
@patch("heritrace.routes.linked_resources.is_virtuoso", new=lambda: False)
def test_resolve_parent_entity_success_non_virtuoso(mock_get_sparql) -> None:
    """Test _resolve_parent_entity successful resolution on non-Virtuoso."""
    mock_sparql = MagicMock()
    mock_get_sparql.return_value = mock_sparql

    mock_result = {
        "results": {"bindings": [{"source": {"value": "http://example.org/source1"}}]}
    }
    mock_sparql.query.return_value.convert.return_value = mock_result

    subject_uri = "http://example.org/composite1"
    predicate = "http://example.org/originalPred"
    connecting_predicate = "http://example.org/connectingPred"

    final_subject, final_predicate = _resolve_parent_entity(
        subject_uri, predicate, connecting_predicate
    )

    assert final_subject == "http://example.org/source1"
    assert final_predicate == connecting_predicate
    mock_sparql.setQuery.assert_called_once()
    query_call = mock_sparql.setQuery.call_args[0][0]
    assert f"?source <{connecting_predicate}> <{subject_uri}>" in query_call
    assert "GRAPH" not in query_call


@patch("heritrace.routes.linked_resources.get_sparql")
@patch("heritrace.routes.linked_resources.is_virtuoso", new=lambda: True)
def test_resolve_parent_entity_success_virtuoso(mock_get_sparql) -> None:
    """Test _resolve_parent_entity successful resolution on Virtuoso."""
    mock_sparql = MagicMock()
    mock_get_sparql.return_value = mock_sparql

    mock_result = {
        "results": {"bindings": [{"source": {"value": "http://example.org/source1"}}]}
    }
    mock_sparql.query.return_value.convert.return_value = mock_result

    subject_uri = "http://example.org/composite1"
    predicate = "http://example.org/originalPred"
    connecting_predicate = "http://example.org/connectingPred"

    final_subject, final_predicate = _resolve_parent_entity(
        subject_uri, predicate, connecting_predicate
    )

    assert final_subject == "http://example.org/source1"
    assert final_predicate == connecting_predicate
    mock_sparql.setQuery.assert_called_once()
    query_call = mock_sparql.setQuery.call_args[0][0]
    assert f"?source <{connecting_predicate}> <{subject_uri}>" in query_call
    assert "GRAPH ?g" in query_call
    assert "FILTER(?g NOT IN" in query_call


@patch("heritrace.routes.linked_resources.get_sparql")
@patch("heritrace.routes.linked_resources.is_virtuoso", new=lambda: False)
def test_resolve_parent_entity_no_results(mock_get_sparql) -> None:
    """Test _resolve_parent_entity when no source is found."""
    mock_sparql = MagicMock()
    mock_get_sparql.return_value = mock_sparql

    mock_result = {"results": {"bindings": []}}
    mock_sparql.query.return_value.convert.return_value = mock_result

    subject_uri = "http://example.org/composite1"
    predicate = "http://example.org/originalPred"
    connecting_predicate = "http://example.org/connectingPred"

    final_subject, final_predicate = _resolve_parent_entity(
        subject_uri, predicate, connecting_predicate
    )

    assert final_subject == subject_uri
    assert final_predicate == predicate


@patch("heritrace.routes.linked_resources.get_sparql")
@patch("heritrace.routes.linked_resources.is_virtuoso", new=lambda: False)
def test_resolve_parent_entity_exception(mock_get_sparql):
    mock_get_sparql.return_value.query.side_effect = SPARQLWrapperException()
    with pytest.raises(SPARQLWrapperException):
        _resolve_parent_entity(
            "http://example.org/composite1",
            "http://example.org/originalPred",
            "http://example.org/connectingPred",
        )


@patch("heritrace.routes.linked_resources._resolve_parent_entity")
@patch(
    "heritrace.routes.linked_resources.determine_shape_for_classes",
    new=lambda _types: COMPOSITE_SHAPE,
)
@patch("heritrace.routes.linked_resources._composite_parent_paths")
@patch("heritrace.routes.linked_resources.get_entity_types")
@patch("heritrace.routes.linked_resources.get_custom_filter")
@patch("heritrace.routes.linked_resources.get_sparql")
@patch("heritrace.routes.linked_resources.is_virtuoso", new=lambda: False)
def test_get_paginated_inverse_references_with_composite_entity(
    mock_get_sparql,
    mock_get_filter,
    mock_get_types,
    mock_composite_paths,
    mock_resolve_composite,
    app,
) -> None:
    """Test get_paginated_inverse_references when a composite entity is found."""
    limit = 5
    offset = 0
    composite_uri = "http://example.org/composite1"
    source_uri = "http://example.org/source1"
    predicate = "http://example.org/originalPred"
    connecting_predicate = "http://example.org/connectingPred"

    mock_bindings = [
        {"s": {"value": composite_uri}, "p": {"value": predicate}},
    ]
    mock_sparql_instance = mock_sparql_query_results(
        mock_bindings, limit=limit, offset=offset
    )
    mock_get_sparql.return_value = mock_sparql_instance

    # Mock composite detection
    mock_composite_paths.return_value = {COMPOSITE_SHAPE: connecting_predicate}
    mock_resolve_composite.return_value = (source_uri, connecting_predicate)

    # Mock entity type calls for both composite and source
    mock_get_types.side_effect = [
        ["http://example.org/CompositeType"],  # types for composite
        ["http://example.org/SourceType"],  # types for source
    ]

    mock_get_filter.return_value.value_label.side_effect = lambda s, _t: f"{s}_label"
    mock_get_filter.return_value.human_readable_predicate.side_effect = lambda p, _: (
        f"{p}_label"
    )
    mock_get_filter.return_value.human_readable_class.return_value = "Source Type"

    with app.app_context():
        refs, has_more = get_paginated_inverse_references(
            SAMPLE_SUBJECT_URI, limit=limit, offset=offset
        )

    assert not has_more
    assert len(refs) == 1
    assert refs[0]["subject"] == source_uri  # Should be resolved source, not composite
    assert (
        refs[0]["predicate"] == connecting_predicate
    )  # Should be connecting predicate
    assert refs[0]["label"] == f"{source_uri}_label"
    assert refs[0]["predicate_label"] == f"{connecting_predicate}_label"
    assert refs[0]["type_label"] == "Source Type"

    # Verify that resolve_composite_entity was called
    mock_resolve_composite.assert_called_once_with(
        composite_uri, predicate, connecting_predicate
    )
    # Verify get_entity_types was called twice - once for composite, once for source
    assert mock_get_types.call_count == 2


@patch("heritrace.routes.linked_resources._resolve_parent_entity")
@patch(
    "heritrace.routes.linked_resources.determine_shape_for_classes",
    new=lambda _types: COMPOSITE_SHAPE,
)
@patch("heritrace.routes.linked_resources._composite_parent_paths")
@patch("heritrace.routes.linked_resources.get_entity_types")
@patch("heritrace.routes.linked_resources.get_custom_filter")
@patch("heritrace.routes.linked_resources.get_sparql")
@patch("heritrace.routes.linked_resources.is_virtuoso", new=lambda: False)
def test_get_paginated_inverse_references_composite_same_as_original(
    mock_get_sparql,
    mock_get_filter,
    mock_get_types,
    mock_composite_paths,
    mock_resolve_composite,
    app,
) -> None:
    """
    Test composite handling when resolved entity is same as original (composite
    resolution failed).
    """
    limit = 5
    offset = 0
    composite_uri = "http://example.org/composite1"
    predicate = "http://example.org/originalPred"
    connecting_predicate = "http://example.org/connectingPred"

    mock_bindings = [
        {"s": {"value": composite_uri}, "p": {"value": predicate}},
    ]
    mock_sparql_instance = mock_sparql_query_results(
        mock_bindings, limit=limit, offset=offset
    )
    mock_get_sparql.return_value = mock_sparql_instance

    # Mock composite detection
    mock_composite_paths.return_value = {COMPOSITE_SHAPE: connecting_predicate}
    # Mock failed resolution - returns same URI
    mock_resolve_composite.return_value = (composite_uri, predicate)

    # Mock entity types - only called once since resolved == original
    mock_get_types.return_value = ["http://example.org/CompositeType"]

    mock_get_filter.return_value.value_label.side_effect = lambda s, _t: f"{s}_label"
    mock_get_filter.return_value.human_readable_predicate.side_effect = lambda p, _: (
        f"{p}_label"
    )
    mock_get_filter.return_value.human_readable_class.return_value = "Composite Type"

    with app.app_context():
        refs, has_more = get_paginated_inverse_references(
            SAMPLE_SUBJECT_URI, limit=limit, offset=offset
        )

    assert not has_more
    assert len(refs) == 1
    assert refs[0]["subject"] == composite_uri
    assert refs[0]["predicate"] == predicate
    assert refs[0]["label"] == f"{composite_uri}_label"
    assert refs[0]["predicate_label"] == f"{predicate}_label"
    assert refs[0]["type_label"] == "Composite Type"

    # Verify get_entity_types was called only once
    assert mock_get_types.call_count == 1


@patch("heritrace.routes.linked_resources.get_entity_types")
@patch("heritrace.routes.linked_resources.get_custom_filter")
@patch("heritrace.routes.linked_resources.get_sparql")
@patch("heritrace.routes.linked_resources.is_virtuoso", new=lambda: False)
def test_get_paginated_inverse_references_no_highest_priority_type(
    mock_get_sparql, mock_get_filter, mock_get_types, app
) -> None:
    """Test when get_highest_priority_class returns None."""
    limit = 5
    offset = 0
    mock_bindings = [
        {
            "s": {"value": SAMPLE_REFERRING_SUBJECT_1},
            "p": {"value": SAMPLE_PREDICATE_1},
        },
    ]
    mock_sparql_instance = mock_sparql_query_results(
        mock_bindings, limit=limit, offset=offset
    )
    mock_get_sparql.return_value = mock_sparql_instance

    mock_get_filter.return_value.value_label.side_effect = lambda s, _t: f"{s}_label"
    mock_get_filter.return_value.human_readable_predicate.side_effect = lambda p, _: (
        f"{p}_label"
    )
    mock_get_filter.return_value.human_readable_class.return_value = (
        None  # No type label
    )
    mock_get_types.return_value = []  # Empty types list

    with app.app_context():
        refs, has_more = get_paginated_inverse_references(
            SAMPLE_SUBJECT_URI, limit=limit, offset=offset
        )

    assert not has_more
    assert len(refs) == 1
    assert refs[0]["subject"] == SAMPLE_REFERRING_SUBJECT_1
    assert refs[0]["predicate"] == SAMPLE_PREDICATE_1
    assert refs[0]["label"] == f"{SAMPLE_REFERRING_SUBJECT_1}_label"
    assert refs[0]["predicate_label"] == f"{SAMPLE_PREDICATE_1}_label"
    assert refs[0]["type_label"] is None  # Should be None when no highest priority type


@pytest.mark.parametrize("error", [TimeoutError("timed out"), SPARQLWrapperException()])
@patch("heritrace.routes.linked_resources.get_paginated_inverse_references")
def test_linked_resources_endpoint_failure(mock_get_paginated, logged_in_client, error):
    mock_get_paginated.side_effect = error
    response = logged_in_client.get(
        "/api/linked-resources/", query_string={"subject_uri": SAMPLE_SUBJECT_URI}
    )
    assert response.status_code == 502
    assert response.get_json() == {
        "status": "error",
        "message": "Error loading linked resources.",
    }


@patch("heritrace.routes.linked_resources._composite_parent_paths")
@patch(
    "heritrace.routes.linked_resources.determine_shape_for_classes",
    new=lambda _types: COMPOSITE_SHAPE,
)
@patch("heritrace.routes.linked_resources.get_highest_priority_class")
@patch("heritrace.routes.linked_resources.get_entity_types")
@patch("heritrace.routes.linked_resources.get_custom_filter")
@patch("heritrace.routes.linked_resources.get_sparql")
@patch("heritrace.routes.linked_resources.is_virtuoso", new=lambda: False)
def test_get_paginated_inverse_references_skips_inverse_composite_children(
    mock_get_sparql,
    _mock_get_filter,
    mock_get_types,
    _mock_priority,
    mock_composite_paths,
    app,
) -> None:
    mock_get_sparql.return_value = mock_sparql_query_results(
        [{"s": {"value": "urn:citation"}, "p": {"value": "urn:cites"}}],
        limit=5,
        offset=0,
    )
    mock_get_types.return_value = ["urn:Citation"]
    mock_composite_paths.return_value = {COMPOSITE_SHAPE: "^urn:cites"}

    with app.app_context():
        references, has_more = get_paginated_inverse_references(
            SAMPLE_SUBJECT_URI, limit=5, offset=0
        )

    assert references == []
    assert not has_more
