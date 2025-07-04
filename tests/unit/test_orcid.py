import pytest
import responses
from heritrace.apis.orcid import (
    extract_orcid_id,
    format_orcid_attribution,
    get_orcid_data,
    is_orcid_url,
)


@pytest.fixture(autouse=True)
def clear_lru_cache():
    get_orcid_data.cache_clear()
    yield
    get_orcid_data.cache_clear()


def test_is_orcid_url_valid():
    assert is_orcid_url("https://orcid.org/0000-0002-1825-0097")
    assert is_orcid_url("http://orcid.org/0000-0002-1825-0097")


def test_is_orcid_url_invalid():
    assert not is_orcid_url("https://example.com")
    assert not is_orcid_url("not-a-url")


def test_is_orcid_url_exception():
    assert not is_orcid_url(None)
    assert not is_orcid_url(123)


def test_extract_orcid_id_valid():
    assert (
        extract_orcid_id("https://orcid.org/0000-0002-1825-0097")
        == "0000-0002-1825-0097"
    )
    assert extract_orcid_id("/0000-0002-1825-0097") == "0000-0002-1825-0097"


def test_extract_orcid_id_with_https_prefix():
    url = "https://orcid.org/https://orcid.org/0000-0002-1825-0097"
    assert extract_orcid_id(url) == "0000-0002-1825-0097"


def test_extract_orcid_id_exception():
    assert extract_orcid_id(None) is None
    assert extract_orcid_id(123) is None


@responses.activate
def test_get_orcid_data_non_200_response(app):
    orcid_id = "0000-0002-1825-0097"
    responses.add(
        responses.GET, f"https://pub.orcid.org/v3.0/{orcid_id}/person", status=404
    )
    with app.app_context():
        assert get_orcid_data(orcid_id) is None


@responses.activate
def test_get_orcid_data_exception(app):
    orcid_id = "0000-0002-1825-0097"
    responses.add(
        responses.GET,
        f"https://pub.orcid.org/v3.0/{orcid_id}/person",
        body=Exception("Connection error"),
    )
    with app.app_context():
        assert get_orcid_data(orcid_id) is None


@responses.activate
def test_get_orcid_data_success(app):
    orcid_id = "0000-0002-1825-0097"
    mock_response = {
        "name": {"given-names": {"value": "John"}, "family-name": {"value": "Doe"}},
        "other-names": {"other-name": [{"content": "Johnny"}]},
        "biography": {"content": "Researcher"},
    }

    responses.add(
        responses.GET,
        f"https://pub.orcid.org/v3.0/{orcid_id}/person",
        json=mock_response,
        status=200,
    )
    with app.app_context():
        result = get_orcid_data(orcid_id)
        assert result["name"] == "John Doe"
        assert result["other_names"] == ["Johnny"]
        assert result["biography"] == "Researcher"
        assert result["orcid"] == orcid_id


def test_format_orcid_attribution_invalid_url():
    url = "https://example.com"
    result = format_orcid_attribution(url)
    assert result == f'<a href="{url}" target="_blank">{url}</a>'


@responses.activate
def test_format_orcid_attribution_no_data(app):
    orcid_id = "0000-0002-1825-0097"
    url = f"https://orcid.org/{orcid_id}"
    responses.add(
        responses.GET, f"https://pub.orcid.org/v3.0/{orcid_id}/person", status=404
    )
    with app.app_context():
        result = format_orcid_attribution(url)
        assert result == f'<a href="{url}" target="_blank">{url}</a>'


@responses.activate
def test_format_orcid_attribution_success(app):
    orcid_id = "0000-0002-1825-0097"
    url = f"https://orcid.org/{orcid_id}"
    mock_response = {
        "name": {"given-names": {"value": "John"}, "family-name": {"value": "Doe"}}
    }

    responses.add(
        responses.GET,
        f"https://pub.orcid.org/v3.0/{orcid_id}/person",
        json=mock_response,
        status=200,
    )
    with app.app_context():
        result = format_orcid_attribution(url)
        expected = f'<a href="{url}" target="_blank" class="orcid-attribution"><img src="/static/images/orcid-logo.png" alt="ORCID iD" class="orcid-icon mx-1 mb-1" style="width: 16px; height: 16px;">John Doe [orcid:{orcid_id}]</a>'
        assert result == expected
