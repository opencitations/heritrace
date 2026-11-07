# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from collections.abc import Callable
from functools import wraps
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, Response, current_app, g, jsonify, request
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required
from requests import RequestException

from heritrace.apis.orcid import (
    OrcidNotFoundError,
    fetch_orcid_name,
    is_valid_orcid_id,
)
from heritrace.configuration.runtime import is_admin, request_reload
from heritrace.configuration.serialization import (
    MalformedConfigurationError,
    settings_from_json,
    settings_json,
)
from heritrace.configuration.settings import (
    STRATEGIES,
    Settings,
    read_settings,
    write_settings,
)
from heritrace.configuration.store import SETTINGS_FILE
from heritrace.configuration.validation import validate_settings
from heritrace.services.resource_lock_manager import LockInfo, LockStatus

configuration_bp = Blueprint("configuration", __name__)

# The system settings have no IRI of their own: admins lock them under this one,
# as they lock an entity while editing it.
SETTINGS_RESOURCE = "https://w3id.org/heritrace/settings"


def _held_by(lock_info: LockInfo) -> dict[str, str]:
    return {
        "status": "locked",
        "user_name": lock_info.user_name,
        "user_id": lock_info.user_id,
    }


def admin_required(
    view: Callable[..., ResponseReturnValue],
) -> Callable[..., ResponseReturnValue]:
    @wraps(view)
    @login_required
    def wrapper(*args: object, **kwargs: object) -> ResponseReturnValue:
        if not is_admin(current_app.config, current_user.orcid):
            return jsonify({"status": "error", "message": "Admins only"}), 403
        return view(*args, **kwargs)

    return wrapper


def _config_dir() -> Path:
    return current_app.config["CONFIG_DIR"]


@configuration_bp.route("/configuration")
@admin_required
def get_settings() -> Response:
    defaults = Settings(primary_source="")
    stored = read_settings(_config_dir() / SETTINGS_FILE)
    return jsonify(
        {
            "settings": settings_json(stored.settings if stored else defaults),
            "options": {
                "strategies": list(STRATEGIES),
                "defaultCountLimit": defaults.count_limit,
            },
        }
    )


@configuration_bp.route("/configuration/lock", methods=["POST"])
@admin_required
def lock_settings() -> ResponseReturnValue:
    status, lock_info = g.resource_lock_manager.check_lock_status(SETTINGS_RESOURCE)
    if status == LockStatus.LOCKED:
        return jsonify(_held_by(lock_info))
    if not g.resource_lock_manager.acquire_lock(SETTINGS_RESOURCE, []):
        return jsonify({"status": "error", "message": "Unable to lock"}), 500
    return jsonify({"status": "success"})


@configuration_bp.route("/configuration/lock", methods=["DELETE"])
@admin_required
def unlock_settings() -> Response:
    g.resource_lock_manager.release_lock(SETTINGS_RESOURCE)
    return jsonify({"status": "success"})


@configuration_bp.route("/configuration", methods=["PUT"])
@admin_required
def save_settings() -> ResponseReturnValue:
    status, lock_info = g.resource_lock_manager.check_lock_status(SETTINGS_RESOURCE)
    if status == LockStatus.LOCKED:
        return jsonify(_held_by(lock_info)), 423
    try:
        settings = settings_from_json(request.get_json())
    except MalformedConfigurationError as error:
        return jsonify({"status": "error", "message": str(error)}), 400
    issues = validate_settings(settings)
    if issues:
        return jsonify(
            {
                "status": "invalid",
                "issues": [
                    {"location": issue.location, "message": issue.message}
                    for issue in issues
                ],
            }
        ), 422
    revision = uuid4().hex
    write_settings(_config_dir() / SETTINGS_FILE, settings, revision)
    return jsonify(
        {"status": "success", "revision": revision, "reloading": request_reload()}
    )


@configuration_bp.route("/configuration/orcid/<orcid_id>")
@admin_required
def look_up_orcid(orcid_id: str) -> ResponseReturnValue:
    if not is_valid_orcid_id(orcid_id):
        return jsonify({"status": "error", "message": "Invalid ORCID iD"}), 400
    try:
        name = fetch_orcid_name(orcid_id)
    except OrcidNotFoundError:
        return jsonify({"status": "error", "message": "No such ORCID iD"}), 404
    except RequestException:
        return jsonify({"status": "error", "message": "ORCID is unreachable"}), 502
    return jsonify({"name": name})
