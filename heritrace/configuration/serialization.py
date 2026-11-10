# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from datetime import datetime
from typing import cast

from heritrace.configuration.settings import Settings

JsonObject = dict[str, object]


class MalformedConfigurationError(ValueError):
    pass


def settings_json(settings: Settings) -> JsonObject:
    return {
        "appTitle": settings.app_title,
        "appSubtitle": settings.app_subtitle,
        "countLimit": settings.count_limit,
        "catalogueDefaultPerPage": settings.catalogue_default_per_page,
        "datasetGenerationTime": settings.dataset_generation_time.isoformat()
        if settings.dataset_generation_time
        else None,
        "primarySource": settings.primary_source,
        "orcidSafelist": settings.orcid_safelist,
        "orphanHandling": settings.orphan_handling,
        "compositeHandling": settings.composite_handling,
    }


def _field(data: JsonObject, key: str, expected: type | tuple[type, ...]) -> object:
    if key not in data or not isinstance(data[key], expected):
        msg = f"Field {key} is missing or has the wrong type"
        raise MalformedConfigurationError(msg)
    return data[key]


def _object(value: object) -> JsonObject:
    if not isinstance(value, dict):
        msg = "Expected a JSON object"
        raise MalformedConfigurationError(msg)
    return cast("JsonObject", value)


def _text(data: JsonObject, key: str) -> str:
    return cast("str", _field(data, key, str))


def _optional_text(data: JsonObject, key: str) -> str | None:
    return cast("str | None", _field(data, key, (str, type(None))))


def _optional_integer(data: JsonObject, key: str) -> int | None:
    value = _field(data, key, (int, type(None)))
    if isinstance(value, bool):
        msg = f"Field {key} must be an integer"
        raise MalformedConfigurationError(msg)
    return cast("int | None", value)


def _integer(data: JsonObject, key: str) -> int:
    value = _optional_integer(data, key)
    if value is None:
        msg = f"Field {key} must be an integer"
        raise MalformedConfigurationError(msg)
    return value


def _texts(data: JsonObject, key: str) -> list[str]:
    values = cast("list", _field(data, key, list))
    if not all(isinstance(value, str) for value in values):
        msg = f"Field {key} must be a list of strings"
        raise MalformedConfigurationError(msg)
    return cast("list[str]", values)


def _optional_datetime(data: JsonObject, key: str) -> datetime | None:
    value = _optional_text(data, key)
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        msg = f"Field {key} must be an ISO 8601 date and time"
        raise MalformedConfigurationError(msg) from error


def settings_from_json(json: object) -> Settings:
    data = _object(json)
    return Settings(
        app_title=_text(data, "appTitle"),
        app_subtitle=_text(data, "appSubtitle"),
        count_limit=_integer(data, "countLimit"),
        catalogue_default_per_page=_integer(data, "catalogueDefaultPerPage"),
        dataset_generation_time=_optional_datetime(data, "datasetGenerationTime"),
        primary_source=_text(data, "primarySource"),
        orcid_safelist=_texts(data, "orcidSafelist"),
        orphan_handling=_text(data, "orphanHandling"),
        composite_handling=_text(data, "compositeHandling"),
    )
