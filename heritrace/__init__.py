import logging
import os
import sys

from flask import Flask
from flask_babel import Babel
from flask_login import LoginManager
from redis import Redis

from heritrace.cli import register_cli_commands
from heritrace.utils.sparql_utils import precompute_available_classes_cache


def create_app(config_object=None):
    app = Flask(__name__)

    if config_object:
        app.config.from_object(config_object)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    app.logger.setLevel(logging.INFO)

    register_cli_commands(app)

    is_translate_command = 'translate' in sys.argv

    if not is_translate_command:
        babel = Babel()
        login_manager = LoginManager()
        
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        app.logger.info(f"Connecting to Redis at: {redis_url}")
        redis_client = Redis.from_url(redis_url, decode_responses=True)

        from heritrace.extensions import init_extensions
        from heritrace.routes import register_blueprints

        init_extensions(app, babel, login_manager, redis_client)

        with app.app_context():
            app.logger.info("[STARTUP] Pre-computing available classes cache...")
            try:
                precompute_available_classes_cache()
                app.logger.info("[STARTUP] Available classes cache computed successfully")
            except Exception as e:
                app.logger.warning(f"[STARTUP] Failed to pre-compute classes cache: {e}")
                app.logger.warning("[STARTUP] Classes will be computed on first request")

        register_blueprints(app)

    return app
