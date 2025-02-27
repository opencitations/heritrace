"""
Tests for the application initialization and basic functionality.
"""

from flask import Flask


def test_app_creation(app: Flask) -> None:
    """Test that the app is created correctly."""
    assert app is not None
    assert isinstance(app, Flask)
    assert app.config["TESTING"] is True


def test_app_config(app: Flask) -> None:
    """Test that the app has the correct configuration."""
    # Check that essential configurations are set
    assert "SECRET_KEY" in app.config
    assert app.config["WTF_CSRF_ENABLED"] is False  # Disabled for testing

    # Check application title and subtitle
    assert "APP_TITLE" in app.config
    assert "APP_SUBTITLE" in app.config

    # Check database configurations
    assert "DATASET_DB_URL" in app.config
    assert "PROVENANCE_DB_URL" in app.config
    assert "DATASET_DB_TRIPLESTORE" in app.config
    assert "PROVENANCE_DB_TRIPLESTORE" in app.config

    # Check ORCID configurations
    assert "ORCID_CLIENT_ID" in app.config
    assert "ORCID_CLIENT_SECRET" in app.config
    assert "ORCID_AUTHORIZE_URL" in app.config
    assert "ORCID_TOKEN_URL" in app.config

    # Check languages configuration
    assert "LANGUAGES" in app.config
    assert isinstance(app.config["LANGUAGES"], list)


def test_app_routes(app: Flask) -> None:
    """Test that the app has the expected routes registered."""
    # Get all registered routes
    routes = [rule.endpoint for rule in app.url_map.iter_rules()]

    # Check that essential routes are registered
    assert "static" in routes  # Flask's static route should always be there

    # Check main blueprint routes
    assert "main.index" in routes
    assert "main.catalogue" in routes
    assert "main.time_vault" in routes
    assert "main.sparql_proxy" in routes
    assert "main.endpoint" in routes
    assert "main.search" in routes

    # Check entity blueprint routes
    assert "entity.about" in routes
    assert "entity.create_entity" in routes
    assert "entity.entity_history" in routes
    assert "entity.entity_version" in routes
    assert "entity.restore_version" in routes

    # Check auth blueprint routes
    assert "auth.login" in routes
    assert "auth.callback" in routes
    assert "auth.logout" in routes

    # Check API blueprint routes
    assert "api.catalogue_api" in routes
    assert "api.get_deleted_entities_api" in routes
    assert "api.check_lock" in routes
    assert "api.acquire_lock" in routes
    assert "api.release_lock" in routes
    assert "api.renew_lock" in routes
    assert "api.validate_literal" in routes
    assert "api.check_orphans" in routes
    assert "api.apply_changes" in routes
    assert "api.get_human_readable_entity" in routes
