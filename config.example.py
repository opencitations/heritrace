# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import os

from heritrace.utils.strategies import OrphanHandlingStrategy, ProxyHandlingStrategy

BASE_HERITRACE_DIR = os.path.abspath(os.path.dirname(__file__))


def _load_class(class_path):
    module_path, class_name = class_path.rsplit(".", 1)
    module = __import__(module_path, fromlist=[class_name])
    return getattr(module, class_name)


counter_handler_class = _load_class(os.environ["COUNTER_HANDLER_CLASS"])
uri_generator_class = _load_class(os.environ["URI_GENERATOR_CLASS"])
counter_handler = counter_handler_class()
uri_generator = uri_generator_class(counter_handler)


class Config:
    APP_TITLE = os.environ["APP_TITLE"]
    APP_SUBTITLE = os.environ["APP_SUBTITLE"]
    SECRET_KEY = os.environ["SECRET_KEY"]
    CACHE_VALIDITY_DAYS = int(os.environ["CACHE_VALIDITY_DAYS"])

    # If REDIS_URL is not set, the application uses an internal Redis instance
    REDIS_URL = os.environ.get("REDIS_URL")

    # COUNT_LIMIT serves dual purpose:
    # 1. Maximum entity count to display (shows "10000+" if exceeded)
    # 2. Threshold for automatic cache refresh after entity modifications
    #    - Datasets below this limit: auto-refresh enabled (always accurate counts)
    #    - Datasets above this limit: cache remains static (manual refresh via admin endpoint)
    COUNT_LIMIT = int(os.environ["COUNT_LIMIT"])

    # Options: 'virtuoso' or 'blazegraph'
    DATASET_DB_TRIPLESTORE = os.environ["DATASET_DB_TRIPLESTORE"]
    DATASET_DB_TEXT_INDEX_ENABLED = os.environ["DATASET_DB_TEXT_INDEX_ENABLED"].lower() == "true"
    PROVENANCE_DB_TRIPLESTORE = os.environ["PROVENANCE_DB_TRIPLESTORE"]

    DATASET_DB_URL = os.environ["DATASET_DB_URL"]
    PROVENANCE_DB_URL = os.environ["PROVENANCE_DB_URL"]

    DATASET_IS_QUADSTORE = os.environ["DATASET_IS_QUADSTORE"].lower() == "true"
    PROVENANCE_IS_QUADSTORE = os.environ["PROVENANCE_IS_QUADSTORE"].lower() == "true"

    DATASET_GENERATION_TIME = os.environ["DATASET_GENERATION_TIME"]
    URI_GENERATOR = uri_generator
    COUNTER_HANDLER = counter_handler

    LANGUAGES = ["en", "it"]
    BABEL_TRANSLATION_DIRECTORIES = os.path.join(BASE_HERITRACE_DIR, "babel", "translations")
    CHANGE_TRACKING_CONFIG = os.path.join(BASE_HERITRACE_DIR, "change_tracking.json")
    PRIMARY_SOURCE = os.environ["PRIMARY_SOURCE"]
    SHACL_PATH = os.path.join(BASE_HERITRACE_DIR, "shacl.ttl")
    DISPLAY_RULES_PATH = os.path.join(BASE_HERITRACE_DIR, "display_rules.yaml")

    ORCID_CLIENT_ID = os.environ["ORCID_CLIENT_ID"]
    ORCID_CLIENT_SECRET = os.environ["ORCID_CLIENT_SECRET"]
    ORCID_SAFELIST = [s.strip() for s in os.environ["ORCID_SAFELIST"].split(",")]

    # Available options: ASK, DELETE, KEEP
    ORPHAN_HANDLING_STRATEGY = getattr(OrphanHandlingStrategy, os.environ["ORPHAN_HANDLING_STRATEGY"].upper())
    PROXY_HANDLING_STRATEGY = getattr(ProxyHandlingStrategy, os.environ["PROXY_HANDLING_STRATEGY"].upper())

    CATALOGUE_DEFAULT_PER_PAGE = int(os.environ["CATALOGUE_DEFAULT_PER_PAGE"])
    CATALOGUE_ALLOWED_PER_PAGE = [int(x) for x in os.environ["CATALOGUE_ALLOWED_PER_PAGE"].split(",")]
