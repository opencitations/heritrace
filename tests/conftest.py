"""
Configuration file for pytest.
This file contains fixtures and configuration for the test suite.
"""

import os
import pytest
from flask import Flask
from config import Config
from heritrace import create_app


class TestConfig(Config):
    """Test configuration that overrides production settings."""

    TESTING = True
    # Use in-memory SQLite for testing if you have a database
    # SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    # Disable CSRF protection in tests
    WTF_CSRF_ENABLED = False
    # Use a test Redis instance or mock it
    # REDIS_URL = "redis://localhost:6379/1"
    # Add other test-specific configuration here


@pytest.fixture
def app():
    """Create and configure a Flask application for testing."""
    app = create_app(TestConfig)

    # Create application context
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()
