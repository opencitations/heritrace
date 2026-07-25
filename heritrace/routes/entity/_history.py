# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import re
from datetime import datetime

from flask import abort, render_template
from flask_babel import gettext
from flask_login import login_required
from rdflib import RDF, Graph, Literal, URIRef
from SPARQLWrapper import JSON
from time_agnostic_library.agnostic_entity import AgnosticEntity

from heritrace.extensions import (
    get_change_tracking_config,
    get_custom_filter,
    get_dataset_is_quadstore,
    get_display_rules_use_inverse_relations,
    get_provenance_sparql,
)
from heritrace.routes.entity._blueprint import entity_bp
from heritrace.routes.entity._rendering import generate_modification_text
from heritrace.routes.entity._types import _DATETIME_MIN_UTC, HistoryContext
from heritrace.sparql import get_sparql_bindings
from heritrace.utils.converters import convert_to_datetime
from heritrace.utils.display_rules_utils import (
    get_grouped_triples,
    get_highest_priority_class,
)
from heritrace.utils.shacl_utils import determine_shape_for_entity_triples
from heritrace.utils.shacl_validation import get_valid_predicates
from heritrace.utils.sparql_utils import (
    convert_to_rdflib_graphs,
    determine_shape_for_classes,
    get_triples_from_graph,
    parse_sparql_update,
)
from heritrace.utils.uri_utils import is_valid_url


@entity_bp.route("/entity-history/<path:entity_uri>")
@login_required
def entity_history(entity_uri: str) -> str:
    entity_uri_ref = URIRef(entity_uri)
    custom_filter = get_custom_filter()
    change_tracking_config = get_change_tracking_config()

    agnostic_entity = AgnosticEntity(
        res=entity_uri,
        config=change_tracking_config,
        include_related_objects=True,
        include_merged_entities=True,
        include_reverse_relations=get_display_rules_use_inverse_relations(),
    )
    history, provenance = agnostic_entity.get_history(include_prov_metadata=True)
    history = convert_to_rdflib_graphs(history, is_quadstore=get_dataset_is_quadstore())

    sorted_metadata = sorted(
        provenance[entity_uri].items(),
        key=lambda x: convert_to_datetime(x[1]["generatedAtTime"]) or _DATETIME_MIN_UTC,
    )
    sorted_timestamps: list[str] = [
        dt.isoformat()
        for _, meta in sorted_metadata
        if (dt := convert_to_datetime(meta["generatedAtTime"])) is not None
    ]

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

    entity_classes = [
        str(triple[2])
        for triple in get_triples_from_graph(
            context_snapshot, (entity_uri_ref, RDF.type, None)
        )
    ]
    highest_priority_class = get_highest_priority_class(entity_classes)

    snapshot_entity_shape = determine_shape_for_entity_triples(
        list(get_triples_from_graph(context_snapshot, (entity_uri_ref, None, None)))
    )

    events = []
    for i, (_snapshot_uri, metadata) in enumerate(sorted_metadata):
        date = convert_to_datetime(metadata["generatedAtTime"])
        if date is None:
            msg = "date must not be None"
            raise AssertionError(msg)
        snapshot_graph = history[entity_uri][date.isoformat()]

        responsible_agent = custom_filter.format_agent_reference(
            metadata["wasAttributedTo"]
        )
        primary_source = custom_filter.format_source_reference(
            metadata["hadPrimarySource"]
        )

        history_ctx = HistoryContext(
            entity_uri=entity_uri,
            highest_priority_class=highest_priority_class,
            entity_shape=snapshot_entity_shape,
            history=history,
            sorted_timestamps=sorted_timestamps,
            custom_filter=custom_filter,
        )

        description = _format_snapshot_description(
            metadata,
            history_ctx,
            context_snapshot,
            i,
        )
        modifications = metadata.get("hasUpdateQuery", "")
        modification_text = ""
        if modifications:
            parsed_modifications = parse_sparql_update(modifications)
            modification_text = generate_modification_text(
                parsed_modifications,
                history_ctx,
                snapshot_graph,
                date.isoformat(),
            )

        can_restore = len(sorted_metadata) > 1 and i + 1 < len(sorted_metadata)
        restore_button = ""
        if can_restore:
            restore_label = gettext("Restore")
            restore_action = (
                f"/restore-version/{entity_uri}/{metadata['generatedAtTime']}"
            )
            restore_button = f"""
                <form action='{restore_action}'
                method='post'
                class='d-inline restore-form'>
                    <button type='submit'
                    class='btn btn-success restore-btn'>
                        <i class='bi
                        bi-arrow-counterclockwise
                        me-1'></i>{restore_label}
                    </button>
                </form>
            """

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
                "text": (
                    f"<p><strong>"
                    f"{gettext('Responsible agent')}"
                    f":</strong>"
                    f" {responsible_agent}</p>"
                    f"<p><strong>"
                    f"{gettext('Primary source')}"
                    f":</strong>"
                    f" {primary_source}</p>"
                    f"<p><strong>"
                    f"{gettext('Description')}"
                    f":</strong>"
                    f" {description}</p>"
                    f'<div class="modifications mb-3">'
                    f"{modification_text}"
                    f"</div>"
                    f'<div class="d-flex gap-2 mt-2">'
                    f"<a href='/entity-version/"
                    f"{entity_uri}/"
                    f"{metadata['generatedAtTime']}'"
                    f" class='btn btn-outline-primary"
                    f" view-version'"
                    f" target='_self'>"
                    f"{gettext('View version')}</a>"
                    f"{restore_button}"
                    f"</div>"
                ),
            },
            "autolink": False,
        }

        if i + 1 < len(sorted_metadata):
            next_date = convert_to_datetime(
                sorted_metadata[i + 1][1]["generatedAtTime"]
            )
            if next_date is None:
                msg = "next_date must not be None"
                raise AssertionError(msg)
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
        entity_uri, (highest_priority_class, snapshot_entity_shape), context_snapshot
    )

    timeline_data = {
        "entityUri": entity_uri,
        "entityLabel": entity_label,
        "entityClasses": list(entity_classes),
        "entityShape": snapshot_entity_shape,
        "events": events,
    }

    return render_template("entity/history.jinja", timeline_data=timeline_data)


def _format_snapshot_description(
    metadata: dict,
    ctx: HistoryContext,
    context_snapshot: Graph,
    current_index: int,
) -> str:
    description = metadata.get("description", "")
    is_merge_snapshot = False
    was_derived_from = metadata.get("wasDerivedFrom")
    if isinstance(was_derived_from, list) and len(was_derived_from) > 1:
        is_merge_snapshot = True

    if is_merge_snapshot:
        match = re.search(
            r"merged with ['\u2018\u2019]?([^'\u2018\u2019<>\s]+)"
            r"['\u2018\u2019]?",
            description,
        )
        if match:
            potential_merged_uri = match.group(1)
            if is_valid_url(potential_merged_uri):
                merged_entity_uri_from_desc = potential_merged_uri
                merged_entity_label = None
                if current_index > 0:
                    previous_snapshot_timestamp = ctx.sorted_timestamps[
                        current_index - 1
                    ]
                    previous_snapshot_graph = ctx.history.get(ctx.entity_uri, {}).get(
                        previous_snapshot_timestamp
                    )
                    if previous_snapshot_graph:
                        raw_merged_entity_classes = [
                            str(o)
                            for s, p, o in get_triples_from_graph(
                                previous_snapshot_graph,
                                (URIRef(merged_entity_uri_from_desc), RDF.type, None),
                            )
                        ]
                        highest_priority_merged_class = (
                            get_highest_priority_class(raw_merged_entity_classes)
                            if raw_merged_entity_classes
                            else None
                        )

                        shape = determine_shape_for_classes(raw_merged_entity_classes)
                        merged_entity_label = ctx.custom_filter.human_readable_entity(
                            merged_entity_uri_from_desc,
                            (highest_priority_merged_class, shape),
                            previous_snapshot_graph,
                        )
                        if (
                            merged_entity_label
                            and merged_entity_label != merged_entity_uri_from_desc
                        ):
                            description = description.replace(
                                match.group(0), f"merged with '{merged_entity_label}'"
                            )

    shape = (
        determine_shape_for_classes([ctx.highest_priority_class])
        if ctx.highest_priority_class
        else None
    )
    entity_label_for_desc = ctx.custom_filter.human_readable_entity(
        ctx.entity_uri, (ctx.highest_priority_class, shape), context_snapshot
    )
    if entity_label_for_desc and entity_label_for_desc != ctx.entity_uri:
        description = description.replace(
            f"'{ctx.entity_uri}'", f"'{entity_label_for_desc}'"
        )

    return description


def _resolve_timestamp(entity_uri: str, timestamp: str) -> tuple[str, datetime]:
    try:
        return timestamp, datetime.fromisoformat(timestamp)
    except ValueError:
        pass

    provenance_sparql = get_provenance_sparql()
    query_timestamp = f"""
        SELECT ?generation_time
        WHERE {{
            <{entity_uri}/prov/se/{timestamp}>
            <http://www.w3.org/ns/prov#generatedAtTime>
            ?generation_time.
        }}
    """
    provenance_sparql.setQuery(query_timestamp)
    provenance_sparql.setReturnFormat(JSON)
    try:
        bindings = get_sparql_bindings(provenance_sparql.queryAndConvert())
        generation_time = bindings[0]["generation_time"]["value"]
    except IndexError:
        abort(404)
    return generation_time, datetime.fromisoformat(generation_time)


def _find_closest_metadata(
    entity_metadata: dict,
    timestamp_dt: datetime,
    latest_timestamp: str,
) -> tuple[dict | None, dict | None]:
    closest_metadata = None
    min_time_diff = None
    latest_metadata = None

    for meta in entity_metadata.values():
        meta_time = convert_to_datetime(meta["generatedAtTime"])
        if meta_time is None:
            msg = "meta_time must not be None"
            raise AssertionError(msg)
        time_diff = abs((meta_time - timestamp_dt).total_seconds())

        if (
            closest_metadata is None
            or min_time_diff is None
            or time_diff < min_time_diff
        ):
            closest_metadata = meta
            min_time_diff = time_diff

        if meta["generatedAtTime"] == latest_timestamp:
            latest_metadata = meta

    return closest_metadata, latest_metadata


def _compute_version_navigation(
    snapshot_times: list[datetime],
    timestamp_dt: datetime,
) -> tuple[str | None, str | None]:
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

    return prev_snapshot_timestamp, next_snapshot_timestamp


def _prepare_modifications(
    closest_metadata: dict,
    ctx: HistoryContext,
    context_version: Graph,
    closest_timestamp: str,
    sorted_timestamps: list[str],
) -> tuple[str, dict]:
    modifications = ""
    if closest_metadata.get("hasUpdateQuery"):
        sparql_query = closest_metadata["hasUpdateQuery"]
        parsed_modifications = parse_sparql_update(sparql_query)
        modifications = generate_modification_text(
            parsed_modifications,
            ctx,
            context_version,
            closest_timestamp,
        )

    try:
        current_index = sorted_timestamps.index(closest_timestamp)
    except ValueError:
        current_index = -1

    if closest_metadata.get("description"):
        formatted_description = _format_snapshot_description(
            closest_metadata,
            ctx,
            context_version,
            current_index,
        )
        closest_metadata["description"] = formatted_description

    return modifications, closest_metadata


@entity_bp.route("/entity-version/<path:entity_uri>/<timestamp>")
@login_required
def entity_version(entity_uri: str, timestamp: str) -> str:
    entity_uri_ref = URIRef(entity_uri)
    custom_filter = get_custom_filter()
    change_tracking_config = get_change_tracking_config()

    timestamp, timestamp_dt = _resolve_timestamp(entity_uri, timestamp)

    agnostic_entity = AgnosticEntity(
        res=entity_uri,
        config=change_tracking_config,
        include_related_objects=True,
        include_merged_entities=True,
        include_reverse_relations=get_display_rules_use_inverse_relations(),
    )
    history, provenance = agnostic_entity.get_history(include_prov_metadata=True)
    history = convert_to_rdflib_graphs(history, is_quadstore=get_dataset_is_quadstore())
    main_entity_history = history.get(entity_uri, {})
    sorted_timestamps = sorted(
        main_entity_history.keys(),
        key=lambda t: convert_to_datetime(t) or _DATETIME_MIN_UTC,
    )

    if not sorted_timestamps:
        abort(404)

    closest_timestamp = min(
        sorted_timestamps,
        key=lambda t: abs(
            (convert_to_datetime(t) or _DATETIME_MIN_UTC).astimezone()
            - timestamp_dt.astimezone()
        ),
    )

    version = main_entity_history[closest_timestamp]
    triples: list[tuple[URIRef, URIRef, URIRef | Literal]] = [
        (URIRef(str(s)), URIRef(str(p)), URIRef(str(o)) if isinstance(o, URIRef) else o)  # type: ignore[misc]
        for s, p, o in get_triples_from_graph(version, (entity_uri_ref, None, None))
    ]

    entity_metadata = provenance.get(entity_uri, {})
    latest_timestamp = max(sorted_timestamps)
    closest_metadata, latest_metadata = _find_closest_metadata(
        entity_metadata, timestamp_dt, latest_timestamp
    )

    if closest_metadata is None or latest_metadata is None:
        abort(404)

    is_deletion_snapshot = (
        closest_timestamp == latest_timestamp
        and "invalidatedAtTime" in latest_metadata
        and latest_metadata["invalidatedAtTime"]
    ) or len(triples) == 0

    context_version = version
    if is_deletion_snapshot and len(sorted_timestamps) > 1:
        current_index = sorted_timestamps.index(closest_timestamp)
        if current_index > 0:
            context_version = main_entity_history[sorted_timestamps[current_index - 1]]

    if is_deletion_snapshot and len(sorted_timestamps) > 1:
        subject_classes = [
            str(o)
            for _, _, o in get_triples_from_graph(
                context_version, (entity_uri_ref, RDF.type, None)
            )
        ]
    else:
        subject_classes = [
            str(o)
            for _, _, o in get_triples_from_graph(
                version, (entity_uri_ref, RDF.type, None)
            )
        ]

    highest_priority_class = get_highest_priority_class(subject_classes)

    entity_shape = determine_shape_for_entity_triples(
        list(get_triples_from_graph(context_version, (entity_uri_ref, None, None)))
    )

    _, _, _, _, _, valid_predicates_set = get_valid_predicates(
        triples, highest_priority_class=URIRef(highest_priority_class or "")
    )

    grouped_triples, _relevant_properties = get_grouped_triples(
        entity_uri_ref,
        triples,
        list(valid_predicates_set),
        historical_snapshot=context_version,
        entity_key=(highest_priority_class, entity_shape),
    )

    snapshot_times: list[datetime] = [
        dt
        for meta in entity_metadata.values()
        if (dt := convert_to_datetime(meta["generatedAtTime"])) is not None
    ]
    snapshot_times = sorted(set(snapshot_times))
    version_number = snapshot_times.index(timestamp_dt) + 1

    prev_snapshot_timestamp, next_snapshot_timestamp = _compute_version_navigation(
        snapshot_times, timestamp_dt
    )

    version_history_ctx = HistoryContext(
        entity_uri=entity_uri,
        highest_priority_class=highest_priority_class,
        entity_shape=entity_shape,
        history=history,
        sorted_timestamps=sorted_timestamps,
        custom_filter=custom_filter,
    )

    modifications, closest_metadata = _prepare_modifications(
        closest_metadata,
        version_history_ctx,
        context_version,
        closest_timestamp,
        sorted_timestamps,
    )

    closest_timestamp = closest_metadata["generatedAtTime"]

    return render_template(
        "entity/version.jinja",
        subject=entity_uri,
        entity_type=highest_priority_class,
        entity_shape=entity_shape,
        metadata={closest_timestamp: closest_metadata},
        timestamp=closest_timestamp,
        next_snapshot_timestamp=next_snapshot_timestamp,
        prev_snapshot_timestamp=prev_snapshot_timestamp,
        modifications=modifications,
        grouped_triples=grouped_triples,
        version_number=version_number,
        version=context_version,
    )
