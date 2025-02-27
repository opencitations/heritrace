"""
Tests for the routes.
"""

from flask import Flask
from flask.testing import FlaskClient


def test_main_routes_exist(app: Flask) -> None:
    """Test that the main routes exist."""
    # Get all registered routes
    routes = [rule.endpoint for rule in app.url_map.iter_rules()]

    # Check for main routes
    expected_routes = [
        "static",  # Flask's static route
        "main.index",
        "main.catalogue",
        "main.time_vault",
        "main.sparql_proxy",
        "main.endpoint",
        "main.search",
    ]

    for route in expected_routes:
        assert route in routes


def test_auth_routes_exist(app: Flask) -> None:
    """Test that the authentication routes exist."""
    # Get all registered routes
    routes = [rule.endpoint for rule in app.url_map.iter_rules()]

    # Check for auth routes
    expected_routes = ["auth.login", "auth.callback", "auth.logout"]

    for route in expected_routes:
        assert route in routes


def test_api_routes_exist(app: Flask) -> None:
    """Test that the API routes exist."""
    # Get all registered routes
    routes = [rule.endpoint for rule in app.url_map.iter_rules()]

    # Check for API routes
    expected_routes = [
        "api.catalogue_api",
        "api.get_deleted_entities_api",
        "api.check_lock",
        "api.acquire_lock",
        "api.release_lock",
        "api.renew_lock",
        "api.validate_literal",
        "api.check_orphans",
        "api.apply_changes",
        "api.get_human_readable_entity",
    ]

    for route in expected_routes:
        assert route in routes


def test_entity_routes_exist(app: Flask) -> None:
    """Test that the entity routes exist."""
    # Get all registered routes
    routes = [rule.endpoint for rule in app.url_map.iter_rules()]

    # Check for entity routes
    expected_routes = [
        "entity.about",
        "entity.create_entity",
        "entity.entity_history",
        "entity.entity_version",
        "entity.restore_version",
    ]

    for route in expected_routes:
        assert route in routes


def test_home_page(client: FlaskClient) -> None:
    """Test that the home page returns a 200 status code."""
    response = client.get("/")  # Assuming the index route is at the root path
    assert response.status_code == 200


def test_login_page(client: FlaskClient) -> None:
    """Test that the login page returns a redirect status code when not authenticated."""
    response = client.get("/auth/login")  # Assuming the login route is at /auth/login
    assert (
        response.status_code == 302
    )  # Expecting a redirect to authentication provider


def test_api_endpoint(client: FlaskClient) -> None:
    """Test that an API endpoint returns a redirect when not authenticated."""
    response = client.get(
        "/api/catalogue"
    )  # Assuming the catalogue API is at /api/catalogue
    assert response.status_code == 302  # Expecting a redirect to login page
    # We can't check response.json since it's a redirect
