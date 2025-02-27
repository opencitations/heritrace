import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import validators
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_babel import gettext
from flask_login import current_user, login_required
from heritrace.editor import Editor
from heritrace.extensions import (
    get_change_tracking_config,
    get_custom_filter,
    get_dataset_endpoint,
    get_dataset_is_quadstore,
    get_display_rules,
    get_form_fields,
    get_provenance_endpoint,
    get_provenance_sparql,
    get_shacl_graph,
    get_sparql,
)
from heritrace.forms import *
from heritrace.utils.converters import convert_to_datetime
from heritrace.utils.display_rules_utils import (
    class_priorities,
    get_grouped_triples,
    get_highest_priority_class,
    get_property_order_from_rules,
    is_entity_type_visible,
)
from heritrace.utils.filters import Filter
from heritrace.utils.shacl_utils import get_valid_predicates
from heritrace.utils.sparql_utils import (
    fetch_current_state_with_related_entities,
    fetch_data_graph_for_subject,
    parse_sparql_update,
)
from heritrace.utils.virtuoso_utils import VIRTUOSO_EXCLUDED_GRAPHS, is_virtuoso
from rdflib import RDF, XSD, ConjunctiveGraph, Graph, Literal, URIRef
from resources.datatypes import DATATYPE_MAPPING
from SPARQLWrapper import JSON
from time_agnostic_library.agnostic_entity import AgnosticEntity

entity_bp = Blueprint("entity", __name__)


@entity_bp.route("/about/<path:subject>")
@login_required
def about(subject):
    """
    Display detailed information about an entity.

    Args:
        subject: URI of the entity to display
    """
    # Get necessary services and configurations
    change_tracking_config = get_change_tracking_config()

    # Initialize agnostic entity and get its history
    agnostic_entity = AgnosticEntity(
        res=subject, config=change_tracking_config, related_entities_history=True
    )
    history, provenance = agnostic_entity.get_history(include_prov_metadata=True)

    is_deleted = False
    context_snapshot = None
    subject_classes = []

    # Process entity history
    if history.get(subject):
        sorted_timestamps = sorted(history[subject].keys())
        latest_snapshot = history[subject][sorted_timestamps[-1]]
        latest_metadata = next(
            (
                meta
                for _, meta in provenance[subject].items()
                if meta["generatedAtTime"] == sorted_timestamps[-1]
            ),
            None,
        )

        is_deleted = (
            latest_metadata
            and "invalidatedAtTime" in latest_metadata
            and latest_metadata["invalidatedAtTime"]
        )

        if is_deleted and len(sorted_timestamps) > 1:
            context_snapshot = history[subject][sorted_timestamps[-2]]
            subject_classes = [
                o
                for _, _, o in context_snapshot.triples(
                    (URIRef(subject), RDF.type, None)
                )
            ]
        else:
            context_snapshot = None

    grouped_triples = {}
    can_be_added = []
    can_be_deleted = []
    datatypes = {}
    mandatory_values = {}
    optional_values = {}
    valid_predicates = []
    entity_type = None

    if not is_deleted:
        # Fetch current entity state
        data_graph = fetch_data_graph_for_subject(subject)
        if data_graph:
            triples = list(data_graph.triples((None, None, None)))
            # Get valid predicates and other metadata
            (
                can_be_added,
                can_be_deleted,
                datatypes,
                mandatory_values,
                optional_values,
                subject_classes,
                valid_predicates,
            ) = get_valid_predicates(triples)

            # Group triples for display
            grouped_triples, relevant_properties = get_grouped_triples(
                subject, triples, subject_classes, valid_predicates
            )

            can_be_added = [uri for uri in can_be_added if uri in relevant_properties]
            can_be_deleted = [
                uri for uri in can_be_deleted if uri in relevant_properties
            ]

    update_form = UpdateTripleForm()
    create_form = (
        CreateTripleFormWithSelect() if can_be_added else CreateTripleFormWithInput()
    )
    if can_be_added:
        create_form.predicate.choices = [
            (p, get_custom_filter().human_readable_predicate(p, subject_classes))
            for p in can_be_added
        ]

    form_fields = get_form_fields()
    entity_types = list(form_fields.keys())

    predicate_details_map = {}
    for entity_type, predicates in form_fields.items():
        for predicate_uri, details_list in predicates.items():
            for details in details_list:
                shape = details.get("nodeShape")
                key = (predicate_uri, entity_type, shape)
                predicate_details_map[key] = details

    entity_type = str(subject_classes[0]) if subject_classes else None

    inverse_references = get_inverse_references(subject)

    return render_template(
        "entity/about.jinja",
        subject=subject,
        history=history,
        can_be_added=can_be_added,
        can_be_deleted=can_be_deleted,
        datatypes=datatypes,
        update_form=update_form,
        create_form=create_form,
        mandatory_values=mandatory_values,
        optional_values=optional_values,
        shacl=bool(len(get_shacl_graph())),
        grouped_triples=grouped_triples,
        subject_classes=[str(s_class) for s_class in subject_classes],
        display_rules=get_display_rules(),
        form_fields=form_fields,
        entity_types=entity_types,
        entity_type=entity_type,
        predicate_details_map=predicate_details_map,
        dataset_db_triplestore=current_app.config["DATASET_DB_TRIPLESTORE"],
        dataset_db_text_index_enabled=current_app.config[
            "DATASET_DB_TEXT_INDEX_ENABLED"
        ],
        inverse_references=inverse_references,
        is_deleted=is_deleted,
        context=context_snapshot,
    )


@entity_bp.route("/create-entity", methods=["GET", "POST"])
@login_required
def create_entity():
    form_fields = get_form_fields()

    entity_types = sorted(
        [
            entity_type
            for entity_type in form_fields.keys()
            if is_entity_type_visible(entity_type)
        ],
        key=lambda et: class_priorities.get(et, 0),
        reverse=True,
    )

    datatype_options = {
        gettext("Text (string)"): XSD.string,
        gettext("Whole number (integer)"): XSD.integer,
        gettext("True or False (boolean)"): XSD.boolean,
        gettext("Date (YYYY-MM-DD)"): XSD.date,
        gettext("Date and Time (YYYY-MM-DDThh:mm:ss)"): XSD.dateTime,
        gettext("Decimal number"): XSD.decimal,
        gettext("Floating point number"): XSD.float,
        gettext("Double precision floating point number"): XSD.double,
        gettext("Time (hh:mm:ss)"): XSD.time,
        gettext("Year (YYYY)"): XSD.gYear,
        gettext("Month (MM)"): XSD.gMonth,
        gettext("Day of the month (DD)"): XSD.gDay,
        gettext("Duration (e.g., P1Y2M3DT4H5M6S)"): XSD.duration,
        gettext("Hexadecimal binary"): XSD.hexBinary,
        gettext("Base64 encoded binary"): XSD.base64Binary,
        gettext("Web address (URL)"): XSD.anyURI,
        gettext("Language code (e.g., en, it)"): XSD.language,
        gettext("Normalized text (no line breaks)"): XSD.normalizedString,
        gettext("Tokenized text (single word)"): XSD.token,
        gettext("Non-positive integer (0 or negative)"): XSD.nonPositiveInteger,
        gettext("Negative integer"): XSD.negativeInteger,
        gettext("Long integer"): XSD.long,
        gettext("Short integer"): XSD.short,
        gettext("Byte-sized integer"): XSD.byte,
        gettext("Non-negative integer (0 or positive)"): XSD.nonNegativeInteger,
        gettext("Positive integer (greater than 0)"): XSD.positiveInteger,
        gettext("Unsigned long integer"): XSD.unsignedLong,
        gettext("Unsigned integer"): XSD.unsignedInt,
        gettext("Unsigned short integer"): XSD.unsignedShort,
        gettext("Unsigned byte"): XSD.unsignedByte,
    }

    if request.method == "POST":
        structured_data = json.loads(request.form.get("structured_data", "{}"))
        validation_errors = validate_entity_data(structured_data, form_fields)

        if validation_errors:
            return jsonify({"status": "error", "errors": validation_errors}), 400

        editor = Editor(
            get_dataset_endpoint(),
            get_provenance_endpoint(),
            current_app.config["COUNTER_HANDLER"],
            URIRef(f"https://orcid.org/{current_user.orcid}"),
            current_app.config["PRIMARY_SOURCE"],
            current_app.config["DATASET_GENERATION_TIME"],
            dataset_is_quadstore=current_app.config["DATASET_IS_QUADSTORE"],
        )

        if get_form_fields():
            entity_type = structured_data.get("entity_type")
            properties = structured_data.get("properties", {})

            entity_uri = generate_unique_uri(entity_type)
            editor.preexisting_finished()

            default_graph_uri = (
                URIRef(f"{entity_uri}/graph") if editor.dataset_is_quadstore else None
            )

            for predicate, values in properties.items():
                if not isinstance(values, list):
                    values = [values]

                field_definitions = form_fields.get(entity_type, {}).get(predicate, [])

                # Get the shape from the property value if available
                property_shape = None
                if values and isinstance(values[0], dict):
                    property_shape = values[0].get("shape")

                # Filter field definitions to find the matching one based on shape
                matching_field_def = None
                for field_def in field_definitions:
                    if property_shape:
                        # If property has a shape, match it with the field definition's subjectShape
                        if field_def.get("subjectShape") == property_shape:
                            matching_field_def = field_def
                            break
                    else:
                        # If no shape specified, use the first field definition without a shape requirement
                        if not field_def.get("subjectShape"):
                            matching_field_def = field_def
                            break

                # If no matching field definition found, use the first one (default behavior)
                if not matching_field_def and field_definitions:
                    matching_field_def = field_definitions[0]

                ordered_by = (
                    matching_field_def.get("orderedBy") if matching_field_def else None
                )

                if ordered_by:
                    # Gestisci le proprietà ordinate per shape
                    values_by_shape = {}
                    for value in values:
                        # Ottieni la shape dell'entità
                        shape = value.get("shape")
                        if not shape:
                            shape = "default_shape"
                        if shape not in values_by_shape:
                            values_by_shape[shape] = []
                        values_by_shape[shape].append(value)

                    # Ora processa ogni gruppo di valori per shape separatamente
                    for shape, shape_values in values_by_shape.items():
                        previous_entity = None
                        for value in shape_values:
                            if isinstance(value, dict) and "entity_type" in value:
                                nested_uri = generate_unique_uri(value["entity_type"])
                                editor.create(
                                    entity_uri,
                                    URIRef(predicate),
                                    nested_uri,
                                    default_graph_uri,
                                )
                                create_nested_entity(
                                    editor,
                                    nested_uri,
                                    value,
                                    default_graph_uri,
                                    form_fields,
                                )
                            else:
                                # If it's a direct URI value (reference to existing entity)
                                nested_uri = URIRef(value)
                                editor.create(
                                    entity_uri,
                                    URIRef(predicate),
                                    nested_uri,
                                    default_graph_uri,
                                )

                            if previous_entity:
                                editor.create(
                                    previous_entity,
                                    URIRef(ordered_by),
                                    nested_uri,
                                    default_graph_uri,
                                )
                            previous_entity = nested_uri
                else:
                    # Gestisci le proprietà non ordinate
                    for value in values:
                        if isinstance(value, dict) and "entity_type" in value:
                            nested_uri = generate_unique_uri(value["entity_type"])
                            editor.create(
                                entity_uri,
                                URIRef(predicate),
                                nested_uri,
                                default_graph_uri,
                            )
                            create_nested_entity(
                                editor,
                                nested_uri,
                                value,
                                default_graph_uri,
                                form_fields,
                            )
                        else:
                            # Handle both URI references and literal values
                            if validators.url(str(value)):
                                object_value = URIRef(value)
                            else:
                                datatype_uris = []
                                if matching_field_def:
                                    datatype_uris = matching_field_def.get(
                                        "datatypes", []
                                    )
                                datatype = determine_datatype(value, datatype_uris)
                                object_value = Literal(value, datatype=datatype)
                            editor.create(
                                entity_uri,
                                URIRef(predicate),
                                object_value,
                                default_graph_uri,
                            )
        else:
            properties = structured_data.get("properties", {})

            entity_uri = generate_unique_uri()
            editor.import_entity(entity_uri)
            editor.preexisting_finished()

            default_graph_uri = (
                URIRef(f"{entity_uri}/graph") if editor.dataset_is_quadstore else None
            )

            for predicate, values in properties.items():
                if not isinstance(values, list):
                    values = [values]
                for value_dict in values:
                    if value_dict["type"] == "uri":
                        editor.create(
                            entity_uri,
                            URIRef(predicate),
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
                            URIRef(predicate),
                            Literal(value_dict["value"], datatype=datatype),
                            default_graph_uri,
                        )

        try:
            editor.save()
            response = jsonify(
                {
                    "status": "success",
                    "redirect_url": url_for("entity.about", subject=str(entity_uri)),
                }
            )
            flash(gettext("Entity created successfully"), "success")
            return response, 200
        except Exception as e:
            error_message = gettext(
                "An error occurred while creating the entity: %(error)s", error=str(e)
            )
            return jsonify({"status": "error", "errors": [error_message]}), 500

    return render_template(
        "create_entity.jinja",
        shacl=bool(get_form_fields()),
        entity_types=entity_types,
        form_fields=form_fields,
        datatype_options=datatype_options,
        dataset_db_triplestore=current_app.config["DATASET_DB_TRIPLESTORE"],
        dataset_db_text_index_enabled=current_app.config[
            "DATASET_DB_TEXT_INDEX_ENABLED"
        ],
    )


def create_nested_entity(
    editor: Editor, entity_uri, entity_data, graph_uri=None, form_fields=None
):
    # Add rdf:type
    editor.create(
        entity_uri,
        URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
        URIRef(entity_data["entity_type"]),
        graph_uri,
    )

    entity_type = entity_data.get("entity_type")
    properties = entity_data.get("properties", {})

    # Add other properties
    for predicate, values in properties.items():
        if not isinstance(values, list):
            values = [values]
        field_definitions = form_fields.get(entity_type, {}).get(predicate, [])
        for value in values:
            if isinstance(value, dict) and "entity_type" in value:
                if "intermediateRelation" in value:
                    intermediate_uri = generate_unique_uri(
                        value["intermediateRelation"]["class"]
                    )
                    target_uri = generate_unique_uri(value["entity_type"])
                    editor.create(
                        entity_uri, URIRef(predicate), intermediate_uri, graph_uri
                    )
                    editor.create(
                        intermediate_uri,
                        URIRef(value["intermediateRelation"]["property"]),
                        target_uri,
                        graph_uri,
                    )
                    create_nested_entity(
                        editor, target_uri, value, graph_uri, form_fields
                    )
                else:
                    # Handle nested entities
                    nested_uri = generate_unique_uri(value["entity_type"])
                    editor.create(entity_uri, URIRef(predicate), nested_uri, graph_uri)
                    create_nested_entity(
                        editor, nested_uri, value, graph_uri, form_fields
                    )
            else:
                # Handle simple properties
                datatype = XSD.string  # Default to string if not specified
                datatype_uris = []
                if field_definitions:
                    datatype_uris = field_definitions[0].get("datatypes", [])
                datatype = determine_datatype(value, datatype_uris)
                object_value = (
                    URIRef(value)
                    if validators.url(value)
                    else Literal(value, datatype=datatype)
                )
                editor.create(entity_uri, URIRef(predicate), object_value, graph_uri)


def determine_datatype(value, datatype_uris):
    for datatype_uri in datatype_uris:
        validation_func = next(
            (d[1] for d in DATATYPE_MAPPING if str(d[0]) == str(datatype_uri)), None
        )
        if validation_func and validation_func(value):
            return URIRef(datatype_uri)
    # If none match, default to XSD.string
    return XSD.string


def generate_unique_uri(entity_type: URIRef | str = None):
    entity_type = str(entity_type)
    uri = current_app.config["URI_GENERATOR"].generate_uri(entity_type)
    if hasattr(current_app.config["URI_GENERATOR"], "counter_handler"):
        current_app.config["URI_GENERATOR"].counter_handler.increment_counter(
            entity_type
        )
    return URIRef(uri)


def validate_entity_data(structured_data, form_fields):
    """
    Validates entity data against form field definitions, considering shape matching.

    Args:
        structured_data (dict): Data to validate containing entity_type and properties
        form_fields (dict): Form field definitions from SHACL shapes

    Returns:
        list: List of validation error messages, empty if validation passes
    """
    custom_filter = get_custom_filter()

    errors = []
    entity_type = structured_data.get("entity_type")
    if not entity_type:
        errors.append(gettext("Entity type is required"))
    elif entity_type not in form_fields:
        errors.append(
            gettext(
                "Invalid entity type selected: %(entity_type)s", entity_type=entity_type
            )
        )

    if errors:
        return errors

    entity_fields = form_fields.get(entity_type, {})
    properties = structured_data.get("properties", {})

    for prop_uri, prop_values in properties.items():
        if URIRef(prop_uri) == RDF.type:
            continue

        field_definitions = entity_fields.get(prop_uri)
        if not field_definitions:
            errors.append(
                gettext(
                    "Unknown property %(prop_uri)s for entity type %(entity_type)s",
                    prop_uri=prop_uri,
                    entity_type=entity_type,
                )
            )
            continue

        if not isinstance(prop_values, list):
            prop_values = [prop_values]

        # Get the shape from the property value if available
        property_shape = None
        if prop_values and isinstance(prop_values[0], dict):
            property_shape = prop_values[0].get("shape")

        # Filter field definitions to find the matching one based on shape
        matching_field_def = None
        for field_def in field_definitions:
            if property_shape:
                # If property has a shape, match it with the field definition's subjectShape
                if field_def.get("subjectShape") == property_shape:
                    matching_field_def = field_def
                    break
            else:
                # If no shape specified, use the first field definition without a shape requirement
                if not field_def.get("subjectShape"):
                    matching_field_def = field_def
                    break

        # If no matching field definition found, use the first one (default behavior)
        if not matching_field_def and field_definitions:
            matching_field_def = field_definitions[0]

        if matching_field_def:
            # Validate cardinality
            min_count = matching_field_def.get("min", 0)
            max_count = matching_field_def.get("max", None)
            value_count = len(prop_values)

            if value_count < min_count:
                value = gettext("values") if min_count > 1 else gettext("value")
                errors.append(
                    gettext(
                        "Property %(prop_uri)s requires at least %(min_count)d %(value)s",
                        prop_uri=custom_filter.human_readable_predicate(
                            prop_uri, [entity_type]
                        ),
                        min_count=min_count,
                        value=value,
                    )
                )
            if max_count is not None and value_count > max_count:
                value = gettext("values") if max_count > 1 else gettext("value")
                errors.append(
                    gettext(
                        "Property %(prop_uri)s allows at most %(max_count)d %(value)s",
                        prop_uri=custom_filter.human_readable_predicate(
                            prop_uri, [entity_type]
                        ),
                        max_count=max_count,
                        value=value,
                    )
                )

            # Validate mandatory values
            mandatory_values = matching_field_def.get("mandatory_values", [])
            for mandatory_value in mandatory_values:
                if mandatory_value not in prop_values:
                    errors.append(
                        gettext(
                            "Property %(prop_uri)s requires the value %(mandatory_value)s",
                            prop_uri=custom_filter.human_readable_predicate(
                                prop_uri, [entity_type]
                            ),
                            mandatory_value=mandatory_value,
                        )
                    )

            # Validate each value
            for value in prop_values:
                if isinstance(value, dict) and "entity_type" in value:
                    nested_errors = validate_entity_data(value, form_fields)
                    errors.extend(nested_errors)
                else:
                    # Validate against datatypes
                    datatypes = matching_field_def.get("datatypes", [])
                    if datatypes:
                        is_valid_datatype = False
                        for dtype in datatypes:
                            validation_func = next(
                                (
                                    d[1]
                                    for d in DATATYPE_MAPPING
                                    if d[0] == URIRef(dtype)
                                ),
                                None,
                            )
                            if validation_func and validation_func(value):
                                is_valid_datatype = True
                                break
                        if not is_valid_datatype:
                            expected_types = ", ".join(
                                [
                                    custom_filter.human_readable_predicate(
                                        dtype, form_fields.keys()
                                    )
                                    for dtype in datatypes
                                ]
                            )
                            errors.append(
                                gettext(
                                    'Value "%(value)s" for property %(prop_uri)s is not of expected type %(expected_types)s',
                                    value=value,
                                    prop_uri=custom_filter.human_readable_predicate(
                                        prop_uri, form_fields.keys()
                                    ),
                                    expected_types=expected_types,
                                )
                            )

                    # Validate against optional values
                    optional_values = matching_field_def.get("optionalValues", [])
                    if optional_values and value not in optional_values:
                        acceptable_values = ", ".join(
                            [
                                custom_filter.human_readable_predicate(
                                    val, form_fields.keys()
                                )
                                for val in optional_values
                            ]
                        )
                        errors.append(
                            gettext(
                                'Value "%(value)s" is not permitted for property %(prop_uri)s. Acceptable values are: %(acceptable_values)s',
                                value=value,
                                prop_uri=custom_filter.human_readable_predicate(
                                    prop_uri, form_fields.keys()
                                ),
                                acceptable_values=acceptable_values,
                            )
                        )

    return errors


@entity_bp.route("/entity-history/<path:entity_uri>")
@login_required
def entity_history(entity_uri):
    """
    Display the history of changes for an entity.

    Args:
        entity_uri: URI of the entity
    """
    custom_filter = get_custom_filter()
    change_tracking_config = get_change_tracking_config()

    agnostic_entity = AgnosticEntity(
        res=entity_uri, config=change_tracking_config, related_entities_history=True
    )
    history, provenance = agnostic_entity.get_history(include_prov_metadata=True)

    sorted_metadata = sorted(
        provenance[entity_uri].items(),
        key=lambda x: convert_to_datetime(x[1]["generatedAtTime"]),
    )
    sorted_timestamps = [
        convert_to_datetime(meta["generatedAtTime"], stringify=True)
        for _, meta in sorted_metadata
    ]

    # Get correct context for entity label
    latest_metadata = sorted_metadata[-1][1] if sorted_metadata else None
    is_latest_deletion = (
        latest_metadata
        and "invalidatedAtTime" in latest_metadata
        and latest_metadata["invalidatedAtTime"]
    )
    if is_latest_deletion and len(sorted_timestamps) > 1:
        context_snapshot = history[entity_uri][sorted_timestamps[-2]]
    else:
        context_snapshot = history[entity_uri][sorted_timestamps[-1]]

    entity_classes = set()
    classes = list(context_snapshot.triples((URIRef(entity_uri), RDF.type, None)))
    for triple in classes:
        entity_classes.add(str(triple[2]))
    entity_classes = [get_highest_priority_class(entity_classes)]

    # Generate timeline events
    events = []
    for i, (snapshot_uri, metadata) in enumerate(sorted_metadata):
        date = convert_to_datetime(metadata["generatedAtTime"])
        snapshot_timestamp_str = convert_to_datetime(
            metadata["generatedAtTime"], stringify=True
        )
        snapshot_graph = history[entity_uri][snapshot_timestamp_str]

        responsible_agent = custom_filter.format_agent_reference(
            metadata["wasAttributedTo"]
        )
        primary_source = custom_filter.format_source_reference(
            metadata["hadPrimarySource"]
        )

        modifications = metadata["hasUpdateQuery"]
        modification_text = ""
        if modifications:
            parsed_modifications = parse_sparql_update(modifications)
            modification_text = generate_modification_text(
                parsed_modifications,
                list(entity_classes),
                history=history,
                entity_uri=entity_uri,
                current_snapshot=snapshot_graph,
                current_snapshot_timestamp=snapshot_timestamp_str,
                custom_filter=custom_filter,
                form_fields=get_form_fields(),
            )

        description = metadata["description"].replace(
            entity_uri,
            custom_filter.human_readable_entity(
                entity_uri, entity_classes, context_snapshot
            ),
        )

        event = {
            "start_date": {
                "year": date.year,
                "month": date.month,
                "day": date.day,
                "hour": date.hour,
                "minute": date.minute,
                "second": date.second,
            },
            "text": {
                "headline": gettext("Snapshot") + " " + str(i + 1),
                "text": f"""
                    <p><strong>{gettext('Responsible agent')}:</strong> {responsible_agent}</p>
                    <p><strong>{gettext('Primary source')}:</strong> {primary_source}</p>
                    <p><strong>{gettext('Description')}:</strong> {description}</p>
                    <div class="modifications mb-3">
                        {modification_text}
                    </div>
                    <a href='/entity-version/{entity_uri}/{metadata["generatedAtTime"]}' class='btn btn-outline-primary mt-2 view-version' target='_self'>{gettext('View version')}</a>
                """,
            },
            "autolink": False,
        }

        if i + 1 < len(sorted_metadata):
            next_date = convert_to_datetime(
                sorted_metadata[i + 1][1]["generatedAtTime"]
            )
            event["end_date"] = {
                "year": next_date.year,
                "month": next_date.month,
                "day": next_date.day,
                "hour": next_date.hour,
                "minute": next_date.minute,
                "second": next_date.second,
            }

        events.append(event)

    entity_label = custom_filter.human_readable_entity(
        entity_uri, entity_classes, context_snapshot
    )

    timeline_data = {
        "entityUri": entity_uri,
        "entityLabel": entity_label,
        "entityClasses": list(entity_classes),
        "events": events,
    }

    return render_template("entity/history.jinja", timeline_data=timeline_data)


@entity_bp.route("/entity-version/<path:entity_uri>/<timestamp>")
@login_required
def entity_version(entity_uri, timestamp):
    """
    Display a specific version of an entity.

    Args:
        entity_uri: URI of the entity
        timestamp: Timestamp of the version to display
    """
    custom_filter = get_custom_filter()
    form_fields = get_form_fields()
    change_tracking_config = get_change_tracking_config()

    try:
        timestamp_dt = datetime.fromisoformat(timestamp)
    except ValueError:
        # Try to get timestamp from provenance graph
        provenance_sparql = get_provenance_sparql()
        query_timestamp = f"""
            SELECT ?generation_time
            WHERE {{
                <{entity_uri}/prov/se/{timestamp}> <http://www.w3.org/ns/prov#generatedAtTime> ?generation_time.
            }}
        """
        provenance_sparql.setQuery(query_timestamp)
        provenance_sparql.setReturnFormat(JSON)
        try:
            generation_time = provenance_sparql.queryAndConvert()["results"][
                "bindings"
            ][0]["generation_time"]["value"]
        except IndexError:
            abort(404)
        timestamp = generation_time
        timestamp_dt = datetime.fromisoformat(generation_time)

    # Get entity history
    agnostic_entity = AgnosticEntity(
        res=entity_uri, config=change_tracking_config, related_entities_history=True
    )
    history, provenance = agnostic_entity.get_history(include_prov_metadata=True)

    # Find closest snapshot
    main_entity_history = history.get(entity_uri, {})
    sorted_timestamps = sorted(
        main_entity_history.keys(), key=lambda t: convert_to_datetime(t)
    )

    if not sorted_timestamps:
        abort(404)

    closest_timestamp = min(
        sorted_timestamps,
        key=lambda t: abs(
            convert_to_datetime(t).astimezone() - timestamp_dt.astimezone()
        ),
    )

    version = main_entity_history[closest_timestamp]
    triples = list(version.triples((URIRef(entity_uri), None, None)))

    # Get metadata
    entity_metadata = provenance.get(entity_uri, {})
    closest_metadata = None
    min_time_diff = None

    latest_timestamp = max(sorted_timestamps)
    latest_metadata = None

    for se_uri, meta in entity_metadata.items():
        meta_time = convert_to_datetime(meta["generatedAtTime"])
        time_diff = abs((meta_time - timestamp_dt).total_seconds())

        if closest_metadata is None or time_diff < min_time_diff:
            closest_metadata = meta
            min_time_diff = time_diff

        if meta["generatedAtTime"] == latest_timestamp:
            latest_metadata = meta

    if closest_metadata is None or latest_metadata is None:
        abort(404)

    # Check if this is a deletion snapshot
    is_deletion_snapshot = (
        closest_timestamp == latest_timestamp
        and "invalidatedAtTime" in latest_metadata
        and latest_metadata["invalidatedAtTime"]
    ) or len(triples) == 0

    # Use appropriate snapshot for context
    context_version = version
    if is_deletion_snapshot and len(sorted_timestamps) > 1:
        current_index = sorted_timestamps.index(closest_timestamp)
        if current_index > 0:
            context_version = main_entity_history[sorted_timestamps[current_index - 1]]

    # Get subject classes
    if is_deletion_snapshot and len(sorted_timestamps) > 1:
        subject_classes = [
            o
            for _, _, o in context_version.triples((URIRef(entity_uri), RDF.type, None))
        ]
    else:
        subject_classes = [
            o for _, _, o in version.triples((URIRef(entity_uri), RDF.type, None))
        ]

    subject_classes = [get_highest_priority_class(subject_classes)]

    # Process and group triples
    _, _, _, _, _, _, valid_predicates = get_valid_predicates(triples)
    grouped_triples, relevant_properties = get_grouped_triples(
        entity_uri,
        triples,
        subject_classes,
        valid_predicates,
        historical_snapshot=context_version,
    )

    # Calculate version number
    snapshot_times = [
        convert_to_datetime(meta["generatedAtTime"])
        for meta in entity_metadata.values()
    ]
    snapshot_times = sorted(set(snapshot_times))
    version_number = snapshot_times.index(timestamp_dt) + 1

    # Find next and previous snapshots
    next_snapshot_timestamp = None
    prev_snapshot_timestamp = None

    for snap_time in snapshot_times:
        if snap_time > timestamp_dt:
            next_snapshot_timestamp = snap_time.isoformat()
            break

    for snap_time in reversed(snapshot_times):
        if snap_time < timestamp_dt:
            prev_snapshot_timestamp = snap_time.isoformat()
            break

    # Generate modification text if update query exists
    modifications = ""
    if closest_metadata.get("hasUpdateQuery"):
        sparql_query = closest_metadata["hasUpdateQuery"]
        parsed_modifications = parse_sparql_update(sparql_query)
        modifications = generate_modification_text(
            parsed_modifications,
            subject_classes,
            history=history,
            entity_uri=entity_uri,
            current_snapshot=version,
            current_snapshot_timestamp=closest_timestamp,
            custom_filter=custom_filter,
            form_fields=form_fields,
        )

    # Update description with human readable entity name
    if closest_metadata.get("description"):
        closest_metadata["description"] = closest_metadata["description"].replace(
            entity_uri,
            custom_filter.human_readable_entity(
                entity_uri, subject_classes, context_version
            ),
        )

    closest_timestamp = closest_metadata["generatedAtTime"]

    return render_template(
        "entity/version.jinja",
        subject=entity_uri,
        metadata={closest_timestamp: closest_metadata},
        timestamp=closest_timestamp,
        next_snapshot_timestamp=next_snapshot_timestamp,
        prev_snapshot_timestamp=prev_snapshot_timestamp,
        modifications=modifications,
        grouped_triples=grouped_triples,
        subject_classes=subject_classes,
        version_number=version_number,
        version=context_version,
    )


@entity_bp.route("/restore-version/<path:entity_uri>/<timestamp>", methods=["POST"])
@login_required
def restore_version(entity_uri, timestamp):
    """
    Restore an entity to a previous version.

    Args:
        entity_uri: URI of the entity to restore
        timestamp: Timestamp of the version to restore to
    """
    timestamp = convert_to_datetime(timestamp, stringify=True)
    change_tracking_config = get_change_tracking_config()

    # Get entity history
    agnostic_entity = AgnosticEntity(
        res=entity_uri, config=change_tracking_config, related_entities_history=True
    )
    history, provenance = agnostic_entity.get_history(include_prov_metadata=True)

    historical_graph = history.get(entity_uri, {}).get(timestamp)
    if historical_graph is None:
        abort(404)

    current_graph = fetch_current_state_with_related_entities(provenance)

    is_deleted = len(list(current_graph.triples((URIRef(entity_uri), None, None)))) == 0

    triples_or_quads_to_delete, triples_or_quads_to_add = compute_graph_differences(
        current_graph, historical_graph
    )

    # Get all entities that need restoration
    entities_to_restore = get_entities_to_restore(
        triples_or_quads_to_delete, triples_or_quads_to_add, entity_uri
    )

    # Prepare snapshot information for all entities
    entity_snapshots = prepare_entity_snapshots(
        entities_to_restore, provenance, timestamp
    )

    # Create editor instance
    editor = Editor(
        get_dataset_endpoint(),
        get_provenance_endpoint(),
        current_app.config["COUNTER_HANDLER"],
        URIRef(f"https://orcid.org/{current_user.orcid}"),
        None if is_deleted else entity_snapshots[entity_uri]["source"],
        current_app.config["DATASET_GENERATION_TIME"],
        dataset_is_quadstore=current_app.config["DATASET_IS_QUADSTORE"],
    )

    # Import current state into editor
    if get_dataset_is_quadstore():
        for quad in current_graph.quads():
            editor.g_set.add(quad)
    else:
        for triple in current_graph:
            editor.g_set.add(triple)

    editor.preexisting_finished()

    # Apply deletions
    for item in triples_or_quads_to_delete:
        if len(item) == 4:
            editor.delete(item[0], item[1], item[2], item[3])
        else:
            editor.delete(item[0], item[1], item[2])

        subject = str(item[0])
        if subject in entity_snapshots:
            entity_info = entity_snapshots[subject]
            if entity_info["needs_restore"]:
                editor.g_set.mark_as_restored(URIRef(subject))
            editor.g_set.entity_index[URIRef(subject)]["restoration_source"] = (
                entity_info["source"]
            )

    # Apply additions
    for item in triples_or_quads_to_add:
        if len(item) == 4:
            editor.create(item[0], item[1], item[2], item[3])
        else:
            editor.create(item[0], item[1], item[2])

        subject = str(item[0])
        if subject in entity_snapshots:
            entity_info = entity_snapshots[subject]
            if entity_info["needs_restore"]:
                editor.g_set.mark_as_restored(URIRef(subject))
                editor.g_set.entity_index[URIRef(subject)]["source"] = entity_info[
                    "source"
                ]

    # Handle main entity restoration if needed
    if is_deleted and entity_uri in entity_snapshots:
        editor.g_set.mark_as_restored(URIRef(entity_uri))
        source = entity_snapshots[entity_uri]["source"]
        editor.g_set.entity_index[URIRef(entity_uri)]["source"] = source

    try:
        editor.save()
        flash(gettext("Version restored successfully"), "success")
    except Exception as e:
        flash(
            gettext(
                "An error occurred while restoring the version: %(error)s", error=str(e)
            ),
            "error",
        )

    return redirect(url_for("entity.about", subject=entity_uri))


def compute_graph_differences(
    current_graph: Graph | ConjunctiveGraph, historical_graph: Graph | ConjunctiveGraph
):
    if get_dataset_is_quadstore():
        current_data = set(current_graph.quads())
        historical_data = set(historical_graph.quads())
    else:
        current_data = set(current_graph.quads())
        historical_data = set(historical_graph.quads())
    triples_or_quads_to_delete = current_data - historical_data
    triples_or_quads_to_add = historical_data - current_data

    return triples_or_quads_to_delete, triples_or_quads_to_add


def get_entities_to_restore(
    triples_or_quads_to_delete: set, triples_or_quads_to_add: set, main_entity_uri: str
) -> set:
    """
    Identify all entities that need to be restored based on the graph differences.

    Args:
        triples_or_quads_to_delete: Set of triples/quads to be deleted
        triples_or_quads_to_add: Set of triples/quads to be added
        main_entity_uri: URI of the main entity being restored

    Returns:
        Set of entity URIs that need to be restored
    """
    entities_to_restore = {main_entity_uri}

    for item in list(triples_or_quads_to_delete) + list(triples_or_quads_to_add):
        predicate = str(item[1])
        if predicate == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type":
            continue

        subject = str(item[0])
        obj = str(item[2])
        for uri in [subject, obj]:
            if uri != main_entity_uri and validators.url(uri):
                entities_to_restore.add(uri)

    return entities_to_restore


def prepare_entity_snapshots(
    entities_to_restore: set, provenance: dict, target_time: str
) -> dict:
    """
    Prepare snapshot information for all entities that need to be restored.

    Args:
        entities_to_restore: Set of entity URIs to process
        provenance: Dictionary containing provenance data for all entities
        target_time: Target restoration time

    Returns:
        Dictionary mapping entity URIs to their restoration information
    """
    entity_snapshots = {}

    for entity_uri in entities_to_restore:
        if entity_uri not in provenance:
            continue

        # Find the appropriate source snapshot
        source_snapshot = find_appropriate_snapshot(provenance[entity_uri], target_time)
        if not source_snapshot:
            continue

        # Check if entity is currently deleted by examining its latest snapshot
        sorted_snapshots = sorted(
            provenance[entity_uri].items(),
            key=lambda x: convert_to_datetime(x[1]["generatedAtTime"]),
        )
        latest_snapshot = sorted_snapshots[-1][1]
        is_deleted = (
            latest_snapshot.get("invalidatedAtTime")
            and latest_snapshot["generatedAtTime"]
            == latest_snapshot["invalidatedAtTime"]
        )

        entity_snapshots[entity_uri] = {
            "source": source_snapshot,
            "needs_restore": is_deleted,
        }

    return entity_snapshots


def find_appropriate_snapshot(provenance_data: dict, target_time: str) -> Optional[str]:
    """
    Find the most appropriate snapshot to use as a source for restoration.

    Args:
        provenance_data: Dictionary of snapshots and their metadata for an entity
        target_time: The target restoration time as ISO format string

    Returns:
        The URI of the most appropriate snapshot, or None if no suitable snapshot is found
    """
    target_datetime = convert_to_datetime(target_time)

    # Convert all generation times to datetime for comparison
    valid_snapshots = []
    for snapshot_uri, metadata in provenance_data.items():
        generation_time = convert_to_datetime(metadata["generatedAtTime"])

        # Skip deletion snapshots (where generation time equals invalidation time)
        if (
            metadata.get("invalidatedAtTime")
            and metadata["generatedAtTime"] == metadata["invalidatedAtTime"]
        ):
            continue

        # Only consider snapshots up to our target time
        if generation_time <= target_datetime:
            valid_snapshots.append((generation_time, snapshot_uri))

    if not valid_snapshots:
        return None

    # Sort by generation time and take the most recent one
    valid_snapshots.sort(key=lambda x: x[0])
    return valid_snapshots[-1][1]


def get_inverse_references(subject_uri: str) -> List[Dict]:
    """
    Get all entities that reference this entity.

    Args:
        subject_uri: URI of the entity to find references to

    Returns:
        List of dictionaries containing reference information
    """
    sparql = get_sparql()
    custom_filter = get_custom_filter()

    # Build appropriate query based on triplestore type
    if is_virtuoso:
        query = f"""
        SELECT DISTINCT ?s ?p ?g WHERE {{
            GRAPH ?g {{
                ?s ?p <{subject_uri}> .
            }}
            FILTER(?g NOT IN (<{'>, <'.join(VIRTUOSO_EXCLUDED_GRAPHS)}>))
            FILTER(?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
        }}
        """
    else:
        query = f"""
        SELECT DISTINCT ?s ?p WHERE {{
            ?s ?p <{subject_uri}> .
            FILTER(?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
        }}
        """

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    references = []
    for result in results["results"]["bindings"]:
        subject = result["s"]["value"]
        predicate = result["p"]["value"]

        # Get the type of the referring entity
        type_query = f"""
        SELECT ?type WHERE {{
            <{subject}> a ?type .
        }}
        """
        sparql.setQuery(type_query)
        type_results = sparql.query().convert()
        types = [t["type"]["value"] for t in type_results["results"]["bindings"]]
        types = [get_highest_priority_class(types)]

        references.append({"subject": subject, "predicate": predicate, "types": types})

    return references


def generate_modification_text(
    modifications,
    subject_classes,
    history,
    entity_uri,
    current_snapshot,
    current_snapshot_timestamp,
    custom_filter: Filter,
    form_fields,
):
    """
    Generate HTML text describing modifications to an entity, using display rules for property ordering.

    Args:
        modifications (dict): Dictionary of modifications from parse_sparql_update
        subject_classes (list): List of classes for the subject entity
        history (dict): Historical snapshots dictionary
        entity_uri (str): URI of the entity being modified
        current_snapshot (Graph): Current entity snapshot
        current_snapshot_timestamp (str): Timestamp of current snapshot
        custom_filter (Filter): Filter instance for formatting
        form_fields (dict): Form fields configuration from SHACL
    """
    modification_text = "<p><strong>" + gettext("Modifications") + "</strong></p>"

    # Get display rules and property order
    display_rules = get_display_rules()
    ordered_properties = get_property_order_from_rules(subject_classes, display_rules)

    for mod_type, triples in modifications.items():
        modification_text += "<ul class='list-group mb-3'><p>"
        if mod_type == gettext("Additions"):
            modification_text += '<i class="bi bi-plus-circle-fill text-success"></i>'
        elif mod_type == gettext("Deletions"):
            modification_text += '<i class="bi bi-dash-circle-fill text-danger"></i>'
        modification_text += " <em>" + gettext(mod_type) + "</em></p>"

        # Group triples by predicate
        predicate_groups = {}
        for triple in triples:
            predicate = str(triple[1])
            if predicate not in predicate_groups:
                predicate_groups[predicate] = []
            predicate_groups[predicate].append(triple)

        # Process predicates in order from display rules
        processed_predicates = set()

        # First handle predicates that are in the ordered list
        for predicate in ordered_properties:
            if predicate in predicate_groups:
                processed_predicates.add(predicate)
                for triple in predicate_groups[predicate]:
                    modification_text += format_triple_modification(
                        triple,
                        subject_classes,
                        mod_type,
                        history,
                        entity_uri,
                        current_snapshot,
                        current_snapshot_timestamp,
                        custom_filter,
                        form_fields,
                    )

        # Then handle any remaining predicates not in the ordered list
        for predicate, triples in predicate_groups.items():
            if predicate not in processed_predicates:
                for triple in triples:
                    modification_text += format_triple_modification(
                        triple,
                        subject_classes,
                        mod_type,
                        history,
                        entity_uri,
                        current_snapshot,
                        current_snapshot_timestamp,
                        custom_filter,
                        form_fields,
                    )

        modification_text += "</ul>"

    return modification_text


def format_triple_modification(
    triple,
    subject_classes,
    mod_type,
    history,
    entity_uri,
    current_snapshot,
    current_snapshot_timestamp,
    custom_filter: Filter,
    form_fields,
):
    """
    Format a single triple modification as HTML.

    Args:
        triple: The RDF triple being modified
        subject_classes: List of classes for the subject entity
        mod_type: Type of modification (addition/deletion)
        history: Historical snapshots dictionary
        entity_uri: URI of the entity being modified
        current_snapshot: Current entity snapshot
        current_snapshot_timestamp: Timestamp of current snapshot
        custom_filter: Filter instance for formatting
        form_fields: Form fields configuration from SHACL

    Returns:
        HTML string representing the triple modification
    """
    predicate = triple[1]
    predicate_label = custom_filter.human_readable_predicate(predicate, subject_classes)
    object_value = triple[2]

    # Determine which snapshot to use for context
    relevant_snapshot = None
    if (
        mod_type == gettext("Deletions")
        and history
        and entity_uri
        and current_snapshot_timestamp
    ):
        sorted_timestamps = sorted(history[entity_uri].keys())
        current_index = sorted_timestamps.index(current_snapshot_timestamp)
        if current_index > 0:
            relevant_snapshot = history[entity_uri][
                sorted_timestamps[current_index - 1]
            ]
    else:
        relevant_snapshot = current_snapshot

    subject_class = get_highest_priority_class(subject_classes)

    object_label = get_object_label(
        object_value,
        predicate,
        subject_class,
        form_fields,
        relevant_snapshot,
        custom_filter,
    )

    return f"""
        <li class='d-flex align-items-center'>
            <span class='flex-grow-1 d-flex flex-column justify-content-center ms-3 mb-2 w-100'>
                <strong>{predicate_label}</strong>
                <span class="object-value word-wrap">{object_label}</span>
            </span>
        </li>"""


def get_object_label(
    object_value: str,
    predicate: str,
    entity_type: str,
    form_fields: dict,
    snapshot: Optional[Graph],
    custom_filter: Filter,
) -> str:
    """
    Get appropriate display label for an object value based on form fields configuration.

    Args:
        object_value: The value to get a label for
        predicate: The predicate URI
        entity_type: The type of the entity
        form_fields: Form fields configuration from SHACL
        snapshot: Optional graph snapshot for context
        custom_filter: Custom filter instance for formatting

    Returns:
        A human-readable label for the object value
    """
    entity_type = str(entity_type)
    predicate = str(predicate)

    # Handle RDF type predicates
    if predicate == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type":
        return custom_filter.human_readable_predicate(
            object_value, [entity_type]
        ).title()

    if form_fields and entity_type in form_fields:
        predicate_fields = form_fields[entity_type].get(predicate, [])
        for field in predicate_fields:
            # Check if this is an entity reference
            if field.get("nodeShape") or field.get("objectClass"):
                if validators.url(object_value):
                    # Get types for the referenced entity
                    object_classes = []
                    if snapshot:
                        object_classes = [
                            str(o)
                            for s, p, o in snapshot.triples(
                                (URIRef(object_value), RDF.type, None)
                            )
                        ]

                    if not object_classes and field.get("objectClass"):
                        object_classes = [field["objectClass"]]

                    return custom_filter.human_readable_entity(
                        object_value, object_classes, snapshot
                    )

            # Check for mandatory values
            if field.get("hasValue") == object_value:
                return custom_filter.human_readable_predicate(
                    object_value, [entity_type]
                )

            # Check for optional values from a predefined set
            if object_value in field.get("optionalValues", []):
                return custom_filter.human_readable_predicate(
                    object_value, [entity_type]
                )

    # Default to simple string representation for literal values
    if not validators.url(object_value):
        return object_value

    # For any other URIs, use human_readable_predicate
    return custom_filter.human_readable_predicate(object_value, [entity_type])


def process_modification_data(data: dict) -> Tuple[str, List[dict]]:
    """
    Process modification data to extract subjects and predicates.

    Args:
        data: Dictionary containing modification data

    Returns:
        Tuple containing subject URI and list of modification details
    """
    subject_uri = data.get("subject")
    if not subject_uri:
        raise ValueError("No subject URI provided in modification data")

    modifications = data.get("modifications", [])
    if not modifications:
        raise ValueError("No modifications provided in data")

    return subject_uri, modifications


def validate_modification(
    modification: dict, subject_uri: str, form_fields: dict
) -> Tuple[bool, str]:
    """
    Validate a single modification operation.

    Args:
        modification: Dictionary containing modification details
        subject_uri: URI of the subject being modified
        form_fields: Form fields configuration from SHACL

    Returns:
        Tuple of (is_valid, error_message)
    """
    operation = modification.get("operation")
    if not operation:
        return False, "No operation specified in modification"

    predicate = modification.get("predicate")
    if not predicate:
        return False, "No predicate specified in modification"

    if operation not in ["add", "remove", "update"]:
        return False, f"Invalid operation: {operation}"

    # Additional validation based on form fields if available
    if form_fields:
        entity_types = [str(t) for t in get_entity_types(subject_uri)]
        entity_type = get_highest_priority_class(entity_types)

        if entity_type in form_fields:
            predicate_fields = form_fields[entity_type].get(predicate, [])

            for field in predicate_fields:
                if operation == "remove" and field.get("minCount", 0) > 0:
                    return False, f"Cannot remove required predicate: {predicate}"

                if operation == "add":
                    current_count = get_predicate_count(subject_uri, predicate)
                    max_count = field.get("maxCount")

                    if max_count and current_count >= max_count:
                        return (
                            False,
                            f"Maximum count exceeded for predicate: {predicate}",
                        )

    return True, ""


def get_entity_types(subject_uri: str) -> List[str]:
    """
    Get all RDF types for an entity.

    Args:
        subject_uri: URI of the entity

    Returns:
        List of type URIs
    """
    sparql = get_sparql()

    query = f"""
    SELECT ?type WHERE {{
        <{subject_uri}> a ?type .
    }}
    """

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    return [result["type"]["value"] for result in results["results"]["bindings"]]


def get_predicate_count(subject_uri: str, predicate: str) -> int:
    """
    Get the current count of values for a predicate.

    Args:
        subject_uri: URI of the entity
        predicate: Predicate URI to count

    Returns:
        Number of values for the predicate
    """
    sparql = get_sparql()

    query = f"""
    SELECT (COUNT(?o) as ?count) WHERE {{
        <{subject_uri}> <{predicate}> ?o .
    }}
    """

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    return int(results["results"]["bindings"][0]["count"]["value"])


def apply_modifications(
    editor: Editor,
    modifications: List[dict],
    subject_uri: str,
    graph_uri: Optional[str] = None,
):
    """
    Apply a list of modifications to an entity.

    Args:
        editor: Editor instance to use for modifications
        modifications: List of modification operations
        subject_uri: URI of the entity being modified
        graph_uri: Optional graph URI for quad store
    """
    for mod in modifications:
        operation = mod["operation"]
        predicate = mod["predicate"]

        if operation == "remove":
            editor.delete(URIRef(subject_uri), URIRef(predicate), graph_uri=graph_uri)

        elif operation == "add":
            value = mod["value"]
            datatype = mod.get("datatype", XSD.string)

            if validators.url(value):
                object_value = URIRef(value)
            else:
                object_value = Literal(value, datatype=URIRef(datatype))

            editor.create(
                URIRef(subject_uri), URIRef(predicate), object_value, graph_uri
            )

        elif operation == "update":
            old_value = mod["oldValue"]
            new_value = mod["newValue"]
            datatype = mod.get("datatype", XSD.string)

            if validators.url(old_value):
                old_object = URIRef(old_value)
            else:
                old_object = Literal(old_value, datatype=URIRef(datatype))

            if validators.url(new_value):
                new_object = URIRef(new_value)
            else:
                new_object = Literal(new_value, datatype=URIRef(datatype))

            editor.update(
                URIRef(subject_uri),
                URIRef(predicate),
                old_object,
                new_object,
                graph_uri,
            )
