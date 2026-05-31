# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from flask import abort, current_app, render_template
from flask_login import current_user, login_required
from rdflib import RDF, Graph, Literal, URIRef
from time_agnostic_library.agnostic_entity import AgnosticEntity

from heritrace.extensions import (
    get_change_tracking_config,
    get_dataset_is_quadstore,
    get_display_rules,
    get_form_fields,
    get_shacl_graph,
)
from heritrace.forms import UpdateTripleForm
from heritrace.routes.entity._blueprint import entity_bp
from heritrace.utils.datatypes import get_datatype_options
from heritrace.utils.display_rules_utils import (
    get_grouped_triples,
    get_highest_priority_class,
)
from heritrace.utils.primary_source_utils import get_default_primary_source
from heritrace.utils.shacl_utils import determine_shape_for_entity_triples
from heritrace.utils.shacl_validation import get_valid_predicates
from heritrace.utils.sparql_utils import (
    convert_to_rdflib_graphs,
    fetch_data_graph_for_subject,
    get_triples_from_graph,
)
from heritrace.utils.virtual_properties import get_virtual_properties_for_entity


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
) -> tuple[dict, list, list, dict, dict, dict, str | None, str | None]:
    data_graph = fetch_data_graph_for_subject(subject_uri)

    if not history.get(subject) and (not data_graph or len(data_graph) == 0):
        abort(404)

    if not data_graph:
        return {}, [], [], {}, {}, {}, None, None

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
        for _, _, o in get_triples_from_graph(
            data_graph, (subject_uri, RDF.type, None)
        )
    ]
    subject_triples = list(
        get_triples_from_graph(data_graph, (subject_uri, None, None))
    )

    highest_priority_class = get_highest_priority_class(subject_classes)
    entity_shape = determine_shape_for_entity_triples(subject_triples)

    if not highest_priority_class:
        return {}, [], [], {}, {}, {}, highest_priority_class, entity_shape

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

    if entity_shape:
        virtual_properties = get_virtual_properties_for_entity(
            highest_priority_class, entity_shape
        )
    else:
        virtual_properties = []

    can_be_added = [
        uri for uri in can_be_added if uri in relevant_properties
    ] + [vp[0] for vp in virtual_properties]
    can_be_deleted = [
        uri for uri in can_be_deleted if uri in relevant_properties
    ] + [vp[0] for vp in virtual_properties]

    return (
        grouped_triples,
        can_be_added,
        can_be_deleted,
        datatypes,
        mandatory_values,
        optional_values,
        highest_priority_class,
        entity_shape,
    )


@entity_bp.route("/about/<path:subject>")
@login_required
def about(subject: str) -> str:
    subject_uri = URIRef(subject)
    change_tracking_config = get_change_tracking_config()

    default_primary_source = get_default_primary_source(current_user.orcid)

    agnostic_entity = AgnosticEntity(
        res=subject,
        config=change_tracking_config,
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
        ) = _build_live_entity_context(subject_uri, history, subject)

    update_form = UpdateTripleForm()
    form_fields = get_form_fields()
    datatype_options = get_datatype_options()

    predicate_details_map = {}
    for entity_type_key, predicates in form_fields.items():
        for predicate_uri, details_list in predicates.items():
            for details in details_list:
                shape = details.get("nodeShape")
                key = (predicate_uri, entity_type_key, shape)
                predicate_details_map[key] = details

    return render_template(
        "entity/about.jinja",
        subject=subject,
        history=history,
        can_be_added=can_be_added,
        can_be_deleted=can_be_deleted,
        datatypes=datatypes,
        update_form=update_form,
        mandatory_values=mandatory_values,
        optional_values=optional_values,
        shacl=bool(len(get_shacl_graph())),
        grouped_triples=grouped_triples,
        display_rules=get_display_rules(),
        form_fields=form_fields,
        entity_type=highest_priority_class,
        entity_shape=entity_shape,
        predicate_details_map=predicate_details_map,
        dataset_db_triplestore=current_app.config["DATASET_DB_TRIPLESTORE"],
        dataset_db_text_index_enabled=current_app.config[
            "DATASET_DB_TEXT_INDEX_ENABLED"
        ],
        is_deleted=is_deleted,
        context=context_snapshot,
        default_primary_source=default_primary_source,
        datatype_options=datatype_options,
    )
