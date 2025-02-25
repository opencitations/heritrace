from flask import Flask
from flask_babel import Babel
from flask_login import LoginManager
from heritrace.cli import register_cli_commands
from redis import Redis


def create_app(config_object=None):
    app = Flask(__name__)

    if config_object:
        app.config.from_object(config_object)

    # Initialize extensions
    babel = Babel()
    login_manager = LoginManager()

    # Initialize Redis
    redis_client = Redis.from_url("redis://redis:6379", decode_responses=True)

    # Deferred imports to avoid circular dependencies
    from heritrace.extensions import init_extensions
    from heritrace.routes import register_blueprints

    init_extensions(app, babel, login_manager, redis_client)

    register_blueprints(app)

    register_cli_commands(app)

    return app
