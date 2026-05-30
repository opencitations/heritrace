# SPDX-FileCopyrightText: 2024-2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import current_app

if TYPE_CHECKING:
    from flask import Flask


VIRTUOSO_EXCLUDED_GRAPHS = [
    "http://localhost:8890/DAV/",
    "http://www.openlinksw.com/schemas/virtrdf#",
    "http://www.w3.org/2002/07/owl#",
    "http://www.w3.org/ns/ldp#",
    "urn:activitystreams-owl:map",
    "urn:core:services:sparql",
]


def is_virtuoso(app: Flask | None = None) -> bool:
    """
    Check if the triplestore is Virtuoso.

    Args:
        app: Flask application object (optional)

    Returns:
        bool: True if triplestore is Virtuoso, False otherwise
    """
    if app is None:
        app = current_app
    return app.config["DATASET_DB_TRIPLESTORE"].lower() == "virtuoso"
