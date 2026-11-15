# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from dataclasses import dataclass
from typing import cast

from flask import Response, jsonify, request
from flask_login import current_user, login_required
from rdflib import RDF, XSD, Literal, URIRef

from heritrace.apis.orcid import get_responsible_agent_uri
from heritrace.configuration.vocabulary import SH
from heritrace.editor import Editor, EditorError
from heritrace.extensions import (
    get_custom_filter,
    get_form_fields,
    get_presentation,
    get_primary_source,
    new_editor,
    record_dataset_change,
)
from heritrace.field_errors import RejectedError, name_new_resource
from heritrace.language import is_tagged, tagged_literal
from heritrace.routes.entity._blueprint import entity_bp
from heritrace.routes.entity._validation import validate_entity_data
from heritrace.utils.datatypes import determine_datatype
from heritrace.utils.inverse_paths import (
    existing_inverse_links,
    new_inverse_entities,
    without_inverse_properties,
)
from heritrace.utils.primary_source_utils import save_user_default_primary_source
from heritrace.utils.shacl_utils import find_matching_form_field
from heritrace.utils.shacl_validation import pair_errors
from heritrace.utils.sparql_utils import import_referenced_entities
from heritrace.utils.uri_utils import generate_unique_uri, is_valid_url


def _prepare_entity_creation_data(
    structured_data: dict,
) -> tuple[dict, str]:
    cleaned_structured_data = without_inverse_properties(structured_data)
    entity_type: str = cleaned_structured_data["entity_type"]

    return cleaned_structured_data, entity_type


def _setup_editor_for_creation(editor: Editor, structured_data: dict) -> None:
    import_referenced_entities(editor, structured_data)
    editor.preexisting_finished()


def _create_inverse_values(
    editor: Editor,
    structured_data: dict,
    entity_uri: URIRef,
    graph_uri: URIRef | None,
) -> None:
    for entity in new_inverse_entities(structured_data, str(entity_uri)):
        create_nested_entity(
            editor,
            generate_unique_uri(entity["entity_type"]),
            entity,
            graph_uri,
        )
    for linked_uri, predicate in existing_inverse_links(structured_data):
        editor.create(URIRef(linked_uri), URIRef(predicate), entity_uri, graph_uri)


def _process_inverse_values_after_creation(
    editor: Editor,
    structured_data: dict,
    entity_uri: URIRef,
    default_graph_uri: URIRef | None,
) -> None:
    if new_inverse_entities(structured_data, str(entity_uri)) or existing_inverse_links(
        structured_data
    ):
        editor.begin_counter_transaction()
        _create_inverse_values(editor, structured_data, entity_uri, default_graph_uri)
        editor.save()


def _create_entity_with_form_fields(
    editor: Editor,
    structured_data: dict,
    entity_uri: URIRef,
    default_graph_uri: URIRef | None,
    form_fields: dict,
) -> None:
    cleaned_structured_data = without_inverse_properties(structured_data)
    entity_type = cleaned_structured_data["entity_type"]
    properties = cleaned_structured_data.get("properties", {})

    for predicate, raw_values in properties.items():
        predicate_uri = URIRef(predicate)
        values = raw_values if isinstance(raw_values, list) else [raw_values]

        entity_shape = cleaned_structured_data.get("entity_shape")
        matching_key = find_matching_form_field(entity_type, entity_shape, form_fields)

        field_definitions = (
            form_fields.get(matching_key, {}).get(predicate, []) if matching_key else []
        )

        property_shape = None
        if values and isinstance(values[0], dict):
            property_shape = values[0].get("shape")

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

        ordered_by = matching_field_def.get("orderedBy") if matching_field_def else None

        ctx = CreationContext(
            editor=editor,
            entity_uri=entity_uri,
            predicate=predicate_uri,
            default_graph_uri=default_graph_uri,
        )

        if ordered_by:
            ordering = get_presentation().ordering(entity_shape, predicate)
            process_ordered_properties(
                ctx,
                values,
                URIRef(ordered_by),
                indexed=ordering is not None and ordering.indexed,
            )
        else:
            process_unordered_properties(ctx, values, matching_field_def)


def _create_entity_without_form_fields(
    editor: Editor,
    structured_data: dict,
    entity_uri: URIRef,
    default_graph_uri: URIRef | None,
) -> None:
    cleaned_structured_data = without_inverse_properties(structured_data)
    entity_type = cleaned_structured_data["entity_type"]
    properties = cleaned_structured_data.get("properties", {})

    editor.create(
        entity_uri,
        RDF.type,
        URIRef(entity_type),
        default_graph_uri,
    )

    for predicate, values in properties.items():
        predicate_uri = URIRef(predicate)
        for value_dict in values:
            if value_dict["type"] == "uri":
                editor.create(
                    entity_uri,
                    predicate_uri,
                    URIRef(value_dict["value"]),
                    default_graph_uri,
                )
            elif value_dict["type"] == "literal":
                datatype = (
                    URIRef(value_dict["datatype"])
                    if "datatype" in value_dict
                    else XSD.string
                )
                editor.create(
                    entity_uri,
                    predicate_uri,
                    Literal(value_dict["value"], datatype=datatype),
                    default_graph_uri,
                )


def _handle_create_entity_post(
    form_fields: dict,
    structured_data: dict,
    primary_source: str | None,
    *,
    save_default_source: bool,
) -> tuple[Response, int]:
    if primary_source and not is_valid_url(primary_source):
        return jsonify(
            {
                "status": "error",
                "errors": ["Invalid primary source URL provided"],
            }
        ), 400

    if save_default_source and primary_source and is_valid_url(primary_source):
        save_user_default_primary_source(current_user.orcid, primary_source)

    if not structured_data.get("entity_type"):
        return jsonify({"status": "error", "errors": ["Entity type is required"]}), 400

    cleaned_structured_data, entity_type = _prepare_entity_creation_data(
        structured_data
    )

    if form_fields:
        validation_errors = validate_entity_data(cleaned_structured_data)
        if validation_errors:
            raise RejectedError(validation_errors)

    resp_agent = get_responsible_agent_uri(current_user.orcid)
    editor = new_editor(resp_agent, get_primary_source())
    entity_uri = generate_unique_uri(entity_type)
    name_new_resource(str(entity_uri), None)
    default_graph_uri = (
        URIRef(f"{entity_uri}/graph") if editor.dataset_is_quadstore else None
    )
    if not form_fields:
        editor.import_entity(entity_uri)
    _setup_editor_for_creation(editor, structured_data)
    editor.set_primary_source(URIRef(primary_source) if primary_source else None)

    if form_fields:
        _create_entity_with_form_fields(
            editor,
            structured_data,
            entity_uri,
            default_graph_uri,
            form_fields,
        )
    else:
        _create_entity_without_form_fields(
            editor,
            structured_data,
            entity_uri,
            default_graph_uri,
        )

    errors = pair_errors(
        editor.g_set,
        {node for node in editor.g_set.subjects() if isinstance(node, URIRef)},
    )
    if errors:
        raise RejectedError(errors)
    try:
        editor.save()
        _process_inverse_values_after_creation(
            editor, structured_data, entity_uri, default_graph_uri
        )
    except (EditorError, OSError) as e:
        error_message = f"An error occurred while creating the entity: {e}"
        return jsonify({"status": "error", "errors": [error_message]}), 500
    record_dataset_change()
    return jsonify({"status": "success", "uri": str(entity_uri)}), 200


@entity_bp.route("/entity", methods=["POST"])
@login_required
def create_entity() -> tuple[Response, int]:
    data = request.get_json()
    try:
        return _handle_create_entity_post(
            get_form_fields(),
            data["structured_data"],
            data.get("primary_source") or None,
            save_default_source=bool(data.get("save_default_source")),
        )
    except ValueError as error:
        return jsonify({"status": "error", "error": str(error)}), 400


@entity_bp.route("/entity-types")
@login_required
def entity_types() -> Response:
    custom_filter = get_custom_filter()
    presentation = get_presentation()
    labelled_keys = [
        (key, custom_filter.human_readable_class(key))
        for key in get_form_fields()
        if not presentation.is_hidden(key[1])
    ]
    labelled_keys.sort(key=lambda item: item[1])
    return jsonify(
        {
            "types": [
                {"class": entity_class, "shape": shape, "label": label}
                for (entity_class, shape), label in labelled_keys
            ]
        }
    )


def create_nested_entity(
    editor: Editor,
    entity_uri: URIRef,
    entity_data: dict,
    graph_uri: URIRef | None = None,
) -> None:
    form_fields = get_form_fields()
    if "tempId" in entity_data:
        name_new_resource(str(entity_uri), entity_data["tempId"])

    editor.create(
        entity_uri,
        RDF.type,
        URIRef(entity_data["entity_type"]),
        graph_uri,
    )

    entity_type = entity_data.get("entity_type")
    entity_shape = entity_data.get("entity_shape")
    properties = without_inverse_properties(entity_data)["properties"]

    matching_key = find_matching_form_field(entity_type, entity_shape, form_fields)

    if not matching_key:
        return

    for predicate, raw_values in properties.items():
        predicate_uri = URIRef(predicate)
        values = raw_values if isinstance(raw_values, list) else [raw_values]
        field_definitions = form_fields[matching_key].get(predicate, [])
        ctx = CreationContext(editor, entity_uri, predicate_uri, graph_uri)
        ordering = get_presentation().ordering(entity_shape, predicate)
        if ordering is not None:
            process_ordered_properties(
                ctx,
                values,
                URIRef(cast("str", ordering.ordered_by)),
                indexed=ordering.indexed,
            )
        else:
            process_unordered_properties(
                ctx, values, field_definitions[0] if field_definitions else None
            )

    _create_inverse_values(editor, entity_data, entity_uri, graph_uri)


@dataclass(frozen=True, slots=True)
class CreationContext:
    editor: Editor
    entity_uri: URIRef
    predicate: URIRef
    default_graph_uri: URIRef | None


def process_entity_value(
    ctx: CreationContext,
    value: dict | str,
    matching_field_def: dict | None,
) -> URIRef | Literal:
    if isinstance(value, dict) and "entity_type" in value:
        nested_uri = generate_unique_uri(value["entity_type"])
        ctx.editor.create(
            ctx.entity_uri,
            ctx.predicate,
            nested_uri,
            ctx.default_graph_uri,
        )
        create_nested_entity(ctx.editor, nested_uri, value, ctx.default_graph_uri)
        return nested_uri
    if isinstance(value, dict) and value.get("is_existing_entity", False):
        entity_ref_uri = value.get("entity_uri")
        if entity_ref_uri:
            object_value = URIRef(entity_ref_uri)
            ctx.editor.create(
                ctx.entity_uri,
                ctx.predicate,
                object_value,
                ctx.default_graph_uri,
            )
            return object_value
        msg = "Missing entity_uri in existing entity reference"
        raise ValueError(msg)
    str_value = str(value)
    node_kind = matching_field_def.get("nodeKind") if matching_field_def else None
    if is_tagged(value):
        object_value: URIRef | Literal = tagged_literal(value)
    elif node_kind == str(SH.IRI) or (
        node_kind != str(SH.Literal) and is_valid_url(str_value)
    ):
        object_value = URIRef(str_value)
    else:
        datatype_uris = []
        if matching_field_def:
            datatype_uris = matching_field_def.get("datatypes", [])
        datatype = determine_datatype(str_value, datatype_uris)
        object_value = Literal(str_value, datatype=datatype)
    ctx.editor.create(
        ctx.entity_uri,
        ctx.predicate,
        object_value,
        ctx.default_graph_uri,
    )
    return object_value


def _process_ordered_entity_value(
    ctx: CreationContext,
    value: dict,
) -> URIRef:
    if isinstance(value, dict) and "entity_type" in value:
        nested_uri = generate_unique_uri(value["entity_type"])
        ctx.editor.create(
            ctx.entity_uri,
            ctx.predicate,
            nested_uri,
            ctx.default_graph_uri,
        )
        create_nested_entity(ctx.editor, nested_uri, value, ctx.default_graph_uri)
        return nested_uri
    if isinstance(value, dict) and value.get("is_existing_entity", False):
        nested_uri = URIRef(value["entity_uri"])
        ctx.editor.create(
            ctx.entity_uri,
            ctx.predicate,
            nested_uri,
            ctx.default_graph_uri,
        )
        return nested_uri
    msg = "Unexpected value type for ordered property"
    raise ValueError(msg)


def process_ordered_properties(
    ctx: CreationContext,
    values: list[dict],
    ordered_by: URIRef,
    *,
    indexed: bool = False,
) -> None:
    ctx.editor.place_in_order(
        [
            (value.get("entity_shape"), _process_ordered_entity_value(ctx, value))
            for value in values
        ],
        ordered_by,
        ctx.default_graph_uri,
        indexed=indexed,
    )


def process_unordered_properties(
    ctx: CreationContext,
    values: list[dict | str],
    matching_field_def: dict | None,
) -> None:
    for value in values:
        process_entity_value(ctx, value, matching_field_def)
