# SPDX-FileCopyrightText: 2024-2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import logging
import os
import sys

from flask import Flask
from flask_babel import Babel
from flask_login import LoginManager
from redis import Redis

from heritrace.cli import register_cli_commands
from heritrace.extensions import init_extensions
from heritrace.routes import register_blueprints
from heritrace.utils.sparql_utils import (
    configure_worker_pool,
    get_available_classes,
    warm_catalogue,
    warm_time_vault,
)


def create_app(config_object: object = None) -> Flask:
    app = Flask(__name__)

    if config_object:
        app.config.from_object(config_object)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    app.logger.setLevel(logging.INFO)

    register_cli_commands(app)

    is_translate_command = "translate" in sys.argv

    if not is_translate_command:
        babel = Babel()
        login_manager = LoginManager()

        redis_url = (
            app.config.get("REDIS_URL")
            or os.environ.get("REDIS_URL")
            or "redis://localhost:6379/0"
        )
        app.logger.info("Connecting to Redis at: %s", redis_url)
        redis_client = Redis.from_url(redis_url, decode_responses=True)

        with app.app_context():
            init_extensions(app, babel, login_manager, redis_client)
            configure_worker_pool(
                app.config["MAX_WORKERS"], app.config["GUNICORN_WORKERS"]
            )

            app.logger.info("[STARTUP] Pre-computing available classes cache...")
            available_classes = get_available_classes()
            app.logger.info("[STARTUP] Available classes cache computed successfully")
            warm_catalogue(available_classes, app.config["CATALOGUE_DEFAULT_PER_PAGE"])
            warm_time_vault()

        register_blueprints(app)

    return app
