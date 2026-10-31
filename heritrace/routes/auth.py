# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import os
from datetime import timedelta

from flask import Blueprint, current_app, redirect, request, session, url_for
from flask_login import current_user, login_user, logout_user
from requests.exceptions import RequestException
from requests_oauthlib import OAuth2Session
from werkzeug.wrappers import Response as WerkzeugResponse

from heritrace.apis.orcid import extract_orcid_id, is_orcid_url
from heritrace.models import User

auth_bp = Blueprint("auth", __name__)

CATALOGUE_PATH = "/catalogue"
LOGIN_ERROR_PATH = "/?login_error="


def _frontend(path: str) -> str:
    return current_app.config["FRONTEND_ORIGIN"] + path


def _start_session(user: User) -> None:
    session["user_name"] = user.name
    session.permanent = True
    current_app.permanent_session_lifetime = timedelta(days=30)
    login_user(user)


@auth_bp.route("/login")
def login() -> WerkzeugResponse:
    if current_user.is_authenticated:
        return redirect(_frontend(CATALOGUE_PATH))

    if os.environ.get("FLASK_ENV") == "demo":
        user_id_from_env = os.environ.get("USER_ID", "demo_user")
        demo_uri = f"http://example.org/demo/{user_id_from_env}"
        user_name = f"Demo User ({user_id_from_env})"
        _start_session(User(user_id=demo_uri, name=user_name, orcid=demo_uri))
        return redirect(_frontend(CATALOGUE_PATH))

    callback_url = url_for("auth.callback", _external=True, _scheme="https")
    orcid = OAuth2Session(
        current_app.config["ORCID_CLIENT_ID"],
        redirect_uri=callback_url,
        scope=["/authenticate", "openid"],
    )
    authorization_url, state = orcid.authorization_url(
        "https://orcid.org/oauth/authorize",
        prompt="login",
        nonce=os.urandom(16).hex(),
    )
    session["oauth_state"] = state
    return redirect(authorization_url)


@auth_bp.route("/callback")
def callback() -> WerkzeugResponse:
    if request.url.startswith("http://"):
        secure_url = request.url.replace("http://", "https://", 1)
    else:
        secure_url = request.url

    orcid = OAuth2Session(
        current_app.config["ORCID_CLIENT_ID"], state=session["oauth_state"]
    )
    try:
        token = orcid.fetch_token(
            "https://orcid.org/oauth/token",
            client_secret=current_app.config["ORCID_CLIENT_SECRET"],
            authorization_response=secure_url,
        )
    except (RequestException, ValueError, KeyError):
        return redirect(_frontend(LOGIN_ERROR_PATH + "oauth_failed"))
    orcid_id = str(token["orcid"])

    safelist = current_app.config["ORCID_SAFELIST"]
    if safelist:
        normalized_safelist = {
            extract_orcid_id(item) if is_orcid_url(item) else item for item in safelist
        }
        if orcid_id not in normalized_safelist:
            return redirect(_frontend(LOGIN_ERROR_PATH + "not_authorized"))

    _start_session(User(user_id=orcid_id, name=str(token["name"]), orcid=orcid_id))
    return redirect(_frontend(CATALOGUE_PATH))


@auth_bp.route("/logout", methods=["POST"])
def logout() -> tuple[str, int]:
    if not current_user.is_authenticated:
        return "", 401
    logout_user()
    return "", 204
