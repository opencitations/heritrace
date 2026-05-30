# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from heritrace.utils.datatypes_validation import (
    validate_base64_binary,
    validate_boolean,
    validate_byte,
    validate_date,
    validate_date_time,
    validate_date_time_stamp,
    validate_day_time_duration,
    validate_decimal,
    validate_double,
    validate_duration,
    validate_entities,
    validate_entity,
    validate_float,
    validate_g_year,
    validate_g_year_month,
    validate_hex_binary,
    validate_hour,
    validate_id,
    validate_idref,
    validate_idrefs,
    validate_integer,
    validate_long,
    validate_minute,
    validate_name,
    validate_ncname,
    validate_negative_integer,
    validate_nmtoken,
    validate_nmtokens,
    validate_non_negative_integer,
    validate_non_positive_integer,
    validate_normalized_string,
    validate_notation,
    validate_positive_integer,
    validate_qname,
    validate_second,
    validate_short,
    validate_string,
    validate_time,
    validate_timezone_offset,
    validate_unsigned_byte,
    validate_unsigned_int,
    validate_unsigned_long,
    validate_unsigned_short,
    validate_url,
    validate_year_month_duration,
)


class TestValidateString:
    def test_valid_string(self) -> None:
        assert validate_string("hello") is True
        assert validate_string("") is True
        assert validate_string(123) is True

    def test_invalid_string(self) -> None:
        class BadStr:
            def __str__(self) -> str:
                raise ValueError

        assert validate_string(BadStr()) is False


class TestValidateNormalizedString:
    def test_valid_normalized_string(self) -> None:
        assert validate_normalized_string("hello world") is True
        assert validate_normalized_string("") is True

    def test_invalid_normalized_string(self) -> None:
        assert validate_normalized_string("hello\nworld") is False
        assert validate_normalized_string("hello\rworld") is False
        assert validate_normalized_string("hello\tworld") is False

    def test_exception_handling(self) -> None:
        assert validate_normalized_string(None) is False


class TestValidateInteger:
    def test_valid_integer(self) -> None:
        assert validate_integer("123") is True
        assert validate_integer("-456") is True
        assert validate_integer("0") is True

    def test_invalid_integer(self) -> None:
        assert validate_integer("abc") is False
        assert validate_integer("12.34") is False
        assert validate_integer("") is False


class TestValidatePositiveInteger:
    def test_valid_positive_integer(self) -> None:
        assert validate_positive_integer("1") is True
        assert validate_positive_integer("999") is True

    def test_invalid_positive_integer(self) -> None:
        assert validate_positive_integer("0") is False
        assert validate_positive_integer("-1") is False
        assert validate_positive_integer("abc") is False


class TestValidateNegativeInteger:
    def test_valid_negative_integer(self) -> None:
        assert validate_negative_integer("-1") is True
        assert validate_negative_integer("-999") is True

    def test_invalid_negative_integer(self) -> None:
        assert validate_negative_integer("0") is False
        assert validate_negative_integer("1") is False
        assert validate_negative_integer("abc") is False


class TestValidateNonNegativeInteger:
    def test_valid_non_negative_integer(self) -> None:
        assert validate_non_negative_integer("0") is True
        assert validate_non_negative_integer("1") is True
        assert validate_non_negative_integer("999") is True

    def test_invalid_non_negative_integer(self) -> None:
        assert validate_non_negative_integer("-1") is False
        assert validate_non_negative_integer("abc") is False


class TestValidateNonPositiveInteger:
    def test_valid_non_positive_integer(self) -> None:
        assert validate_non_positive_integer("0") is True
        assert validate_non_positive_integer("-1") is True
        assert validate_non_positive_integer("-999") is True

    def test_invalid_non_positive_integer(self) -> None:
        assert validate_non_positive_integer("1") is False
        assert validate_non_positive_integer("abc") is False


class TestValidateByte:
    def test_valid_byte(self) -> None:
        assert validate_byte("127") is True
        assert validate_byte("-128") is True
        assert validate_byte("0") is True

    def test_invalid_byte(self) -> None:
        assert validate_byte("128") is False
        assert validate_byte("-129") is False
        assert validate_byte("abc") is False


class TestValidateShort:
    def test_valid_short(self) -> None:
        assert validate_short("32767") is True
        assert validate_short("-32768") is True
        assert validate_short("0") is True

    def test_invalid_short(self) -> None:
        assert validate_short("32768") is False
        assert validate_short("-32769") is False
        assert validate_short("abc") is False


class TestValidateLong:
    def test_valid_long(self) -> None:
        assert validate_long("2147483647") is True
        assert validate_long("-2147483648") is True
        assert validate_long("0") is True

    def test_invalid_long(self) -> None:
        assert validate_long("2147483648") is False
        assert validate_long("-2147483649") is False
        assert validate_long("abc") is False


class TestValidateUnsignedByte:
    def test_valid_unsigned_byte(self) -> None:
        assert validate_unsigned_byte("255") is True
        assert validate_unsigned_byte("0") is True

    def test_invalid_unsigned_byte(self) -> None:
        assert validate_unsigned_byte("256") is False
        assert validate_unsigned_byte("-1") is False
        assert validate_unsigned_byte("abc") is False


class TestValidateUnsignedShort:
    def test_valid_unsigned_short(self) -> None:
        assert validate_unsigned_short("65535") is True
        assert validate_unsigned_short("0") is True

    def test_invalid_unsigned_short(self) -> None:
        assert validate_unsigned_short("65536") is False
        assert validate_unsigned_short("-1") is False
        assert validate_unsigned_short("abc") is False


class TestValidateUnsignedLong:
    def test_valid_unsigned_long(self) -> None:
        assert validate_unsigned_long("4294967295") is True
        assert validate_unsigned_long("0") is True

    def test_invalid_unsigned_long(self) -> None:
        assert validate_unsigned_long("4294967296") is False
        assert validate_unsigned_long("-1") is False
        assert validate_unsigned_long("abc") is False


class TestValidateUnsignedInt:
    def test_valid_unsigned_int(self) -> None:
        assert validate_unsigned_int("4294967295") is True
        assert validate_unsigned_int("0") is True

    def test_invalid_unsigned_int(self) -> None:
        assert validate_unsigned_int("4294967296") is False
        assert validate_unsigned_int("-1") is False
        assert validate_unsigned_int("abc") is False


class TestValidateFloat:
    def test_valid_float(self) -> None:
        assert validate_float("123.45") is True
        assert validate_float("123") is True
        assert validate_float("-123.45") is True

    def test_invalid_float(self) -> None:
        assert validate_float("abc") is False


class TestValidateDouble:
    def test_valid_double(self) -> None:
        assert validate_double("123.45") is True
        assert validate_double("123") is True
        assert validate_double("-123.45") is True

    def test_invalid_double(self) -> None:
        assert validate_double("abc") is False


class TestValidateDecimal:
    def test_valid_decimal(self) -> None:
        assert validate_decimal("123.45") is True
        assert validate_decimal("123") is True
        assert validate_decimal("-123.45") is True

    def test_invalid_decimal(self) -> None:
        assert validate_decimal("abc") is False


class TestValidateDuration:
    def test_valid_duration(self) -> None:
        assert validate_duration("P1Y2M3DT4H5M6S") is True
        assert validate_duration("PT1H") is True
        assert validate_duration("P1D") is True

    def test_invalid_duration(self) -> None:
        assert validate_duration("invalid") is False
        assert validate_duration("P") is False

    def test_exception_handling(self) -> None:
        assert validate_duration(None) is False


class TestValidateDayTimeDuration:
    def test_valid_day_time_duration(self) -> None:
        assert validate_day_time_duration("P1DT1H1M1S") is True
        assert validate_day_time_duration("PT1H") is True
        assert validate_day_time_duration("P1D") is True

    def test_invalid_day_time_duration(self) -> None:
        assert validate_day_time_duration("P1Y") is False
        assert validate_day_time_duration("invalid") is False

    def test_exception_handling(self) -> None:
        assert validate_day_time_duration(None) is False


class TestValidateYearMonthDuration:
    def test_valid_year_month_duration(self) -> None:
        assert validate_year_month_duration("P1Y2M") is True
        assert validate_year_month_duration("P1Y") is True
        assert validate_year_month_duration("P2M") is True

    def test_invalid_year_month_duration(self) -> None:
        assert validate_year_month_duration("P1D") is False
        assert validate_year_month_duration("invalid") is False

    def test_exception_handling(self) -> None:
        assert validate_year_month_duration(None) is False


class TestValidateGYearMonth:
    def test_valid_g_year_month(self) -> None:
        assert validate_g_year_month("2023-12") is True
        assert validate_g_year_month("2023-01") is True

    def test_invalid_g_year_month(self) -> None:
        assert validate_g_year_month("2023-13") is False
        assert validate_g_year_month("2023-00") is False
        assert validate_g_year_month("invalid") is False

    def test_exception_handling(self) -> None:
        assert validate_g_year_month(None) is False


class TestValidateGYear:
    def test_valid_g_year(self) -> None:
        assert validate_g_year("2023") is True
        assert validate_g_year("1582") is True
        assert validate_g_year("9999") is True

    def test_invalid_g_year(self) -> None:
        assert validate_g_year("1581") is False
        assert validate_g_year("10000") is False
        assert validate_g_year("invalid") is False

    def test_exception_handling(self) -> None:
        assert validate_g_year(None) is False


class TestValidateDateTime:
    def test_valid_date_time(self) -> None:
        assert validate_date_time("2023-12-25T10:30:00") is True
        assert validate_date_time("2023-12-25T10:30:00.123") is True
        assert validate_date_time("2023-12-25T10:30:00Z") is True
        assert validate_date_time("2023-12-25T10:30:00+05:30") is True

    def test_invalid_date_time(self) -> None:
        assert validate_date_time("invalid") is False
        assert validate_date_time("2023-12-25") is False

    def test_exception_handling(self) -> None:
        assert validate_date_time(None) is False


class TestValidateDateTimeStamp:
    def test_valid_date_time_stamp(self) -> None:
        assert validate_date_time_stamp("2023-12-25T10:30:00Z") is True
        assert validate_date_time_stamp("2023-12-25T10:30:00+05:30") is True

    def test_invalid_date_time_stamp(self) -> None:
        assert validate_date_time_stamp("2023-12-25T10:30:00") is False
        assert validate_date_time_stamp("invalid") is False

    def test_exception_handling(self) -> None:
        assert validate_date_time_stamp(None) is False


class TestValidateDate:
    def test_valid_date(self) -> None:
        assert validate_date("2023-12-25") is True
        assert validate_date("2023-01-01") is True

    def test_invalid_date(self) -> None:
        assert validate_date("2023-13-01") is False
        assert validate_date("invalid") is False


class TestValidateTime:
    def test_valid_time(self) -> None:
        assert validate_time("10:30:45") is True
        assert validate_time("23:59:59") is True
        assert validate_time("00:00:00") is True

    def test_invalid_time(self) -> None:
        assert validate_time("25:00:00") is False
        assert validate_time("invalid") is False

    def test_exception_handling(self) -> None:
        assert validate_time(None) is False


class TestValidateHour:
    def test_valid_hour(self) -> None:
        assert validate_hour("0") is True
        assert validate_hour("23") is True

    def test_invalid_hour(self) -> None:
        assert validate_hour("24") is False
        assert validate_hour("-1") is False
        assert validate_hour("abc") is False


class TestValidateMinute:
    def test_valid_minute(self) -> None:
        assert validate_minute("0") is True
        assert validate_minute("59") is True

    def test_invalid_minute(self) -> None:
        assert validate_minute("60") is False
        assert validate_minute("-1") is False
        assert validate_minute("abc") is False


class TestValidateSecond:
    def test_valid_second(self) -> None:
        assert validate_second("0") is True
        assert validate_second("59.999") is True

    def test_invalid_second(self) -> None:
        assert validate_second("60") is False
        assert validate_second("-1") is False
        assert validate_second("abc") is False


class TestValidateTimezoneOffset:
    def test_valid_timezone_offset(self) -> None:
        assert validate_timezone_offset("+05:30") is True
        assert validate_timezone_offset("-08:00") is True

    def test_invalid_timezone_offset(self) -> None:
        assert validate_timezone_offset("invalid") is False
        assert validate_timezone_offset("+5:30") is False

    def test_exception_handling(self) -> None:
        assert validate_timezone_offset(None) is False


class TestValidateBoolean:
    def test_valid_boolean(self) -> None:
        assert validate_boolean("true") is True
        assert validate_boolean("false") is True
        assert validate_boolean("TRUE") is True
        assert validate_boolean("FALSE") is True

    def test_invalid_boolean(self) -> None:
        assert validate_boolean("yes") is False
        assert validate_boolean("1") is False

    def test_exception_handling(self) -> None:
        assert validate_boolean(None) is False


class TestValidateHexBinary:
    def test_valid_hex_binary(self) -> None:
        assert validate_hex_binary("48656c6c6f") is True
        assert validate_hex_binary("") is True

    def test_invalid_hex_binary(self) -> None:
        assert validate_hex_binary("xyz") is False
        assert validate_hex_binary("48656c6c6g") is False


class TestValidateBase64Binary:
    def test_valid_base64_binary(self) -> None:
        assert validate_base64_binary("SGVsbG8=") is True
        assert validate_base64_binary("") is True

    def test_invalid_base64_binary(self) -> None:
        assert validate_base64_binary("invalid!@#") is False


class TestValidateUrl:
    def test_valid_url(self) -> None:
        assert validate_url("https://example.com") is True
        assert validate_url("http://example.com/path") is True

    def test_invalid_url(self) -> None:
        assert validate_url("not-a-url") is False
        assert validate_url("://example.com") is False


class TestValidateQName:
    def test_valid_qname(self) -> None:
        assert validate_qname("prefix:localname") is True
        assert validate_qname("localname") is True
        assert validate_qname("_localname") is True

    def test_invalid_qname(self) -> None:
        assert validate_qname("123invalid") is False
        assert validate_qname("") is False

    def test_exception_handling(self) -> None:
        assert validate_qname(None) is False


class TestValidateEntities:
    def test_valid_entities(self) -> None:
        assert validate_entities("entity1 entity2") is True
        assert validate_entities("single") is True

    def test_invalid_entities(self) -> None:
        assert validate_entities("123invalid entity2") is False
        assert validate_entities("") is True

    def test_exception_handling(self) -> None:
        assert validate_entities(None) is False


class TestValidateEntity:
    def test_validate_entity_alias(self) -> None:
        assert validate_entity == validate_entities


class TestValidateId:
    def test_valid_id(self) -> None:
        assert validate_id("validId") is True
        assert validate_id("_validId") is True

    def test_invalid_id(self) -> None:
        assert validate_id("123invalid") is False
        assert validate_id("") is False

    def test_exception_handling(self) -> None:
        assert validate_id(None) is False


class TestValidateAliases:
    def test_idref_alias(self) -> None:
        assert validate_idref == validate_id

    def test_idrefs_alias(self) -> None:
        assert validate_idrefs == validate_entities

    def test_ncname_alias(self) -> None:
        assert validate_ncname == validate_id


class TestValidateNmtoken:
    def test_valid_nmtoken(self) -> None:
        assert validate_nmtoken("token123") is True
        assert validate_nmtoken("123") is True

    def test_invalid_nmtoken(self) -> None:
        assert validate_nmtoken("") is False
        assert validate_nmtoken("token with space") is False

    def test_exception_handling(self) -> None:
        assert validate_nmtoken(None) is False


class TestValidateNmtokens:
    def test_valid_nmtokens(self) -> None:
        assert validate_nmtokens("token1 token2") is True
        assert validate_nmtokens("single") is True

    def test_invalid_nmtokens(self) -> None:
        assert validate_nmtokens("valid invalid@token") is False

    def test_exception_handling(self) -> None:
        assert validate_nmtokens(None) is False


class TestValidateNotation:
    def test_notation_alias(self) -> None:
        assert validate_notation == validate_qname


class TestValidateName:
    def test_valid_name(self) -> None:
        assert validate_name("validName") is True
        assert validate_name("_validName") is True
        assert validate_name(":validName") is True

    def test_invalid_name(self) -> None:
        assert validate_name("123invalid") is False
        assert validate_name("") is False

    def test_exception_handling(self) -> None:
        assert validate_name(None) is False
