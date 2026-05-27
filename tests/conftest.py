# SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import subprocess
from pathlib import Path
from typing import Generator

import pytest
from flask import Flask
from flask.testing import FlaskClient, FlaskCliRunner
from redis import Redis
from tests.test_config import TestConfig

COMPOSE_FILE = str(Path(__file__).parent / "docker-compose.yml")

VIRTUOSO_GRANTS = (
    "GRANT SPARQL_UPDATE TO \"SPARQL\"; "
    "GRANT execute ON \"DB.DBA.SPARQL_INSERT_DICT_CONTENT\" TO \"SPARQL\"; "
    "GRANT execute ON \"DB.DBA.SPARQL_DELETE_DICT_CONTENT\" TO \"SPARQL\"; "
    "DB.DBA.RDF_DEFAULT_USER_PERMS_SET ('nobody', 7);"
)


def _grant_virtuoso_permissions(container: str) -> None:
    subprocess.run(
        [
            "docker", "exec", container,
            "/opt/virtuoso-opensource/bin/isql", "-U", "dba", "-P", "dba",
            f"exec={VIRTUOSO_GRANTS}",
        ],
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="session", autouse=True)
def docker_services() -> Generator[None, None, None]:
    subprocess.run(
        ["docker", "compose", "-f", COMPOSE_FILE, "up", "-d", "--wait"],
        check=True,
    )
    _grant_virtuoso_permissions("tests-dataset-db-1")
    _grant_virtuoso_permissions("tests-provenance-db-1")
    yield
    subprocess.run(
        ["docker", "compose", "-f", COMPOSE_FILE, "down"],
        check=True,
    )


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()


@pytest.fixture
def runner(app: Flask) -> FlaskCliRunner:
    return app.test_cli_runner()


@pytest.fixture
def redis_client() -> Generator[Redis, None, None]:
    client = Redis.from_url(TestConfig.REDIS_URL)
    client.flushdb()
    yield client
    client.flushdb()


@pytest.fixture
def logged_in_client(client: FlaskClient) -> Generator[FlaskClient, None, None]:
    with client.session_transaction() as sess:
        sess["user_id"] = "0000-0000-0000-0000"
        sess["user_name"] = "Test User"
        sess["is_authenticated"] = True
        sess["lang"] = "en"
        sess["orcid"] = "0000-0000-0000-0000"
        sess["_fresh"] = True
        sess["_id"] = "test-session-id"
        sess["_user_id"] = "0000-0000-0000-0000"
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
