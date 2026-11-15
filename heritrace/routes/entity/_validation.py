# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from dataclasses import dataclass, replace

from rdflib import RDF, URIRef

from heritrace.configuration.vocabulary import SH
from heritrace.extensions import get_custom_filter, get_form_fields
from heritrace.field_errors import FieldError, field_error
from heritrace.language import is_tagged
from heritrace.utils.datatypes import DATATYPE_MAPPING
from heritrace.utils.filters import Filter
from heritrace.utils.shacl_patterns import broken_pattern, pattern_error
from heritrace.utils.shacl_presentation import is_inverse_path
from heritrace.utils.shacl_utils import find_matching_form_field
from heritrace.utils.uri_utils import is_iri
from heritrace.utils.value_bounds import BOUND_NAMES, broken_bound


@dataclass(frozen=True, slots=True)
class PropertyValidationInput:
    matching_field_def: dict
    normalized_prop_values: list
    prop_uri: str
    entity_key: tuple
    custom_filter: Filter
    # The temporary id of the resource, or None for the one the request creates.
    subject: str | None
    # The values of every property of the resource, which conditional patterns
    # read.
    properties: dict

    def holds(self, condition: tuple[str, str]) -> bool:
        path, value = condition
        values = self.properties.get(path, [])
        return value in (values if isinstance(values, list) else [values])

    def label(self, iri: str) -> str:
        return self.custom_filter.human_readable_predicate(iri, self.entity_key)

    def error(self, code: str, **params: str | int) -> FieldError:
        return field_error(code, self.subject, self.prop_uri, **params)


def _validate_property_cardinality(
    errors: list[FieldError],
    prop_input: PropertyValidationInput,
) -> None:
    min_count = prop_input.matching_field_def.get("min", 0)
    max_count = prop_input.matching_field_def.get("max")
    value_count = len(prop_input.normalized_prop_values)
    name = prop_input.label(prop_input.prop_uri)
    if value_count < min_count:
        errors.append(
            prop_input.error("tooFew", name=name, count=value_count, min=min_count)
        )
    if max_count is not None and value_count > max_count:
        errors.append(
            prop_input.error("tooMany", name=name, count=value_count, max=max_count)
        )

    mandatory_values = prop_input.matching_field_def.get("mandatory_values", [])
    errors.extend(
        prop_input.error("requiredValue", value=prop_input.label(mandatory_value))
        for mandatory_value in mandatory_values
        if mandatory_value not in prop_input.normalized_prop_values
    )


def _validate_property_values(
    errors: list[FieldError],
    prop_input: PropertyValidationInput,
) -> None:
    for value in prop_input.normalized_prop_values:
        if isinstance(value, dict) and "entity_type" in value:
            errors.extend(validate_entity_data(value))
        else:
            errors.extend(_value_errors(prop_input, str(value)))


def _datatype_error(
    prop_input: PropertyValidationInput, value: str
) -> FieldError | None:
    field_def = prop_input.matching_field_def
    datatypes = field_def.get("datatypes", [])
    if not datatypes:
        return None
    checks = [
        check
        for datatype in datatypes
        for iri, check, _ in DATATYPE_MAPPING
        if iri == URIRef(datatype)
    ]
    if not any(check(value) for check in checks):
        expected = ", ".join(prop_input.label(datatype) for datatype in datatypes)
        return prop_input.error("invalidInput", expected=expected, input=value)
    broken = broken_bound(value, {name: field_def.get(name) for name in BOUND_NAMES})
    if broken:
        code, limit = broken
        return prop_input.error(code, limit=str(limit), input=value)
    return None


def _value_errors(prop_input: PropertyValidationInput, value: str) -> list[FieldError]:
    field_def = prop_input.matching_field_def
    optional_values = field_def.get("optionalValues", [])
    broken = broken_pattern(value, field_def["patterns"], prop_input.holds)
    errors = [
        _datatype_error(prop_input, value),
        prop_input.error("invalidIri", input=value)
        if field_def.get("nodeKind") == str(SH.IRI) and not is_iri(value)
        else None,
        prop_input.error(
            "notAllowed",
            values=", ".join(prop_input.label(option) for option in optional_values),
            input=value,
        )
        if optional_values and value not in optional_values
        else None,
        pattern_error(broken, prop_input.subject, prop_input.prop_uri, value)
        if broken
        else None,
    ]
    return [error for error in errors if error is not None]


def _validate_languages(
    errors: list[FieldError],
    prop_input: PropertyValidationInput,
) -> None:
    languages = [
        value["language"]
        for value in prop_input.normalized_prop_values
        if is_tagged(value)
    ]
    if not languages:
        return
    datatypes = prop_input.matching_field_def["datatypes"]
    if datatypes and str(RDF.langString) not in datatypes:
        errors.append(prop_input.error("languageNotAccepted"))
    if prop_input.matching_field_def["uniqueLang"] and len(languages) != len(
        set(languages)
    ):
        errors.append(prop_input.error("languageTaken"))


def _check_missing_required_properties(  # noqa: PLR0913
    errors: list[FieldError],
    entity_fields: dict,
    properties: dict,
    entity_key: tuple,
    custom_filter: Filter,
    subject: str | None,
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
                    name = custom_filter.human_readable_predicate(prop_uri, entity_key)
                    errors.append(
                        field_error(
                            "tooFew",
                            subject,
                            prop_uri,
                            name=name,
                            count=0,
                            min=min_count,
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


# The forms send only the types and properties that the shapes declare: any
# other one is a request the server refuses outright.
def validate_entity_data(structured_data: dict) -> list[FieldError]:
    custom_filter = get_custom_filter()
    form_fields = get_form_fields()

    errors: list[FieldError] = []
    entity_type = structured_data.get("entity_type")
    entity_shape = structured_data.get("entity_shape")
    subject = structured_data.get("tempId")

    if not entity_type:
        msg = "Entity type is required"
        raise ValueError(msg)

    entity_key = find_matching_form_field(entity_type, entity_shape, form_fields)

    if not entity_key:
        msg = f"No form fields found for entity type: {entity_type}" + (
            f" and shape: {entity_shape}" if entity_shape else ""
        )
        raise ValueError(msg)

    entity_fields = form_fields[entity_key]
    properties = structured_data.get("properties", {})

    for prop_uri, prop_values in properties.items():
        if URIRef(prop_uri) == RDF.type or is_inverse_path(prop_uri):
            continue

        field_definitions = entity_fields.get(prop_uri)
        if not field_definitions:
            prop_label = custom_filter.human_readable_predicate(prop_uri, entity_key)
            type_label = custom_filter.human_readable_class(entity_key)
            msg = f"Unknown property {prop_label} for entity type {type_label}"
            raise ValueError(msg)

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
                subject=subject,
                properties=properties,
            )
            _validate_property_cardinality(errors, prop_input)
            _validate_property_values(
                errors,
                replace(
                    prop_input,
                    normalized_prop_values=[
                        value
                        for value in normalized_prop_values
                        if not is_tagged(value)
                    ],
                ),
            )
            _validate_languages(errors, prop_input)

    _check_missing_required_properties(
        errors,
        entity_fields,
        properties,
        entity_key,
        custom_filter,
        subject,
    )

    return errors
