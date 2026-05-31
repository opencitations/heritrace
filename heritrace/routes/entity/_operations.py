# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from rdflib import XSD, Literal, URIRef
from SPARQLWrapper import JSON

from heritrace.editor import Editor
from heritrace.extensions import get_form_fields, get_sparql
from heritrace.sparql import get_sparql_bindings
from heritrace.utils.display_rules_utils import get_highest_priority_class
from heritrace.utils.shacl_utils import find_matching_form_field
from heritrace.utils.sparql_utils import get_entity_types
from heritrace.utils.uri_utils import is_valid_url


def process_modification_data(data: dict) -> tuple[str, list[dict]]:
    subject_uri = data.get("subject")
    if not subject_uri:
        msg = "No subject URI provided in modification data"
        raise ValueError(msg)

    modifications = data.get("modifications", [])
    if not modifications:
        msg = "No modifications provided in data"
        raise ValueError(msg)

    return subject_uri, modifications


def _validate_removal(
    predicate_fields: list[dict],
    predicate: str,
) -> tuple[bool, str]:
    for field in predicate_fields:
        if field.get("minCount", 0) > 0:
            return False, f"Cannot remove required predicate: {predicate}"
    return True, ""


def _validate_addition(
    predicate_fields: list[dict],
    predicate: str,
    subject_uri: URIRef,
) -> tuple[bool, str]:
    for field in predicate_fields:
        max_count = field.get("maxCount")
        if max_count:
            current_count = get_predicate_count(subject_uri, URIRef(predicate))
            if current_count >= max_count:
                return (
                    False,
                    f"Maximum count exceeded for predicate: {predicate}",
                )
    return True, ""


def _resolve_entity_type(
    modification: dict,
    subject_uri: URIRef,
) -> str | None:
    entity_type = modification.get("entity_type")
    if not entity_type:
        entity_types = get_entity_types(subject_uri)
        if entity_types:
            entity_type = get_highest_priority_class(entity_types)
    return entity_type


def validate_modification(modification: dict, subject_uri: URIRef) -> tuple[bool, str]:
    form_fields = get_form_fields()
    operation = modification.get("operation")
    if not operation:
        return False, "No operation specified in modification"

    predicate = modification.get("predicate")
    if not predicate:
        return False, "No predicate specified in modification"

    if operation not in ["add", "remove", "update"]:
        return False, f"Invalid operation: {operation}"

    if form_fields:
        entity_type = _resolve_entity_type(modification, subject_uri)
        entity_shape = modification.get("entity_shape")
        matching_key = find_matching_form_field(entity_type, entity_shape, form_fields)

        if matching_key:
            predicate_fields = form_fields[matching_key].get(predicate, [])
            if operation == "remove":
                return _validate_removal(predicate_fields, predicate)
            if operation == "add":
                return _validate_addition(predicate_fields, predicate, subject_uri)

    return True, ""


def get_predicate_count(subject_uri: URIRef, predicate: URIRef) -> int:
    sparql = get_sparql()

    query = f"""
    SELECT (COUNT(?o) as ?count) WHERE {{
        <{subject_uri}> <{predicate}> ?o .
    }}
    """

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    bindings = get_sparql_bindings(sparql.query().convert())

    return int(bindings[0]["count"]["value"])


def apply_modifications(
    editor: Editor,
    modifications: list[dict],
    subject_uri: URIRef,
    graph_uri: URIRef | None = None,
) -> None:
    for mod in modifications:
        operation = mod["operation"]
        predicate = URIRef(mod["predicate"])

        if operation == "remove":
            editor.delete(subject_uri, predicate, graph=graph_uri)

        elif operation == "add":
            value = mod["value"]
            datatype = mod.get("datatype", XSD.string)

            if is_valid_url(value):
                object_value = URIRef(value)
            else:
                object_value = Literal(value, datatype=URIRef(datatype))

            editor.create(subject_uri, predicate, object_value, graph_uri)

        elif operation == "update":
            old_value = mod["oldValue"]
            new_value = mod["newValue"]
            datatype = mod.get("datatype", XSD.string)

            if is_valid_url(old_value):
                old_object = URIRef(old_value)
            else:
                old_object = Literal(old_value, datatype=URIRef(datatype))

            if is_valid_url(new_value):
                new_object = URIRef(new_value)
            else:
                new_object = Literal(new_value, datatype=URIRef(datatype))

            editor.update(
                subject_uri,
                predicate,
                old_object,
                new_object,
                graph_uri,
            )
