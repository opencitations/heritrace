"""
Tests for the main.py routes.
"""

from unittest.mock import MagicMock, patch

from flask.testing import FlaskClient
from SPARQLWrapper import JSON


def test_index_route(client: FlaskClient) -> None:
    """Test that the index route returns a 200 status code."""
    response = client.get("/")
    assert response.status_code == 200


def test_catalogue_route_unauthenticated(client: FlaskClient) -> None:
    """Test that the catalogue route redirects to login when unauthenticated."""
    response = client.get("/catalogue")
    assert response.status_code == 302  # Redirect to login


@patch("heritrace.routes.main.get_available_classes")
@patch("heritrace.routes.main.get_catalog_data")
def test_catalogue_route_authenticated(
    mock_get_catalog_data: MagicMock,
    mock_get_available_classes: MagicMock,
    logged_in_client: FlaskClient,
) -> None:
    """Test that the catalogue route works when authenticated."""
    # Mock the return values
    mock_get_available_classes.return_value = [
        {"uri": "test_class", "label": "Test Class"}
    ]
    mock_get_catalog_data.return_value = {
        "entities": [],
        "total_pages": 1,
        "sortable_properties": [],
    }

    response = logged_in_client.get("/catalogue")
    assert response.status_code == 200

    # Test with query parameters
    response = logged_in_client.get(
        "/catalogue?page=2&per_page=100&class=test_class&sort_property=name&sort_direction=DESC"
    )
    assert response.status_code == 200
    mock_get_catalog_data.assert_called_with("test_class", 2, 100, "name", "DESC")


def test_time_vault_route_unauthenticated(client: FlaskClient) -> None:
    """Test that the time-vault route redirects to login when unauthenticated."""
    response = client.get("/time-vault")
    assert response.status_code == 302  # Redirect to login


@patch("heritrace.routes.main.get_display_rules")
@patch("heritrace.routes.main.get_form_fields")
@patch("heritrace.routes.main.get_deleted_entities_with_filtering")
@patch("heritrace.routes.main.get_sortable_properties")
def test_time_vault_route_authenticated(
    mock_get_sortable_properties: MagicMock,
    mock_get_deleted_entities: MagicMock,
    mock_get_form_fields: MagicMock,
    mock_get_display_rules: MagicMock,
    logged_in_client: FlaskClient,
) -> None:
    """Test that the time-vault route works when authenticated."""
    # Mock the return values
    mock_get_display_rules.return_value = {}
    mock_get_form_fields.return_value = {}
    mock_get_deleted_entities.return_value = (
        [],  # initial_entities
        [{"uri": "test_class", "label": "Test Class"}],  # available_classes
        "test_class",  # selected_class
        1,  # total_pages
    )
    mock_get_sortable_properties.return_value = []

    response = logged_in_client.get("/time-vault")
    assert response.status_code == 200

    # Test with query parameters
    response = logged_in_client.get(
        "/time-vault?page=2&per_page=100&class=test_class&sort_property=name&sort_direction=DESC"
    )
    assert response.status_code == 200
    mock_get_deleted_entities.assert_called_with(2, 100, "name", "DESC", "test_class")


def test_dataset_endpoint_route_unauthenticated(client: FlaskClient) -> None:
    """Test that the dataset-endpoint route redirects to login when unauthenticated."""
    response = client.post(
        "/dataset-endpoint", data={"query": "SELECT * WHERE {?s ?p ?o}"}
    )
    assert response.status_code == 302  # Redirect to login


@patch("heritrace.routes.main.get_sparql")
def test_dataset_endpoint_route_authenticated(
    mock_get_sparql: MagicMock,
    logged_in_client: FlaskClient,
) -> None:
    """Test that the dataset-endpoint route works when authenticated."""
    # Mock the SPARQLWrapper
    mock_sparql = MagicMock()
    mock_get_sparql.return_value = mock_sparql
    
    # Mock the query result
    mock_query_result = MagicMock()
    mock_query_result.convert.return_value = {"results": {"bindings": []}}
    mock_sparql.query.return_value = mock_query_result

    response = logged_in_client.post(
        "/dataset-endpoint", data={"query": "SELECT * WHERE {?s ?p ?o}"}
    )
    assert response.status_code == 200
    
    # Verify the query was set correctly
    mock_sparql.setQuery.assert_called_with("SELECT * WHERE {?s ?p ?o}")
    mock_sparql.setReturnFormat.assert_called_with(JSON)
    mock_sparql.query.assert_called_once()


def test_endpoint_route_unauthenticated(client: FlaskClient) -> None:
    """Test that the endpoint route redirects to login when unauthenticated."""
    response = client.get("/endpoint")
    assert response.status_code == 302  # Redirect to login


@patch("heritrace.extensions.dataset_endpoint", "http://example.com/sparql")
@patch("heritrace.routes.main.render_template")
def test_endpoint_route_authenticated(
    mock_render_template: MagicMock,
    logged_in_client: FlaskClient,
) -> None:
    """Test that the endpoint route works when authenticated."""
    # Mock the render_template function to return a simple string
    mock_render_template.return_value = "Endpoint page"

    response = logged_in_client.get("/endpoint")
    assert response.status_code == 200

    # Verify render_template was called with the correct arguments
    mock_render_template.assert_called_with(
        "endpoint.jinja", dataset_endpoint="http://example.com/sparql"
    )


def test_search_route_unauthenticated(client: FlaskClient) -> None:
    """Test that the search route redirects to login when unauthenticated."""
    response = client.get("/search?q=test")
    assert response.status_code == 302  # Redirect to login


def test_search_route_authenticated(logged_in_client: FlaskClient) -> None:
    """Test that the search route redirects to the entity page."""
    response = logged_in_client.get("/search?q=test")
    assert response.status_code == 302  # Redirect to entity.about
    assert response.location.endswith("/about/test")
