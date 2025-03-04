from datetime import timezone

import dateutil.parser


def convert_to_datetime(date_str, stringify=False):
    try:
        dt = dateutil.parser.parse(date_str)
        # Convert to UTC timezone regardless of input timezone
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc)
        else:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt if not stringify else dt.isoformat()
    except (ValueError, TypeError):
        return None
