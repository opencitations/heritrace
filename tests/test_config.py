import os

from default_components.meta_counter_handler import MetaCounterHandler
from default_components.meta_uri_generator import MetaURIGenerator
from heritrace.utils.strategies import (OrphanHandlingStrategy,
                                        ProxyHandlingStrategy)


BASE_HERITRACE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

test_counter_handler = MetaCounterHandler()

test_meta_uri_generator = MetaURIGenerator(test_counter_handler)

test_shacl_path = os.path.join(BASE_HERITRACE_DIR, "shacl.ttl")
test_display_rules_path = os.path.join(BASE_HERITRACE_DIR, "display_rules.yaml")


class TestConfig(object):
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
    
    REDIS_URL = "redis://localhost:6379/0"

    DATASET_DB_TRIPLESTORE = "virtuoso"
    DATASET_DB_TEXT_INDEX_ENABLED = True
    PROVENANCE_DB_TRIPLESTORE = "virtuoso"

    DATASET_DB_URL = "http://localhost:9999/sparql"
    PROVENANCE_DB_URL = "http://localhost:9998/sparql"

    DATASET_IS_QUADSTORE = True
    PROVENANCE_IS_QUADSTORE = True

    DATASET_GENERATION_TIME = "2024-01-01T00:00:00+00:00"
    URI_GENERATOR = test_meta_uri_generator
    COUNTER_HANDLER = test_counter_handler
    LANGUAGES = ["en", "it"]
    BABEL_TRANSLATION_DIRECTORIES = os.path.join(
        BASE_HERITRACE_DIR, "heritrace", "babel", "translations"
    )
    CHANGE_TRACKING_CONFIG = os.path.join(BASE_HERITRACE_DIR, "tests", "test_change_tracking.json")
    PRIMARY_SOURCE = "https://example.com/test-primary-source"
    SHACL_PATH = test_shacl_path
    DISPLAY_RULES_PATH = test_display_rules_path

    ORCID_CLIENT_ID = "test-client-id"
    ORCID_CLIENT_SECRET = "test-client-secret"
    ORCID_AUTHORIZE_URL = "https://orcid.org/oauth/authorize"
    ORCID_TOKEN_URL = "https://orcid.org/oauth/token"
    ORCID_API_URL = "https://pub.orcid.org/v2.1"
    ORCID_SCOPE = "/authenticate"
    ORCID_SAFELIST = [
        "0000-0000-0000-0000",
    ]

    ORPHAN_HANDLING_STRATEGY = OrphanHandlingStrategy.ASK
    PROXY_HANDLING_STRATEGY = ProxyHandlingStrategy.ASK

    # Catalogue pagination configuration
    CATALOGUE_DEFAULT_PER_PAGE = 50
    CATALOGUE_ALLOWED_PER_PAGE = [50, 100, 200, 500]

    # Query configuration
    COUNT_LIMIT = 10000