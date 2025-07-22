import os

from heritrace.utils.strategies import OrphanHandlingStrategy, ProxyHandlingStrategy

BASE_HERITRACE_DIR = os.path.abspath(os.path.dirname(__file__))

def _load_class(class_path: str):
    """Dynamically load a class from a module path."""
    module_path, class_name = class_path.rsplit('.', 1)
    module = __import__(module_path, fromlist=[class_name])
    return getattr(module, class_name)

counter_handler_class_path = os.environ.get('COUNTER_HANDLER_CLASS', 'default_components.meta_counter_handler.MetaCounterHandler')
uri_generator_class_path = os.environ.get('URI_GENERATOR_CLASS', 'default_components.meta_uri_generator.MetaURIGenerator')

counter_handler_class = _load_class(counter_handler_class_path)
uri_generator_class = _load_class(uri_generator_class_path)

counter_handler = counter_handler_class()
meta_uri_generator = uri_generator_class(counter_handler)

shacl_path = os.path.join(BASE_HERITRACE_DIR, "shacl.ttl")
display_rules_path = os.path.join(BASE_HERITRACE_DIR, "display_rules.yaml")


class Config(object):
    APP_TITLE = os.environ.get("APP_TITLE", "HERITRACE")
    APP_SUBTITLE = os.environ.get("APP_SUBTITLE", "Heritage Enhanced Repository Interface")

    SECRET_KEY = os.environ.get("SECRET_KEY", "generate-a-secure-random-key")

    CACHE_VALIDITY_DAYS = int(os.environ.get("CACHE_VALIDITY_DAYS", "7"))

    # Database configuration
    DATASET_DB_TRIPLESTORE = os.environ.get("DATASET_DB_TRIPLESTORE", "virtuoso")  # Options: 'virtuoso' or 'blazegraph'
    DATASET_DB_TEXT_INDEX_ENABLED = os.environ.get("DATASET_DB_TEXT_INDEX_ENABLED", "true").lower() == "true"
    PROVENANCE_DB_TRIPLESTORE = os.environ.get("PROVENANCE_DB_TRIPLESTORE", "virtuoso")

    # Database endpoints
    DATASET_DB_URL = os.environ.get("DATASET_DB_URL", "http://localhost:8999/sparql")
    PROVENANCE_DB_URL = os.environ.get("PROVENANCE_DB_URL", "http://localhost:8998/sparql")

    # Database store types
    DATASET_IS_QUADSTORE = os.environ.get("DATASET_IS_QUADSTORE", "true").lower() == "true"
    PROVENANCE_IS_QUADSTORE = os.environ.get("PROVENANCE_IS_QUADSTORE", "true").lower() == "true"

    DATASET_GENERATION_TIME = os.environ.get("DATASET_GENERATION_TIME", "2024-12-25T00:00:00+00:00")
    URI_GENERATOR = meta_uri_generator
    COUNTER_HANDLER = counter_handler

    # Internationalization
    LANGUAGES = ["en", "it"]
    BABEL_TRANSLATION_DIRECTORIES = os.path.join(
        BASE_HERITRACE_DIR, "babel", "translations"
    )

    CHANGE_TRACKING_CONFIG = os.path.join(BASE_HERITRACE_DIR, "change_tracking.json")
    PRIMARY_SOURCE = os.environ.get("PRIMARY_SOURCE", "https://doi.org/your-doi")
    SHACL_PATH = shacl_path
    DISPLAY_RULES_PATH = display_rules_path

    # ORCID Integration
    # Get these values from https://orcid.org/developer-tools
    ORCID_CLIENT_ID = os.environ.get("ORCID_CLIENT_ID", "your-client-id")
    ORCID_CLIENT_SECRET = os.environ.get("ORCID_CLIENT_SECRET", "your-client-secret")
    ORCID_AUTHORIZE_URL = os.environ.get("ORCID_AUTHORIZE_URL", "https://orcid.org/oauth/authorize")
    ORCID_TOKEN_URL = os.environ.get("ORCID_TOKEN_URL", "https://orcid.org/oauth/token")
    ORCID_API_URL = os.environ.get("ORCID_API_URL", "https://pub.orcid.org/v2.1")
    ORCID_SCOPE = os.environ.get("ORCID_SCOPE", "/authenticate")
    
    # Parse ORCID whitelist from environment (comma-separated)
    _orcid_whitelist_str = os.environ.get("ORCID_WHITELIST", "your-allowed-orcid-1,your-allowed-orcid-2")
    ORCID_WHITELIST = [orcid.strip() for orcid in _orcid_whitelist_str.split(",") if orcid.strip()]

    # Entity handling configuration - strategies can be configured via environment variables
    # Available options: ASK, DELETE, KEEP
    _orphan_strategy_str = os.environ.get("ORPHAN_HANDLING_STRATEGY", "ASK").upper()
    ORPHAN_HANDLING_STRATEGY = getattr(OrphanHandlingStrategy, _orphan_strategy_str, OrphanHandlingStrategy.ASK)
    
    _proxy_strategy_str = os.environ.get("PROXY_HANDLING_STRATEGY", "DELETE").upper()
    PROXY_HANDLING_STRATEGY = getattr(ProxyHandlingStrategy, _proxy_strategy_str, ProxyHandlingStrategy.DELETE)
