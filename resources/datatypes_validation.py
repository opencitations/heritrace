import base64
import re
from datetime import datetime
from urllib.parse import urlparse


def validate_string(value):
    try:
        value = str(value)
    except ValueError:
        return False
    return isinstance(value, str)

def validate_normalizedString(value):
    return '\n' not in value and '\r' not in value and '\t' not in value

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
    duration_pattern = re.compile(r'^P(?=\d|T\d)(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$')
    return bool(duration_pattern.match(value))

def validate_dayTimeDuration(value):
    dayTimeDuration_pattern = re.compile(r'^P(?:\d+D)?(?:T(?:\d+H)?(?:\d+M)?(?:\d+(?:\.\d+)?S)?)?$')
    return bool(dayTimeDuration_pattern.match(value))

def validate_yearMonthDuration(value):
    yearMonthDuration_pattern = re.compile(r'^P(?:\d+Y)?(?:\d+M)?$')
    return bool(yearMonthDuration_pattern.match(value))

import re

def validate_gYearMonth(value):
    pattern = re.compile(r'^(\d{4})-(\d{2})$')
    match = pattern.match(value)
    if match:
        year, month = map(int, match.groups())
        if 1582 <= year <= 9999 and 1 <= month <= 12:
            return True
    return False

def validate_gYear(value):
    pattern = re.compile(r'^\d{4}$')
    if pattern.match(value):
        year = int(value)
        if 1582 <= year <= 9999:
            return True
    return False

def validate_dateTime(value):
    pattern = re.compile(
        r'^-?\d{4,}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$'
    )
    return bool(pattern.match(value))

def validate_dateTimeStamp(value):
    pattern = re.compile(
        r'^-?\d{4,}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(Z|[+-]\d{2}:\d{2})$'
    )
    return bool(pattern.match(value))

def validate_date(value):
    try:
        datetime.strptime(value, '%Y-%m-%d').date()
        return True
    except ValueError:
        return False

def validate_time(value):
    return bool(re.match(r'^([01]\d|2[0-3]):?([0-5]\d):?([0-5]\d)$', value))

def validate_hour(value):
    return 0 <= int(value) <= 23

def validate_minute(value):
    return 0 <= int(value) <= 59

def validate_second(value):
    return 0 <= float(value) < 60

def validate_timezoneOffset(value):
    timezoneOffset_pattern = re.compile(r'^[+-]\d{2}:\d{2}$')
    return bool(timezoneOffset_pattern.match(value))

def validate_boolean(value):
    return value.lower() in ['true', 'false']

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
    QName_pattern = re.compile(r'^(?:[a-zA-Z_][\w.-]*:)?[a-zA-Z_][\w.-]*$')
    return bool(QName_pattern.match(value))

def validate_ENTITIES(value):
    entities = value.split()
    return all(re.match(r'^[a-zA-Z_][\w.-]*$', entity) for entity in entities)

validate_ENTITY = validate_ENTITIES

def validate_ID(value):
    return re.match(r'^[a-zA-Z_][\w.-]*$', value) is not None

validate_IDREF = validate_ID
validate_IDREFS = validate_ENTITIES
validate_NCName = validate_ID

def validate_NMTOKEN(value):
    return re.match(r'^[\w.-]+$', value) is not None

def validate_NMTOKENS(value):
    tokens = value.split()
    return all(re.match(r'^[\w.-]+$', token) for token in tokens)

validate_NOTATION = validate_QName

def validate_Name(value):
    return re.match(r'^[a-zA-Z_:][\w.-]*$', value) is not None