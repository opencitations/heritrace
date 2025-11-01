import json
from unittest.mock import MagicMock, patch

from flask.testing import FlaskClient


@patch("heritrace.routes.api.get_custom_filter")
def test_format_source_api_success(
    mock_get_custom_filter: MagicMock, logged_in_client: FlaskClient
) -> None:
    """
    Test the /api/format-source endpoint for a successful formatting request.
    """
    mock_filter_instance = MagicMock()
    mock_filter_instance.format_source_reference.return_value = (
        '<a href="http://example.com" target="_blank">Formatted Example</a>'
    )
    mock_get_custom_filter.return_value = mock_filter_instance
    test_url = "http://example.com"

    response = logged_in_client.post(
        "/api/format-source", json={"url": test_url}
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert "formatted_html" in data
    assert (
        data["formatted_html"]
        == '<a href="http://example.com" target="_blank">Formatted Example</a>'
    )
    mock_get_custom_filter.assert_called_once()
    mock_filter_instance.format_source_reference.assert_called_once_with(
        test_url
    )


def test_format_source_api_missing_url(
    logged_in_client: FlaskClient,
) -> None:
    """
    Test the /api/format-source endpoint when the URL is missing in the request.
    """
    response = logged_in_client.post("/api/format-source", json={})

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "Invalid or missing URL"


@patch("heritrace.routes.api.validators.url")
def test_format_source_api_invalid_url(
    mock_validators_url: MagicMock, logged_in_client: FlaskClient
) -> None:
    """
    Test the /api/format-source endpoint when the provided URL is invalid.
    """
    mock_validators_url.return_value = False
    invalid_url = "not-a-valid-url"

    response = logged_in_client.post(
        "/api/format-source", json={"url": invalid_url}
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "Invalid or missing URL"
    mock_validators_url.assert_called_once_with(invalid_url)


@patch("heritrace.routes.api.get_custom_filter")
@patch("heritrace.routes.api.current_app")
def test_format_source_api_exception(
    mock_current_app: MagicMock,
    mock_get_custom_filter: MagicMock,
    logged_in_client: FlaskClient,
) -> None:
    """
    Test the /api/format-source endpoint when an exception occurs during formatting.
    """
    # Explicitly set logger to be a regular MagicMock to avoid AsyncMock issues
    mock_current_app.logger = MagicMock()
    mock_current_app.logger.error = MagicMock()

    mock_filter_instance = MagicMock()
    exception_message = "Formatting failed"
    mock_filter_instance.format_source_reference.side_effect = Exception(
        exception_message
    )
    mock_get_custom_filter.return_value = mock_filter_instance
    test_url = "http://example.com/problem"

    response = logged_in_client.post(
        "/api/format-source", json={"url": test_url}
    )

    assert response.status_code == 200  # Fallback HTML is returned with 200
    data = json.loads(response.data)
    assert "formatted_html" in data
    assert data["formatted_html"] == (
        f'<a href="{test_url}" target="_blank">{test_url}</a>'
    )
    mock_get_custom_filter.assert_called_once()
    mock_filter_instance.format_source_reference.assert_called_once_with(
        test_url
    )
    mock_current_app.logger.error.assert_called_once()
    log_call_args = mock_current_app.logger.error.call_args[0]
    assert f"Error formatting source URL '{test_url}'" in log_call_args[0]
    assert exception_message in log_call_args[0] 