from datetime import datetime, timezone


def convert_to_datetime(date_str, stringify=False):
    try:
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt if not stringify else dt.isoformat()
    except ValueError:
        return None
