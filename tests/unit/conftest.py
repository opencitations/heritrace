# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import pytest
from collections.abc import Generator

from flask import Flask
from flask.testing import FlaskClient
from heritrace import create_app
from tests.test_config import TestConfig


@pytest.fixture(scope="session")
def _shared_app() -> Flask:
    return create_app(TestConfig)


@pytest.fixture
def app(_shared_app: Flask) -> Generator[Flask, None, None]:
    config = dict(_shared_app.config)
    exts = dict(_shared_app.extensions)
    login_mgr = getattr(_shared_app, 'login_manager', None)
    before_fns = {k: list(v) for k, v in _shared_app.before_request_funcs.items()}
    teardown_fns = list(_shared_app.teardown_appcontext_funcs)

    with _shared_app.app_context():
        yield _shared_app

    _shared_app.config.clear()
    _shared_app.config.update(config)
    _shared_app.extensions.clear()
    _shared_app.extensions.update(exts)
    if login_mgr is not None:
        setattr(_shared_app, 'login_manager', login_mgr)
    _shared_app.before_request_funcs.clear()
    _shared_app.before_request_funcs.update(before_fns)
    _shared_app.teardown_appcontext_funcs[:] = teardown_fns
    _shared_app._got_first_request = False


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()


@pytest.fixture
def logged_in_client(client: FlaskClient):
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
