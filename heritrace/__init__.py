import logging
import sys

from flask import Flask
from flask_babel import Babel
from flask_login import LoginManager
from heritrace.cli import register_cli_commands
from redis import Redis


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

        redis_url = 'redis://localhost:6379/0'  # Internal Redis service
        redis_client = Redis.from_url(redis_url, decode_responses=True)

        from heritrace.extensions import init_extensions
        from heritrace.routes import register_blueprints

        init_extensions(app, babel, login_manager, redis_client)

        register_blueprints(app)

    return app
