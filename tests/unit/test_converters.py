from datetime import timezone

from heritrace.utils.converters import convert_to_datetime


def test_convert_to_datetime():
    """Test the convert_to_datetime function."""
    # Test with a datetime string that has timezone info
    dt_with_tz = convert_to_datetime("2023-01-01T12:00:00+00:00")
    assert dt_with_tz.tzinfo is not None
    assert dt_with_tz.tzinfo == timezone.utc

    # Test with a datetime string that has no timezone info
    # This tests the specific case where tzinfo is None and gets replaced with UTC
    dt_without_tz = convert_to_datetime("2023-01-01T12:00:00")
    assert dt_without_tz.tzinfo is not None
    assert dt_without_tz.tzinfo == timezone.utc

    # Test with stringify=True
    dt_str = convert_to_datetime("2023-01-01T12:00:00", stringify=True)
    assert isinstance(dt_str, str)
    assert dt_str.endswith("+00:00")

    # Test with invalid datetime string
    assert convert_to_datetime("not-a-date") is None
