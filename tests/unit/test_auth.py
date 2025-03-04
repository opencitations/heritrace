from unittest.mock import MagicMock, patch

from flask import Flask, url_for
from flask.testing import FlaskClient


def test_login_authenticated_user(logged_in_client: FlaskClient, app: Flask):
    """Test that authenticated users are redirected to catalogue."""
    with app.test_request_context():
        response = logged_in_client.get("/auth/login")
        assert response.status_code == 302
        assert response.location == url_for("main.catalogue")


def test_login_unauthenticated_user(client: FlaskClient, app: Flask):
    """Test login route for unauthenticated users."""
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
            assert sess.get("oauth_state") == "test-state"
        mock_session.authorization_url.assert_called_once()


def test_callback_success(client: FlaskClient, app: Flask):
    """Test successful OAuth callback."""
    test_token = {
        "access_token": "test-token",
        "name": "Test User",
        "orcid": "0000-0000-0000-0001",
    }

    with client.session_transaction() as sess:
        sess["oauth_state"] = "test-state"

    with patch("heritrace.routes.auth.OAuth2Session") as mock_oauth:
        mock_session = MagicMock()
        mock_session.fetch_token.return_value = test_token
        mock_oauth.return_value = mock_session

        app.config["ORCID_WHITELIST"] = ["0000-0000-0000-0001"]
        with app.test_request_context():
            expected_url = url_for("main.catalogue")
        response = client.get("/auth/callback?code=test-code&state=test-state")

        assert response.status_code == 302
        assert response.location == expected_url

        with client.session_transaction() as sess:
            assert sess.get("user_name") == "Test User"
            assert sess.get("_user_id") == "0000-0000-0000-0001"


def test_callback_unauthorized_orcid(client: FlaskClient, app: Flask):
    """Test callback with unauthorized ORCID."""
    test_token = {
        "access_token": "test-token",
        "name": "Test User",
        "orcid": "unauthorized-orcid",
    }

    with client.session_transaction() as sess:
        sess["oauth_state"] = "test-state"

    with patch("heritrace.routes.auth.OAuth2Session") as mock_oauth:
        mock_session = MagicMock()
        mock_session.fetch_token.return_value = test_token
        mock_oauth.return_value = mock_session

        app.config["ORCID_WHITELIST"] = ["0000-0000-0000-0001"]
        with app.test_request_context():
            expected_url = url_for("auth.login")
        response = client.get("/auth/callback?code=test-code&state=test-state")

        assert response.status_code == 302
        assert response.location == expected_url


def test_callback_error(client: FlaskClient, app: Flask):
    """Test callback with OAuth error."""
    with client.session_transaction() as sess:
        sess["oauth_state"] = "test-state"

    with patch("heritrace.routes.auth.OAuth2Session") as mock_oauth:
        mock_session = MagicMock()
        mock_session.fetch_token.side_effect = Exception("OAuth Error")
        mock_oauth.return_value = mock_session

        with app.test_request_context():
            expected_url = url_for("auth.login")
        response = client.get("/auth/callback?error=access_denied")

        assert response.status_code == 302
        assert response.location == expected_url


def test_callback_http_to_https(client: FlaskClient, app: Flask):
    """Test callback URL scheme conversion from http to https."""
    with client.session_transaction() as sess:
        sess["oauth_state"] = "test-state"

    with patch("heritrace.routes.auth.OAuth2Session") as mock_oauth:
        mock_session = MagicMock()
        mock_session.fetch_token.side_effect = Exception("OAuth Error")
        mock_oauth.return_value = mock_session

        with app.test_request_context():
            expected_url = url_for("auth.login")
        response = client.get("/auth/callback", base_url="http://localhost")

        assert response.status_code == 302
        assert response.location == expected_url


def test_logout(logged_in_client: FlaskClient, app: Flask):
    """Test logout route."""
    with app.test_request_context():
        expected_url = url_for("main.index")
    response = logged_in_client.get("/auth/logout")

    assert response.status_code == 302
    assert response.location == expected_url
    with logged_in_client.session_transaction() as sess:
        assert "_user_id" not in sess


def test_logout_unauthenticated(client: FlaskClient, app: Flask):
    """Test logout route when user is not authenticated."""
    response = client.get("/auth/logout")
    assert (
        response.status_code == 401
    )  # Should return unauthorized for unauthenticated users
