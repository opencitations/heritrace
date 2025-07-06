from rdflib import XSD

from resources.datatypes_validation import *

def get_datatype_options():
    """
    Returns an ordered list of datatype options with human-readable names mapped to their XSD URIs.
    This function requires Flask-Babel to be initialized for translations.
    Ordered by frequency of use (most common first).
    """
    from flask_babel import gettext
    
    return [
        # Most common types first
        {"label": gettext("Text (string)"), "uri": str(XSD.string)},
        {"label": gettext("Web address (URL)"), "uri": str(XSD.anyURI)},
        {"label": gettext("Whole number (integer)"), "uri": str(XSD.integer)},
        {"label": gettext("True or False (boolean)"), "uri": str(XSD.boolean)},
        {"label": gettext("Date (YYYY-MM-DD)"), "uri": str(XSD.date)},
        {"label": gettext("Decimal number"), "uri": str(XSD.decimal)},
        {"label": gettext("Date and Time (YYYY-MM-DDThh:mm:ss)"), "uri": str(XSD.dateTime)},
        {"label": gettext("Year (YYYY)"), "uri": str(XSD.gYear)},
        {"label": gettext("Floating point number"), "uri": str(XSD.float)},
        {"label": gettext("Time (hh:mm:ss)"), "uri": str(XSD.time)},
        {"label": gettext("Normalized text (no line breaks)"), "uri": str(XSD.normalizedString)},
        {"label": gettext("Language code (e.g., en, it)"), "uri": str(XSD.language)},
        {"label": gettext("Double precision floating point number"), "uri": str(XSD.double)},
        {"label": gettext("Tokenized text (single word)"), "uri": str(XSD.token)},
        # Less common numeric types
        {"label": gettext("Non-negative integer (0 or positive)"), "uri": str(XSD.nonNegativeInteger)},
        {"label": gettext("Positive integer (greater than 0)"), "uri": str(XSD.positiveInteger)},
        {"label": gettext("Non-positive integer (0 or negative)"), "uri": str(XSD.nonPositiveInteger)},
        {"label": gettext("Negative integer"), "uri": str(XSD.negativeInteger)},
        {"label": gettext("Long integer"), "uri": str(XSD.long)},
        {"label": gettext("Short integer"), "uri": str(XSD.short)},
        {"label": gettext("Byte-sized integer"), "uri": str(XSD.byte)},
        {"label": gettext("Unsigned integer"), "uri": str(XSD.unsignedInt)},
        {"label": gettext("Unsigned long integer"), "uri": str(XSD.unsignedLong)},
        {"label": gettext("Unsigned short integer"), "uri": str(XSD.unsignedShort)},
        {"label": gettext("Unsigned byte"), "uri": str(XSD.unsignedByte)},
        # Date/time variations
        {"label": gettext("Month (MM)"), "uri": str(XSD.gMonth)},
        {"label": gettext("Day of the month (DD)"), "uri": str(XSD.gDay)},
        {"label": gettext("Duration (e.g., P1Y2M3DT4H5M6S)"), "uri": str(XSD.duration)},
        # Rarely used types
        {"label": gettext("Hexadecimal binary"), "uri": str(XSD.hexBinary)},
        {"label": gettext("Base64 encoded binary"), "uri": str(XSD.base64Binary)},
    ]

DATATYPE_MAPPING = [
    [XSD.string, validate_string, "text"],
    # Una stringa che non può contenere caratteri di interruzione (ad es. newline).
    [XSD.normalizedString, validate_normalizedString, "text"],
    [XSD.integer, validate_integer, "number"],
    [XSD.int, validate_integer, "number"],
    [XSD.positiveInteger, validate_positive_integer, "number"],
    [XSD.negativeInteger, validate_negative_integer, "number"],
    [XSD.nonNegativeInteger, validate_non_negative_integer, "number"],
    [XSD.nonPositiveInteger, validate_non_positive_integer, "number"],
    # Intero compreso tra -128 e 127
    [XSD.byte, validate_byte, "number"],
    # Intero compreso tra -32,768 e 32,767
    [XSD.short, validate_short, "number"],
    # Intero compreso tra -2,147,483,648 e 2,147,483,647 (Nota: questa definizione può variare tra le implementazioni, ma in generale, un long è spesso equivalente a un int a 32 bit in molti linguaggi.)
    [XSD.long, validate_long, "number"],
    # Intero compreso tra 0 e 255
    [XSD.unsignedByte, validate_unsigned_byte, "number"],
    # Intero compreso tra 0 e 65,535
    [XSD.unsignedShort, validate_unsigned_short, "number"],
    # Intero compreso tra 0 e 4,294,967,295 (anche qui, come per long, la definizione può variare.)
    [XSD.unsignedLong, validate_unsigned_long, "number"],
    # Intero compreso tra 0 e 4,294,967,295
    [XSD.unsignedInt, validate_unsigned_int, "number"],
    [XSD.float, validate_float, "number"],
    # Un numero in virgola mobile doppia precisione
    [XSD.double, validate_double, "number"],
    # Un numero decimale esatto
    [XSD.decimal, validate_decimal, "number"],
    # Una durata nel formato PnYnMnDTnHnMnS, dove P è il designatore di periodo.
    [XSD.duration, validate_duration, "text"],
    # Una durata limitata ai giorni, ore, minuti e secondi.
    [XSD.dayTimeDuration, validate_dayTimeDuration, "text"],
    # Una durata limitata agli anni e ai mesi.
    [XSD.yearMonthDuration, validate_yearMonthDuration, "text"],
    [XSD.dateTime, validate_dateTime, "datetime-local"],
    [XSD.dateTimeStamp, validate_dateTimeStamp, "datetime-local"],
    # Un anno gregoriano, ad es. 2023.
    [XSD.gYear, validate_gYear, "number"],
    # Un anno e un mese gregoriano, ad es. 2023-09.
    [XSD.gYearMonth, validate_gYearMonth, "month"],
    [XSD.date, validate_date, "date"],
    [XSD.time, validate_time, "time"],
    [XSD.hour, validate_hour, "time"],
    # Offset del fuso orario, come +05:00.
    [XSD.timezoneOffset, validate_timezoneOffset, "time"],
    [XSD.minute, validate_minute, "time"],
    [XSD.second, validate_second, "time"],
    [XSD.boolean, validate_boolean, "checkbox"],
    # Sequenza binaria in esadecimale
    [XSD.hexBinary, validate_hexBinary, "password"],
    # Sequenza binaria codificata in Base64.
    [XSD.base64Binary, validate_base64Binary, "password"],
    [XSD.anyURI, validate_url, "url"],
    [XSD.QName, validate_QName, "text"],
    [XSD.ENTITIES, validate_ENTITIES, "text"],
    [XSD.ENTITY, validate_ENTITY, "text"],
    [XSD.ID, validate_ID, "text"],
    [XSD.IDREF, validate_IDREF, "text"],
    [XSD.IDREFS, validate_IDREFS, "text"],
    [XSD.NCName, validate_NCName, "text"],
    [XSD.NMTOKEN, validate_NMTOKEN, "text"],
    [XSD.NMTOKENS, validate_NMTOKENS, "text"],
    [XSD.NOTATION, validate_NOTATION, "text"],
    [XSD.Name, validate_Name, "text"],
]
