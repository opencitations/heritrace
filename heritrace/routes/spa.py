# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from flask import Blueprint, Response, current_app, send_from_directory

spa_bp = Blueprint("spa", __name__)

SPA_PATHS = (
    "/",
    "/catalogue",
    "/recycle-bin",
    "/create-entity",
    "/about/<path:subject>",
    "/entity-history/<path:entity_uri>",
    "/entity-version/<path:entity_uri>/<timestamp>",
    "/merge/compare-and-merge",
    "/settings",
)


def serve_index(**_params: str) -> Response:
    response = send_from_directory(
        current_app.config["FRONTEND_BUILD_DIR"], "index.html"
    )
    response.headers["Cache-Control"] = "no-cache"
    return response


for path in SPA_PATHS:
    spa_bp.add_url_rule(path, endpoint="index", view_func=serve_index)
