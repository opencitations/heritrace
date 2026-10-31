# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from rdflib import XSD, URIRef

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


def get_datatype_options() -> list[dict[str, str]]:
    return [
        {"label": "Text (string)", "uri": str(XSD.string)},
        {"label": "Web address (URL)", "uri": str(XSD.anyURI)},
        {"label": "Whole number (integer)", "uri": str(XSD.integer)},
        {"label": "True or False (boolean)", "uri": str(XSD.boolean)},
        {"label": "Date (YYYY-MM-DD)", "uri": str(XSD.date)},
        {"label": "Decimal number", "uri": str(XSD.decimal)},
        {
            "label": "Date and Time (YYYY-MM-DDThh:mm:ss)",
            "uri": str(XSD.dateTime),
        },
        {"label": "Year (YYYY)", "uri": str(XSD.gYear)},
        {"label": "Floating point number", "uri": str(XSD.float)},
        {"label": "Time (hh:mm:ss)", "uri": str(XSD.time)},
        {
            "label": "Normalized text (no line breaks)",
            "uri": str(XSD.normalizedString),
        },
        {"label": "Language code (e.g., en, it)", "uri": str(XSD.language)},
        {
            "label": "Double precision floating point number",
            "uri": str(XSD.double),
        },
        {"label": "Tokenized text (single word)", "uri": str(XSD.token)},
        {
            "label": "Non-negative integer (0 or positive)",
            "uri": str(XSD.nonNegativeInteger),
        },
        {
            "label": "Positive integer (greater than 0)",
            "uri": str(XSD.positiveInteger),
        },
        {
            "label": "Non-positive integer (0 or negative)",
            "uri": str(XSD.nonPositiveInteger),
        },
        {"label": "Negative integer", "uri": str(XSD.negativeInteger)},
        {"label": "Long integer", "uri": str(XSD.long)},
        {"label": "Short integer", "uri": str(XSD.short)},
        {"label": "Byte-sized integer", "uri": str(XSD.byte)},
        {"label": "Unsigned integer", "uri": str(XSD.unsignedInt)},
        {"label": "Unsigned long integer", "uri": str(XSD.unsignedLong)},
        {"label": "Unsigned short integer", "uri": str(XSD.unsignedShort)},
        {"label": "Unsigned byte", "uri": str(XSD.unsignedByte)},
        {"label": "Month (MM)", "uri": str(XSD.gMonth)},
        {"label": "Day of the month (DD)", "uri": str(XSD.gDay)},
        {
            "label": "Duration (e.g., P1Y2M3DT4H5M6S)",
            "uri": str(XSD.duration),
        },
        {"label": "Hexadecimal binary", "uri": str(XSD.hexBinary)},
        {"label": "Base64 encoded binary", "uri": str(XSD.base64Binary)},
    ]


DATATYPE_MAPPING = [
    [XSD.string, validate_string, "text"],
    [XSD.normalizedString, validate_normalized_string, "text"],
    [XSD.integer, validate_integer, "number"],
    [XSD.int, validate_integer, "number"],
    [XSD.positiveInteger, validate_positive_integer, "number"],
    [XSD.negativeInteger, validate_negative_integer, "number"],
    [XSD.nonNegativeInteger, validate_non_negative_integer, "number"],
    [XSD.nonPositiveInteger, validate_non_positive_integer, "number"],
    [XSD.byte, validate_byte, "number"],
    [XSD.short, validate_short, "number"],
    [XSD.long, validate_long, "number"],
    [XSD.unsignedByte, validate_unsigned_byte, "number"],
    [XSD.unsignedShort, validate_unsigned_short, "number"],
    [XSD.unsignedLong, validate_unsigned_long, "number"],
    [XSD.unsignedInt, validate_unsigned_int, "number"],
    [XSD.float, validate_float, "number"],
    [XSD.double, validate_double, "number"],
    [XSD.decimal, validate_decimal, "number"],
    [XSD.duration, validate_duration, "text"],
    [XSD.dayTimeDuration, validate_day_time_duration, "text"],
    [XSD.yearMonthDuration, validate_year_month_duration, "text"],
    [XSD.dateTime, validate_date_time, "datetime-local"],
    [XSD.dateTimeStamp, validate_date_time_stamp, "datetime-local"],
    [XSD.gYear, validate_g_year, "number"],
    [XSD.gYearMonth, validate_g_year_month, "month"],
    [XSD.date, validate_date, "date"],
    [XSD.time, validate_time, "time"],
    [XSD.hour, validate_hour, "time"],
    [XSD.timezoneOffset, validate_timezone_offset, "time"],
    [XSD.minute, validate_minute, "time"],
    [XSD.second, validate_second, "time"],
    [XSD.boolean, validate_boolean, "checkbox"],
    [XSD.hexBinary, validate_hex_binary, "password"],
    [XSD.base64Binary, validate_base64_binary, "password"],
    [XSD.anyURI, validate_url, "url"],
    [XSD.QName, validate_qname, "text"],
    [XSD.ENTITIES, validate_entities, "text"],
    [XSD.ENTITY, validate_entity, "text"],
    [XSD.ID, validate_id, "text"],
    [XSD.IDREF, validate_idref, "text"],
    [XSD.IDREFS, validate_idrefs, "text"],
    [XSD.NCName, validate_ncname, "text"],
    [XSD.NMTOKEN, validate_nmtoken, "text"],
    [XSD.NMTOKENS, validate_nmtokens, "text"],
    [XSD.NOTATION, validate_notation, "text"],
    [XSD.Name, validate_name, "text"],
]


def determine_datatype(value: str, datatype_uris: list[str]) -> URIRef:
    for datatype_uri in datatype_uris:
        validation_func = next(
            (d[1] for d in DATATYPE_MAPPING if str(d[0]) == str(datatype_uri)), None
        )
        if validation_func and validation_func(value):
            return URIRef(datatype_uri)
    return XSD.string
