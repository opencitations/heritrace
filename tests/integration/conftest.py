# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import pytest
from collections.abc import Generator

from flask import Flask
from heritrace import create_app
from tests.test_config import TestConfig


@pytest.fixture(scope="session")
def _shared_app(docker_services) -> Flask:
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
