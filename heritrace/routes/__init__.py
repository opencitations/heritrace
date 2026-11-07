# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from flask import Flask, Response, current_app, g, jsonify, request
from flask_login import current_user

from heritrace.configuration.entity import (
    ConfigurationRejectedError,
    configuration_lock,
)
from heritrace.configuration.runtime import is_admin
from heritrace.errors.handlers import errors_bp
from heritrace.routes.api import api_bp
from heritrace.routes.auth import auth_bp
from heritrace.routes.configuration import configuration_bp
from heritrace.routes.entity import entity_bp
from heritrace.routes.linked_resources import linked_resources_bp
from heritrace.routes.merge import merge_bp
from heritrace.routes.search import search_bp
from heritrace.routes.spa import spa_bp

CONFIGURATION_BLUEPRINTS = (
    "configuration_entity",
    "configuration_api",
    "configuration_search",
)


# The entity routes also serve the SHACL configuration, as one entity that only
# admins edit, under /api/configuration. CORS preflights carry no session, so
# they pass through. A request that may change the configuration holds its lock
# until the end, so two workers never number the same snapshot.
def use_configuration_store() -> tuple[Response, int] | None:
    if request.method == "OPTIONS" or request.blueprint not in CONFIGURATION_BLUEPRINTS:
        return None
    if not current_user.is_authenticated:
        return jsonify({"status": "error", "message": "Authentication required"}), 401
    if not is_admin(current_app.config, current_user.orcid):
        return jsonify({"status": "error", "message": "Admins only"}), 403
    if "heritrace_configuration" not in current_app.extensions:
        return jsonify({"status": "error", "message": "Setup required"}), 503
    g.store = current_app.extensions["heritrace_configuration"]
    if request.method != "GET":
        g.configuration_lock = configuration_lock(current_app.config["CONFIG_DIR"])
        g.configuration_lock.acquire()
    return None


def release_configuration_lock(_error: BaseException | None) -> None:
    if "configuration_lock" in g:
        g.pop("configuration_lock").release()


def reject_configuration(
    error: ConfigurationRejectedError,
) -> tuple[Response, int]:
    return jsonify({"status": "error", "errors": error.issues}), 422


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(spa_bp)
    app.register_blueprint(entity_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(configuration_bp, url_prefix="/api")
    app.register_blueprint(search_bp, url_prefix="/api")
    app.register_blueprint(errors_bp)
    app.register_blueprint(merge_bp, url_prefix="/api/merge")
    app.register_blueprint(linked_resources_bp)
    app.register_blueprint(
        entity_bp, url_prefix="/api/configuration", name="configuration_entity"
    )
    app.register_blueprint(
        api_bp, url_prefix="/api/configuration", name="configuration_api"
    )
    app.register_blueprint(
        search_bp, url_prefix="/api/configuration", name="configuration_search"
    )
    app.before_request(use_configuration_store)
    app.teardown_request(release_configuration_lock)
    app.register_error_handler(ConfigurationRejectedError, reject_configuration)
