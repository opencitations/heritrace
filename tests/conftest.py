"""
Configuration file for pytest.
This file contains fixtures and configuration for the test suite.
"""

from typing import Generator

import pytest
from flask import Flask
from flask.testing import FlaskClient, FlaskCliRunner
from heritrace import create_app
from redis import Redis
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


@pytest.fixture
def redis_client() -> Generator[Redis, None, None]:
    """Create a Redis client for testing.

    This connects to the Redis instance running on port 6380 (database 1)
    which is started by the test database scripts.
    """
    client = Redis.from_url(TestConfig.REDIS_URL)

    # Clear any existing test data
    client.flushdb()

    yield client

    # Clean up after tests
    client.flushdb()


@pytest.fixture
def logged_in_client(client: FlaskClient) -> Generator[FlaskClient, None, None]:
    """Create a client with a logged-in user session."""
    with client.session_transaction() as sess:
        sess["user_id"] = "0000-0000-0000-0000"
        sess["user_name"] = "Test User"
        sess["is_authenticated"] = True
        sess["lang"] = "en"
        sess["orcid"] = "0000-0000-0000-0000"
        sess["_fresh"] = True
        sess["_id"] = "test-session-id"
        sess["_user_id"] = "0000-0000-0000-0000"

        # Add OAuth token information if needed
        sess["oauth_token"] = {
            "access_token": "test-access-token",
            "token_type": "bearer",
            "refresh_token": "test-refresh-token",
            "expires_in": 3600,
            "scope": ["openid", "/read-limited"],
            "name": "Test User",
            "orcid": "0000-0000-0000-0000",
        }

    yield client
