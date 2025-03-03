from unittest.mock import patch

import pytest
import requests
from heritrace.apis.zenodo import (
    ZenodoRequestError,
    extract_zenodo_id,
    format_apa_date,
    format_authors_apa,
    format_zenodo_source,
    get_zenodo_data,
    is_zenodo_url,
    make_request_with_retry,
)


class TestZenodoUrlFunctions:
    """Test functions related to Zenodo URL handling."""

    def test_is_zenodo_url(self):
        """Test the is_zenodo_url function with various inputs."""
        # Valid Zenodo URLs
        assert is_zenodo_url("https://zenodo.org/record/12345") is True
        assert is_zenodo_url("https://www.zenodo.org/records/12345") is True
        assert is_zenodo_url("https://doi.org/10.5281/zenodo.12345") is True
        assert is_zenodo_url("10.5281/zenodo.12345") is True

        # Invalid Zenodo URLs
        assert is_zenodo_url("https://example.com") is False
        assert is_zenodo_url("https://doi.org/10.1234/abcd") is False

        # Edge cases - these may need to be adjusted based on actual implementation
        assert is_zenodo_url("") is False
        assert is_zenodo_url(None) is False

    def test_extract_zenodo_id(self):
        """Test the extract_zenodo_id function with various inputs."""
        # Direct Zenodo URLs
        assert extract_zenodo_id("https://zenodo.org/record/7406075") == "7406075"
        assert extract_zenodo_id("https://www.zenodo.org/records/7406075") == "7406075"

        # DOI URLs
        assert extract_zenodo_id("https://doi.org/10.5281/zenodo.7406075") == "7406075"
        assert (
            extract_zenodo_id("https://www.doi.org/10.5281/zenodo.7406075") == "7406075"
        )

        # Raw DOI strings
        assert extract_zenodo_id("10.5281/zenodo.7406075") == "7406075"

        # Invalid inputs
        assert extract_zenodo_id("https://example.com") is None
        assert extract_zenodo_id("") is None
        assert extract_zenodo_id("https://zenodo.org/not-a-record") is None
        assert extract_zenodo_id("https://doi.org/10.1234/abcd") is None

        # Edge cases that trigger exception handling
        assert extract_zenodo_id(None) is None


class TestZenodoAPIFunctions:
    """Test functions that interact with the Zenodo API."""

    def test_get_zenodo_data_real(self):
        """Test fetching real data from Zenodo API."""
        # Using a known stable Zenodo record
        record_id = "7406075"  # This is a real Zenodo record ID

        data = get_zenodo_data(record_id)

        # Verify we got valid data back
        assert data is not None
        assert "title" in data
        assert "authors" in data
        assert "doi" in data
        assert "publication_date" in data

        # Verify some specific fields from this record
        assert "10.5281/zenodo.7406075" in data["doi"]
        assert len(data["authors"]) > 0
        assert data["record_id"] == record_id

    def test_get_zenodo_data_invalid(self):
        """Test fetching data for an invalid Zenodo record ID."""
        # Using a non-existent record ID
        record_id = "999999999999999"

        # This should return None for a non-existent record
        data = get_zenodo_data(record_id)
        assert data is None


class TestZenodoFormattingFunctions:
    """Test functions related to formatting Zenodo data."""

    def test_format_apa_date(self):
        """Test the format_apa_date function with various inputs."""
        # Full date
        assert format_apa_date("2023-01-15") == "2023, January 15"

        # Year and month
        assert format_apa_date("2023-01") == "2023, January"

        # Year only
        assert format_apa_date("2023") == "2023"

        # Invalid date
        assert format_apa_date("invalid-date") == "invalid-date"

    def test_format_authors_apa(self):
        """Test the format_authors_apa function with various inputs."""
        # Single author
        single_author = [{"name": "Doe, John"}]
        assert format_authors_apa(single_author) == "Doe, John"

        # Single author without comma
        single_author_no_comma = [{"name": "John Doe"}]
        assert format_authors_apa(single_author_no_comma) == "John Doe"

        # Two authors
        two_authors = [{"name": "Doe, John"}, {"name": "Smith, Jane"}]
        assert format_authors_apa(two_authors) == "Doe, John & Smith, Jane"

        # Multiple authors
        multiple_authors = [
            {"name": "Doe, John"},
            {"name": "Smith, Jane"},
            {"name": "Brown, Robert"},
        ]
        assert (
            format_authors_apa(multiple_authors)
            == "Doe, John, Smith, Jane, & Brown, Robert"
        )

        # Empty list
        assert format_authors_apa([]) == ""

        # None
        assert format_authors_apa(None) == ""

    def test_format_authors_apa_edge_cases(self):
        """Test the format_authors_apa function with edge cases."""
        # Empty string for author name
        empty_name_author = [{"name": ""}]
        assert format_authors_apa(empty_name_author) == ""

        # Missing name key
        missing_name_author = [{}]
        with pytest.raises(KeyError):
            format_authors_apa(missing_name_author)

    def test_format_authors_apa_with_empty_string(self):
        """Test format_authors_apa with empty string."""
        result = format_authors_apa("")
        assert result == ""

    def test_format_authors_apa_with_empty_list(self):
        """Test format_authors_apa with empty list."""
        # Test with empty list - should return empty string
        authors_empty = []
        result = format_authors_apa(authors_empty)
        assert result == ""

    def test_format_authors_apa_with_one_or_two_authors(self):
        """Test format_authors_apa with one or two authors."""
        # Test with one author
        authors_one = [{"name": "Smith, J."}]
        result_one = format_authors_apa(authors_one)
        assert result_one == "Smith, J."

        # Test with two authors
        authors_two = [{"name": "Smith, J."}, {"name": "Doe, A."}]
        result_two = format_authors_apa(authors_two)
        assert result_two == "Smith, J. & Doe, A."

    def test_format_zenodo_source_real(self):
        """Test the format_zenodo_source function with a real Zenodo URL."""
        # Using a known stable Zenodo record
        url = "https://doi.org/10.5281/zenodo.7406075"

        html = format_zenodo_source(url)

        # Verify we got valid HTML back
        assert html is not None
        assert '<a href="' in html
        assert 'class="zenodo-attribution"' in html
        assert '<img src="/static/images/zenodo-logo.png"' in html

        # Verify the DOI is in the HTML
        assert "10.5281/zenodo.7406075" in html

    def test_format_zenodo_source_invalid(self):
        """Test the format_zenodo_source function with an invalid URL."""
        # Using a non-Zenodo URL
        url = "https://example.com"

        html = format_zenodo_source(url)

        # Should just return a simple link
        assert html == f'<a href="{url}" target="_blank">{url}</a>'

    def test_format_zenodo_source_with_invalid_record_id(self):
        """Test the format_zenodo_source function with a valid Zenodo URL but invalid record ID."""
        # Using a Zenodo URL with an invalid record ID
        url = "https://doi.org/10.5281/zenodo.999999999999"

        html = format_zenodo_source(url)

        # Should just return a simple link
        assert html == f'<a href="{url}" target="_blank">{url}</a>'

    def test_format_zenodo_source_with_complete_metadata(self):
        """Test the format_zenodo_source function with a record that has complete metadata."""
        # Using a record with rich metadata
        url = "https://doi.org/10.5281/zenodo.3233486"  # A record with more complete metadata

        html = format_zenodo_source(url)

        # Verify we got valid HTML back with extra metadata
        assert html is not None
        assert '<a href="' in html
        assert 'class="zenodo-attribution"' in html
        assert '<div class="text-muted small mt-1">' in html

        # Verify the DOI is in the HTML
        assert "10.5281/zenodo.3233486" in html

    def test_format_zenodo_source_with_minimal_metadata(self):
        """Test the format_zenodo_source function with a record that has minimal metadata."""
        # Mock a record with minimal metadata
        record_id = "7406075"

        # Create a patch for get_zenodo_data to return minimal data
        minimal_data = {
            "title": "Test Dataset",
            "authors": [{"name": "Test Author"}],
            "doi": "10.5281/zenodo.7406075",
            "publication_date": "2023",
            "record_id": record_id,
            # Add required fields with empty values to avoid KeyError
            "type": "",
            "subtype": "",
            "journal": "",
            "journal_volume": "",
            "journal_issue": "",
            "journal_pages": "",
            "conference": "",
            "conference_acronym": "",
            "conference_place": "",
            "conference_date": "",
            "publisher": "",
            "keywords": [],
            "description": "",
            "access_right": "",
            "language": "",
            "notes": "",
            "version": "",
        }

        with patch("heritrace.apis.zenodo.get_zenodo_data", return_value=minimal_data):
            url = f"https://doi.org/10.5281/zenodo.{record_id}"
            html = format_zenodo_source(url)

            # Verify we got valid HTML back
            assert html is not None
            assert '<a href="' in html
            assert 'class="zenodo-attribution"' in html
            assert "Test Dataset" in html
            assert "Test Author" in html
            assert "2023" in html

            # Verify there's no extra metadata section (since all fields are empty)
            assert '<div class="text-muted small mt-1">' not in html

    def test_format_zenodo_source_with_rich_metadata(self):
        """Test the format_zenodo_source function with a record that has rich metadata."""
        # Mock a record with rich metadata
        record_id = "7406075"

        # Create a patch for get_zenodo_data to return rich data
        rich_data = {
            "title": "Test Dataset",
            "authors": [
                {
                    "name": "Test Author",
                    "orcid": "0000-0000-0000-0000",
                    "affiliation": "Test University",
                }
            ],
            "doi": "10.5281/zenodo.7406075",
            "publication_date": "2023-01-15",
            "version": "1.0",
            "type": "dataset",
            "subtype": "survey",
            "journal": "Test Journal",
            "journal_volume": "1",
            "journal_issue": "2",
            "journal_pages": "3-4",
            "conference": "Test Conference",
            "conference_acronym": "TC",
            "conference_place": "Test Place",
            "conference_date": "2023-01-15",
            "publisher": "Test Publisher",
            "keywords": ["test", "dataset"],
            "description": "Test Description",
            "access_right": "open",
            "language": "en",
            "record_id": record_id,
            "notes": "Test Notes",
        }

        with patch("heritrace.apis.zenodo.get_zenodo_data", return_value=rich_data):
            url = f"https://doi.org/10.5281/zenodo.{record_id}"
            html = format_zenodo_source(url)

            # Verify we got valid HTML back with rich metadata
            assert html is not None
            assert '<a href="' in html
            assert 'class="zenodo-attribution"' in html
            assert "Test Dataset" in html
            assert "Test Author" in html
            assert "2023, January 15" in html
            assert "Test Journal" in html
            assert "Test Publisher" in html
            assert "Version 1.0" in html

            # Verify the extra metadata section
            assert '<div class="text-muted small mt-1">' in html
            assert "Type: dataset (survey)" in html
            assert "Keywords: test, dataset" in html
            assert "Language: en" in html
            assert "Access: open" in html

    def test_format_zenodo_source_with_conference_data(self):
        """Test the format_zenodo_source function with conference data."""
        # Mock a record with conference data
        record_id = "7406075"

        # Create a patch for get_zenodo_data to return data with conference info
        conference_data = {
            "title": "Test Conference Paper",
            "authors": [{"name": "Test Author"}],
            "doi": "10.5281/zenodo.7406075",
            "publication_date": "2023-01-15",
            "record_id": record_id,
            "type": "publication",
            "subtype": "conferencepaper",
            "journal": "",
            "journal_volume": "",
            "journal_issue": "",
            "journal_pages": "",
            "conference": "Test Conference",
            "conference_place": "Test Place",
            "conference_acronym": "TC",
            "conference_date": "2023-01",
            "publisher": "Test Publisher",
            "keywords": ["test", "conference"],
            "description": "Test Description",
            "access_right": "open",
            "language": "en",
            "notes": "Test Notes",
            "version": "1.0",
        }

        with patch(
            "heritrace.apis.zenodo.get_zenodo_data", return_value=conference_data
        ):
            url = f"https://doi.org/10.5281/zenodo.{record_id}"
            html = format_zenodo_source(url)

            # Verify we got valid HTML back with conference info
            assert html is not None
            assert '<a href="' in html
            assert 'class="zenodo-attribution"' in html
            assert "Test Conference Paper" in html
            assert "Test Author" in html
            assert "2023, January 15" in html
            assert "In Test Conference" in html
            assert "(Test Place)" in html
            assert "Test Publisher" in html

            # Verify the extra metadata section
            assert '<div class="text-muted small mt-1">' in html
            assert "Type: publication (conferencepaper)" in html

    def test_format_zenodo_source_with_journal_data(self):
        """Test the format_zenodo_source function with journal data."""
        # Mock a record with journal data
        record_id = "7406075"

        # Create a patch for get_zenodo_data to return data with journal info
        journal_data = {
            "title": "Test Journal Article",
            "authors": [{"name": "Test Author"}],
            "doi": "10.5281/zenodo.7406075",
            "publication_date": "2023-01-15",
            "record_id": record_id,
            "type": "publication",
            "subtype": "article",
            "journal": "Test Journal",
            "journal_volume": "10",
            "journal_issue": "2",
            "journal_pages": "100-120",
            "conference": "",
            "conference_place": "",
            "conference_acronym": "",
            "conference_date": "",
            "publisher": "Test Publisher",
            "keywords": ["test", "journal"],
            "description": "Test Description",
            "access_right": "open",
            "language": "en",
            "notes": "Test Notes",
            "version": "1.0",
        }

        with patch("heritrace.apis.zenodo.get_zenodo_data", return_value=journal_data):
            url = f"https://doi.org/10.5281/zenodo.{record_id}"
            html = format_zenodo_source(url)

            # Verify we got valid HTML back with journal info
            assert html is not None
            assert '<a href="' in html
            assert 'class="zenodo-attribution"' in html
            assert "Test Journal Article" in html
            assert "Test Author" in html
            assert "2023, January 15" in html
            assert "Test Journal" in html
            assert "10" in html
            assert "(2)" in html
            assert ", 100-120" in html
            assert "Test Publisher" in html

            # Verify the extra metadata section
            assert '<div class="text-muted small mt-1">' in html
            assert "Type: publication (article)" in html

    def test_format_zenodo_source_with_software_data(self):
        """Test the format_zenodo_source function with software data."""
        # Mock a record with software data
        record_id = "7406075"

        # Create a patch for get_zenodo_data to return data with software info
        software_data = {
            "title": "Test Software",
            "authors": [{"name": "Test Author"}],
            "doi": "10.5281/zenodo.7406075",
            "publication_date": "2023-01-15",
            "record_id": record_id,
            "type": "software",
            "subtype": "",
            "journal": "",
            "journal_volume": "",
            "journal_issue": "",
            "journal_pages": "",
            "conference": "",
            "conference_place": "",
            "conference_acronym": "",
            "conference_date": "",
            "publisher": "Test Publisher",
            "keywords": ["test", "software"],
            "description": "Test Description",
            "access_right": "open",
            "language": "en",
            "notes": "Test Notes",
            "version": "1.0",
        }

        with patch("heritrace.apis.zenodo.get_zenodo_data", return_value=software_data):
            url = f"https://doi.org/10.5281/zenodo.{record_id}"
            html = format_zenodo_source(url)

            # Verify we got valid HTML back with software info
            assert html is not None
            assert '<a href="' in html
            assert 'class="zenodo-attribution"' in html
            assert "Test Software [Computer software]" in html
            assert "Test Author" in html
            assert "2023, January 15" in html
            assert "Test Publisher" in html

            # Verify the extra metadata section
            assert '<div class="text-muted small mt-1">' in html
            assert "Type: software" in html


class TestZenodoErrorHandling:
    """Test error handling in Zenodo API functions."""

    def test_make_request_with_retry_invalid_url(self):
        """Test make_request_with_retry with an invalid URL."""
        # This should raise a ZenodoRequestError
        with pytest.raises(ZenodoRequestError):
            make_request_with_retry(
                "https://nonexistent-domain-12345.org", {}, max_retries=1
            )

    def test_make_request_with_retry_rate_limit(self):
        """Test make_request_with_retry with a rate limit response."""

        # This test uses a real URL but mocks the response to simulate a rate limit
        class MockResponse:
            def __init__(self, status_code, headers=None):
                self.status_code = status_code
                self.headers = headers or {}

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise requests.exceptions.HTTPError(
                        f"HTTP Error: {self.status_code}"
                    )

            def json(self):
                return {"message": "Test response"}

        # Create a sequence of responses: first rate limited, then success
        responses = [
            MockResponse(429, {"Retry-After": "1"}),  # Rate limited
            MockResponse(200),  # Success
        ]

        # Use patch to mock the requests.get function
        with patch("requests.get", side_effect=responses):
            response = make_request_with_retry(
                "https://zenodo.org/api/records/7406075",
                {},
                max_retries=2,
                initial_delay=0.1,
            )
            assert response is not None

    def test_make_request_with_retry_server_error(self):
        """Test make_request_with_retry with a server error response."""

        # This test uses a real URL but mocks the response to simulate a server error
        class MockResponse:
            def __init__(self, status_code):
                self.status_code = status_code

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise requests.exceptions.HTTPError(
                        f"HTTP Error: {self.status_code}"
                    )

            def json(self):
                return {"message": "Test response"}

        # Create a sequence of responses: first server error, then success
        responses = [MockResponse(500), MockResponse(200)]  # Server error  # Success

        # Use patch to mock the requests.get function
        with patch("requests.get", side_effect=responses):
            # We expect this to raise a ZenodoRequestError for the 500 status code
            with pytest.raises(ZenodoRequestError):
                make_request_with_retry(
                    "https://zenodo.org/api/records/7406075",
                    {},
                    max_retries=1,
                    initial_delay=0.1,
                )

    def test_make_request_with_retry_connection_error(self):
        """Test make_request_with_retry with a connection error."""
        # This test mocks a connection error
        with patch(
            "requests.get",
            side_effect=requests.exceptions.ConnectionError("Connection error"),
        ):
            # We expect this to raise a ZenodoRequestError
            with pytest.raises(ZenodoRequestError):
                make_request_with_retry(
                    "https://zenodo.org/api/records/7406075",
                    {},
                    max_retries=1,
                    initial_delay=0.1,
                )

    def test_make_request_with_retry_timeout(self):
        """Test make_request_with_retry with a timeout error."""
        # This test mocks a timeout error
        with patch(
            "requests.get", side_effect=requests.exceptions.Timeout("Timeout error")
        ):
            # We expect this to raise a ZenodoRequestError
            with pytest.raises(ZenodoRequestError):
                make_request_with_retry(
                    "https://zenodo.org/api/records/7406075",
                    {},
                    max_retries=1,
                    initial_delay=0.1,
                )
