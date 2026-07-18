# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import json
from dataclasses import dataclass

from flask import current_app, flash, jsonify, render_template, request, url_for
from flask_babel import gettext
from flask_login import current_user, login_required
from rdflib import RDF, XSD, Literal, URIRef
from werkzeug.wrappers import Response

from heritrace.apis.orcid import get_responsible_agent_uri
from heritrace.editor import Editor, EditorError, EndpointConfig
from heritrace.extensions import (
    get_dataset_endpoint,
    get_form_fields,
    get_provenance_endpoint,
)
from heritrace.routes.entity._blueprint import entity_bp
from heritrace.routes.entity._validation import validate_entity_data
from heritrace.utils.datatypes import DATATYPE_MAPPING, get_datatype_options
from heritrace.utils.display_rules_utils import (
    get_class_priority,
    is_entity_type_visible,
)
from heritrace.utils.primary_source_utils import (
    get_default_primary_source,
    save_user_default_primary_source,
)
from heritrace.utils.shacl_utils import find_matching_form_field
from heritrace.utils.sparql_utils import import_referenced_entities
from heritrace.utils.uri_utils import generate_unique_uri, is_valid_url
from heritrace.utils.virtual_properties import (
    remove_virtual_properties_from_creation_data,
    transform_entity_creation_with_virtual_properties,
)


def _prepare_entity_creation_data(
    structured_data: dict,
) -> tuple[dict, str]:
    cleaned_structured_data = remove_virtual_properties_from_creation_data(
        structured_data
    )
    entity_type: str = cleaned_structured_data["entity_type"]

    return cleaned_structured_data, entity_type


def _setup_editor_for_creation(editor: Editor, cleaned_structured_data: dict) -> None:
    import_referenced_entities(editor, cleaned_structured_data)
    editor.preexisting_finished()


def _process_virtual_properties_after_creation(
    editor: Editor,
    structured_data: dict,
    entity_uri: URIRef,
    default_graph_uri: URIRef | None,
) -> None:
    virtual_entities = transform_entity_creation_with_virtual_properties(
        structured_data, str(entity_uri)
    )

    if virtual_entities:
        editor.begin_counter_transaction()
        for virtual_entity in virtual_entities:
            virtual_entity_uri = generate_unique_uri(virtual_entity["entity_type"])
            create_nested_entity(
                editor, virtual_entity_uri, virtual_entity, default_graph_uri
            )

        editor.save()


def _create_entity_with_form_fields(
    editor: Editor,
    structured_data: dict,
    entity_uri: URIRef,
    default_graph_uri: URIRef | None,
    form_fields: dict,
) -> None:
    cleaned_structured_data = remove_virtual_properties_from_creation_data(
        structured_data
    )
    entity_type = cleaned_structured_data["entity_type"]
    properties = cleaned_structured_data.get("properties", {})

    _setup_editor_for_creation(editor, cleaned_structured_data)

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
            process_ordered_properties(ctx, values, URIRef(ordered_by))
        else:
            process_unordered_properties(ctx, values, matching_field_def)


def _create_entity_without_form_fields(
    editor: Editor,
    structured_data: dict,
    entity_uri: URIRef,
    default_graph_uri: URIRef | None,
) -> None:
    cleaned_structured_data = remove_virtual_properties_from_creation_data(
        structured_data
    )
    entity_type = cleaned_structured_data["entity_type"]
    properties = cleaned_structured_data.get("properties", {})

    editor.import_entity(entity_uri)
    _setup_editor_for_creation(editor, cleaned_structured_data)

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
                "errors": [gettext("Invalid primary source URL provided")],
            }
        ), 400

    if save_default_source and primary_source and is_valid_url(primary_source):
        save_user_default_primary_source(current_user.orcid, primary_source)

    if not structured_data.get("entity_type"):
        return jsonify(
            {"status": "error", "errors": [gettext("Entity type is required")]}
        ), 400

    cleaned_structured_data, entity_type = _prepare_entity_creation_data(
        structured_data
    )

    if form_fields:
        validation_errors = validate_entity_data(cleaned_structured_data)
        if validation_errors:
            return jsonify({"status": "error", "errors": validation_errors}), 400

    resp_agent = get_responsible_agent_uri(current_user.orcid)
    editor = Editor(
        EndpointConfig(
            dataset=get_dataset_endpoint(),
            provenance=get_provenance_endpoint(),
            is_quadstore=current_app.config["DATASET_IS_QUADSTORE"],
        ),
        current_app.config["COUNTER_HANDLER"],
        resp_agent,
        URIRef(primary_source) if primary_source else None,
        current_app.config["DATASET_GENERATION_TIME"],
        save_plugin=current_app.config.get("SAVE_PLUGIN"),
    )
    entity_uri = generate_unique_uri(entity_type)
    default_graph_uri = (
        URIRef(f"{entity_uri}/graph") if editor.dataset_is_quadstore else None
    )

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

    try:
        editor.save()
        _process_virtual_properties_after_creation(
            editor, structured_data, entity_uri, default_graph_uri
        )
    except (EditorError, OSError) as e:
        error_message = gettext(
            "An error occurred while creating the entity: %(error)s", error=str(e)
        )
        return jsonify({"status": "error", "errors": [error_message]}), 500
    else:
        response = jsonify(
            {
                "status": "success",
                "redirect_url": url_for("entity.about", subject=str(entity_uri)),
            }
        )
        flash(gettext("Entity created successfully"), "success")
        return response, 200


@entity_bp.route("/create-entity", methods=["GET", "POST"])
@login_required
def create_entity() -> str | tuple[Response, int]:
    form_fields = get_form_fields()

    default_primary_source = get_default_primary_source(current_user.orcid)

    entity_class_shape_pairs = sorted(
        [
            entity_key
            for entity_key in form_fields
            if is_entity_type_visible(entity_key)
        ],
        key=get_class_priority,
        reverse=True,
    )

    datatype_options = get_datatype_options()

    if request.method == "POST":
        structured_data = json.loads(request.form.get("structured_data", "{}"))
        primary_source = request.form.get("primary_source") or None
        save_default_source = request.form.get("save_default_source") == "true"
        return _handle_create_entity_post(
            form_fields,
            structured_data,
            primary_source,
            save_default_source=save_default_source,
        )

    return render_template(
        "create_entity.jinja",
        datatype_options=datatype_options,
        dataset_db_triplestore=current_app.config["DATASET_DB_TRIPLESTORE"],
        dataset_db_text_index_enabled=current_app.config[
            "DATASET_DB_TEXT_INDEX_ENABLED"
        ],
        default_primary_source=default_primary_source,
        shacl=bool(form_fields),
        entity_class_shape_pairs=entity_class_shape_pairs,
    )


def create_nested_entity(
    editor: Editor,
    entity_uri: URIRef,
    entity_data: dict,
    graph_uri: URIRef | None = None,
) -> None:
    form_fields = get_form_fields()

    editor.create(
        entity_uri,
        RDF.type,
        URIRef(entity_data["entity_type"]),
        graph_uri,
    )

    entity_type = entity_data.get("entity_type")
    entity_shape = entity_data.get("entity_shape")
    properties = entity_data.get("properties", {})

    matching_key = find_matching_form_field(entity_type, entity_shape, form_fields)

    if not matching_key:
        return

    for predicate, raw_values in properties.items():
        predicate_uri = URIRef(predicate)
        values = raw_values if isinstance(raw_values, list) else [raw_values]
        field_definitions = form_fields[matching_key].get(predicate, [])

        for value in values:
            if isinstance(value, dict) and "entity_type" in value:
                if "intermediateRelation" in value:
                    intermediate_uri = generate_unique_uri(
                        value["intermediateRelation"]["class"]
                    )
                    target_uri = generate_unique_uri(value["entity_type"])
                    editor.create(
                        entity_uri, predicate_uri, intermediate_uri, graph_uri
                    )
                    editor.create(
                        intermediate_uri,
                        URIRef(value["intermediateRelation"]["property"]),
                        target_uri,
                        graph_uri,
                    )
                    create_nested_entity(editor, target_uri, value, graph_uri)
                else:
                    nested_uri = generate_unique_uri(value["entity_type"])
                    editor.create(entity_uri, predicate_uri, nested_uri, graph_uri)
                    create_nested_entity(editor, nested_uri, value, graph_uri)
            elif isinstance(value, dict) and value.get("is_existing_entity", False):
                existing_entity_uri = value.get("entity_uri")
                if existing_entity_uri:
                    editor.create(
                        entity_uri,
                        predicate_uri,
                        URIRef(existing_entity_uri),
                        graph_uri,
                    )
            else:
                str_value = str(value)
                if is_valid_url(str_value):
                    object_value: URIRef | Literal = URIRef(str_value)
                else:
                    datatype = XSD.string
                    datatype_uris = []
                    if field_definitions:
                        datatype_uris = field_definitions[0].get("datatypes", [])
                    datatype = determine_datatype(str_value, datatype_uris)
                    object_value = Literal(str_value, datatype=datatype)
                editor.create(entity_uri, predicate_uri, object_value, graph_uri)


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
    if is_valid_url(str_value):
        object_value: URIRef | Literal = URIRef(str_value)
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
) -> None:
    values_by_shape = {}
    for value in values:
        shape = value.get("entity_shape")
        if not shape:
            shape = "default_shape"
        if shape not in values_by_shape:
            values_by_shape[shape] = []
        values_by_shape[shape].append(value)

    for shape_values in values_by_shape.values():
        previous_entity = None
        for value in shape_values:
            nested_uri = _process_ordered_entity_value(ctx, value)

            if previous_entity:
                ctx.editor.create(
                    previous_entity,
                    ordered_by,
                    nested_uri,
                    ctx.default_graph_uri,
                )
            previous_entity = nested_uri


def process_unordered_properties(
    ctx: CreationContext,
    values: list[dict | str],
    matching_field_def: dict | None,
) -> None:
    for value in values:
        process_entity_value(ctx, value, matching_field_def)


def determine_datatype(value: str, datatype_uris: list[str]) -> URIRef:
    for datatype_uri in datatype_uris:
        validation_func = next(
            (d[1] for d in DATATYPE_MAPPING if str(d[0]) == str(datatype_uri)), None
        )
        if validation_func and validation_func(value):
            return URIRef(datatype_uri)
    return XSD.string
