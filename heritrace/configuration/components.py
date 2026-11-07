# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import import_module
from typing import cast
from urllib.parse import urlparse

from rdflib_ocdm.counter_handler.counter_handler import CounterHandler
from rdflib_ocdm.counter_handler.redis_counter_handler import RedisCounterHandler

from heritrace.save_plugin import SavePlugin
from heritrace.uri_generator.default_uri_generator import DefaultURIGenerator
from heritrace.uri_generator.uri_generator import URIGenerator


class ComponentError(Exception):
    pass


@dataclass(frozen=True)
class Components:
    uri_generator: URIGenerator
    counter_handler: CounterHandler | RedisCounterHandler
    save_plugin: SavePlugin | None


def component_options(environment_variable: str) -> dict[str, object]:
    if environment_variable not in os.environ:
        return {}
    try:
        options = json.loads(os.environ[environment_variable])
    except json.JSONDecodeError as error:
        msg = f"{environment_variable} must contain a valid JSON object"
        raise ComponentError(msg) from error
    if not isinstance(options, dict):
        msg = f"{environment_variable} must contain a JSON object"
        raise ComponentError(msg)
    return cast("dict[str, object]", options)


def _instantiate(
    config: Mapping[str, object], name: str, *args: object
) -> object | None:
    class_path = cast("str | None", config[f"{name}_CLASS"])
    options = cast("dict[str, object]", config[f"{name}_OPTIONS"])
    if class_path is None:
        if options:
            msg = f"{name}_OPTIONS requires {name}_CLASS"
            raise ComponentError(msg)
        return None
    module_path, _, class_name = class_path.rpartition(".")
    try:
        component_class = getattr(import_module(module_path), class_name)
    except (ImportError, AttributeError, ValueError) as error:
        msg = f"{name}_CLASS: no Python class exists at {class_path}"
        raise ComponentError(msg) from error
    return component_class(*args, **options)


def _redis_counter_handler(redis_url: str) -> RedisCounterHandler:
    parsed = urlparse(redis_url)
    handler = RedisCounterHandler(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        db=int(parsed.path.lstrip("/") or 0),
        password=parsed.password,
    )
    handler.connect()
    return handler


def build_components(config: Mapping[str, object], redis_url: str) -> Components:
    counter_handler = cast(
        "CounterHandler | None", _instantiate(config, "COUNTER_HANDLER")
    )
    uri_generator_args = () if counter_handler is None else (counter_handler,)
    uri_generator = cast(
        "URIGenerator | None",
        _instantiate(config, "URI_GENERATOR", *uri_generator_args),
    )
    if uri_generator is None:
        base_iri = cast("str | None", config["BASE_IRI"])
        if base_iri is None:
            msg = "Set BASE_IRI, or URI_GENERATOR_CLASS for a custom IRI generator"
            raise ComponentError(msg)
        uri_generator = DefaultURIGenerator(base_iri)
    return Components(
        uri_generator,
        counter_handler or _redis_counter_handler(redis_url),
        cast("SavePlugin | None", _instantiate(config, "SAVE_PLUGIN")),
    )
