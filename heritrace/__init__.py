# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import logging
import os

from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager
from redis import Redis

from heritrace.extensions import init_extensions
from heritrace.routes import register_blueprints
from heritrace.utils.sparql_utils import (
    configure_worker_pool,
    get_available_classes,
    warm_catalogue,
    warm_time_vault,
)


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

    login_manager = LoginManager()

    redis_url = (
        app.config.get("REDIS_URL")
        or os.environ.get("REDIS_URL")
        or "redis://localhost:6379/0"
    )
    app.logger.info("Connecting to Redis at: %s", redis_url)
    redis_client = Redis.from_url(redis_url, decode_responses=True)

    with app.app_context():
        init_extensions(app, login_manager, redis_client)
        configure_worker_pool(app.config["MAX_WORKERS"], app.config["GUNICORN_WORKERS"])

        app.logger.info("[STARTUP] Pre-computing available classes cache...")
        available_classes = get_available_classes()
        app.logger.info("[STARTUP] Available classes cache computed successfully")
        warm_catalogue(available_classes, app.config["CATALOGUE_DEFAULT_PER_PAGE"])
        warm_time_vault()

    register_blueprints(app)

    return app
