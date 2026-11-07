# SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import os
from pathlib import Path
from typing import ClassVar

from heritrace.configuration.components import component_options
from heritrace.configuration.store import DISPLAY_RULES_FILE

_BASE_DIR = Path(__file__).resolve().parent

if "GUNICORN_WORKERS" in os.environ:
    _gunicorn_workers = int(os.environ["GUNICORN_WORKERS"])
else:
    _cpu_count = os.cpu_count()
    if _cpu_count is None:
        msg = "Cannot determine the default GUNICORN_WORKERS value"
        raise RuntimeError(msg)
    _gunicorn_workers = _cpu_count * 2 + 1


class Config:
    SECRET_KEY = os.environ["SECRET_KEY"]
    SESSION_COOKIE_SAMESITE = "Lax"
    FRONTEND_BUILD_DIR = _BASE_DIR / "frontend" / "build" / "web"
    FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "")

    # If REDIS_URL is not set, the application uses an internal Redis instance
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    GUNICORN_WORKERS = _gunicorn_workers

    CONFIG_DIR = _BASE_DIR / os.environ["CONFIG_DIR"]
    DISPLAY_RULES_PATH = CONFIG_DIR / DISPLAY_RULES_FILE
    ADMIN_ORCIDS: ClassVar[list[str]] = [
        orcid.strip()
        for orcid in os.environ["ADMIN_ORCIDS"].split(",")
        if orcid.strip()
    ]

    DATASET_DB_TRIPLESTORE = os.environ["DATASET_DB_TRIPLESTORE"]
    PROVENANCE_DB_TRIPLESTORE = os.environ["PROVENANCE_DB_TRIPLESTORE"]

    DATASET_DB_URL = os.environ["DATASET_DB_URL"]
    PROVENANCE_DB_URL = os.environ["PROVENANCE_DB_URL"]

    DATASET_IS_QUADSTORE = os.environ["DATASET_IS_QUADSTORE"].lower() == "true"
    DATASET_DB_TEXT_INDEX_ENABLED = (
        os.environ["DATASET_DB_TEXT_INDEX_ENABLED"].lower() == "true"
    )
    PROVENANCE_IS_QUADSTORE = os.environ["PROVENANCE_IS_QUADSTORE"].lower() == "true"

    BASE_IRI = os.environ.get("BASE_IRI")
    URI_GENERATOR_CLASS = os.environ.get("URI_GENERATOR_CLASS")
    URI_GENERATOR_OPTIONS = component_options("URI_GENERATOR_OPTIONS")
    COUNTER_HANDLER_CLASS = os.environ.get("COUNTER_HANDLER_CLASS")
    COUNTER_HANDLER_OPTIONS = component_options("COUNTER_HANDLER_OPTIONS")
    SAVE_PLUGIN_CLASS = os.environ.get("SAVE_PLUGIN_CLASS")
    SAVE_PLUGIN_OPTIONS = component_options("SAVE_PLUGIN_OPTIONS")

    ORCID_CLIENT_ID = os.environ["ORCID_CLIENT_ID"]
    ORCID_CLIENT_SECRET = os.environ["ORCID_CLIENT_SECRET"]
