# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import abort, current_app, flash, redirect, url_for
from flask_babel import gettext
from flask_login import current_user, login_required
from rdflib import Dataset, Graph, Literal, URIRef
from time_agnostic_library.agnostic_entity import AgnosticEntity

if TYPE_CHECKING:
    from datetime import datetime

    from werkzeug.wrappers import Response

from heritrace.apis.orcid import get_responsible_agent_uri
from heritrace.editor import Editor
from heritrace.extensions import (
    get_change_tracking_config,
    get_dataset_endpoint,
    get_dataset_is_quadstore,
    get_provenance_endpoint,
)
from heritrace.routes.entity._blueprint import entity_bp
from heritrace.routes.entity._types import _DATETIME_MIN_UTC, _QUAD_LENGTH
from heritrace.utils.converters import convert_to_datetime
from heritrace.utils.sparql_utils import (
    convert_to_rdflib_graphs,
    fetch_current_state_with_related_entities,
    get_triples_from_graph,
)
from heritrace.utils.uri_utils import is_valid_url


@entity_bp.route("/restore-version/<path:entity_uri>/<timestamp>", methods=["POST"])
@login_required
def restore_version(entity_uri: str, timestamp: str) -> Response:  # noqa: C901, PLR0912, PLR0915
    entity_uri_ref = URIRef(entity_uri)
    timestamp_dt = convert_to_datetime(timestamp)
    if timestamp_dt is None:
        abort(404)
    timestamp = timestamp_dt.isoformat()
    change_tracking_config = get_change_tracking_config()

    agnostic_entity = AgnosticEntity(
        res=entity_uri,
        config=change_tracking_config,
        include_related_objects=True,
        include_merged_entities=True,
        include_reverse_relations=True,
    )
    history, provenance = agnostic_entity.get_history(include_prov_metadata=True)
    history = convert_to_rdflib_graphs(history, is_quadstore=get_dataset_is_quadstore())

    historical_graph = history.get(entity_uri, {}).get(timestamp)
    if historical_graph is None:
        abort(404)

    current_graph = fetch_current_state_with_related_entities(provenance)

    is_deleted = (
        len(list(get_triples_from_graph(current_graph, (entity_uri_ref, None, None))))
        == 0
    )

    triples_or_quads_to_delete, triples_or_quads_to_add = compute_graph_differences(
        current_graph, historical_graph
    )

    entities_to_restore = get_entities_to_restore(
        triples_or_quads_to_delete, triples_or_quads_to_add, entity_uri
    )

    entity_snapshots = prepare_entity_snapshots(
        entities_to_restore, provenance, timestamp
    )

    source_uri = None if is_deleted else entity_snapshots[entity_uri]["source"]
    resp_agent = get_responsible_agent_uri(current_user.orcid)
    editor = Editor(
        get_dataset_endpoint(),
        get_provenance_endpoint(),
        current_app.config["COUNTER_HANDLER"],
        resp_agent,
        URIRef(source_uri) if source_uri else None,
        current_app.config["DATASET_GENERATION_TIME"],
        dataset_is_quadstore=current_app.config["DATASET_IS_QUADSTORE"],
    )

    if get_dataset_is_quadstore():
        if not isinstance(current_graph, Dataset):
            msg = "Expected Dataset instance"
            raise TypeError(msg)
        for quad in current_graph.quads():
            editor.g_set.add(quad)  # type: ignore[arg-type]
    else:
        for triple in current_graph:
            editor.g_set.add(triple)  # type: ignore[arg-type]
    editor.preexisting_finished()

    for item in triples_or_quads_to_delete:
        s, p, o = URIRef(str(item[0])), URIRef(str(item[1])), item[2]
        obj: URIRef | Literal = URIRef(str(o)) if isinstance(o, URIRef) else Literal(o)
        if len(item) == _QUAD_LENGTH:
            editor.delete(s, p, obj, URIRef(str(item[3])))
        else:
            editor.delete(s, p, obj)

        subject = str(item[0])
        if subject in entity_snapshots:
            entity_info = entity_snapshots[subject]
            if entity_info["needs_restore"]:
                editor.g_set.mark_as_restored(URIRef(subject))
            editor.g_set.entity_index[URIRef(subject)]["restoration_source"] = (
                entity_info["source"]
            )

    for item in triples_or_quads_to_add:
        s, p, o = URIRef(str(item[0])), URIRef(str(item[1])), item[2]
        obj = URIRef(str(o)) if isinstance(o, URIRef) else Literal(o)
        if len(item) == _QUAD_LENGTH:
            editor.create(s, p, obj, URIRef(str(item[3])))
        else:
            editor.create(s, p, obj)

        subject = str(item[0])
        if subject in entity_snapshots:
            entity_info = entity_snapshots[subject]
            if entity_info["needs_restore"]:
                editor.g_set.mark_as_restored(URIRef(subject))
                editor.g_set.entity_index[URIRef(subject)]["source"] = entity_info[
                    "source"
                ]

    if is_deleted and entity_uri in entity_snapshots:
        editor.g_set.mark_as_restored(entity_uri_ref)
        source = entity_snapshots[entity_uri]["source"]
        editor.g_set.entity_index[entity_uri_ref]["source"] = source

    try:
        editor.save()
        flash(gettext("Version restored successfully"), "success")
    except Exception as e:  # noqa: BLE001
        flash(
            gettext(
                "An error occurred while restoring the version: %(error)s", error=str(e)
            ),
            "error",
        )

    return redirect(url_for("entity.about", subject=entity_uri))


def compute_graph_differences(
    current_graph: Graph | Dataset, historical_graph: Graph | Dataset
) -> tuple[set, set]:
    if get_dataset_is_quadstore():
        if not isinstance(current_graph, Dataset):
            msg = "Expected Dataset instance for current_graph"
            raise TypeError(msg)
        if not isinstance(historical_graph, Dataset):
            msg = "Expected Dataset instance for historical_graph"
            raise TypeError(msg)
        current_quads = set(current_graph.quads())
        historical_quads = set(historical_graph.quads())
        return current_quads - historical_quads, historical_quads - current_quads
    current_triples = set(get_triples_from_graph(current_graph, (None, None, None)))
    historical_triples = set(
        get_triples_from_graph(historical_graph, (None, None, None))
    )
    return current_triples - historical_triples, historical_triples - current_triples


def get_entities_to_restore(
    triples_or_quads_to_delete: set, triples_or_quads_to_add: set, main_entity_uri: str
) -> set:
    entities_to_restore = {main_entity_uri}

    for item in list(triples_or_quads_to_delete) + list(triples_or_quads_to_add):
        predicate = str(item[1])
        if predicate == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type":
            continue

        subject = str(item[0])
        obj = str(item[2])
        for uri in [subject, obj]:
            if uri != main_entity_uri and is_valid_url(uri):
                entities_to_restore.add(uri)

    return entities_to_restore


def prepare_entity_snapshots(
    entities_to_restore: set, provenance: dict, target_time: str
) -> dict:
    entity_snapshots = {}

    for entity_uri in entities_to_restore:
        if entity_uri not in provenance:
            continue

        source_snapshot = find_appropriate_snapshot(provenance[entity_uri], target_time)
        if not source_snapshot:
            continue

        sorted_snapshots = sorted(
            provenance[entity_uri].items(),
            key=lambda x: (
                convert_to_datetime(x[1]["generatedAtTime"]) or _DATETIME_MIN_UTC
            ),
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


def find_appropriate_snapshot(provenance_data: dict, target_time: str) -> str | None:
    target_datetime = convert_to_datetime(target_time)
    if target_datetime is None:
        msg = f"Failed to parse target_time: {target_time}"
        raise ValueError(msg)

    valid_snapshots: list[tuple[datetime, str]] = []
    for snapshot_uri, metadata in provenance_data.items():
        generation_time = convert_to_datetime(metadata["generatedAtTime"])

        if (
            metadata.get("invalidatedAtTime")
            and metadata["generatedAtTime"] == metadata["invalidatedAtTime"]
        ):
            continue

        if generation_time is not None and generation_time <= target_datetime:
            valid_snapshots.append((generation_time, snapshot_uri))

    if not valid_snapshots:
        return None

    valid_snapshots.sort(key=lambda x: x[0])
    return valid_snapshots[-1][1]
