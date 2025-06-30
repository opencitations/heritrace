import os

from heritrace.meta_counter_handler import MetaCounterHandler
from heritrace.uri_generator import DefaultURIGenerator, MetaURIGenerator
from heritrace.utils.strategies import OrphanHandlingStrategy, ProxyHandlingStrategy

# Base directory for the application
BASE_HERITRACE_DIR = os.path.abspath(os.path.dirname(__file__))

# Redis configuration - will be resolved at runtime
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))
REDIS_DB = int(os.environ.get('REDIS_DB', '0'))

# Initialize counter handler for URI generation - using environment variables
counter_handler = MetaCounterHandler(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB
)

# URI generators for different types of resources
default_uri_generator = DefaultURIGenerator("https://example.com")
meta_uri_generator = MetaURIGenerator(
    "https://w3id.org/oc/meta", "prefix", counter_handler
)

# Paths to resource files
shacl_path = os.path.join(BASE_HERITRACE_DIR, "resources", "shacl.ttl")
display_rules_path = os.path.join(BASE_HERITRACE_DIR, "resources", "display_rules.yaml")


class Config(object):
    # Application display settings
    APP_TITLE = "Your App Title"
    APP_SUBTITLE = "Your App Subtitle"

    # Security settings
    SECRET_KEY = "generate-a-secure-random-key"  # CHANGE THIS IN PRODUCTION!

    # Cache settings
    CACHE_FILE = "cache.json"
    CACHE_VALIDITY_DAYS = 7

    # Database configuration
    DATASET_DB_TRIPLESTORE = "virtuoso"  # Options: 'virtuoso' or 'blazegraph'
    DATASET_DB_TEXT_INDEX_ENABLED = True
    PROVENANCE_DB_TRIPLESTORE = "virtuoso"

    # Database endpoints
    DATASET_DB_URL = "http://localhost:8999/sparql"
    PROVENANCE_DB_URL = "http://localhost:8998/sparql"

    # Redis configuration
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

    # Database store types
    DATASET_IS_QUADSTORE = True
    PROVENANCE_IS_QUADSTORE = True

    # Data management settings
    DATASET_GENERATION_TIME = "2024-01-01T00:00:00+00:00"
    URI_GENERATOR = meta_uri_generator
    COUNTER_HANDLER = counter_handler

    # Internationalization
    LANGUAGES = ["en", "it"]
    BABEL_TRANSLATION_DIRECTORIES = os.path.join(
        BASE_HERITRACE_DIR, "babel", "translations"
    )

    # Data model and tracking
    CHANGE_TRACKING_CONFIG = os.path.join(BASE_HERITRACE_DIR, "change_tracking.json")
    PRIMARY_SOURCE = "https://doi.org/your-doi"
    SHACL_PATH = shacl_path
    DISPLAY_RULES_PATH = display_rules_path

    # ORCID Integration
    # Get these values from https://orcid.org/developer-tools
    ORCID_CLIENT_ID = "your-client-id"
    ORCID_CLIENT_SECRET = "your-client-secret"
    ORCID_AUTHORIZE_URL = "https://orcid.org/oauth/authorize"
    ORCID_TOKEN_URL = "https://orcid.org/oauth/token"
    ORCID_API_URL = "https://pub.orcid.org/v2.1"
    ORCID_SCOPE = "/authenticate"
    ORCID_WHITELIST = ["your-allowed-orcid-1", "your-allowed-orcid-2"]

    # Entity handling configuration
    ORPHAN_HANDLING_STRATEGY = OrphanHandlingStrategy.ASK
    PROXY_HANDLING_STRATEGY = ProxyHandlingStrategy.DELETE
