# SPDX-FileCopyrightText: 2024-2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from datetime import datetime, timezone

import dateutil.parser


def convert_to_datetime(date_str: str) -> datetime | None:
    try:
        dt = dateutil.parser.parse(date_str)
    except (ValueError, TypeError):
        return None
    else:
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc)
        else:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
