"""
Configuration file for pytest.
This file contains fixtures and configuration for the test suite.
"""

from typing import Generator

import pytest
from flask import Flask
from flask.testing import FlaskClient, FlaskCliRunner
from heritrace import create_app
from tests.test_config import TestConfig


@pytest.fixture
def app() -> Generator[Flask, None, None]:
    """Create and configure a Flask application for testing."""
    app = create_app(TestConfig)

    # Create application context
    with app.app_context():
        yield app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app: Flask) -> FlaskCliRunner:
    """A test CLI runner for the app."""
    return app.test_cli_runner()
