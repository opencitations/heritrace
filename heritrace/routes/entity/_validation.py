# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from flask_babel import gettext
from rdflib import RDF, URIRef

from heritrace.extensions import get_custom_filter, get_form_fields
from heritrace.utils.datatypes import DATATYPE_MAPPING
from heritrace.utils.filters import Filter
from heritrace.utils.shacl_utils import find_matching_form_field


def _validate_property_cardinality(  # noqa: PLR0913
    errors: list[str],
    matching_field_def: dict,
    normalized_prop_values: list,
    prop_uri: str,
    entity_key: tuple,
    custom_filter: Filter,
) -> None:
    min_count = matching_field_def.get("min", 0)
    max_count = matching_field_def.get("max")
    value_count = len(normalized_prop_values)

    if value_count < min_count:
        value = gettext("values") if min_count > 1 else gettext("value")
        errors.append(
            gettext(
                "Property %(prop_uri)s requires at least %(min_count)d %(value)s",
                prop_uri=custom_filter.human_readable_predicate(prop_uri, entity_key),
                min_count=min_count,
                value=value,
            )
        )
    if max_count is not None and value_count > max_count:
        value = gettext("values") if max_count > 1 else gettext("value")
        errors.append(
            gettext(
                "Property %(prop_uri)s allows at most %(max_count)d %(value)s",
                prop_uri=custom_filter.human_readable_predicate(prop_uri, entity_key),
                max_count=max_count,
                value=value,
            )
        )

    mandatory_values = matching_field_def.get("mandatory_values", [])
    errors.extend(
        gettext(
            "Property %(prop_uri)s requires the value %(mandatory_value)s",
            prop_uri=custom_filter.human_readable_predicate(prop_uri, entity_key),
            mandatory_value=mandatory_value,
        )
        for mandatory_value in mandatory_values
        if mandatory_value not in normalized_prop_values
    )


def _validate_property_values(  # noqa: PLR0913
    errors: list[str],
    matching_field_def: dict,
    normalized_prop_values: list,
    prop_uri: str,
    entity_key: tuple,
    custom_filter: Filter,
) -> None:
    for value in normalized_prop_values:
        if isinstance(value, dict) and "entity_type" in value:
            nested_errors = validate_entity_data(value)
            errors.extend(nested_errors)
        else:
            datatypes = matching_field_def.get("datatypes", [])
            if datatypes:
                is_valid_datatype = False
                for dtype in datatypes:
                    validation_func = next(
                        (d[1] for d in DATATYPE_MAPPING if d[0] == URIRef(dtype)),
                        None,
                    )
                    if validation_func and validation_func(value):
                        is_valid_datatype = True
                        break
                if not is_valid_datatype:
                    expected_types = ", ".join(
                        [
                            custom_filter.human_readable_predicate(dtype, entity_key)
                            for dtype in datatypes
                        ]
                    )
                    errors.append(
                        gettext(
                            'Value "%(value)s" for property'
                            " %(prop_uri)s is not of expected"
                            " type %(expected_types)s",
                            value=value,
                            prop_uri=custom_filter.human_readable_predicate(
                                prop_uri, entity_key
                            ),
                            expected_types=expected_types,
                        )
                    )

            optional_values = matching_field_def.get("optionalValues", [])
            if optional_values and value not in optional_values:
                acceptable_values = ", ".join(
                    [
                        custom_filter.human_readable_predicate(val, entity_key)
                        for val in optional_values
                    ]
                )
                errors.append(
                    gettext(
                        'Value "%(value)s" is not permitted for'
                        " property %(prop_uri)s. Acceptable values"
                        " are: %(acceptable_values)s",
                        value=value,
                        prop_uri=custom_filter.human_readable_predicate(
                            prop_uri, entity_key
                        ),
                        acceptable_values=acceptable_values,
                    )
                )


def _check_missing_required_properties(
    errors: list[str],
    entity_fields: dict,
    properties: dict,
    entity_key: tuple,
    custom_filter: Filter,
) -> None:
    # In the RDF model, a property with zero values is
    # equivalent to the property being absent, as a triple
    # requires a subject, predicate, and object. Therefore,
    # this section checks for properties defined in the schema
    # that are completely absent from the input data but are
    # required (min_count > 0). This complements the cardinality check above, which only
    # validates properties that are present in the data.
    for prop_uri, field_definitions in entity_fields.items():
        if prop_uri not in properties:
            for field_def in field_definitions:
                min_count = field_def.get("min", 0)
                if min_count > 0:
                    value = gettext("values") if min_count > 1 else gettext("value")
                    errors.append(
                        gettext(
                            "Missing required property:"
                            " %(prop_uri)s requires at least"
                            " %(min_count)d %(value)s",
                            prop_uri=custom_filter.human_readable_predicate(
                                prop_uri, entity_key
                            ),
                            min_count=min_count,
                            value=value,
                        )
                    )
                    break


def _find_matching_field_definition(
    field_definitions: list[dict],
    normalized_prop_values: list,
) -> dict | None:
    property_shape = None
    if normalized_prop_values and isinstance(normalized_prop_values[0], dict):
        property_shape = normalized_prop_values[0].get("shape")

    matching_field_def = None
    for field_def in field_definitions:
        if property_shape:
            if field_def.get("subjectShape") == property_shape:
                matching_field_def = field_def
                break
        elif not field_def.get("subjectShape"):
            matching_field_def = field_def
            break

    if not matching_field_def and field_definitions:
        matching_field_def = field_definitions[0]

    return matching_field_def


def validate_entity_data(structured_data: dict) -> list[str]:
    custom_filter = get_custom_filter()
    form_fields = get_form_fields()

    errors = []
    entity_type = structured_data.get("entity_type")
    entity_shape = structured_data.get("entity_shape")

    if not entity_type:
        errors.append(gettext("Entity type is required"))
        return errors

    entity_key = find_matching_form_field(entity_type, entity_shape, form_fields)

    if not entity_key:
        errors.append(
            f"No form fields found for entity type: {entity_type}"
            + (f" and shape: {entity_shape}" if entity_shape else "")
        )
        return errors

    entity_fields = form_fields[entity_key]
    properties = structured_data.get("properties", {})

    for prop_uri, prop_values in properties.items():
        if URIRef(prop_uri) == RDF.type:
            continue

        field_definitions = entity_fields.get(prop_uri)
        if not field_definitions:
            errors.append(
                gettext(
                    "Unknown property %(prop_uri)s for entity type %(entity_type)s",
                    prop_uri=custom_filter.human_readable_predicate(
                        prop_uri, entity_key
                    ),
                    entity_type=custom_filter.human_readable_class(entity_key),
                )
            )
            continue

        normalized_prop_values = (
            prop_values if isinstance(prop_values, list) else [prop_values]
        )

        matching_field_def = _find_matching_field_definition(
            field_definitions,
            normalized_prop_values,
        )

        if matching_field_def:
            _validate_property_cardinality(
                errors,
                matching_field_def,
                normalized_prop_values,
                prop_uri,
                entity_key,
                custom_filter,
            )
            _validate_property_values(
                errors,
                matching_field_def,
                normalized_prop_values,
                prop_uri,
                entity_key,
                custom_filter,
            )

    _check_missing_required_properties(
        errors,
        entity_fields,
        properties,
        entity_key,
        custom_filter,
    )

    return errors
