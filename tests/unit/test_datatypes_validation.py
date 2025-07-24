"""
Tests for the datatypes validation module.
"""

from heritrace.utils.datatypes_validation import (
    validate_base64Binary, validate_boolean, validate_byte, validate_date,
    validate_dateTime, validate_dateTimeStamp, validate_dayTimeDuration,
    validate_decimal, validate_double, validate_duration, validate_ENTITIES,
    validate_ENTITY, validate_float, validate_gYear, validate_gYearMonth,
    validate_hexBinary, validate_hour, validate_ID, validate_IDREF,
    validate_IDREFS, validate_integer, validate_long, validate_minute,
    validate_Name, validate_NCName, validate_negative_integer,
    validate_NMTOKEN, validate_NMTOKENS, validate_non_negative_integer,
    validate_non_positive_integer, validate_normalizedString,
    validate_NOTATION, validate_positive_integer, validate_QName,
    validate_second, validate_short, validate_string, validate_time,
    validate_timezoneOffset, validate_unsigned_byte, validate_unsigned_int,
    validate_unsigned_long, validate_unsigned_short, validate_url,
    validate_yearMonthDuration)


class TestValidateString:
    def test_valid_string(self):
        assert validate_string("hello") is True
        assert validate_string("") is True
        assert validate_string(123) is True

    def test_invalid_string(self):
        # Test ValueError scenario with mock that raises ValueError
        class BadStr:
            def __str__(self):
                raise ValueError()
        assert validate_string(BadStr()) is False


class TestValidateNormalizedString:
    def test_valid_normalized_string(self):
        assert validate_normalizedString("hello world") is True
        assert validate_normalizedString("") is True

    def test_invalid_normalized_string(self):
        assert validate_normalizedString("hello\nworld") is False
        assert validate_normalizedString("hello\rworld") is False
        assert validate_normalizedString("hello\tworld") is False

    def test_exception_handling(self):
        assert validate_normalizedString(None) is False


class TestValidateInteger:
    def test_valid_integer(self):
        assert validate_integer("123") is True
        assert validate_integer("-456") is True
        assert validate_integer("0") is True

    def test_invalid_integer(self):
        assert validate_integer("abc") is False
        assert validate_integer("12.34") is False
        assert validate_integer("") is False


class TestValidatePositiveInteger:
    def test_valid_positive_integer(self):
        assert validate_positive_integer("1") is True
        assert validate_positive_integer("999") is True

    def test_invalid_positive_integer(self):
        assert validate_positive_integer("0") is False
        assert validate_positive_integer("-1") is False
        assert validate_positive_integer("abc") is False


class TestValidateNegativeInteger:
    def test_valid_negative_integer(self):
        assert validate_negative_integer("-1") is True
        assert validate_negative_integer("-999") is True

    def test_invalid_negative_integer(self):
        assert validate_negative_integer("0") is False
        assert validate_negative_integer("1") is False
        assert validate_negative_integer("abc") is False


class TestValidateNonNegativeInteger:
    def test_valid_non_negative_integer(self):
        assert validate_non_negative_integer("0") is True
        assert validate_non_negative_integer("1") is True
        assert validate_non_negative_integer("999") is True

    def test_invalid_non_negative_integer(self):
        assert validate_non_negative_integer("-1") is False
        assert validate_non_negative_integer("abc") is False


class TestValidateNonPositiveInteger:
    def test_valid_non_positive_integer(self):
        assert validate_non_positive_integer("0") is True
        assert validate_non_positive_integer("-1") is True
        assert validate_non_positive_integer("-999") is True

    def test_invalid_non_positive_integer(self):
        assert validate_non_positive_integer("1") is False
        assert validate_non_positive_integer("abc") is False


class TestValidateByte:
    def test_valid_byte(self):
        assert validate_byte("127") is True
        assert validate_byte("-128") is True
        assert validate_byte("0") is True

    def test_invalid_byte(self):
        assert validate_byte("128") is False
        assert validate_byte("-129") is False
        assert validate_byte("abc") is False


class TestValidateShort:
    def test_valid_short(self):
        assert validate_short("32767") is True
        assert validate_short("-32768") is True
        assert validate_short("0") is True

    def test_invalid_short(self):
        assert validate_short("32768") is False
        assert validate_short("-32769") is False
        assert validate_short("abc") is False


class TestValidateLong:
    def test_valid_long(self):
        assert validate_long("2147483647") is True
        assert validate_long("-2147483648") is True
        assert validate_long("0") is True

    def test_invalid_long(self):
        assert validate_long("2147483648") is False
        assert validate_long("-2147483649") is False
        assert validate_long("abc") is False


class TestValidateUnsignedByte:
    def test_valid_unsigned_byte(self):
        assert validate_unsigned_byte("255") is True
        assert validate_unsigned_byte("0") is True

    def test_invalid_unsigned_byte(self):
        assert validate_unsigned_byte("256") is False
        assert validate_unsigned_byte("-1") is False
        assert validate_unsigned_byte("abc") is False


class TestValidateUnsignedShort:
    def test_valid_unsigned_short(self):
        assert validate_unsigned_short("65535") is True
        assert validate_unsigned_short("0") is True

    def test_invalid_unsigned_short(self):
        assert validate_unsigned_short("65536") is False
        assert validate_unsigned_short("-1") is False
        assert validate_unsigned_short("abc") is False


class TestValidateUnsignedLong:
    def test_valid_unsigned_long(self):
        assert validate_unsigned_long("4294967295") is True
        assert validate_unsigned_long("0") is True

    def test_invalid_unsigned_long(self):
        assert validate_unsigned_long("4294967296") is False
        assert validate_unsigned_long("-1") is False
        assert validate_unsigned_long("abc") is False


class TestValidateUnsignedInt:
    def test_valid_unsigned_int(self):
        assert validate_unsigned_int("4294967295") is True
        assert validate_unsigned_int("0") is True

    def test_invalid_unsigned_int(self):
        assert validate_unsigned_int("4294967296") is False
        assert validate_unsigned_int("-1") is False
        assert validate_unsigned_int("abc") is False


class TestValidateFloat:
    def test_valid_float(self):
        assert validate_float("123.45") is True
        assert validate_float("123") is True
        assert validate_float("-123.45") is True

    def test_invalid_float(self):
        assert validate_float("abc") is False


class TestValidateDouble:
    def test_valid_double(self):
        assert validate_double("123.45") is True
        assert validate_double("123") is True
        assert validate_double("-123.45") is True

    def test_invalid_double(self):
        assert validate_double("abc") is False


class TestValidateDecimal:
    def test_valid_decimal(self):
        assert validate_decimal("123.45") is True
        assert validate_decimal("123") is True
        assert validate_decimal("-123.45") is True

    def test_invalid_decimal(self):
        assert validate_decimal("abc") is False


class TestValidateDuration:
    def test_valid_duration(self):
        assert validate_duration("P1Y2M3DT4H5M6S") is True
        assert validate_duration("PT1H") is True
        assert validate_duration("P1D") is True

    def test_invalid_duration(self):
        assert validate_duration("invalid") is False
        assert validate_duration("P") is False

    def test_exception_handling(self):
        assert validate_duration(None) is False


class TestValidateDayTimeDuration:
    def test_valid_day_time_duration(self):
        assert validate_dayTimeDuration("P1DT1H1M1S") is True
        assert validate_dayTimeDuration("PT1H") is True
        assert validate_dayTimeDuration("P1D") is True

    def test_invalid_day_time_duration(self):
        assert validate_dayTimeDuration("P1Y") is False
        assert validate_dayTimeDuration("invalid") is False

    def test_exception_handling(self):
        assert validate_dayTimeDuration(None) is False


class TestValidateYearMonthDuration:
    def test_valid_year_month_duration(self):
        assert validate_yearMonthDuration("P1Y2M") is True
        assert validate_yearMonthDuration("P1Y") is True
        assert validate_yearMonthDuration("P2M") is True

    def test_invalid_year_month_duration(self):
        assert validate_yearMonthDuration("P1D") is False
        assert validate_yearMonthDuration("invalid") is False

    def test_exception_handling(self):
        assert validate_yearMonthDuration(None) is False


class TestValidateGYearMonth:
    def test_valid_g_year_month(self):
        assert validate_gYearMonth("2023-12") is True
        assert validate_gYearMonth("2023-01") is True

    def test_invalid_g_year_month(self):
        assert validate_gYearMonth("2023-13") is False
        assert validate_gYearMonth("2023-00") is False
        assert validate_gYearMonth("invalid") is False

    def test_exception_handling(self):
        assert validate_gYearMonth(None) is False


class TestValidateGYear:
    def test_valid_g_year(self):
        assert validate_gYear("2023") is True
        assert validate_gYear("1582") is True
        assert validate_gYear("9999") is True

    def test_invalid_g_year(self):
        assert validate_gYear("1581") is False
        assert validate_gYear("10000") is False
        assert validate_gYear("invalid") is False

    def test_exception_handling(self):
        assert validate_gYear(None) is False


class TestValidateDateTime:
    def test_valid_date_time(self):
        assert validate_dateTime("2023-12-25T10:30:00") is True
        assert validate_dateTime("2023-12-25T10:30:00.123") is True
        assert validate_dateTime("2023-12-25T10:30:00Z") is True
        assert validate_dateTime("2023-12-25T10:30:00+05:30") is True

    def test_invalid_date_time(self):
        assert validate_dateTime("invalid") is False
        assert validate_dateTime("2023-12-25") is False

    def test_exception_handling(self):
        assert validate_dateTime(None) is False


class TestValidateDateTimeStamp:
    def test_valid_date_time_stamp(self):
        assert validate_dateTimeStamp("2023-12-25T10:30:00Z") is True
        assert validate_dateTimeStamp("2023-12-25T10:30:00+05:30") is True

    def test_invalid_date_time_stamp(self):
        assert validate_dateTimeStamp("2023-12-25T10:30:00") is False
        assert validate_dateTimeStamp("invalid") is False

    def test_exception_handling(self):
        assert validate_dateTimeStamp(None) is False


class TestValidateDate:
    def test_valid_date(self):
        assert validate_date("2023-12-25") is True
        assert validate_date("2023-01-01") is True

    def test_invalid_date(self):
        assert validate_date("2023-13-01") is False
        assert validate_date("invalid") is False


class TestValidateTime:
    def test_valid_time(self):
        assert validate_time("10:30:45") is True
        assert validate_time("23:59:59") is True
        assert validate_time("00:00:00") is True

    def test_invalid_time(self):
        assert validate_time("25:00:00") is False
        assert validate_time("invalid") is False

    def test_exception_handling(self):
        assert validate_time(None) is False


class TestValidateHour:
    def test_valid_hour(self):
        assert validate_hour("0") is True
        assert validate_hour("23") is True

    def test_invalid_hour(self):
        assert validate_hour("24") is False
        assert validate_hour("-1") is False
        assert validate_hour("abc") is False


class TestValidateMinute:
    def test_valid_minute(self):
        assert validate_minute("0") is True
        assert validate_minute("59") is True

    def test_invalid_minute(self):
        assert validate_minute("60") is False
        assert validate_minute("-1") is False
        assert validate_minute("abc") is False


class TestValidateSecond:
    def test_valid_second(self):
        assert validate_second("0") is True
        assert validate_second("59.999") is True

    def test_invalid_second(self):
        assert validate_second("60") is False
        assert validate_second("-1") is False
        assert validate_second("abc") is False


class TestValidateTimezoneOffset:
    def test_valid_timezone_offset(self):
        assert validate_timezoneOffset("+05:30") is True
        assert validate_timezoneOffset("-08:00") is True

    def test_invalid_timezone_offset(self):
        assert validate_timezoneOffset("invalid") is False
        assert validate_timezoneOffset("+5:30") is False

    def test_exception_handling(self):
        assert validate_timezoneOffset(None) is False


class TestValidateBoolean:
    def test_valid_boolean(self):
        assert validate_boolean("true") is True
        assert validate_boolean("false") is True
        assert validate_boolean("TRUE") is True
        assert validate_boolean("FALSE") is True

    def test_invalid_boolean(self):
        assert validate_boolean("yes") is False
        assert validate_boolean("1") is False

    def test_exception_handling(self):
        assert validate_boolean(None) is False


class TestValidateHexBinary:
    def test_valid_hex_binary(self):
        assert validate_hexBinary("48656c6c6f") is True
        assert validate_hexBinary("") is True

    def test_invalid_hex_binary(self):
        assert validate_hexBinary("xyz") is False
        assert validate_hexBinary("48656c6c6g") is False


class TestValidateBase64Binary:
    def test_valid_base64_binary(self):
        assert validate_base64Binary("SGVsbG8=") is True
        assert validate_base64Binary("") is True

    def test_invalid_base64_binary(self):
        assert validate_base64Binary("invalid!@#") is False


class TestValidateUrl:
    def test_valid_url(self):
        assert validate_url("https://example.com") is True
        assert validate_url("http://example.com/path") is True

    def test_invalid_url(self):
        assert validate_url("not-a-url") is False
        assert validate_url("://example.com") is False


class TestValidateQName:
    def test_valid_qname(self):
        assert validate_QName("prefix:localname") is True
        assert validate_QName("localname") is True
        assert validate_QName("_localname") is True

    def test_invalid_qname(self):
        assert validate_QName("123invalid") is False
        assert validate_QName("") is False

    def test_exception_handling(self):
        assert validate_QName(None) is False


class TestValidateEntities:
    def test_valid_entities(self):
        assert validate_ENTITIES("entity1 entity2") is True
        assert validate_ENTITIES("single") is True

    def test_invalid_entities(self):
        assert validate_ENTITIES("123invalid entity2") is False
        assert validate_ENTITIES("") is True  # Empty string splits to empty list

    def test_exception_handling(self):
        assert validate_ENTITIES(None) is False


class TestValidateEntity:
    def test_validate_entity_alias(self):
        # Test that validate_ENTITY is an alias for validate_ENTITIES
        assert validate_ENTITY == validate_ENTITIES


class TestValidateId:
    def test_valid_id(self):
        assert validate_ID("validId") is True
        assert validate_ID("_validId") is True

    def test_invalid_id(self):
        assert validate_ID("123invalid") is False
        assert validate_ID("") is False

    def test_exception_handling(self):
        assert validate_ID(None) is False


class TestValidateAliases:
    def test_idref_alias(self):
        assert validate_IDREF == validate_ID

    def test_idrefs_alias(self):
        assert validate_IDREFS == validate_ENTITIES

    def test_ncname_alias(self):
        assert validate_NCName == validate_ID


class TestValidateNmtoken:
    def test_valid_nmtoken(self):
        assert validate_NMTOKEN("token123") is True
        assert validate_NMTOKEN("123") is True

    def test_invalid_nmtoken(self):
        assert validate_NMTOKEN("") is False
        assert validate_NMTOKEN("token with space") is False

    def test_exception_handling(self):
        assert validate_NMTOKEN(None) is False


class TestValidateNmtokens:
    def test_valid_nmtokens(self):
        assert validate_NMTOKENS("token1 token2") is True
        assert validate_NMTOKENS("single") is True

    def test_invalid_nmtokens(self):
        assert validate_NMTOKENS("valid invalid@token") is False

    def test_exception_handling(self):
        assert validate_NMTOKENS(None) is False


class TestValidateNotation:
    def test_notation_alias(self):
        assert validate_NOTATION == validate_QName


class TestValidateName:
    def test_valid_name(self):
        assert validate_Name("validName") is True
        assert validate_Name("_validName") is True
        assert validate_Name(":validName") is True

    def test_invalid_name(self):
        assert validate_Name("123invalid") is False
        assert validate_Name("") is False

    def test_exception_handling(self):
        assert validate_Name(None) is False