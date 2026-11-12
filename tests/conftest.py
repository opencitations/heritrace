# SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import shutil
import subprocess
from collections.abc import Generator
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient
from redis import Redis

from heritrace import create_app
from heritrace.scripts.seed_config import seed_config
from tests.test_config import TestConfig, test_example_dir

COMPOSE_FILE = str(Path(__file__).parent / "docker-compose.yml")

VIRTUOSO_GRANTS = (
    'GRANT SPARQL_UPDATE TO "SPARQL"; '
    'GRANT execute ON "DB.DBA.SPARQL_INSERT_DICT_CONTENT" TO "SPARQL"; '
    'GRANT execute ON "DB.DBA.SPARQL_DELETE_DICT_CONTENT" TO "SPARQL"; '
    "DB.DBA.RDF_DEFAULT_USER_PERMS_SET ('nobody', 7);"
)


def run_isql(container: str, statements: str) -> None:
    subprocess.run(
        [
            "docker",
            "exec",
            container,
            "/opt/virtuoso-opensource/bin/isql",
            "-U",
            "dba",
            "-P",
            "dba",
            f"exec={statements}",
        ],
        check=True,
        capture_output=True,
    )


def write_test_configuration() -> None:
    shutil.rmtree(TestConfig.CONFIG_DIR, ignore_errors=True)
    seed_config(TestConfig.CONFIG_DIR, test_example_dir)


@pytest.fixture(scope="session", autouse=True)
def docker_services() -> None:
    subprocess.run(
        ["docker", "compose", "-f", COMPOSE_FILE, "up", "-d", "--wait"],
        check=True,
    )
    run_isql("tests-dataset-db-1", VIRTUOSO_GRANTS)
    run_isql("tests-provenance-db-1", VIRTUOSO_GRANTS)
    write_test_configuration()


@pytest.fixture(scope="session")
def _shared_app(docker_services) -> Flask:
    return create_app(TestConfig)


@pytest.fixture
def app(_shared_app: Flask) -> Generator[Flask, None, None]:
    config = dict(_shared_app.config)
    exts = dict(_shared_app.extensions)
    login_mgr = getattr(_shared_app, "login_manager", None)
    before_fns = {k: list(v) for k, v in _shared_app.before_request_funcs.items()}
    teardown_fns = list(_shared_app.teardown_appcontext_funcs)

    with _shared_app.app_context():
        yield _shared_app

    _shared_app.config.clear()
    _shared_app.config.update(config)
    _shared_app.extensions.clear()
    _shared_app.extensions.update(exts)
    if login_mgr is not None:
        _shared_app.login_manager = login_mgr
    _shared_app.before_request_funcs.clear()
    _shared_app.before_request_funcs.update(before_fns)
    _shared_app.teardown_appcontext_funcs[:] = teardown_fns
    _shared_app._got_first_request = False  # noqa: SLF001


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()


@pytest.fixture
def redis_client() -> Generator[Redis, None, None]:
    client = Redis.from_url(TestConfig.REDIS_URL)
    client.flushdb()
    yield client
    client.flushdb()


@pytest.fixture
def logged_in_client(client: FlaskClient) -> FlaskClient:
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
    return client
