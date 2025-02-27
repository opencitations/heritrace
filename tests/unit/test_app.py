"""
Tests for the application initialization and basic functionality.
"""

import pytest
from flask import Flask


def test_app_creation(app):
    """Test that the app is created correctly."""
    assert app is not None
    assert isinstance(app, Flask)
    assert app.config["TESTING"] is True


def test_app_config(app):
    """Test that the app has the correct configuration."""
    # Check that essential configurations are set
    assert "SECRET_KEY" in app.config
    assert app.config["WTF_CSRF_ENABLED"] is False  # Disabled for testing


def test_app_routes(app):
    """Test that the app has the expected routes registered."""
    # Get all registered routes
    routes = [rule.endpoint for rule in app.url_map.iter_rules()]

    # Check that essential routes are registered
    # Adjust these based on your actual route names
    assert "static" in routes  # Flask's static route should always be there

    # Add assertions for your specific routes
    # For example:
    # assert 'main.index' in routes
    # assert 'auth.login' in routes
    # assert 'api.get_entities' in routes
