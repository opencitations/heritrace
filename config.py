# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import os
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlparse

from rdflib_ocdm.counter_handler.redis_counter_handler import RedisCounterHandler

from heritrace.component_options import load_component_options
from heritrace.utils.strategies import OrphanHandlingStrategy, ProxyHandlingStrategy

_BASE_DIR = Path(__file__).resolve().parent

DEFAULT_URI_GENERATOR_CLASS = (
    "heritrace.uri_generator.default_uri_generator.DefaultURIGenerator"
)


def _load_class(class_path: str) -> type:
    module_path, class_name = class_path.rsplit(".", 1)
    module = __import__(module_path, fromlist=[class_name])
    return getattr(module, class_name)


def _default_counter_handler() -> RedisCounterHandler:
    parsed = urlparse(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    handler = RedisCounterHandler(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        db=int(parsed.path.lstrip("/") or 0),
        password=parsed.password,
    )
    handler.connect()
    return handler


uri_generator_class = _load_class(
    os.environ.get("URI_GENERATOR_CLASS", DEFAULT_URI_GENERATOR_CLASS)
)
uri_generator_options = load_component_options("URI_GENERATOR_OPTIONS")
counter_handler_class_path = os.environ.get("COUNTER_HANDLER_CLASS")
counter_handler_options = load_component_options("COUNTER_HANDLER_OPTIONS")
if counter_handler_class_path:
    counter_handler = _load_class(counter_handler_class_path)(**counter_handler_options)
    uri_generator = uri_generator_class(counter_handler, **uri_generator_options)
else:
    if counter_handler_options:
        msg = "COUNTER_HANDLER_OPTIONS requires COUNTER_HANDLER_CLASS"
        raise ValueError(msg)
    counter_handler = _default_counter_handler()
    uri_generator = uri_generator_class(**uri_generator_options)


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
    #    - Datasets above this limit: cache remains static
    #      (manual refresh via admin endpoint)
    COUNT_LIMIT = int(os.environ["COUNT_LIMIT"])

    DATASET_DB_TRIPLESTORE = os.environ["DATASET_DB_TRIPLESTORE"]
    DATASET_DB_TEXT_INDEX_ENABLED = (
        os.environ["DATASET_DB_TEXT_INDEX_ENABLED"].lower() == "true"
    )
    PROVENANCE_DB_TRIPLESTORE = os.environ["PROVENANCE_DB_TRIPLESTORE"]

    DATASET_DB_URL = os.environ["DATASET_DB_URL"]
    PROVENANCE_DB_URL = os.environ["PROVENANCE_DB_URL"]

    DATASET_IS_QUADSTORE = os.environ["DATASET_IS_QUADSTORE"].lower() == "true"
    PROVENANCE_IS_QUADSTORE = os.environ["PROVENANCE_IS_QUADSTORE"].lower() == "true"

    DATASET_GENERATION_TIME = os.environ["DATASET_GENERATION_TIME"]
    BASE_IRI = os.environ.get("BASE_IRI")
    URI_GENERATOR = uri_generator
    COUNTER_HANDLER = counter_handler

    PRIMARY_SOURCE = os.environ["PRIMARY_SOURCE"]
    SHACL_PATH = _BASE_DIR / "shacl.ttl"
    DISPLAY_RULES_PATH = _BASE_DIR / "display_rules.yaml"

    ORCID_CLIENT_ID = os.environ["ORCID_CLIENT_ID"]
    ORCID_CLIENT_SECRET = os.environ["ORCID_CLIENT_SECRET"]
    ORCID_SAFELIST: ClassVar[list[str]] = [
        s.strip() for s in os.environ["ORCID_SAFELIST"].split(",")
    ]

    # Available options: ASK, DELETE, KEEP
    ORPHAN_HANDLING_STRATEGY = getattr(
        OrphanHandlingStrategy, os.environ["ORPHAN_HANDLING_STRATEGY"].upper()
    )
    PROXY_HANDLING_STRATEGY = getattr(
        ProxyHandlingStrategy, os.environ["PROXY_HANDLING_STRATEGY"].upper()
    )

    CATALOGUE_DEFAULT_PER_PAGE = int(os.environ["CATALOGUE_DEFAULT_PER_PAGE"])
    CATALOGUE_ALLOWED_PER_PAGE: ClassVar[list[int]] = [
        int(x) for x in os.environ["CATALOGUE_ALLOWED_PER_PAGE"].split(",")
    ]
