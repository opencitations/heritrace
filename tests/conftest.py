"""
Configuration file for pytest.
This file contains fixtures and configuration for the test suite.
"""

import os
import pytest
from flask import Flask
from tests.test_config import TestConfig
from heritrace import create_app


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
