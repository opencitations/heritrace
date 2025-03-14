import os

from heritrace.meta_counter_handler import MetaCounterHandler
from heritrace.uri_generator import MetaURIGenerator
from heritrace.utils.strategies import (OrphanHandlingStrategy,
                                        ProxyHandlingStrategy)

BASE_HERITRACE_DIR = os.path.abspath(os.path.dirname(__file__))

counter_handler = MetaCounterHandler(
    host='localhost',
    port=6379,
    db=0
)

meta_uri_generator = MetaURIGenerator(
    "https://w3id.org/oc/meta", "09110", counter_handler
)

shacl_path = os.path.join(BASE_HERITRACE_DIR, "resources", "shacl.ttl")

display_rules_path = os.path.join(BASE_HERITRACE_DIR, "display_rules.yaml")


class Config(object):
    APP_TITLE = "ParaText"
    APP_SUBTITLE = "Bibliographical database"

    SECRET_KEY = "adoiugwoad7y78agdlauwvdliu"
    CACHE_FILE = "cache.json"
    CACHE_VALIDITY_DAYS = 7

    DATASET_DB_TRIPLESTORE = "virtuoso"  # virtuoso or blazegraph
    DATASET_DB_TEXT_INDEX_ENABLED = True

    PROVENANCE_DB_TRIPLESTORE = "virtuoso"  # virtuoso or blazegraph

    DATASET_DB_URL = "http://localhost:8999/sparql"
    PROVENANCE_DB_URL = "http://localhost:8998/sparql"

    DATASET_IS_QUADSTORE = (
        True  # Set to True if using a quadstore for dataset, False for triplestore
    )
    PROVENANCE_IS_QUADSTORE = (
        True  # Set to True if using a quadstore for provenance, False for triplestore
    )

    DATASET_GENERATION_TIME = "2024-09-16T00:00:00+02:00"
    URI_GENERATOR = meta_uri_generator
    COUNTER_HANDLER = counter_handler
    LANGUAGES = ["en", "it"]
    BABEL_TRANSLATION_DIRECTORIES = os.path.join(
        BASE_HERITRACE_DIR, "babel", "translations"
    )
    CHANGE_TRACKING_CONFIG = os.path.join(BASE_HERITRACE_DIR, "change_tracking.json")
    PRIMARY_SOURCE = "https://doi.org/10.5281/zenodo.13768531"
    SHACL_PATH = shacl_path
    DISPLAY_RULES_PATH = display_rules_path

    ORCID_CLIENT_ID = "APP-92M0BPT8JBZ9YIBZ"
    ORCID_CLIENT_SECRET = "8045b4ea-36ec-4211-9385-dab78cf4e7bd"
    ORCID_AUTHORIZE_URL = "https://orcid.org/oauth/authorize"
    ORCID_TOKEN_URL = "https://orcid.org/oauth/token"
    ORCID_API_URL = "https://pub.orcid.org/v2.1"
    ORCID_SCOPE = "/authenticate"
    ORCID_WHITELIST = [
        "0000-0002-8420-0696",
        "0009-0002-5790-4804",
        "0000-0003-0530-4305",
        "0009-0000-8864-6583",
    ]

    ORPHAN_HANDLING_STRATEGY = OrphanHandlingStrategy.ASK
    PROXY_HANDLING_STRATEGY = ProxyHandlingStrategy.ASK
