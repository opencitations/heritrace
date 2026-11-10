# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import os
import signal

from flask import Config, request

from heritrace.apis.orcid import normalize_orcid
from heritrace.configuration.components import build_components
from heritrace.configuration.settings import Settings, StoredSettings
from heritrace.configuration.validation import validate_settings
from heritrace.utils.strategies import CompositeHandlingStrategy, OrphanHandlingStrategy


class SetupRequiredError(Exception):
    pass


def load_settings(stored: StoredSettings | None) -> StoredSettings:
    if stored is None:
        msg = "The configuration has no system settings"
        raise SetupRequiredError(msg)
    issues = validate_settings(stored.settings)
    if issues:
        msg = "; ".join(f"{issue.location}: {issue.message}" for issue in issues)
        raise SetupRequiredError(msg)
    return stored


def apply_settings(config: Config, settings: Settings) -> None:
    config.update(
        APP_TITLE=settings.app_title,
        APP_SUBTITLE=settings.app_subtitle,
        COUNT_LIMIT=settings.count_limit,
        CATALOGUE_DEFAULT_PER_PAGE=settings.catalogue_default_per_page,
        DATASET_GENERATION_TIME=settings.dataset_generation_time,
        PRIMARY_SOURCE=settings.primary_source,
        ORCID_SAFELIST=settings.orcid_safelist,
        ORPHAN_HANDLING_STRATEGY=OrphanHandlingStrategy[settings.orphan_handling],
        COMPOSITE_HANDLING_STRATEGY=CompositeHandlingStrategy[
            settings.composite_handling
        ],
    )


def install_components(config: Config, redis_url: str) -> None:
    components = build_components(config, redis_url)
    config.update(
        URI_GENERATOR=components.uri_generator,
        COUNTER_HANDLER=components.counter_handler,
        SAVE_PLUGIN=components.save_plugin,
    )


def is_admin(config: Config, orcid: str) -> bool:
    return normalize_orcid(orcid) in {
        normalize_orcid(admin) for admin in config["ADMIN_ORCIDS"]
    }


def request_reload() -> bool:
    server = request.environ.get("SERVER_SOFTWARE")
    if not isinstance(server, str) or not server.startswith("gunicorn"):
        return False
    os.kill(os.getppid(), signal.SIGHUP)
    return True
