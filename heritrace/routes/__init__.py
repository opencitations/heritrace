# SPDX-FileCopyrightText: 2024-2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from flask import Flask


def register_blueprints(app: Flask) -> None:
    """Register all blueprints for the application."""
    from heritrace.errors.handlers import errors_bp  # noqa: PLC0415
    from heritrace.routes.api import api_bp  # noqa: PLC0415
    from heritrace.routes.auth import auth_bp  # noqa: PLC0415
    from heritrace.routes.entity import entity_bp  # noqa: PLC0415
    from heritrace.routes.linked_resources import linked_resources_bp  # noqa: PLC0415
    from heritrace.routes.main import main_bp  # noqa: PLC0415
    from heritrace.routes.merge import merge_bp  # noqa: PLC0415

    app.register_blueprint(main_bp)
    app.register_blueprint(entity_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(errors_bp, url_prefix="/errors")
    app.register_blueprint(merge_bp, url_prefix="/merge")
    app.register_blueprint(linked_resources_bp)
