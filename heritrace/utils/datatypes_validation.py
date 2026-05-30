# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import base64
import re
from datetime import datetime
from urllib.parse import urlparse

_BYTE_MIN = -128
_BYTE_MAX = 127
_SHORT_MIN = -32_768
_SHORT_MAX = 32_767
_INT_MIN = -2_147_483_648
_INT_MAX = 2_147_483_647
_UNSIGNED_BYTE_MAX = 255
_UNSIGNED_SHORT_MAX = 65_535
_UNSIGNED_INT_MAX = 4_294_967_295
_UNSIGNED_LONG_MAX = 18_446_744_073_709_551_615
_LONG_MIN = -9_223_372_036_854_775_808
_LONG_MAX = 9_223_372_036_854_775_807
_MAX_YEAR = 9999
_MIN_GREGORIAN_YEAR = 1582
_MAX_MONTH = 12
_MAX_HOUR = 23
_MAX_MINUTE = 59
_MAX_SECOND = 60


def validate_string(value: str) -> bool:
    try:
        value = str(value)
    except ValueError:
        return False
    else:
        return isinstance(value, str)


def validate_normalized_string(value: str) -> bool:
    try:
        return "\n" not in value and "\r" not in value and "\t" not in value
    except TypeError:
        return False


def validate_integer(value: str) -> bool:
    try:
        int(value)
    except (ValueError, TypeError):
        return False
    else:
        return True


def validate_positive_integer(value: str) -> bool:
    try:
        return int(value) > 0
    except (ValueError, TypeError):
        return False


def validate_negative_integer(value: str) -> bool:
    try:
        return int(value) < 0
    except (ValueError, TypeError):
        return False


def validate_non_negative_integer(value: str) -> bool:
    try:
        return int(value) >= 0
    except (ValueError, TypeError):
        return False


def validate_non_positive_integer(value: str) -> bool:
    try:
        return int(value) <= 0
    except (ValueError, TypeError):
        return False


def validate_byte(value: str) -> bool:
    try:
        val = int(value)
    except (ValueError, TypeError):
        return False
    else:
        return _BYTE_MIN <= val <= _BYTE_MAX


def validate_short(value: str) -> bool:
    try:
        val = int(value)
    except (ValueError, TypeError):
        return False
    else:
        return _SHORT_MIN <= val <= _SHORT_MAX


def validate_long(value: str) -> bool:
    try:
        val = int(value)
    except (ValueError, TypeError):
        return False
    else:
        return _INT_MIN <= val <= _INT_MAX


def validate_unsigned_byte(value: str) -> bool:
    try:
        val = int(value)
    except (ValueError, TypeError):
        return False
    else:
        return 0 <= val <= _UNSIGNED_BYTE_MAX


def validate_unsigned_short(value: str) -> bool:
    try:
        val = int(value)
    except (ValueError, TypeError):
        return False
    else:
        return 0 <= val <= _UNSIGNED_SHORT_MAX


def validate_unsigned_long(value: str) -> bool:
    try:
        val = int(value)
    except (ValueError, TypeError):
        return False
    else:
        return 0 <= val <= _UNSIGNED_INT_MAX


def validate_unsigned_int(value: str) -> bool:
    try:
        val = int(value)
    except (ValueError, TypeError):
        return False
    else:
        return 0 <= val <= _UNSIGNED_INT_MAX


def validate_float(value: str) -> bool:
    try:
        float(value)
    except (ValueError, TypeError):
        return False
    else:
        return True


def validate_double(value: str) -> bool:
    try:
        float(value)
    except (ValueError, TypeError):
        return False
    else:
        return True


def validate_decimal(value: str) -> bool:
    try:
        float(value)
    except (ValueError, TypeError):
        return False
    else:
        return True


def validate_duration(value: str) -> bool:
    try:
        duration_pattern = re.compile(
            r"^P(?=\d|T\d)(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+?)?)S)?)?$"
        )
        return bool(duration_pattern.match(value))
    except TypeError:
        return False


def validate_day_time_duration(value: str) -> bool:
    try:
        pattern = re.compile(r"^P(?:\d+D)?(?:T(?:\d+H)?(?:\d+M)?(?:\d+(?:\.\d+)?S)?)?$")
        return bool(pattern.match(value))
    except TypeError:
        return False


def validate_year_month_duration(value: str) -> bool:
    try:
        pattern = re.compile(r"^P(?:\d+Y)?(?:\d+M)?$")
        return bool(pattern.match(value))
    except TypeError:
        return False


def validate_g_year_month(value: str) -> bool:
    try:
        pattern = re.compile(r"^(\d{4})-(\d{2})$")
        match = pattern.match(value)
    except TypeError:
        return False
    else:
        if match:
            year, month = map(int, match.groups())
            return year <= _MAX_YEAR and 1 <= month <= _MAX_MONTH
        return False


def validate_g_year(value: str) -> bool:
    try:
        pattern = re.compile(r"^\d{4}$")
        match = pattern.match(value)
    except TypeError:
        return False
    else:
        if match:
            year = int(value)
            return _MIN_GREGORIAN_YEAR <= year <= _MAX_YEAR
        return False


def validate_date_time(value: str) -> bool:
    try:
        pattern = re.compile(
            r"^-?\d{4,}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$"
        )
        return bool(pattern.match(value))
    except TypeError:
        return False


def validate_date_time_stamp(value: str) -> bool:
    try:
        pattern = re.compile(
            r"^-?\d{4,}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(Z|[+-]\d{2}:\d{2})$"
        )
        return bool(pattern.match(value))
    except TypeError:
        return False


def validate_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return False
    else:
        return True


def validate_time(value: str) -> bool:
    try:
        return bool(re.match(r"^([01]\d|2[0-3]):?([0-5]\d):?([0-5]\d)$", value))
    except TypeError:
        return False


def validate_hour(value: str) -> bool:
    try:
        return 0 <= int(value) <= _MAX_HOUR
    except (ValueError, TypeError):
        return False


def validate_minute(value: str) -> bool:
    try:
        return 0 <= int(value) <= _MAX_MINUTE
    except (ValueError, TypeError):
        return False


def validate_second(value: str) -> bool:
    try:
        return 0 <= float(value) < _MAX_SECOND
    except (ValueError, TypeError):
        return False


def validate_timezone_offset(value: str) -> bool:
    try:
        pattern = re.compile(r"^[+-]\d{2}:\d{2}$")
        return bool(pattern.match(value))
    except TypeError:
        return False


def validate_boolean(value: str) -> bool:
    try:
        return value.lower() in ["true", "false"]
    except AttributeError:
        return False


def validate_hex_binary(value: str) -> bool:
    try:
        bytes.fromhex(value)
    except (ValueError, TypeError):
        return False
    else:
        return True


def validate_base64_binary(value: str) -> bool:
    try:
        base64.b64decode(value)
    except (ValueError, TypeError):
        return False
    else:
        return True


def validate_url(value: str) -> bool:
    try:
        result = urlparse(value)
        return all([result.scheme, result.netloc])
    except (ValueError, TypeError):
        return False


def validate_qname(value: str) -> bool:
    try:
        pattern = re.compile(r"^(?:[a-zA-Z_][\w.-]*:)?[a-zA-Z_][\w.-]*$")
        return bool(pattern.match(value))
    except TypeError:
        return False


def validate_entities(value: str) -> bool:
    try:
        entities = value.split()
        return all(re.match(r"^[a-zA-Z_][\w.-]*$", entity) for entity in entities)
    except (TypeError, AttributeError):
        return False


validate_entity = validate_entities


def validate_id(value: str) -> bool:
    try:
        return re.match(r"^[a-zA-Z_][\w.-]*$", value) is not None
    except TypeError:
        return False


validate_idref = validate_id
validate_idrefs = validate_entities
validate_ncname = validate_id


def validate_nmtoken(value: str) -> bool:
    try:
        return re.match(r"^[\w.-]+$", value) is not None
    except TypeError:
        return False


def validate_nmtokens(value: str) -> bool:
    try:
        tokens = value.split()
        return all(re.match(r"^[\w.-]+$", token) for token in tokens)
    except (TypeError, AttributeError):
        return False


validate_notation = validate_qname


def validate_name(value: str) -> bool:
    try:
        return re.match(r"^[a-zA-Z_:][\w.-]*$", value) is not None
    except TypeError:
        return False
