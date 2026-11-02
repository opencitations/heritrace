# SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from unittest.mock import MagicMock, patch

from flask import Flask
from flask.testing import FlaskClient
from requests.exceptions import RequestException

TEST_TOKEN = {
    "access_token": "test-token",
    "name": "Test User",
    "orcid": "0000-0000-0000-0001",
}


def _callback_with_token(client: FlaskClient, token: dict) -> str:
    with client.session_transaction() as sess:
        sess["oauth_state"] = "test-state"
    with patch("heritrace.routes.auth.OAuth2Session") as mock_oauth:
        mock_session = MagicMock()
        mock_session.fetch_token.return_value = token
        mock_oauth.return_value = mock_session
        response = client.get("/auth/callback?code=test-code&state=test-state")
    assert response.status_code == 302
    return response.location


def _callback_with_error(client: FlaskClient, base_url: str) -> str:
    with client.session_transaction() as sess:
        sess["oauth_state"] = "test-state"
    with patch("heritrace.routes.auth.OAuth2Session") as mock_oauth:
        mock_session = MagicMock()
        mock_session.fetch_token.side_effect = RequestException("OAuth Error")
        mock_oauth.return_value = mock_session
        response = client.get("/auth/callback", base_url=base_url)
    assert response.status_code == 302
    return response.location


def test_login_authenticated_user(logged_in_client: FlaskClient) -> None:
    response = logged_in_client.get("/auth/login")
    assert response.status_code == 302
    assert response.location == "/catalogue"


def test_login_unauthenticated_user(client: FlaskClient) -> None:
    with patch("heritrace.routes.auth.OAuth2Session") as mock_oauth:
        mock_session = MagicMock()
        mock_session.authorization_url.return_value = (
            "https://test-auth-url",
            "test-state",
        )
        mock_oauth.return_value = mock_session

        response = client.get("/auth/login")
        assert response.status_code == 302
        assert response.location == "https://test-auth-url"

        with client.session_transaction() as sess:
            assert sess["oauth_state"] == "test-state"
        mock_session.authorization_url.assert_called_once()


def test_callback_success(client: FlaskClient, app: Flask) -> None:
    app.config["ORCID_SAFELIST"] = ["0000-0000-0000-0001"]
    assert _callback_with_token(client, TEST_TOKEN) == "/catalogue"
    with client.session_transaction() as sess:
        assert sess["user_name"] == "Test User"
        assert sess["_user_id"] == "0000-0000-0000-0001"


def test_callback_unauthorized_orcid(client: FlaskClient, app: Flask) -> None:
    app.config["ORCID_SAFELIST"] = ["0000-0000-0000-0001"]
    token = {**TEST_TOKEN, "orcid": "unauthorized-orcid"}
    assert _callback_with_token(client, token) == "/?login_error=not_authorized"
    with client.session_transaction() as sess:
        assert "_user_id" not in sess


def test_callback_error_over_http(client: FlaskClient) -> None:
    location = _callback_with_error(client, "http://localhost:5000")
    assert location == "/?login_error=oauth_failed"


def test_callback_error_over_https(client: FlaskClient) -> None:
    location = _callback_with_error(client, "https://localhost:5000")
    assert location == "/?login_error=oauth_failed"


def test_logout(logged_in_client: FlaskClient) -> None:
    response = logged_in_client.post("/auth/logout")
    assert response.status_code == 204
    with logged_in_client.session_transaction() as sess:
        assert "_user_id" not in sess


def test_logout_unauthenticated(client: FlaskClient) -> None:
    response = client.post("/auth/logout")
    assert response.status_code == 401


def test_login_demo_mode(client: FlaskClient) -> None:
    with patch.dict("os.environ", {"FLASK_ENV": "demo", "USER_ID": "test_demo"}):
        response = client.get("/auth/login")
        assert response.status_code == 302
        assert response.location == "/catalogue"
        with client.session_transaction() as sess:
            assert sess["user_name"] == "Demo User"
            assert sess["_user_id"] == "http://example.org/demo/test_demo"


def test_callback_no_safelist(client: FlaskClient, app: Flask) -> None:
    app.config["ORCID_SAFELIST"] = []
    assert _callback_with_token(client, TEST_TOKEN) == "/catalogue"


def test_redirects_target_the_frontend_origin_when_configured(
    client: FlaskClient, app: Flask
) -> None:
    app.config["FRONTEND_ORIGIN"] = "https://localhost:5100"
    app.config["ORCID_SAFELIST"] = []
    try:
        location = _callback_with_token(client, TEST_TOKEN)
    finally:
        app.config["FRONTEND_ORIGIN"] = ""
    assert location == "https://localhost:5100/catalogue"
