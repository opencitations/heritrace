# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from __future__ import annotations

from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from heritrace.utils.filters import Filter


# The datatypes offered for a custom property, the most common first.
DATATYPE_OPTIONS = (
    XSD.string,
    XSD.anyURI,
    XSD.integer,
    XSD.boolean,
    XSD.date,
    XSD.decimal,
    XSD.dateTime,
    XSD.gYear,
    XSD.float,
    XSD.time,
    XSD.normalizedString,
    XSD.language,
    XSD.double,
    XSD.token,
    XSD.nonNegativeInteger,
    XSD.positiveInteger,
    XSD.nonPositiveInteger,
    XSD.negativeInteger,
    XSD.long,
    XSD.short,
    XSD.byte,
    XSD.unsignedInt,
    XSD.unsignedLong,
    XSD.unsignedShort,
    XSD.unsignedByte,
    XSD.gMonth,
    XSD.gDay,
    XSD.duration,
    XSD.hexBinary,
    XSD.base64Binary,
)


def get_datatype_options(custom_filter: Filter) -> list[dict[str, str]]:
    labels = custom_filter.value_labels(dict.fromkeys(DATATYPE_OPTIONS))
    return [
        {"label": labels[datatype], "uri": str(datatype)}
        for datatype in DATATYPE_OPTIONS
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
