# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from pathlib import Path
from typing import ClassVar

from default_components.meta_counter_handler import MetaCounterHandler
from default_components.meta_uri_generator import MetaURIGenerator
from heritrace.utils.strategies import OrphanHandlingStrategy, ProxyHandlingStrategy

BASE_DIR = Path(__file__).parent.parent.resolve()

test_counter_handler = MetaCounterHandler()
test_counter_handler.port = 41804

test_meta_uri_generator = MetaURIGenerator(test_counter_handler)

test_shacl_path = BASE_DIR / "tests" / "shacl.ttl"
test_display_rules_path = BASE_DIR / "tests" / "display_rules.yaml"


class TestConfig:
    """Configuration for testing."""

    APP_TITLE = "ParaText Test"
    APP_SUBTITLE = "Bibliographical database - Test Environment"

    SECRET_KEY = "test-secret-key-for-testing-only"
    WTF_CSRF_ENABLED = False
    SERVER_NAME = "localhost:5000"
    APPLICATION_ROOT = "/"
    PREFERRED_URL_SCHEME = "http"
    CACHE_VALIDITY_DAYS = 1
    TESTING = True

    REDIS_URL = "redis://localhost:41804/0"

    DATASET_DB_TRIPLESTORE = "virtuoso"
    DATASET_DB_TEXT_INDEX_ENABLED = True
    PROVENANCE_DB_TRIPLESTORE = "virtuoso"

    DATASET_DB_URL = "http://localhost:41800/sparql"
    PROVENANCE_DB_URL = "http://localhost:41802/sparql"

    DATASET_IS_QUADSTORE = True
    PROVENANCE_IS_QUADSTORE = True

    DATASET_GENERATION_TIME = "2024-01-01T00:00:00+00:00"
    URI_GENERATOR = test_meta_uri_generator
    COUNTER_HANDLER = test_counter_handler
    PRIMARY_SOURCE = "https://example.com/test-primary-source"
    SHACL_PATH = test_shacl_path
    DISPLAY_RULES_PATH = test_display_rules_path

    ORCID_CLIENT_ID = "test-client-id"
    ORCID_CLIENT_SECRET = "test-client-secret"
    ORCID_SAFELIST: ClassVar[list[str]] = [
        "0000-0000-0000-0000",
    ]

    ORPHAN_HANDLING_STRATEGY = OrphanHandlingStrategy.ASK
    PROXY_HANDLING_STRATEGY = ProxyHandlingStrategy.ASK

    # Catalogue pagination configuration
    CATALOGUE_DEFAULT_PER_PAGE = 50
    CATALOGUE_ALLOWED_PER_PAGE: ClassVar[list[int]] = [50, 100, 200, 500]

    # Query configuration
    COUNT_LIMIT = 10000
    MAX_WORKERS = 1
    GUNICORN_WORKERS = 2
