from unittest.mock import MagicMock, patch

from heritrace.routes.linked_resources import (
    _is_proxy_entity, _resolve_proxy_entity, get_paginated_inverse_references)

SAMPLE_SUBJECT_URI = "http://example.org/entity1"
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
        fetched_bindings = results_bindings[offset:offset + query_limit] if offset is not None else results_bindings[:query_limit]
    else:
        fetched_bindings = results_bindings

    data_results = {
        "results": {
            "bindings": fetched_bindings
        }
    }

    mock_convert.return_value = data_results
    mock_sparql.query.return_value.convert = mock_convert
    return mock_sparql

@patch('heritrace.routes.linked_resources.get_entity_types')
@patch('heritrace.routes.linked_resources.get_custom_filter')
@patch('heritrace.routes.linked_resources.get_sparql')
@patch('heritrace.routes.linked_resources.is_virtuoso', False)
def test_get_paginated_inverse_references_basic(mock_get_sparql, mock_get_filter, mock_get_types, app):
    """Test basic functionality with results."""
    limit = 5
    offset = 0
    mock_bindings = [
        {"s": {"value": SAMPLE_REFERRING_SUBJECT_1}, "p": {"value": SAMPLE_PREDICATE_1}},
        {"s": {"value": SAMPLE_REFERRING_SUBJECT_2}, "p": {"value": SAMPLE_PREDICATE_2}},
    ]
    mock_sparql_instance = mock_sparql_query_results(mock_bindings, limit=limit, offset=offset)
    mock_get_sparql.return_value = mock_sparql_instance
    mock_get_filter.return_value.human_readable_entity.side_effect = lambda s, t: f"{s}_label"
    # Updated to match the new tuple-based structure
    mock_get_filter.return_value.human_readable_predicate.side_effect = lambda p, _: f"{p}_label"
    mock_get_filter.return_value.human_readable_class.return_value = "Type A"
    mock_get_types.return_value = [SAMPLE_TYPE_1]

    with app.app_context():
        refs, has_more = get_paginated_inverse_references(SAMPLE_SUBJECT_URI, limit=limit, offset=offset)

    assert not has_more
    assert len(refs) == 2
    assert refs[0]["subject"] == SAMPLE_REFERRING_SUBJECT_1
    assert refs[0]["predicate"] == SAMPLE_PREDICATE_1
    assert refs[0]["label"] == f"{SAMPLE_REFERRING_SUBJECT_1}_label"
    assert refs[0]["predicate_label"] == f"{SAMPLE_PREDICATE_1}_label"
    assert refs[0]["type_label"] == "Type A"
    assert refs[1]["subject"] == SAMPLE_REFERRING_SUBJECT_2

@patch('heritrace.routes.linked_resources.get_entity_types')
@patch('heritrace.routes.linked_resources.get_custom_filter')
@patch('heritrace.routes.linked_resources.get_sparql')
@patch('heritrace.routes.linked_resources.is_virtuoso', False)
def test_get_paginated_inverse_references_pagination_has_more(mock_get_sparql, mock_get_filter, mock_get_types, app):
    """Test pagination where more results exist."""
    limit = 2
    offset = 0
    mock_bindings = [
        {"s": {"value": SAMPLE_REFERRING_SUBJECT_1}, "p": {"value": SAMPLE_PREDICATE_1}},
        {"s": {"value": SAMPLE_REFERRING_SUBJECT_2}, "p": {"value": SAMPLE_PREDICATE_2}},
        {"s": {"value": SAMPLE_REFERRING_SUBJECT_3}, "p": {"value": SAMPLE_PREDICATE_1}},
    ]
    mock_sparql_instance = mock_sparql_query_results(mock_bindings, limit=limit, offset=offset)
    mock_get_sparql.return_value = mock_sparql_instance
    mock_get_filter.return_value.human_readable_entity.side_effect = lambda s, t: f"{s}_label"
    # Updated to match the new tuple-based structure
    mock_get_filter.return_value.human_readable_predicate.side_effect = lambda p, _: f"{p}_label"
    mock_get_filter.return_value.human_readable_class.return_value = "Type A"
    mock_get_types.return_value = [SAMPLE_TYPE_1]

    with app.app_context():
        refs, has_more = get_paginated_inverse_references(SAMPLE_SUBJECT_URI, limit=limit, offset=offset)

    assert has_more
    assert len(refs) == 2
    assert refs[0]["subject"] == SAMPLE_REFERRING_SUBJECT_1
    assert refs[0]["label"] == f"{SAMPLE_REFERRING_SUBJECT_1}_label"
    assert refs[0]["predicate"] == SAMPLE_PREDICATE_1
    assert refs[0]["predicate_label"] == f"{SAMPLE_PREDICATE_1}_label"
    assert refs[0]["type_label"] == "Type A"
    assert refs[1]["subject"] == SAMPLE_REFERRING_SUBJECT_2

@patch('heritrace.routes.linked_resources.get_entity_types')
@patch('heritrace.routes.linked_resources.get_custom_filter')
@patch('heritrace.routes.linked_resources.get_sparql')
@patch('heritrace.routes.linked_resources.is_virtuoso', False)
def test_get_paginated_inverse_references_pagination_no_more(mock_get_sparql, mock_get_filter, mock_get_types, app):
    """Test pagination where no more results exist."""
    limit = 2
    offset = 2
    all_bindings = [
        {"s": {"value": SAMPLE_REFERRING_SUBJECT_1}, "p": {"value": SAMPLE_PREDICATE_1}},
        {"s": {"value": SAMPLE_REFERRING_SUBJECT_2}, "p": {"value": SAMPLE_PREDICATE_2}},
        {"s": {"value": SAMPLE_REFERRING_SUBJECT_3}, "p": {"value": SAMPLE_PREDICATE_1}},
    ]
    mock_sparql_instance = mock_sparql_query_results(all_bindings, limit=limit, offset=offset)
    mock_get_sparql.return_value = mock_sparql_instance
    mock_get_filter.return_value.human_readable_entity.side_effect = lambda s, t: f"{s}_label"
    # Updated to match the new tuple-based structure
    mock_get_filter.return_value.human_readable_predicate.side_effect = lambda p, _: f"{p}_label"
    mock_get_filter.return_value.human_readable_class.return_value = "Type A"
    mock_get_types.return_value = [SAMPLE_TYPE_1]

    with app.app_context():
        refs, has_more = get_paginated_inverse_references(SAMPLE_SUBJECT_URI, limit=limit, offset=offset)

    assert not has_more
    assert len(refs) == 1
    assert refs[0]["subject"] == SAMPLE_REFERRING_SUBJECT_3
    assert refs[0]["label"] == f"{SAMPLE_REFERRING_SUBJECT_3}_label"
    assert refs[0]["predicate"] == SAMPLE_PREDICATE_1
    assert refs[0]["predicate_label"] == f"{SAMPLE_PREDICATE_1}_label"
    assert refs[0]["type_label"] == "Type A"

@patch('heritrace.routes.linked_resources.get_entity_types')
@patch('heritrace.routes.linked_resources.get_custom_filter')
@patch('heritrace.routes.linked_resources.get_sparql')
@patch('heritrace.routes.linked_resources.is_virtuoso', False)
def test_get_paginated_inverse_references_no_results(mock_get_sparql, mock_get_filter, mock_get_types, app):
    """Test the case with no inverse references."""
    limit = 5
    offset = 0
    mock_sparql_instance = mock_sparql_query_results([], limit=limit, offset=offset)
    mock_get_sparql.return_value = mock_sparql_instance

    with app.app_context():
        refs, has_more = get_paginated_inverse_references(SAMPLE_SUBJECT_URI, limit=limit, offset=offset)

    assert not has_more
    assert len(refs) == 0

@patch('heritrace.routes.linked_resources.get_entity_types')
@patch('heritrace.routes.linked_resources.get_custom_filter')
@patch('heritrace.routes.linked_resources.get_sparql')
@patch('heritrace.routes.linked_resources.is_virtuoso', True)
def test_get_paginated_inverse_references_virtuoso(mock_get_sparql, mock_get_filter, mock_get_types, app):
    """Test query structure when is_virtuoso is True."""
    limit = 5
    offset = 0
    mock_sparql_instance = mock_sparql_query_results([], limit=limit, offset=offset)
    mock_get_sparql.return_value = mock_sparql_instance

    with app.app_context():
        get_paginated_inverse_references(SAMPLE_SUBJECT_URI, limit=limit, offset=offset)

    call_args_list = mock_sparql_instance.setQuery.call_args_list
    assert len(call_args_list) == 1
    main_query = call_args_list[0].args[0]
    assert "GRAPH ?g { ?s ?p ?o . }" in main_query
    assert "FILTER(?g NOT IN (" in main_query
    assert f"OFFSET {offset} LIMIT {limit + 1}" in main_query

@patch('heritrace.routes.linked_resources.get_sparql')
def test_get_paginated_inverse_references_exception(mock_get_sparql, app):
    """Test exception handling during SPARQL query."""
    mock_sparql_instance = MagicMock()
    mock_sparql_instance.query.side_effect = Exception("SPARQL Error")
    mock_get_sparql.return_value = mock_sparql_instance

    with app.app_context():
        refs, has_more = get_paginated_inverse_references(SAMPLE_SUBJECT_URI, limit=5, offset=0)

    assert not has_more
    assert len(refs) == 0

@patch('heritrace.routes.linked_resources.get_paginated_inverse_references')
def test_get_linked_resources_api_success(mock_get_paginated, logged_in_client):
    """Test successful API call."""
    limit = 5
    offset = 0
    mock_data = [
        {"subject": SAMPLE_REFERRING_SUBJECT_1, "predicate": SAMPLE_PREDICATE_1, "label": "Ref1", "type_label": "Type A", "predicate_label": "Pred1"},
    ]
    mock_get_paginated.return_value = (mock_data, False)

    response = logged_in_client.get(f'/api/linked-resources/?subject_uri={SAMPLE_SUBJECT_URI}&limit={limit}&offset={offset}')

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'success'
    assert json_data['results'] == mock_data
    assert not json_data['has_more']
    mock_get_paginated.assert_called_once_with(SAMPLE_SUBJECT_URI, limit, offset)

@patch('heritrace.routes.linked_resources.get_paginated_inverse_references')
def test_get_linked_resources_api_success_no_results(mock_get_paginated, logged_in_client):
    """Test successful API call with no results."""
    mock_get_paginated.return_value = ([], False)

    response = logged_in_client.get(f'/api/linked-resources/?subject_uri={SAMPLE_SUBJECT_URI}')

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'success'
    assert json_data['results'] == []
    assert not json_data['has_more']
    mock_get_paginated.assert_called_once_with(SAMPLE_SUBJECT_URI, 5, 0)

def test_get_linked_resources_api_missing_subject(logged_in_client):
    """Test API call with missing subject_uri."""
    response = logged_in_client.get('/api/linked-resources/')
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data['status'] == 'error'
    assert 'Missing subject_uri' in json_data['message']

def test_get_linked_resources_api_invalid_limit(logged_in_client):
    """Test API call with invalid limit."""
    response = logged_in_client.get(f'/api/linked-resources/?subject_uri={SAMPLE_SUBJECT_URI}&limit=abc')
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data['status'] == 'error'
    assert 'Invalid limit or offset' in json_data['message']

def test_get_linked_resources_api_invalid_offset(logged_in_client):
    """Test API call with invalid offset."""
    response = logged_in_client.get(f'/api/linked-resources/?subject_uri={SAMPLE_SUBJECT_URI}&offset=xyz')
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data['status'] == 'error'
    assert 'Invalid limit or offset' in json_data['message']

def test_get_linked_resources_api_negative_limit(logged_in_client):
    """Test API call with negative limit."""
    response = logged_in_client.get(f'/api/linked-resources/?subject_uri={SAMPLE_SUBJECT_URI}&limit=-1')
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data['status'] == 'error'
    assert 'Limit must be positive' in json_data['message']

def test_get_linked_resources_api_negative_offset(logged_in_client):
    """Test API call with negative offset."""
    response = logged_in_client.get(f'/api/linked-resources/?subject_uri={SAMPLE_SUBJECT_URI}&offset=-5')
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data['status'] == 'error'
    assert 'offset non-negative' in json_data['message']

@patch('heritrace.routes.linked_resources.get_paginated_inverse_references')
def test_get_linked_resources_api_internal_error(mock_get_paginated, logged_in_client, app):
    """Test API call when get_paginated_inverse_references handles an internal error."""
    mock_get_paginated.return_value = ([], False)

    response = logged_in_client.get(f'/api/linked-resources/?subject_uri={SAMPLE_SUBJECT_URI}')

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'success'
    assert json_data['results'] == []
    assert not json_data['has_more']
    mock_get_paginated.assert_called_once_with(SAMPLE_SUBJECT_URI, 5, 0)


@patch('heritrace.routes.linked_resources.get_display_rules')
def test_is_proxy_entity_empty_types(mock_get_display_rules):
    """Test _is_proxy_entity with empty entity types."""
    result, predicate = _is_proxy_entity([])
    assert not result
    assert predicate == ""
    mock_get_display_rules.assert_not_called()

@patch('heritrace.routes.linked_resources.get_display_rules')
def test_is_proxy_entity_no_display_rules(mock_get_display_rules):
    """Test _is_proxy_entity when display rules are None."""
    mock_get_display_rules.return_value = None
    result, predicate = _is_proxy_entity(["http://example.org/SomeType"])
    assert not result
    assert predicate == ""

@patch('heritrace.routes.linked_resources.get_display_rules')
def test_is_proxy_entity_no_matching_proxy(mock_get_display_rules):
    """Test _is_proxy_entity when no proxy class matches."""
    mock_get_display_rules.return_value = [
        {
            "displayProperties": [
                {
                    "property": "http://example.org/predicate1",
                    "intermediateRelation": {
                        "class": "http://example.org/DifferentType"
                    }
                }
            ]
        }
    ]
    result, predicate = _is_proxy_entity(["http://example.org/SomeType"])
    assert not result
    assert predicate == ""

@patch('heritrace.routes.linked_resources.get_display_rules')
def test_is_proxy_entity_matching_proxy(mock_get_display_rules):
    """Test _is_proxy_entity when a proxy class matches."""
    mock_get_display_rules.return_value = [
        {
            "displayProperties": [
                {
                    "property": "http://example.org/predicate1",
                    "intermediateRelation": {
                        "class": "http://example.org/ProxyType"
                    }
                }
            ]
        }
    ]
    result, predicate = _is_proxy_entity(["http://example.org/ProxyType"])
    assert result
    assert predicate == "http://example.org/predicate1"

@patch('heritrace.routes.linked_resources.get_display_rules')
def test_is_proxy_entity_nested_display_rules(mock_get_display_rules):
    """Test _is_proxy_entity with nested display rules."""
    mock_get_display_rules.return_value = [
        {
            "displayProperties": [
                {
                    "property": "http://example.org/predicate2",
                    "displayRules": [
                        {
                            "intermediateRelation": {
                                "class": "http://example.org/NestedProxyType"
                            }
                        }
                    ]
                }
            ]
        }
    ]
    result, predicate = _is_proxy_entity(["http://example.org/NestedProxyType"])
    assert result
    assert predicate == "http://example.org/predicate2"

@patch('heritrace.routes.linked_resources.get_display_rules')
def test_is_proxy_entity_no_intermediate_relation(mock_get_display_rules):
    """Test _is_proxy_entity when displayProperties have no intermediateRelation."""
    mock_get_display_rules.return_value = [
        {
            "displayProperties": [
                {
                    "property": "http://example.org/predicate1"
                    # No intermediateRelation
                }
            ]
        }
    ]
    result, predicate = _is_proxy_entity(["http://example.org/SomeType"])
    assert not result
    assert predicate == ""


@patch('heritrace.routes.linked_resources.get_sparql')
@patch('heritrace.routes.linked_resources.is_virtuoso', False)
def test_resolve_proxy_entity_success_non_virtuoso(mock_get_sparql):
    """Test _resolve_proxy_entity successful resolution on non-Virtuoso."""
    mock_sparql = MagicMock()
    mock_get_sparql.return_value = mock_sparql
    
    mock_result = {
        "results": {
            "bindings": [
                {"source": {"value": "http://example.org/source1"}}
            ]
        }
    }
    mock_sparql.query.return_value.convert.return_value = mock_result
    
    subject_uri = "http://example.org/proxy1"
    predicate = "http://example.org/originalPred"
    connecting_predicate = "http://example.org/connectingPred"
    
    final_subject, final_predicate = _resolve_proxy_entity(subject_uri, predicate, connecting_predicate)
    
    assert final_subject == "http://example.org/source1"
    assert final_predicate == connecting_predicate
    mock_sparql.setQuery.assert_called_once()
    query_call = mock_sparql.setQuery.call_args[0][0]
    assert f"?source <{connecting_predicate}> <{subject_uri}>" in query_call
    assert "GRAPH" not in query_call

@patch('heritrace.routes.linked_resources.get_sparql')
@patch('heritrace.routes.linked_resources.is_virtuoso', True)
def test_resolve_proxy_entity_success_virtuoso(mock_get_sparql):
    """Test _resolve_proxy_entity successful resolution on Virtuoso."""
    mock_sparql = MagicMock()
    mock_get_sparql.return_value = mock_sparql
    
    mock_result = {
        "results": {
            "bindings": [
                {"source": {"value": "http://example.org/source1"}}
            ]
        }
    }
    mock_sparql.query.return_value.convert.return_value = mock_result
    
    subject_uri = "http://example.org/proxy1"
    predicate = "http://example.org/originalPred"
    connecting_predicate = "http://example.org/connectingPred"
    
    final_subject, final_predicate = _resolve_proxy_entity(subject_uri, predicate, connecting_predicate)
    
    assert final_subject == "http://example.org/source1"
    assert final_predicate == connecting_predicate
    mock_sparql.setQuery.assert_called_once()
    query_call = mock_sparql.setQuery.call_args[0][0]
    assert f"?source <{connecting_predicate}> <{subject_uri}>" in query_call
    assert "GRAPH ?g" in query_call
    assert "FILTER(?g NOT IN" in query_call

@patch('heritrace.routes.linked_resources.get_sparql')
@patch('heritrace.routes.linked_resources.is_virtuoso', False)
def test_resolve_proxy_entity_no_results(mock_get_sparql):
    """Test _resolve_proxy_entity when no source is found."""
    mock_sparql = MagicMock()
    mock_get_sparql.return_value = mock_sparql
    
    mock_result = {
        "results": {
            "bindings": []
        }
    }
    mock_sparql.query.return_value.convert.return_value = mock_result
    
    subject_uri = "http://example.org/proxy1"
    predicate = "http://example.org/originalPred"
    connecting_predicate = "http://example.org/connectingPred"
    
    final_subject, final_predicate = _resolve_proxy_entity(subject_uri, predicate, connecting_predicate)
    
    assert final_subject == subject_uri
    assert final_predicate == predicate

@patch('heritrace.routes.linked_resources.get_sparql')
@patch('heritrace.routes.linked_resources.current_app')
@patch('heritrace.routes.linked_resources.is_virtuoso', False)
def test_resolve_proxy_entity_exception(mock_current_app, mock_get_sparql, app):
    """Test _resolve_proxy_entity when SPARQL query raises exception."""
    mock_sparql = MagicMock()
    mock_get_sparql.return_value = mock_sparql
    mock_sparql.query.side_effect = Exception("SPARQL Error")
    
    mock_logger = MagicMock()
    mock_current_app.logger = mock_logger
    
    subject_uri = "http://example.org/proxy1"
    predicate = "http://example.org/originalPred"
    connecting_predicate = "http://example.org/connectingPred"
    
    with app.app_context():
        final_subject, final_predicate = _resolve_proxy_entity(subject_uri, predicate, connecting_predicate)
    
    assert final_subject == subject_uri
    assert final_predicate == predicate
    mock_logger.error.assert_called_once()
    assert "Error resolving proxy entity" in mock_logger.error.call_args[0][0]


@patch('heritrace.routes.linked_resources._resolve_proxy_entity')
@patch('heritrace.routes.linked_resources._is_proxy_entity')
@patch('heritrace.routes.linked_resources.get_entity_types')
@patch('heritrace.routes.linked_resources.get_custom_filter')
@patch('heritrace.routes.linked_resources.get_sparql')
@patch('heritrace.routes.linked_resources.is_virtuoso', False)
def test_get_paginated_inverse_references_with_proxy_entity(mock_get_sparql, mock_get_filter, mock_get_types, mock_is_proxy, mock_resolve_proxy, app):
    """Test get_paginated_inverse_references when a proxy entity is found."""
    limit = 5
    offset = 0
    proxy_uri = "http://example.org/proxy1"
    source_uri = "http://example.org/source1" 
    predicate = "http://example.org/originalPred"
    connecting_predicate = "http://example.org/connectingPred"
    
    mock_bindings = [
        {"s": {"value": proxy_uri}, "p": {"value": predicate}},
    ]
    mock_sparql_instance = mock_sparql_query_results(mock_bindings, limit=limit, offset=offset)
    mock_get_sparql.return_value = mock_sparql_instance
    
    # Mock proxy detection
    mock_is_proxy.return_value = (True, connecting_predicate)
    mock_resolve_proxy.return_value = (source_uri, connecting_predicate)
    
    # Mock entity type calls for both proxy and source
    mock_get_types.side_effect = [
        ["http://example.org/ProxyType"],  # types for proxy
        ["http://example.org/SourceType"]  # types for source
    ]
    
    mock_get_filter.return_value.human_readable_entity.side_effect = lambda s, t: f"{s}_label"
    mock_get_filter.return_value.human_readable_predicate.side_effect = lambda p, _: f"{p}_label"
    mock_get_filter.return_value.human_readable_class.return_value = "Source Type"

    with app.app_context():
        refs, has_more = get_paginated_inverse_references(SAMPLE_SUBJECT_URI, limit=limit, offset=offset)

    assert not has_more
    assert len(refs) == 1
    assert refs[0]["subject"] == source_uri  # Should be resolved source, not proxy
    assert refs[0]["predicate"] == connecting_predicate  # Should be connecting predicate
    assert refs[0]["label"] == f"{source_uri}_label"
    assert refs[0]["predicate_label"] == f"{connecting_predicate}_label"
    assert refs[0]["type_label"] == "Source Type"
    
    # Verify that resolve_proxy_entity was called
    mock_resolve_proxy.assert_called_once_with(proxy_uri, predicate, connecting_predicate)
    # Verify get_entity_types was called twice - once for proxy, once for source
    assert mock_get_types.call_count == 2

@patch('heritrace.routes.linked_resources._resolve_proxy_entity')
@patch('heritrace.routes.linked_resources._is_proxy_entity')
@patch('heritrace.routes.linked_resources.get_entity_types')
@patch('heritrace.routes.linked_resources.get_custom_filter')
@patch('heritrace.routes.linked_resources.get_sparql')
@patch('heritrace.routes.linked_resources.is_virtuoso', False)
def test_get_paginated_inverse_references_proxy_same_as_original(mock_get_sparql, mock_get_filter, mock_get_types, mock_is_proxy, mock_resolve_proxy, app):
    """Test proxy handling when resolved entity is same as original (proxy resolution failed)."""
    limit = 5
    offset = 0
    proxy_uri = "http://example.org/proxy1"
    predicate = "http://example.org/originalPred"
    connecting_predicate = "http://example.org/connectingPred"
    
    mock_bindings = [
        {"s": {"value": proxy_uri}, "p": {"value": predicate}},
    ]
    mock_sparql_instance = mock_sparql_query_results(mock_bindings, limit=limit, offset=offset)
    mock_get_sparql.return_value = mock_sparql_instance
    
    # Mock proxy detection
    mock_is_proxy.return_value = (True, connecting_predicate)
    # Mock failed resolution - returns same URI
    mock_resolve_proxy.return_value = (proxy_uri, predicate)
    
    # Mock entity types - only called once since resolved == original
    mock_get_types.return_value = ["http://example.org/ProxyType"]
    
    mock_get_filter.return_value.human_readable_entity.side_effect = lambda s, t: f"{s}_label"
    mock_get_filter.return_value.human_readable_predicate.side_effect = lambda p, _: f"{p}_label"
    mock_get_filter.return_value.human_readable_class.return_value = "Proxy Type"

    with app.app_context():
        refs, has_more = get_paginated_inverse_references(SAMPLE_SUBJECT_URI, limit=limit, offset=offset)

    assert not has_more
    assert len(refs) == 1
    assert refs[0]["subject"] == proxy_uri
    assert refs[0]["predicate"] == predicate
    assert refs[0]["label"] == f"{proxy_uri}_label"
    assert refs[0]["predicate_label"] == f"{predicate}_label"
    assert refs[0]["type_label"] == "Proxy Type"
    
    # Verify get_entity_types was called only once
    assert mock_get_types.call_count == 1

@patch('heritrace.routes.linked_resources.get_entity_types')
@patch('heritrace.routes.linked_resources.get_custom_filter')
@patch('heritrace.routes.linked_resources.get_sparql')
@patch('heritrace.routes.linked_resources.is_virtuoso', False)
def test_get_paginated_inverse_references_no_highest_priority_type(mock_get_sparql, mock_get_filter, mock_get_types, app):
    """Test when get_highest_priority_class returns None."""
    limit = 5
    offset = 0
    mock_bindings = [
        {"s": {"value": SAMPLE_REFERRING_SUBJECT_1}, "p": {"value": SAMPLE_PREDICATE_1}},
    ]
    mock_sparql_instance = mock_sparql_query_results(mock_bindings, limit=limit, offset=offset)
    mock_get_sparql.return_value = mock_sparql_instance
    
    mock_get_filter.return_value.human_readable_entity.side_effect = lambda s, t: f"{s}_label"
    mock_get_filter.return_value.human_readable_predicate.side_effect = lambda p, _: f"{p}_label"
    mock_get_filter.return_value.human_readable_class.return_value = None  # No type label
    mock_get_types.return_value = []  # Empty types list

    with app.app_context():
        refs, has_more = get_paginated_inverse_references(SAMPLE_SUBJECT_URI, limit=limit, offset=offset)

    assert not has_more
    assert len(refs) == 1
    assert refs[0]["subject"] == SAMPLE_REFERRING_SUBJECT_1
    assert refs[0]["predicate"] == SAMPLE_PREDICATE_1
    assert refs[0]["label"] == f"{SAMPLE_REFERRING_SUBJECT_1}_label"
    assert refs[0]["predicate_label"] == f"{SAMPLE_PREDICATE_1}_label"
    assert refs[0]["type_label"] is None  # Should be None when no highest priority type


@patch('heritrace.routes.linked_resources.get_display_rules')
def test_is_proxy_entity_missing_displayproperties(mock_get_display_rules):
    """Test _is_proxy_entity when displayProperties key is missing."""
    mock_get_display_rules.return_value = [
        {
            # Missing displayProperties key
        }
    ]
    result, predicate = _is_proxy_entity(["http://example.org/SomeType"])
    assert not result
    assert predicate == ""

@patch('heritrace.routes.linked_resources.get_display_rules')
def test_is_proxy_entity_missing_display_rules_in_property(mock_get_display_rules):
    """Test _is_proxy_entity when displayRules key is missing in property."""
    mock_get_display_rules.return_value = [
        {
            "displayProperties": [
                {
                    "property": "http://example.org/predicate1"
                    # Missing displayRules key
                }
            ]
        }
    ]
    result, predicate = _is_proxy_entity(["http://example.org/SomeType"])
    assert not result
    assert predicate == ""
