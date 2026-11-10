# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from flask import Response, abort, jsonify
from flask_login import login_required
from rdflib import RDF, Graph, Literal, URIRef
from time_agnostic_library.agnostic_entity import AgnosticEntity

from heritrace.extensions import (
    get_change_tracking_config,
    get_custom_filter,
    get_dataset_is_quadstore,
    get_form_fields,
    get_presentation,
    get_shacl_graph,
)
from heritrace.routes.entity._blueprint import entity_bp
from heritrace.utils.display_rules_utils import (
    get_grouped_triples,
    get_highest_priority_class,
)
from heritrace.utils.filters import field_with_labels
from heritrace.utils.shacl_presentation import is_inverse_path
from heritrace.utils.shacl_utils import determine_shape_for_entity_triples
from heritrace.utils.shacl_validation import get_valid_predicates
from heritrace.utils.sparql_utils import (
    convert_to_rdflib_graphs,
    fetch_data_graph_for_subject,
    get_triples_from_graph,
)

RDF_TYPE = str(RDF.type)


def get_deleted_entity_context_info(
    *,
    is_deleted: bool,
    sorted_timestamps: list[str],
    history: dict,
    subject: URIRef,
) -> tuple[Graph | None, str | None, str | None]:
    if is_deleted and len(sorted_timestamps) > 1:
        context_snapshot = history[str(subject)][sorted_timestamps[-2]]

        subject_classes = [
            str(o)
            for _, _, o in get_triples_from_graph(
                context_snapshot, (subject, RDF.type, None)
            )
        ]

        highest_priority_class = get_highest_priority_class(subject_classes)
        entity_shape = determine_shape_for_entity_triples(
            list(get_triples_from_graph(context_snapshot, (subject, None, None)))
        )

        return context_snapshot, highest_priority_class, entity_shape
    return None, None, None


def _build_live_entity_context(
    subject_uri: URIRef,
    history: dict,
    subject: str,
) -> tuple[dict, list, list, dict, dict, dict, str | None, str | None, list[str]]:
    data_graph = fetch_data_graph_for_subject(subject_uri)

    if not history.get(subject) and (not data_graph or len(data_graph) == 0):
        abort(404)

    if not data_graph:
        return {}, [], [], {}, {}, {}, None, None, []

    triples: list[tuple[URIRef, URIRef, URIRef | Literal]] = [
        (
            URIRef(str(s)),
            URIRef(str(p)),
            URIRef(str(o)) if isinstance(o, URIRef) else o,
        )  # type: ignore[misc]
        for s, p, o in get_triples_from_graph(data_graph, (None, None, None))
    ]
    subject_classes = [
        str(o)
        for _, _, o in get_triples_from_graph(data_graph, (subject_uri, RDF.type, None))
    ]
    subject_triples = list(
        get_triples_from_graph(data_graph, (subject_uri, None, None))
    )

    highest_priority_class = get_highest_priority_class(subject_classes)
    entity_shape = determine_shape_for_entity_triples(subject_triples)

    if not highest_priority_class:
        return (
            {},
            [],
            [],
            {},
            {},
            {},
            highest_priority_class,
            entity_shape,
            subject_classes,
        )

    (
        can_be_added,
        can_be_deleted,
        datatypes,
        mandatory_values,
        optional_values,
        valid_predicates_set,
    ) = get_valid_predicates(
        triples, highest_priority_class=URIRef(highest_priority_class)
    )
    valid_predicates = list(valid_predicates_set)

    grouped_triples, relevant_properties = get_grouped_triples(
        subject_uri,
        triples,
        valid_predicates,
        entity_key=(highest_priority_class, entity_shape),
    )

    inverse_paths = [
        prop.path
        for prop in get_presentation().shape_properties(entity_shape)
        if is_inverse_path(prop.path)
    ]

    can_be_added = [
        uri for uri in can_be_added if uri in relevant_properties
    ] + inverse_paths
    can_be_deleted = [
        uri for uri in can_be_deleted if uri in relevant_properties
    ] + inverse_paths

    return (
        grouped_triples,
        can_be_added,
        can_be_deleted,
        datatypes,
        mandatory_values,
        optional_values,
        highest_priority_class,
        entity_shape,
        subject_classes,
    )


def _field_for_group(
    predicate: str,
    entity_type: str | None,
    subject_shape: str | None,
    object_shape: str | None,
) -> dict | None:
    for details in (
        get_form_fields().get((entity_type, subject_shape), {}).get(predicate, [])
    ):
        if details.get("nodeShape") == object_shape:
            return field_with_labels(details, get_custom_filter())
    return None


def _value_label(
    predicate: str, value: str, subject_class: str | None, subject_shape: str | None
) -> str:
    custom_filter = get_custom_filter()
    if predicate == RDF_TYPE:
        return custom_filter.human_readable_class((value, None))
    return custom_filter.human_readable_predicate(value, (subject_class, subject_shape))


def _serialize_group(
    display_name: str,
    data: dict,
    entity_type: str | None,
    mandatory_values: dict,
    optional_values: dict,
) -> dict:
    predicate = data["property"]
    subject_class = data.get("subjectClass")
    subject_shape = data.get("subjectShape")
    object_shape = data.get("objectShape")
    predicate_mandatory = mandatory_values.get(predicate, [])
    triples = [
        {
            "subject": str(triple_data["triple"][0]),
            "predicate": str(triple_data["triple"][1]),
            "value": str(triple_data["triple"][2]),
            "object": str(triple_data["object"]),
            "external_entity": triple_data.get("external_entity"),
            "details": triple_data.get("details"),
            "is_mandatory": str(triple_data["object"]) in predicate_mandatory,
            "label": _value_label(
                predicate, str(triple_data["object"]), subject_class, subject_shape
            )
            if predicate in optional_values
            else None,
        }
        for triple_data in data["triples"]
    ]
    return {
        "display_name": display_name,
        "property": predicate,
        "object_shape": object_shape,
        "is_draggable": data.get("is_draggable", False),
        "ordered_by": data.get("ordered_by"),
        "field": _field_for_group(predicate, entity_type, subject_shape, object_shape),
        "triples": triples,
    }


def build_entity_view(subject: str) -> dict:
    subject_uri = URIRef(subject)
    custom_filter = get_custom_filter()

    agnostic_entity = AgnosticEntity(
        res=subject,
        config=get_change_tracking_config(),
        include_related_objects=False,
        include_merged_entities=False,
        include_reverse_relations=False,
    )
    history, provenance = agnostic_entity.get_history(include_prov_metadata=True)
    history = convert_to_rdflib_graphs(history, is_quadstore=get_dataset_is_quadstore())

    is_deleted = False
    context_snapshot = None
    highest_priority_class = None
    entity_shape = None
    classes: list[str] = []

    if history.get(subject):
        sorted_timestamps = sorted(history[subject].keys())
        latest_metadata = next(
            (
                meta
                for _, meta in provenance[subject].items()
                if meta["generatedAtTime"] == sorted_timestamps[-1]
            ),
            None,
        )

        is_deleted = bool(
            latest_metadata
            and "invalidatedAtTime" in latest_metadata
            and latest_metadata["invalidatedAtTime"]
        )

        context_snapshot, highest_priority_class, entity_shape = (
            get_deleted_entity_context_info(
                is_deleted=is_deleted,
                sorted_timestamps=sorted_timestamps,
                history=history,
                subject=subject_uri,
            )
        )

    if is_deleted:
        grouped_triples: dict = {}
        can_be_added: list = []
        can_be_deleted: list = []
        datatypes: dict = {}
        mandatory_values: dict = {}
        optional_values: dict = {}
    else:
        (
            grouped_triples,
            can_be_added,
            can_be_deleted,
            datatypes,
            mandatory_values,
            optional_values,
            highest_priority_class,
            entity_shape,
            classes,
        ) = _build_live_entity_context(subject_uri, history, subject)

    entity_key = (highest_priority_class, entity_shape)
    return {
        "uri": subject,
        "label": custom_filter.entity_title(subject, entity_key, context_snapshot),
        "type": highest_priority_class,
        "type_label": custom_filter.human_readable_class(entity_key),
        "shape": entity_shape,
        "classes": classes,
        "is_deleted": is_deleted,
        "has_history": bool(history.get(subject)),
        "shacl": bool(len(get_shacl_graph())),
        "has_form_fields": entity_key in get_form_fields(),
        "can_be_added": can_be_added,
        "can_be_deleted": can_be_deleted,
        "datatypes": datatypes,
        "optional_values": {
            predicate: [
                {
                    "value": value,
                    "label": _value_label(
                        predicate, value, highest_priority_class, entity_shape
                    ),
                }
                for value in values
            ]
            for predicate, values in optional_values.items()
        },
        "groups": [
            _serialize_group(
                display_name,
                data,
                highest_priority_class,
                mandatory_values,
                optional_values,
            )
            for display_name, data in grouped_triples.items()
        ],
    }


@entity_bp.route("/entity/<path:subject>")
@login_required
def about(subject: str) -> Response:
    return jsonify(build_entity_view(subject))
