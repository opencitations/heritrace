from unittest.mock import patch, MagicMock

from heritrace.routes.linked_resources import get_paginated_inverse_references

SAMPLE_SUBJECT_URI = "http://example.org/entity1"
SAMPLE_REFERRING_SUBJECT_1 = "http://example.org/ref1"
SAMPLE_REFERRING_SUBJECT_2 = "http://example.org/ref2"
SAMPLE_REFERRING_SUBJECT_3 = "http://example.org/ref3"
SAMPLE_PREDICATE_1 = "http://example.org/pred1"
SAMPLE_PREDICATE_2 = "http://example.org/pred2"
SAMPLE_TYPE_1 = "http://example.org/TypeA"


def mock_sparql_query_results(results_bindings=None, count_value=0):
    """Helper to mock SPARQLWrapper query results."""
    mock_sparql = MagicMock()
    mock_convert = MagicMock()
    
    count_results = {
        "results": {
            "bindings": [{
                "count": {"value": str(count_value)}
            }]
        }
    }
    
    data_results = {
        "results": {
            "bindings": results_bindings if results_bindings is not None else []
        }
    }
    
    mock_convert.side_effect = [count_results, data_results]
    mock_sparql.query.return_value.convert = mock_convert
    return mock_sparql

@patch('heritrace.routes.linked_resources.get_entity_types')
@patch('heritrace.routes.linked_resources.get_custom_filter')
@patch('heritrace.routes.linked_resources.get_sparql')
@patch('heritrace.routes.linked_resources.is_virtuoso', False)
def test_get_paginated_inverse_references_basic(mock_get_sparql, mock_get_filter, mock_get_types, app):
    """Test basic functionality with results."""
    mock_bindings = [
        {"s": {"value": SAMPLE_REFERRING_SUBJECT_1}, "p": {"value": SAMPLE_PREDICATE_1}},
        {"s": {"value": SAMPLE_REFERRING_SUBJECT_2}, "p": {"value": SAMPLE_PREDICATE_2}},
    ]
    mock_sparql_instance = mock_sparql_query_results(mock_bindings, 2)
    mock_get_sparql.return_value = mock_sparql_instance
    mock_get_filter.return_value.human_readable_entity.side_effect = lambda s, t: f"{s}_label"
    mock_get_filter.return_value.human_readable_predicate.side_effect = lambda p, t: f"{p}_label"
    mock_get_types.return_value = [SAMPLE_TYPE_1]

    with app.app_context():
        refs, total, has_more = get_paginated_inverse_references(SAMPLE_SUBJECT_URI, limit=5, offset=0)

    assert total == 2
    assert not has_more
    assert len(refs) == 2
    assert refs[0]["subject"] == SAMPLE_REFERRING_SUBJECT_1
    assert refs[0]["predicate"] == SAMPLE_PREDICATE_1
    assert refs[0]["label"] == f"{SAMPLE_REFERRING_SUBJECT_1}_label"
    assert refs[0]["predicate_label"] == f"{SAMPLE_PREDICATE_1}_label"
    assert refs[0]["types"] == [SAMPLE_TYPE_1]
    assert refs[1]["subject"] == SAMPLE_REFERRING_SUBJECT_2

@patch('heritrace.routes.linked_resources.get_entity_types')
@patch('heritrace.routes.linked_resources.get_custom_filter')
@patch('heritrace.routes.linked_resources.get_sparql')
@patch('heritrace.routes.linked_resources.is_virtuoso', False)
def test_get_paginated_inverse_references_pagination_has_more(mock_get_sparql, mock_get_filter, mock_get_types, app):
    """Test pagination where more results exist."""
    mock_bindings = [
        {"s": {"value": SAMPLE_REFERRING_SUBJECT_1}, "p": {"value": SAMPLE_PREDICATE_1}},
        {"s": {"value": SAMPLE_REFERRING_SUBJECT_2}, "p": {"value": SAMPLE_PREDICATE_2}},
    ]
    mock_sparql_instance = mock_sparql_query_results(mock_bindings, 3) # Total count is 3
    mock_get_sparql.return_value = mock_sparql_instance
    mock_get_filter.return_value.human_readable_entity.side_effect = lambda s, t: f"{s}_label"
    mock_get_filter.return_value.human_readable_predicate.side_effect = lambda p, t: f"{p}_label"
    mock_get_types.return_value = [SAMPLE_TYPE_1]

    with app.app_context():
        refs, total, has_more = get_paginated_inverse_references(SAMPLE_SUBJECT_URI, limit=2, offset=0) # Limit is 2

    assert total == 3
    assert has_more # Since 0 + 2 < 3
    assert len(refs) == 2

@patch('heritrace.routes.linked_resources.get_entity_types')
@patch('heritrace.routes.linked_resources.get_custom_filter')
@patch('heritrace.routes.linked_resources.get_sparql')
@patch('heritrace.routes.linked_resources.is_virtuoso', False)
def test_get_paginated_inverse_references_pagination_no_more(mock_get_sparql, mock_get_filter, mock_get_types, app):
    """Test pagination where no more results exist."""
    mock_bindings = [
        {"s": {"value": SAMPLE_REFERRING_SUBJECT_3}, "p": {"value": SAMPLE_PREDICATE_1}},
    ]
    mock_sparql_instance = mock_sparql_query_results(mock_bindings, 3) # Total count is 3
    mock_get_sparql.return_value = mock_sparql_instance
    mock_get_filter.return_value.human_readable_entity.side_effect = lambda s, t: f"{s}_label"
    mock_get_filter.return_value.human_readable_predicate.side_effect = lambda p, t: f"{p}_label"
    mock_get_types.return_value = [SAMPLE_TYPE_1]

    with app.app_context():
        refs, total, has_more = get_paginated_inverse_references(SAMPLE_SUBJECT_URI, limit=2, offset=2) # Limit 2, offset 2

    assert total == 3
    assert not has_more # Since 2 + 2 >= 3
    assert len(refs) == 1
    assert refs[0]["subject"] == SAMPLE_REFERRING_SUBJECT_3

@patch('heritrace.routes.linked_resources.get_entity_types')
@patch('heritrace.routes.linked_resources.get_custom_filter')
@patch('heritrace.routes.linked_resources.get_sparql')
@patch('heritrace.routes.linked_resources.is_virtuoso', False)
def test_get_paginated_inverse_references_no_results(mock_get_sparql, mock_get_filter, mock_get_types, app):
    """Test the case with no inverse references."""
    mock_sparql_instance = mock_sparql_query_results([], 0)
    mock_get_sparql.return_value = mock_sparql_instance

    with app.app_context():
        refs, total, has_more = get_paginated_inverse_references(SAMPLE_SUBJECT_URI, limit=5, offset=0)

    assert total == 0
    assert not has_more
    assert len(refs) == 0

@patch('heritrace.routes.linked_resources.get_entity_types')
@patch('heritrace.routes.linked_resources.get_custom_filter')
@patch('heritrace.routes.linked_resources.get_sparql')
@patch('heritrace.routes.linked_resources.is_virtuoso', True) # Test Virtuoso case
def test_get_paginated_inverse_references_virtuoso(mock_get_sparql, mock_get_filter, mock_get_types, app):
    """Test query structure when is_virtuoso is True."""
    mock_sparql_instance = mock_sparql_query_results([], 0)
    mock_get_sparql.return_value = mock_sparql_instance

    with app.app_context():
        get_paginated_inverse_references(SAMPLE_SUBJECT_URI, limit=5, offset=0)

    # Check if queries contained GRAPH ?g { ... }
    call_args_list = mock_sparql_instance.setQuery.call_args_list
    assert len(call_args_list) == 2 # Count query and main query
    assert "GRAPH ?g { ?s ?p ?o . }" in call_args_list[0].args[0] # Count query
    assert "GRAPH ?g { ?s ?p ?o . }" in call_args_list[1].args[0] # Main query
    assert "FILTER(?g NOT IN (" in call_args_list[0].args[0]
    assert "FILTER(?g NOT IN (" in call_args_list[1].args[0]

@patch('heritrace.routes.linked_resources.get_sparql')
def test_get_paginated_inverse_references_exception(mock_get_sparql, app):
    """Test exception handling during SPARQL query."""
    mock_sparql_instance = MagicMock()
    mock_sparql_instance.query.side_effect = Exception("SPARQL Error")
    mock_get_sparql.return_value = mock_sparql_instance

    with app.app_context():
        refs, total, has_more = get_paginated_inverse_references(SAMPLE_SUBJECT_URI, limit=5, offset=0)

    assert total == 0
    assert not has_more
    assert len(refs) == 0

# --- Tests for /api/linked-resources/ endpoint --- 

@patch('heritrace.routes.linked_resources.get_paginated_inverse_references')
def test_get_linked_resources_api_success(mock_get_paginated, logged_in_client):
    """Test successful API call."""
    mock_data = [
        {"subject": SAMPLE_REFERRING_SUBJECT_1, "predicate": SAMPLE_PREDICATE_1, "label": "Ref1", "types": [], "type_labels": [], "predicate_label": "Pred1"},
    ]
    mock_get_paginated.return_value = (mock_data, 1, False)

    response = logged_in_client.get(f'/api/linked-resources/?subject_uri={SAMPLE_SUBJECT_URI}&limit=5&offset=0')

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'success'
    assert json_data['results'] == mock_data
    assert json_data['total_count'] == 1
    assert not json_data['has_more']
    mock_get_paginated.assert_called_once_with(SAMPLE_SUBJECT_URI, 5, 0)

@patch('heritrace.routes.linked_resources.get_paginated_inverse_references')
def test_get_linked_resources_api_success_no_results(mock_get_paginated, logged_in_client):
    """Test successful API call with no results."""
    mock_get_paginated.return_value = ([], 0, False)

    response = logged_in_client.get(f'/api/linked-resources/?subject_uri={SAMPLE_SUBJECT_URI}')

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'success'
    assert json_data['results'] == []
    assert json_data['total_count'] == 0
    assert not json_data['has_more']
    mock_get_paginated.assert_called_once_with(SAMPLE_SUBJECT_URI, 5, 0) # Default limit/offset

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
    # Simulate the function returning default values after catching an error internally
    mock_get_paginated.return_value = ([], 0, False)
    
    response = logged_in_client.get(f'/api/linked-resources/?subject_uri={SAMPLE_SUBJECT_URI}')
    
    # The API should return success with empty data because the function handled the error
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'success' 
    assert json_data['results'] == []
    assert json_data['total_count'] == 0
    assert not json_data['has_more']
    mock_get_paginated.assert_called_once_with(SAMPLE_SUBJECT_URI, 5, 0) # Check it was called with default args 