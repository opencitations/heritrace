from flask import Flask
from flask_babel import Babel
from flask_login import LoginManager
from heritrace.cli import register_cli_commands
from redis import Redis
import logging


def create_app(config_object=None):
    app = Flask(__name__)

    if config_object:
        app.config.from_object(config_object)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    app.logger.setLevel(logging.INFO)

    babel = Babel()
    login_manager = LoginManager()

    redis_url = app.config.get('REDIS_URL', 'redis://redis:6379') # Default to production if not set
    redis_client = Redis.from_url(redis_url, decode_responses=True)

    from heritrace.extensions import init_extensions
    from heritrace.routes import register_blueprints

    init_extensions(app, babel, login_manager, redis_client)

    register_blueprints(app)

    register_cli_commands(app)

    return app
