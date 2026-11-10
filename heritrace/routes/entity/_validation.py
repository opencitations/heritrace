# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from dataclasses import dataclass

from rdflib import RDF, URIRef

from heritrace.extensions import get_custom_filter, get_form_fields
from heritrace.utils.datatypes import DATATYPE_MAPPING
from heritrace.utils.filters import Filter
from heritrace.utils.shacl_presentation import is_inverse_path
from heritrace.utils.shacl_utils import find_matching_form_field


def _plural(noun: str, count: int) -> str:
    return noun if count == 1 else f"{noun}s"


@dataclass(frozen=True, slots=True)
class PropertyValidationInput:
    matching_field_def: dict
    normalized_prop_values: list
    prop_uri: str
    entity_key: tuple
    custom_filter: Filter


def _validate_property_cardinality(
    errors: list[str],
    prop_input: PropertyValidationInput,
) -> None:
    min_count = prop_input.matching_field_def.get("min", 0)
    max_count = prop_input.matching_field_def.get("max")
    value_count = len(prop_input.normalized_prop_values)

    prop_label = prop_input.custom_filter.human_readable_predicate(
        prop_input.prop_uri, prop_input.entity_key
    )
    if value_count < min_count:
        errors.append(
            f"Property {prop_label} requires at least"
            f" {min_count} {_plural('value', min_count)}"
        )
    if max_count is not None and value_count > max_count:
        errors.append(
            f"Property {prop_label} allows at most"
            f" {max_count} {_plural('value', max_count)}"
        )

    mandatory_values = prop_input.matching_field_def.get("mandatory_values", [])
    errors.extend(
        f"Property {prop_label} requires the value {mandatory_value}"
        for mandatory_value in mandatory_values
        if mandatory_value not in prop_input.normalized_prop_values
    )


def _validate_property_values(
    errors: list[str],
    prop_input: PropertyValidationInput,
) -> None:
    prop_label = prop_input.custom_filter.human_readable_predicate(
        prop_input.prop_uri, prop_input.entity_key
    )
    for value in prop_input.normalized_prop_values:
        if isinstance(value, dict) and "entity_type" in value:
            nested_errors = validate_entity_data(value)
            errors.extend(nested_errors)
        else:
            datatypes = prop_input.matching_field_def.get("datatypes", [])
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
                        prop_input.custom_filter.human_readable_predicate(
                            dtype, prop_input.entity_key
                        )
                        for dtype in datatypes
                    )
                    errors.append(
                        f'Value "{value}" for property {prop_label}'
                        f" is not of expected type {expected_types}"
                    )

            optional_values = prop_input.matching_field_def.get("optionalValues", [])
            if optional_values and value not in optional_values:
                acceptable_values = ", ".join(
                    prop_input.custom_filter.human_readable_predicate(
                        val, prop_input.entity_key
                    )
                    for val in optional_values
                )
                errors.append(
                    f'Value "{value}" is not permitted for property {prop_label}.'
                    f" Acceptable values are: {acceptable_values}"
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
                    prop_label = custom_filter.human_readable_predicate(
                        prop_uri, entity_key
                    )
                    errors.append(
                        f"Missing required property: {prop_label} requires"
                        f" at least {min_count} {_plural('value', min_count)}"
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
        errors.append("Entity type is required")
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
        if URIRef(prop_uri) == RDF.type or is_inverse_path(prop_uri):
            continue

        field_definitions = entity_fields.get(prop_uri)
        if not field_definitions:
            prop_label = custom_filter.human_readable_predicate(prop_uri, entity_key)
            type_label = custom_filter.human_readable_class(entity_key)
            errors.append(f"Unknown property {prop_label} for entity type {type_label}")
            continue

        normalized_prop_values = (
            prop_values if isinstance(prop_values, list) else [prop_values]
        )

        matching_field_def = _find_matching_field_definition(
            field_definitions,
            normalized_prop_values,
        )

        if matching_field_def:
            prop_input = PropertyValidationInput(
                matching_field_def=matching_field_def,
                normalized_prop_values=normalized_prop_values,
                prop_uri=prop_uri,
                entity_key=entity_key,
                custom_filter=custom_filter,
            )
            _validate_property_cardinality(errors, prop_input)
            _validate_property_values(errors, prop_input)

    _check_missing_required_properties(
        errors,
        entity_fields,
        properties,
        entity_key,
        custom_filter,
    )

    return errors
