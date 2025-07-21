import os

from heritrace.meta_counter_handler import MetaCounterHandler
from heritrace.uri_generator import DefaultURIGenerator, MetaURIGenerator
from heritrace.utils.strategies import OrphanHandlingStrategy, ProxyHandlingStrategy

# Base directory for the application
BASE_HERITRACE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Redis configuration for testing - using Docker container name
REDIS_TEST_HOST = 'localhost'  # Use container name in Docker network
REDIS_TEST_PORT = 6379  # Same port as production for tests
REDIS_TEST_DB = 1      # Different database number for tests

# Initialize counter handler for URI generation
counter_handler = MetaCounterHandler(
    host=REDIS_TEST_HOST,
    port=REDIS_TEST_PORT,
    db=REDIS_TEST_DB
)

# URI generators for different types of resources
default_uri_generator = DefaultURIGenerator("https://example.com")
meta_uri_generator = MetaURIGenerator(
    base_iri="https://w3id.org/oc/meta",
    supplier_prefix_regex="test",
    new_supplier_prefix="test",
    counter_handler=counter_handler,
)

# Paths to resource files
shacl_path = os.path.join(BASE_HERITRACE_DIR, "shacl.ttl")
display_rules_path = os.path.join(BASE_HERITRACE_DIR, "display_rules.yaml")


class TestConfig(object):
    # Application display settings
    APP_TITLE = "Test App"
    APP_SUBTITLE = "Test Environment"

    # Testing flag
    TESTING = True

    # Server configuration
    SERVER_NAME = "localhost"
    APPLICATION_ROOT = "/"
    PREFERRED_URL_SCHEME = "http"

    # Security settings
    SECRET_KEY = "test-secret-key"

    # Cache settings
    CACHE_FILE = os.path.join(BASE_HERITRACE_DIR, "tests", "test_cache.json")
    CACHE_VALIDITY_DAYS = 1

    # Database configuration
    DATASET_DB_TRIPLESTORE = "virtuoso"
    DATASET_DB_TEXT_INDEX_ENABLED = True
    PROVENANCE_DB_TRIPLESTORE = "virtuoso"

    # Database endpoints - using different ports for test databases
    DATASET_DB_URL = "http://localhost:9999/sparql"
    PROVENANCE_DB_URL = "http://localhost:9998/sparql"

    # Redis configuration for testing
    REDIS_URL = f"redis://{REDIS_TEST_HOST}:{REDIS_TEST_PORT}/{REDIS_TEST_DB}"

    # Database store types
    DATASET_IS_QUADSTORE = True
    PROVENANCE_IS_QUADSTORE = True

    # Data management settings
    DATASET_GENERATION_TIME = "2024-01-01T00:00:00+00:00"
    URI_GENERATOR = meta_uri_generator
    COUNTER_HANDLER = counter_handler

    # Internationalization
    LANGUAGES = ["en"]
    BABEL_TRANSLATION_DIRECTORIES = os.path.join(
        BASE_HERITRACE_DIR, "babel", "translations"
    )

    # Data model and tracking
    CHANGE_TRACKING_CONFIG = os.path.join(
        BASE_HERITRACE_DIR, "tests", "test_change_tracking.json"
    )
    PRIMARY_SOURCE = "https://doi.org/test-doi"
    SHACL_PATH = shacl_path
    DISPLAY_RULES_PATH = display_rules_path

    # ORCID Integration - using test values
    ORCID_CLIENT_ID = "test-client-id"
    ORCID_CLIENT_SECRET = "test-client-secret"
    ORCID_AUTHORIZE_URL = "https://sandbox.orcid.org/oauth/authorize"
    ORCID_TOKEN_URL = "https://sandbox.orcid.org/oauth/token"
    ORCID_API_URL = "https://pub.sandbox.orcid.org/v2.1"
    ORCID_SCOPE = "/authenticate"
    ORCID_WHITELIST = ["0000-0000-0000-0000"]

    # Entity handling configuration
    ORPHAN_HANDLING_STRATEGY = OrphanHandlingStrategy.DELETE  # Auto-delete in tests
    PROXY_HANDLING_STRATEGY = ProxyHandlingStrategy.DELETE  # Auto-delete in tests

    # Disable CSRF protection in tests
    WTF_CSRF_ENABLED = False
