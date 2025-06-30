import os
from datetime import timedelta

from flask import (Blueprint, current_app, flash, redirect, request, session,
                   url_for)
from flask_babel import gettext
from flask_login import current_user, login_user, logout_user
from heritrace.apis.orcid import extract_orcid_id, is_orcid_url
from heritrace.models import User
from requests_oauthlib import OAuth2Session

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.catalogue"))

    callback_url = url_for("auth.callback", _external=True, _scheme="https")
    orcid = OAuth2Session(
        current_app.config["ORCID_CLIENT_ID"],
        redirect_uri=callback_url,
        scope=[current_app.config["ORCID_SCOPE"], "openid"],
    )
    authorization_url, state = orcid.authorization_url(
        current_app.config["ORCID_AUTHORIZE_URL"],
        prompt="login",  # Forza il re-login
        nonce=os.urandom(16).hex(),  # Aggiungiamo un nonce per sicurezza
    )
    session["oauth_state"] = state
    return redirect(authorization_url)


@auth_bp.route("/callback")
def callback():
    if request.url.startswith("http://"):
        secure_url = request.url.replace("http://", "https://", 1)
    else:
        secure_url = request.url

    orcid = OAuth2Session(
        current_app.config["ORCID_CLIENT_ID"], state=session["oauth_state"]
    )
    try:
        token = orcid.fetch_token(
            current_app.config["ORCID_TOKEN_URL"],
            client_secret=current_app.config["ORCID_CLIENT_SECRET"],
            authorization_response=secure_url,
        )
    except Exception as e:
        flash(
            gettext("An error occurred during authentication. Please try again"),
            "danger",
        )
        return redirect(url_for("auth.login"))
    orcid_id = token["orcid"]

    whitelist = current_app.config["ORCID_WHITELIST"]
    if whitelist:
        normalized_whitelist = {
            extract_orcid_id(item) if is_orcid_url(item) else item for item in whitelist
        }
        if orcid_id not in normalized_whitelist:
            flash(
                gettext("Your ORCID is not authorized to access this application"),
                "danger",
            )
            return redirect(url_for("auth.login"))

    session["user_name"] = token["name"]
    user = User(id=orcid_id, name=token["name"], orcid=orcid_id)
    session.permanent = True
    current_app.permanent_session_lifetime = timedelta(days=30)
    login_user(user)
    flash(gettext("Welcome back %(name)s!", name=current_user.name), "success")
    return redirect(url_for("main.catalogue"))


@auth_bp.route("/logout")
def logout():
    if not current_user.is_authenticated:
        return "", 401
    logout_user()
    flash(gettext("You have been logged out"), "info")
    return redirect(url_for("main.index"))
