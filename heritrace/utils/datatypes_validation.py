import base64
import re
from datetime import datetime
from urllib.parse import urlparse


def validate_string(value):
    try:
        value = str(value)
        return isinstance(value, str)
    except ValueError:
        return False


def validate_normalizedString(value):
    try:
        return "\n" not in value and "\r" not in value and "\t" not in value
    except Exception:
        return False


def validate_integer(value):
    try:
        int(value)
        return True
    except ValueError:
        return False


def validate_positive_integer(value):
    try:
        return int(value) > 0
    except ValueError:
        return False


def validate_negative_integer(value):
    try:
        return int(value) < 0
    except ValueError:
        return False


def validate_non_negative_integer(value):
    try:
        return int(value) >= 0
    except ValueError:
        return False


def validate_non_positive_integer(value):
    try:
        return int(value) <= 0
    except ValueError:
        return False


def validate_byte(value):
    try:
        val = int(value)
        return -128 <= val <= 127
    except ValueError:
        return False


def validate_short(value):
    try:
        val = int(value)
        return -32_768 <= val <= 32_767
    except ValueError:
        return False


def validate_long(value):
    try:
        val = int(value)
        return -2_147_483_648 <= val <= 2_147_483_647
    except ValueError:
        return False


def validate_unsigned_byte(value):
    try:
        val = int(value)
        return 0 <= val <= 255
    except ValueError:
        return False


def validate_unsigned_short(value):
    try:
        val = int(value)
        return 0 <= val <= 65_535
    except ValueError:
        return False


def validate_unsigned_long(value):
    try:
        val = int(value)
        return 0 <= val <= 4_294_967_295
    except ValueError:
        return False


def validate_unsigned_int(value):
    try:
        val = int(value)
        return 0 <= val <= 4_294_967_295
    except ValueError:
        return False


def validate_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def validate_double(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def validate_decimal(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def validate_duration(value):
    try:
        duration_pattern = re.compile(
            r"^P(?=\d|T\d)(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+?)?)S)?)?$"
        )
        return bool(duration_pattern.match(value))
    except Exception:
        return False


def validate_dayTimeDuration(value):
    try:
        dayTimeDuration_pattern = re.compile(
            r"^P(?:\d+D)?(?:T(?:\d+H)?(?:\d+M)?(?:\d+(?:\.\d+)?S)?)?$"
        )
        return bool(dayTimeDuration_pattern.match(value))
    except Exception:
        return False


def validate_yearMonthDuration(value):
    try:
        yearMonthDuration_pattern = re.compile(r"^P(?:\d+Y)?(?:\d+M)?$")
        return bool(yearMonthDuration_pattern.match(value))
    except Exception:
        return False


def validate_gYearMonth(value):
    try:
        pattern = re.compile(r"^(\d{4})-(\d{2})$")
        match = pattern.match(value)
        if match:
            year, month = map(int, match.groups())
            return year <= 9999 and 1 <= month <= 12
        return False
    except Exception:
        return False


def validate_gYear(value):
    try:
        pattern = re.compile(r"^\d{4}$")
        if pattern.match(value):
            year = int(value)
            return 1582 <= year <= 9999
        return False
    except Exception:
        return False


def validate_dateTime(value):
    try:
        pattern = re.compile(
            r"^-?\d{4,}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$"
        )
        return bool(pattern.match(value))
    except Exception:
        return False


def validate_dateTimeStamp(value):
    try:
        pattern = re.compile(
            r"^-?\d{4,}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(Z|[+-]\d{2}:\d{2})$"
        )
        return bool(pattern.match(value))
    except Exception:
        return False


def validate_date(value):
    try:
        datetime.strptime(value, "%Y-%m-%d").date()
        return True
    except ValueError:
        return False


def validate_time(value):
    try:
        return bool(re.match(r"^([01]\d|2[0-3]):?([0-5]\d):?([0-5]\d)$", value))
    except Exception:
        return False


def validate_hour(value):
    try:
        return 0 <= int(value) <= 23
    except ValueError:
        return False


def validate_minute(value):
    try:
        return 0 <= int(value) <= 59
    except ValueError:
        return False


def validate_second(value):
    try:
        return 0 <= float(value) < 60
    except ValueError:
        return False


def validate_timezoneOffset(value):
    try:
        timezoneOffset_pattern = re.compile(r"^[+-]\d{2}:\d{2}$")
        return bool(timezoneOffset_pattern.match(value))
    except Exception:
        return False


def validate_boolean(value):
    try:
        return value.lower() in ["true", "false"]
    except Exception:
        return False


def validate_hexBinary(value):
    try:
        bytes.fromhex(value)
        return True
    except ValueError:
        return False


def validate_base64Binary(value):
    try:
        base64.b64decode(value)
        return True
    except ValueError:
        return False


def validate_url(value):
    try:
        result = urlparse(value)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def validate_QName(value):
    try:
        QName_pattern = re.compile(r"^(?:[a-zA-Z_][\w.-]*:)?[a-zA-Z_][\w.-]*$")
        return bool(QName_pattern.match(value))
    except Exception:
        return False


def validate_ENTITIES(value):
    try:
        entities = value.split()
        return all(re.match(r"^[a-zA-Z_][\w.-]*$", entity) for entity in entities)
    except Exception:
        return False


validate_ENTITY = validate_ENTITIES


def validate_ID(value):
    try:
        return re.match(r"^[a-zA-Z_][\w.-]*$", value) is not None
    except Exception:
        return False


validate_IDREF = validate_ID
validate_IDREFS = validate_ENTITIES
validate_NCName = validate_ID


def validate_NMTOKEN(value):
    try:
        return re.match(r"^[\w.-]+$", value) is not None
    except Exception:
        return False


def validate_NMTOKENS(value):
    try:
        tokens = value.split()
        return all(re.match(r"^[\w.-]+$", token) for token in tokens)
    except Exception:
        return False


validate_NOTATION = validate_QName


def validate_Name(value):
    try:
        return re.match(r"^[a-zA-Z_:][\w.-]*$", value) is not None
    except Exception:
        return False
