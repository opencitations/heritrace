# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from flask import Flask

from heritrace.errors.handlers import errors_bp
from heritrace.routes.api import api_bp
from heritrace.routes.auth import auth_bp
from heritrace.routes.entity import entity_bp
from heritrace.routes.linked_resources import linked_resources_bp
from heritrace.routes.merge import merge_bp
from heritrace.routes.search import search_bp
from heritrace.routes.spa import spa_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(spa_bp)
    app.register_blueprint(entity_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(search_bp, url_prefix="/api")
    app.register_blueprint(errors_bp)
    app.register_blueprint(merge_bp, url_prefix="/api/merge")
    app.register_blueprint(linked_resources_bp)
