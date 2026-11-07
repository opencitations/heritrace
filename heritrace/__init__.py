# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import logging

from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from flask_login import LoginManager
from rdflib.plugins.parsers.notation3 import BadSyntax
from redis import Redis

from heritrace.configuration.entity import (
    ConfigurationRejectedError,
    ensure_configuration_entity,
    read_shacl,
)
from heritrace.configuration.runtime import (
    SetupRequiredError,
    apply_settings,
    install_components,
    load_settings,
)
from heritrace.configuration.settings import read_settings
from heritrace.configuration.store import SETTINGS_FILE
from heritrace.extensions import (
    build_configuration_state,
    init_extensions,
    init_login_manager,
    init_request_handlers,
)
from heritrace.routes import register_blueprints
from heritrace.utils.sparql_utils import (
    configure_worker_pool,
    get_available_classes,
    warm_catalogue,
    warm_recycle_bin,
)

SETUP_API_PATHS = ("/api/me", "/api/configuration")


def _allowed_in_setup(path: str) -> bool:
    return any(
        path == allowed or path.startswith(f"{allowed}/") for allowed in SETUP_API_PATHS
    )


def _start_setup_mode(
    app: Flask, login_manager: LoginManager, redis_client: Redis, error: str
) -> None:
    app.logger.warning("[STARTUP] HERITRACE needs configuration: %s", error)
    app.config["SETUP_ERROR"] = error
    init_login_manager(app, login_manager)
    init_request_handlers(app, redis_client)

    @app.before_request
    def require_configuration() -> tuple[Response, int] | None:
        if request.path.startswith("/api/") and not _allowed_in_setup(request.path):
            return jsonify({"status": "error", "message": "Setup required"}), 503
        return None


def _start(
    app: Flask, login_manager: LoginManager, redis_client: Redis, redis_url: str
) -> None:
    config_dir = app.config["CONFIG_DIR"]
    install_components(app.config, redis_url)
    stored = read_settings(config_dir / SETTINGS_FILE)
    app.config["CONFIGURATION_REVISION"] = stored.revision if stored else None
    try:
        ensure_configuration_entity(config_dir)
        shacl_graph = read_shacl(config_dir)
        apply_settings(app.config, load_settings(stored).settings)
        init_extensions(app, login_manager, redis_client, shacl_graph)
    except (BadSyntax, ConfigurationRejectedError, SetupRequiredError) as error:
        _start_setup_mode(app, login_manager, redis_client, str(error))
        return
    app.extensions["heritrace_configuration"] = build_configuration_state(app)
    app.config["SETUP_ERROR"] = None
    configure_worker_pool(app.config["GUNICORN_WORKERS"])

    app.logger.info("[STARTUP] Pre-computing available classes cache...")
    available_classes = get_available_classes()
    app.logger.info("[STARTUP] Available classes cache computed successfully")
    warm_catalogue(available_classes, app.config["CATALOGUE_DEFAULT_PER_PAGE"])
    warm_recycle_bin()


def create_app(config_object: type) -> Flask:
    app = Flask(
        __name__,
        static_folder=str(config_object.FRONTEND_BUILD_DIR),
        static_url_path="",
    )
    app.config.from_object(config_object)
    if app.config["FRONTEND_ORIGIN"]:
        CORS(
            app,
            origins=[app.config["FRONTEND_ORIGIN"]],
            supports_credentials=True,
        )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    app.logger.setLevel(logging.INFO)

    redis_url = app.config["REDIS_URL"]
    app.logger.info("Connecting to Redis at: %s", redis_url)
    redis_client = Redis.from_url(redis_url, decode_responses=True)

    with app.app_context():
        _start(app, LoginManager(), redis_client, redis_url)

    register_blueprints(app)

    return app
