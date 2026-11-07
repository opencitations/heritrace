# SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import tempfile
from pathlib import Path
from typing import ClassVar

from default_components.meta_counter_handler import MetaCounterHandler

BASE_DIR = Path(__file__).parent.parent.resolve()

test_counter_handler = MetaCounterHandler(port=17804)

# The tests seed a copy, so the tests that save the configuration leave the
# sources untouched.
test_example_dir = BASE_DIR / "tests"
test_config_dir = Path(tempfile.gettempdir()) / "heritrace-config"
test_frontend_build_dir = BASE_DIR / "tests" / "frontend_build"


class TestConfig:
    """Configuration for testing."""

    SECRET_KEY = "test-secret-key-for-testing-only"
    SESSION_COOKIE_SAMESITE = "Lax"
    FRONTEND_BUILD_DIR = test_frontend_build_dir
    FRONTEND_ORIGIN = ""
    SERVER_NAME = "localhost:5000"
    APPLICATION_ROOT = "/"
    PREFERRED_URL_SCHEME = "http"
    TESTING = True

    REDIS_URL = "redis://localhost:17804/0"
    GUNICORN_WORKERS = 2

    CONFIG_DIR = test_config_dir
    DISPLAY_RULES_PATH = test_config_dir / "display_rules.yaml"
    ADMIN_ORCIDS: ClassVar[list[str]] = ["0000-0000-0000-0000"]

    DATASET_DB_TRIPLESTORE = "virtuoso"
    PROVENANCE_DB_TRIPLESTORE = "virtuoso"

    DATASET_DB_URL = "http://localhost:17800/sparql"
    PROVENANCE_DB_URL = "http://localhost:17802/sparql"

    DATASET_IS_QUADSTORE = True
    DATASET_DB_TEXT_INDEX_ENABLED = True
    PROVENANCE_IS_QUADSTORE = True

    BASE_IRI = None
    URI_GENERATOR_CLASS = "default_components.meta_uri_generator.MetaURIGenerator"
    URI_GENERATOR_OPTIONS: ClassVar[dict[str, object]] = {}
    COUNTER_HANDLER_CLASS = "default_components.meta_counter_handler.MetaCounterHandler"
    COUNTER_HANDLER_OPTIONS: ClassVar[dict[str, object]] = {"port": 17804}
    SAVE_PLUGIN_CLASS = None
    SAVE_PLUGIN_OPTIONS: ClassVar[dict[str, object]] = {}

    ORCID_CLIENT_ID = "test-client-id"
    ORCID_CLIENT_SECRET = "test-client-secret"
