# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import traceback
from dataclasses import dataclass
from typing import TypedDict, cast

from flask import (
    Blueprint,
    Response,
    current_app,
    g,
    jsonify,
    request,
)
from flask_login import current_user, login_required
from rdflib import RDF, XSD, Graph, Literal, URIRef

from heritrace.apis.orcid import get_responsible_agent_uri
from heritrace.configuration.entity import ConfigurationRejectedError
from heritrace.configuration.runtime import is_admin
from heritrace.editor import Editor
from heritrace.extensions import (
    get_custom_filter,
    get_form_fields,
    get_presentation,
    get_primary_source,
    get_shacl_graph,
    new_editor,
    record_dataset_change,
)
from heritrace.services.resource_lock_manager import LockInfo, LockStatus
from heritrace.utils.datatypes import DATATYPE_MAPPING, get_datatype_options
from heritrace.utils.draft_labels import draft_label
from heritrace.utils.filters import field_with_labels
from heritrace.utils.inverse_paths import expand_inverse_changes
from heritrace.utils.primary_source_utils import (
    get_user_default_primary_source,
    save_user_default_primary_source,
)
from heritrace.utils.shacl_utils import determine_shape_for_entity_triples
from heritrace.utils.shacl_validation import validate_new_triple
from heritrace.utils.sparql_utils import (
    CatalogQuery,
    DeletedEntitiesQuery,
    fetch_data_graph_for_subject,
    find_orphaned_entities,
    get_available_classes,
    get_catalog_data,
    get_deleted_entities_with_filtering,
    get_triples_from_graph,
    import_entity_graph,
    import_referenced_entities,
)
from heritrace.utils.strategies import CompositeHandlingStrategy, OrphanHandlingStrategy
from heritrace.utils.uri_utils import generate_unique_uri, is_valid_url


@dataclass(frozen=True, slots=True)
class ChangeOperation:
    editor: Editor
    subject: URIRef
    graph_uri: URIRef | None = None
    entity_type: str | None = None
    entity_shape: str | None = None


api_bp = Blueprint("api", __name__)


@api_bp.route("/me")
def me() -> Response:
    signed_in = current_user.is_authenticated
    admin = signed_in and is_admin(current_app.config, current_user.orcid)
    setup_error = current_app.config["SETUP_ERROR"]
    configured = setup_error is None
    return jsonify(
        {
            "user": {
                "id": current_user.id,
                "name": current_user.name,
                "orcid": current_user.orcid,
            }
            if signed_in
            else None,
            "is_admin": admin,
            "setup_required": not configured,
            "configuration_revision": current_app.config["CONFIGURATION_REVISION"],
            "setup_error": setup_error if admin else None,
            "default_primary_source": get_user_default_primary_source(
                current_user.orcid
            )
            if signed_in and configured
            else None,
            "config": {
                "app_title": current_app.config["APP_TITLE"],
                "app_subtitle": current_app.config["APP_SUBTITLE"],
                "shacl": bool(len(get_shacl_graph())),
                "datatype_options": get_datatype_options(),
            }
            if configured
            else None,
        }
    )


@api_bp.route("/catalogue")
@login_required
def catalogue_api() -> Response:
    selected_class = request.args.get("class")
    selected_shape = request.args.get("shape")
    page = int(request.args.get("page", 1))
    per_page = current_app.config["CATALOGUE_DEFAULT_PER_PAGE"]

    available_classes = get_available_classes()

    catalog_data = get_catalog_data(
        CatalogQuery(
            selected_class=selected_class,
            page=page,
            per_page=per_page,
            selected_shape=selected_shape,
        ),
        available_classes,
    )

    catalog_data["available_classes"] = available_classes
    return jsonify(catalog_data)


@api_bp.route("/recycle-bin")
@login_required
def get_deleted_entities_api() -> Response:
    """
    API endpoint to retrieve deleted entities with pagination and sorting.
    Only processes and returns entities whose classes are marked as visible.
    """
    selected_class = request.args.get("class")
    selected_shape = request.args.get("shape")
    page = int(request.args.get("page", 1))
    per_page = current_app.config["CATALOGUE_DEFAULT_PER_PAGE"]
    sort_direction = request.args.get("sort_direction", "DESC")

    (
        deleted_entities,
        available_classes,
        selected_class,
        selected_shape,
        sortable_properties,
        total_count,
    ) = get_deleted_entities_with_filtering(
        DeletedEntitiesQuery(
            page,
            per_page,
            sort_direction,
            selected_class,
            selected_shape,
        )
    )

    return jsonify(
        {
            "entities": deleted_entities,
            "total_pages": (total_count + per_page - 1) // per_page
            if total_count > 0
            else 0,
            "current_page": page,
            "per_page": per_page,
            "total_count": total_count,
            "sort_property": sortable_properties[0]["property"],
            "sort_direction": sort_direction,
            "selected_class": selected_class,
            "selected_shape": selected_shape,
            "available_classes": available_classes,
            "sortable_properties": sortable_properties,
        }
    )


def _locked_response(lock_info: LockInfo) -> dict[str, str]:
    return {
        "status": "locked",
        "title": "Resource Locked",
        "message": (
            "This resource is currently being edited by"
            f" {lock_info.user_name} [{lock_info.user_id}]"
        ),
    }


@api_bp.route("/check-lock", methods=["POST"])
@login_required
def check_lock() -> Response | tuple[Response, int]:
    """Check if a resource is locked."""
    try:
        data = request.get_json()
        resource_uri = data.get("resource_uri")

        if not resource_uri:
            return (
                jsonify({"status": "error", "message": "No resource URI provided"}),
                400,
            )

        status, lock_info = g.resource_lock_manager.check_lock_status(resource_uri)

        if status == LockStatus.LOCKED:
            return jsonify(_locked_response(lock_info))
        if status == LockStatus.ERROR:
            return (
                jsonify(
                    {
                        "status": "error",
                        "title": "Error",
                        "message": "An error occurred while checking the lock",
                    }
                ),
                500,
            )
        return jsonify({"status": "available"})

    except Exception:
        current_app.logger.exception("Error in check_lock")
        return (
            jsonify(
                {
                    "status": "error",
                    "title": "Error",
                    "message": "An unexpected error occurred",
                }
            ),
            500,
        )


@api_bp.route("/acquire-lock", methods=["POST"])
@login_required
def acquire_lock() -> Response | tuple[Response, int]:
    """Try to acquire a lock on a resource."""
    try:
        data = request.get_json()
        resource_uri = data.get("resource_uri")
        linked_resources = data.get("linked_resources", [])

        if not resource_uri:
            return (
                jsonify({"status": "error", "message": "No resource URI provided"}),
                400,
            )

        # First check if the resource or any related resource is locked by another user
        status, lock_info = g.resource_lock_manager.check_lock_status(resource_uri)
        if status == LockStatus.LOCKED:
            return jsonify(_locked_response(lock_info)), 200

        # Use the provided linked_resources
        success = g.resource_lock_manager.acquire_lock(resource_uri, linked_resources)

        if success:
            return jsonify({"status": "success"})

        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Resource is locked by another user",
                }
            ),
            423,
        )

    except Exception:
        current_app.logger.exception("Error in acquire_lock")
        return (
            jsonify({"status": "error", "message": "An unexpected error occurred"}),
            500,
        )


@api_bp.route("/release-lock", methods=["POST"])
@login_required
def release_lock() -> Response | tuple[Response, int]:
    """Release a lock on a resource."""
    try:
        data = request.get_json()
        resource_uri = data.get("resource_uri")

        if not resource_uri:
            return (
                jsonify({"status": "error", "message": "No resource URI provided"}),
                400,
            )

        success = g.resource_lock_manager.release_lock(resource_uri)

        if success:
            return jsonify({"status": "success"})

        return (
            jsonify({"status": "error", "message": "Unable to release lock"}),
            400,
        )

    except Exception:
        current_app.logger.exception("Error in release_lock")
        return (
            jsonify({"status": "error", "message": "An unexpected error occurred"}),
            500,
        )


@api_bp.route("/renew-lock", methods=["POST"])
@login_required
def renew_lock() -> Response | tuple[Response, int]:
    """Renew an existing lock on a resource."""
    try:
        data = request.get_json()
        resource_uri = data.get("resource_uri")

        if not resource_uri:
            return (
                jsonify({"status": "error", "message": "No resource URI provided"}),
                400,
            )

        # When renewing a lock, we don't need to check for linked resources again
        # Just pass an empty list as we're only refreshing the existing lock
        success = g.resource_lock_manager.acquire_lock(resource_uri, [])

        if success:
            return jsonify({"status": "success"})

        return (
            jsonify({"status": "error", "message": "Unable to renew lock"}),
            423,
        )

    except Exception:
        current_app.logger.exception("Error in renew_lock")
        return (
            jsonify({"status": "error", "message": "An unexpected error occurred"}),
            500,
        )


@api_bp.route("/validate-literal", methods=["POST"])
@login_required
def validate_literal() -> tuple[Response, int]:
    """Validate a literal value and suggest appropriate datatypes."""
    value = request.json.get("value")
    if not value:
        return jsonify({"error": "Value is required."}), 400

    matching_datatypes = []
    for datatype, validation_func, _ in DATATYPE_MAPPING:
        if validation_func(value):
            matching_datatypes.append(str(datatype))

    if not matching_datatypes:
        return jsonify({"error": "No matching datatypes found."}), 400

    return jsonify({"valid_datatypes": matching_datatypes}), 200


def _collect_affected_entities(
    changes: list[dict],
    entity_type: str,
    *,
    check_for_orphans: bool,
    check_for_composites: bool,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    orphans: list[dict[str, str]] = []
    composite_children: list[dict[str, str]] = []
    for change in changes:
        if change["action"] == "delete":
            found_orphans, found_children = find_orphaned_entities(
                URIRef(change["subject"]),
                entity_type,
                URIRef(change["predicate"]) if change.get("predicate") else None,
                change.get("object"),
            )
            if check_for_orphans:
                orphans.extend(found_orphans)
            if check_for_composites:
                composite_children.extend(found_children)
    return orphans, composite_children


def _format_orphan_response(
    orphans: list[dict[str, str]],
    composite_children: list[dict[str, str]],
    orphan_strategy: OrphanHandlingStrategy,
    composite_strategy: CompositeHandlingStrategy,
) -> Response:
    custom_filter = get_custom_filter()

    def format_entity(
        entity: dict[str, str], *, is_composite: bool
    ) -> dict[str, str | bool]:
        uri = URIRef(entity["uri"])
        shape = determine_shape_for_entity_triples(
            list(
                get_triples_from_graph(
                    fetch_data_graph_for_subject(uri), (uri, None, None)
                )
            )
        )
        entity_key = (entity["type"], shape)
        return {
            "uri": entity["uri"],
            "label": custom_filter.human_readable_entity(uri, entity_key),
            "type": custom_filter.human_readable_class(entity_key),
            "is_composite": is_composite,
        }

    affected_entities = [
        format_entity(entity, is_composite=False) for entity in orphans
    ] + [format_entity(entity, is_composite=True) for entity in composite_children]

    should_delete = (
        orphan_strategy == OrphanHandlingStrategy.DELETE
        and composite_strategy == CompositeHandlingStrategy.DELETE
    )

    return jsonify(
        {
            "status": "success",
            "affected_entities": affected_entities,
            "should_delete": should_delete,
            "orphan_strategy": orphan_strategy.value,
            "composite_strategy": composite_strategy.value,
        }
    )


@api_bp.route("/check_orphans", methods=["POST"])
@login_required
def check_orphans() -> Response | tuple[Response, int]:
    try:
        orphan_strategy = current_app.config["ORPHAN_HANDLING_STRATEGY"]
        composite_strategy = current_app.config["COMPOSITE_HANDLING_STRATEGY"]

        data = request.json
        if not data or "changes" not in data or "entity_type" not in data:
            return (
                jsonify(
                    {
                        "status": "error",
                        "error_type": "validation",
                        "message": "Invalid request: 'changes' and"
                        " 'entity_type' are required fields",
                    }
                ),
                400,
            )

        changes = data.get("changes", [])
        entity_type = data.get("entity_type")

        check_for_orphans = orphan_strategy in (
            OrphanHandlingStrategy.DELETE,
            OrphanHandlingStrategy.ASK,
        )
        check_for_composites = composite_strategy in (
            CompositeHandlingStrategy.DELETE,
            CompositeHandlingStrategy.ASK,
        )

        orphans: list[dict[str, str]] = []
        composite_children: list[dict[str, str]] = []
        if check_for_orphans or check_for_composites:
            orphans, composite_children = _collect_affected_entities(
                changes,
                entity_type,
                check_for_orphans=check_for_orphans,
                check_for_composites=check_for_composites,
            )

        if (orphan_strategy == OrphanHandlingStrategy.KEEP or not orphans) and (
            composite_strategy == CompositeHandlingStrategy.KEEP
            or not composite_children
        ):
            return jsonify({"status": "success", "affected_entities": []})

        return _format_orphan_response(
            orphans,
            composite_children,
            orphan_strategy,
            composite_strategy,
        )
    except ValueError as e:
        error_message = str(e)
        current_app.logger.warning(
            "Validation error in check_orphans: %s", error_message
        )
        return (
            jsonify(
                {
                    "status": "error",
                    "error_type": "validation",
                    "message": "An error occurred while checking for orphaned entities",
                }
            ),
            400,
        )
    except Exception as e:
        error_message = f"Error checking orphans: {e!s}"
        current_app.logger.exception("%s\n%s", error_message, traceback.format_exc())
        return (
            jsonify(
                {
                    "status": "error",
                    "error_type": "system",
                    "message": "An error occurred while checking for orphaned entities",
                }
            ),
            500,
        )


def _parse_change_request(
    changes: list[dict],
) -> tuple[URIRef, list[dict], bool, str | None, bool]:
    first_change = changes[0] if changes else {}
    subject = URIRef(first_change.get("subject", ""))
    affected_entities = first_change.get("affected_entities", [])
    delete_affected = first_change.get("delete_affected", False)
    primary_source = first_change.get("primary_source")
    save_default_source = first_change.get("save_default_source", False)
    return (
        subject,
        affected_entities,
        delete_affected,
        primary_source,
        save_default_source,
    )


def _affected_entity_will_be_deleted(entity: dict, *, delete_affected: bool) -> bool:
    orphan_strategy = current_app.config["ORPHAN_HANDLING_STRATEGY"]
    composite_strategy = current_app.config["COMPOSITE_HANDLING_STRATEGY"]

    if entity["is_composite"]:
        return delete_affected and composite_strategy in (
            CompositeHandlingStrategy.DELETE,
            CompositeHandlingStrategy.ASK,
        )
    return delete_affected and orphan_strategy in (
        OrphanHandlingStrategy.DELETE,
        OrphanHandlingStrategy.ASK,
    )


def _collect_entity_deletion_subjects(
    changes: list[dict],
    affected_entities: list[dict],
    *,
    delete_affected: bool,
) -> set[URIRef]:
    deletion_subjects = {
        URIRef(change["subject"])
        for change in changes
        if change["action"] == "delete" and not change.get("predicate")
    }

    for entity in affected_entities:
        if _affected_entity_will_be_deleted(entity, delete_affected=delete_affected):
            deletion_subjects.add(URIRef(entity["uri"]))

    return deletion_subjects


def _setup_editor(
    primary_source: str | None,
    changes: list[dict],
    subject: URIRef,
    affected_entities: list[dict],
    *,
    delete_affected: bool,
) -> tuple[Editor, URIRef | None]:
    resp_agent = get_responsible_agent_uri(current_user.orcid)
    editor = new_editor(resp_agent, get_primary_source())

    deletion_subjects = _collect_entity_deletion_subjects(
        changes, affected_entities, delete_affected=delete_affected
    )

    editor = import_entity_graph(
        editor,
        subject,
        include_referencing_entities=subject in deletion_subjects,
    )
    for deletion_subject in sorted(deletion_subjects - {subject}, key=str):
        editor = import_entity_graph(
            editor, deletion_subject, include_referencing_entities=True
        )

    for change in changes:
        if change["action"] == "create":
            data = change.get("data")
            if data:
                import_referenced_entities(editor, data)
        elif URIRef(change["subject"]) != subject and (
            change["action"] == "add_link"
            or (change["action"] == "delete" and change.get("predicate"))
        ):
            editor = import_entity_graph(editor, URIRef(change["subject"]))

    editor.preexisting_finished()
    editor.set_primary_source(URIRef(primary_source) if primary_source else None)

    graph_uri: URIRef | None = None
    if editor.dataset_is_quadstore:
        for quad in editor.g_set.quads((subject, None, None, None)):  # type: ignore[union-attr]
            graph_uri = get_graph_uri_from_context(cast("Graph | URIRef", quad[3]))
            break

    return editor, graph_uri


def _process_creates(
    editor: Editor,
    changes: list[dict],
    graph_uri: URIRef | None,
    subject: URIRef,
) -> tuple[dict[str, str], URIRef]:
    temp_id_to_uri: dict[str, str] = {}
    for change in changes:
        if change["action"] == "create":
            data = change.get("data")
            if data:
                change_subject_str = change.get("subject")
                change_subject = (
                    URIRef(change_subject_str) if change_subject_str else None
                )
                created_subject = create_logic(
                    editor,
                    data,
                    change_subject,
                    graph_uri,
                    temp_id_to_uri=temp_id_to_uri,
                    parent_entity_type=None,
                )
                if change_subject is not None:
                    subject = created_subject
    return temp_id_to_uri, subject


def _handle_affected_entities(
    editor: Editor,
    affected_entities: list[dict],
    *,
    delete_affected: bool,
    graph_uri: URIRef | None,
    deleted_entities: set[URIRef],
) -> None:
    orphan_strategy = current_app.config["ORPHAN_HANDLING_STRATEGY"]
    composite_strategy = current_app.config["COMPOSITE_HANDLING_STRATEGY"]
    # Separiamo le operazioni di delete in due fasi:
    # 1. Prima eliminiamo tutte le entità orfane/intermedie
    # 2. Poi eliminiamo le triple specifiche

    # Fase 1: Elimina le entità orfane/intermedie
    if not (affected_entities and delete_affected):
        return

    orphans = [entity for entity in affected_entities if not entity.get("is_composite")]
    composites = [entity for entity in affected_entities if entity.get("is_composite")]

    # Gestione degli orfani secondo la strategia per gli orfani
    should_delete_orphans = orphan_strategy == OrphanHandlingStrategy.DELETE or (
        orphan_strategy == OrphanHandlingStrategy.ASK and delete_affected
    )

    if should_delete_orphans and orphans:
        for orphan in orphans:
            orphan_uri = URIRef(orphan["uri"])
            if orphan_uri in deleted_entities:
                continue

            delete_logic(
                ChangeOperation(editor=editor, subject=orphan_uri, graph_uri=graph_uri)
            )
            deleted_entities.add(orphan_uri)

    should_delete_composites = (
        composite_strategy == CompositeHandlingStrategy.DELETE
        or (composite_strategy == CompositeHandlingStrategy.ASK and delete_affected)
    )

    if should_delete_composites and composites:
        for composite in composites:
            composite_uri = URIRef(composite["uri"])
            if composite_uri in deleted_entities:
                continue

            delete_logic(
                ChangeOperation(
                    editor=editor, subject=composite_uri, graph_uri=graph_uri
                )
            )
            deleted_entities.add(composite_uri)


def _process_remaining_changes(
    editor: Editor,
    changes: list[dict],
    graph_uri: URIRef | None,
    deleted_entities: set[URIRef],
    temp_id_to_uri: dict[str, str],
) -> None:
    for change in changes:
        if change["action"] == "delete":
            _process_delete_change(editor, change, graph_uri, deleted_entities)
        elif change["action"] == "add_link":
            editor.create(
                URIRef(change["subject"]),
                URIRef(change["predicate"]),
                URIRef(change["object"]),
                graph_uri,
            )
        elif change["action"] == "update":
            op = ChangeOperation(
                editor=editor,
                subject=URIRef(change["subject"]),
                graph_uri=graph_uri,
                entity_type=change.get("entity_type"),
                entity_shape=change.get("entity_shape"),
            )
            update_logic(
                op,
                URIRef(change["predicate"]),
                change["object"],
                change["newObject"],
            )
        elif change["action"] == "order":
            op = ChangeOperation(
                editor=editor,
                subject=URIRef(change["subject"]),
                graph_uri=graph_uri,
            )
            presentation = get_presentation().property_presentation(
                change["entity_shape"], change["predicate"], change["shape"]
            )
            indexed = presentation is not None and presentation.indexed
            (index_logic if indexed else order_logic)(
                op,
                URIRef(change["predicate"]),
                change["object"],
                URIRef(change["newObject"]),
                temp_id_to_uri,
            )


def _process_delete_change(
    editor: Editor,
    change: dict,
    graph_uri: URIRef | None,
    deleted_entities: set[URIRef],
) -> None:
    change_subject = URIRef(change["subject"])
    change_predicate = URIRef(change["predicate"]) if change.get("predicate") else None
    raw_object_value = change.get("object")
    object_value = str(raw_object_value) if raw_object_value is not None else None

    op = ChangeOperation(
        editor=editor,
        subject=change_subject,
        graph_uri=graph_uri,
        entity_type=change.get("entity_type"),
        entity_shape=change.get("entity_shape"),
    )

    if not change_predicate:
        if change_subject in deleted_entities:
            return

        delete_logic(op)
        deleted_entities.add(change_subject)
    elif object_value is not None:
        if change_subject in deleted_entities or (
            is_valid_url(object_value) and URIRef(object_value) in deleted_entities
        ):
            return

        delete_logic(op, change_predicate, object_value)


def _save_and_respond(editor: Editor) -> tuple[Response, int]:
    try:
        editor.save()
    except (ConfigurationRejectedError, ValueError):
        current_app.logger.exception("Error during save operation")
        raise
    except Exception as save_error:
        current_app.logger.exception("Error during save operation")
        return jsonify(
            {
                "status": "error",
                "error_type": "database",
                "message": f"Failed to save changes to the database: {save_error!s}",
            }
        ), 500

    record_dataset_change()
    return (
        jsonify(
            {
                "status": "success",
                "message": "Changes applied successfully",
            }
        ),
        200,
    )


@api_bp.route("/apply_changes", methods=["POST"])
@login_required
def apply_changes() -> tuple[Response, int]:
    """Apply changes to entities.

    Request body:
    {
        "subject": (str) Main entity URI being modified,
        "changes": (list) List of changes to apply,
        "primary_source": (str) Primary source to use for provenance,
        "save_default_source": (bool) Whether to save primary_source as default for
        current user,
        "affected_entities": (list) Entities potentially affected by delete operations,
        "delete_affected": (bool) Whether to delete affected entities
    }

    Responses:
    200 OK: Changes applied successfully
    400 Bad Request: Invalid request or validation error
    500 Internal Server Error: Server error while applying changes
    """
    try:
        changes = request.get_json()
        if not changes:
            return jsonify({"error": "No request data provided"}), 400

        (
            subject,
            affected_entities,
            delete_affected,
            primary_source,
            save_default_source,
        ) = _parse_change_request(changes)

        if primary_source and not is_valid_url(primary_source):
            return jsonify({"error": "Invalid primary source URL"}), 400

        if save_default_source and primary_source and is_valid_url(primary_source):
            save_user_default_primary_source(current_user.orcid, primary_source)

        changes = expand_inverse_changes(changes)

        editor, graph_uri = _setup_editor(
            primary_source,
            changes,
            subject,
            affected_entities,
            delete_affected=delete_affected,
        )

        temp_id_to_uri, subject = _process_creates(editor, changes, graph_uri, subject)

        deleted_entities: set[URIRef] = set()
        _handle_affected_entities(
            editor,
            affected_entities,
            delete_affected=delete_affected,
            graph_uri=graph_uri,
            deleted_entities=deleted_entities,
        )
        _process_remaining_changes(
            editor, changes, graph_uri, deleted_entities, temp_id_to_uri
        )

        return _save_and_respond(editor)

    except ConfigurationRejectedError:
        raise
    except ValueError as e:
        error_message = str(e)
        current_app.logger.warning("Validation error: %s", error_message)
        return (
            jsonify(
                {
                    "status": "error",
                    "error_type": "validation",
                    "message": error_message,
                }
            ),
            400,
        )
    except Exception as e:
        error_message = f"Error while applying changes: {e!s}\n{traceback.format_exc()}"
        current_app.logger.exception(error_message)
        return (
            jsonify(
                {
                    "status": "error",
                    "error_type": "system",
                    "message": "An error occurred while applying changes",
                }
            ),
            500,
        )


def get_graph_uri_from_context(graph_context: Graph | URIRef) -> URIRef:
    if isinstance(graph_context, Graph):
        return cast("URIRef", graph_context.identifier)
    return cast("URIRef", graph_context)


class CreateEntityData(TypedDict, total=False):
    entity_type: str
    # TODO(arcangelo): tighten this type after normalizing
    # the frontend payload to a consistent shape
    properties: dict[str, list | dict | str]
    tempId: str


@dataclass
class _CreateContext:
    editor: Editor
    graph_uri: URIRef | None
    entity_type: str | None
    temp_id_to_uri: dict[str, str] | None


def _handle_property_value(
    ctx: _CreateContext,
    value: dict | str,
    subject: URIRef,
    predicate: URIRef,
) -> None:
    if isinstance(value, dict) and "entity_type" in value:
        nested_subject = generate_unique_uri(value["entity_type"])
        create_logic(
            ctx.editor,
            cast("CreateEntityData", value),
            nested_subject,
            ctx.graph_uri,
            subject,
            predicate,
            ctx.temp_id_to_uri,
            parent_entity_type=ctx.entity_type,
        )
    elif isinstance(value, dict) and value.get("is_existing_entity", False):
        entity_uri = value.get("entity_uri")
        if entity_uri:
            ctx.editor.create(subject, predicate, URIRef(entity_uri), ctx.graph_uri)
        else:
            msg = "Missing entity_uri in existing entity reference"
            raise ValueError(msg)
    elif isinstance(value, dict) and value.get("is_custom_property", False):
        if value["type"] == "uri":
            object_value = URIRef(value["value"])
        elif value["type"] == "literal":
            datatype = URIRef(value["datatype"]) if "datatype" in value else XSD.string
            object_value = Literal(value["value"], datatype=datatype)
        else:
            msg = f"Unknown custom property type: {value['type']}"
            raise ValueError(msg)

        ctx.editor.create(subject, predicate, object_value, ctx.graph_uri)
    else:
        object_value, _, error_message = validate_new_triple(
            subject,
            predicate,
            str(value),
            "create",
            entity_types=ctx.entity_type,
        )
        if error_message:
            raise ValueError(error_message)

        if object_value is not None:
            ctx.editor.create(subject, predicate, object_value, ctx.graph_uri)


def _setup_parent_relations(
    ctx: _CreateContext,
    subject: URIRef,
    parent_subject: URIRef,
    parent_predicate: URIRef | None,
    parent_entity_type: str | None,
) -> None:
    type_value, _, error_message = validate_new_triple(
        subject, RDF.type, ctx.entity_type, "create", entity_types=ctx.entity_type
    )
    if error_message:
        raise ValueError(error_message)

    if type_value is not None:
        ctx.editor.create(subject, RDF.type, type_value, ctx.graph_uri)

    if parent_predicate:
        parent_value, _, error_message = validate_new_triple(
            parent_subject,
            parent_predicate,
            subject,
            "create",
            entity_types=parent_entity_type,
        )
        if error_message:
            raise ValueError(error_message)

        if parent_value is not None:
            ctx.editor.create(
                parent_subject, parent_predicate, parent_value, ctx.graph_uri
            )


def create_logic(  # noqa: PLR0913
    editor: Editor,
    data: CreateEntityData,
    subject: URIRef | None = None,
    graph_uri: URIRef | None = None,
    parent_subject: URIRef | None = None,
    parent_predicate: URIRef | None = None,
    temp_id_to_uri: dict[str, str] | None = None,
    parent_entity_type: str | None = None,
) -> URIRef:
    entity_type: str | None = data.get("entity_type")
    properties: dict = data.get("properties", {})
    temp_id: str | None = data.get("tempId")

    if subject is None:
        subject = generate_unique_uri(entity_type, cast("dict", data))

    if temp_id and temp_id_to_uri is not None:
        temp_id_to_uri[temp_id] = str(subject)

    ctx = _CreateContext(editor, graph_uri, entity_type, temp_id_to_uri)

    if parent_subject is not None:
        _setup_parent_relations(
            ctx, subject, parent_subject, parent_predicate, parent_entity_type
        )

    for predicate_str, values in properties.items():
        predicate = URIRef(predicate_str)
        values_list = values if isinstance(values, list) else [values]
        for value in values_list:
            _handle_property_value(ctx, value, subject, predicate)

    return subject


def update_logic(
    op: ChangeOperation,
    predicate: URIRef,
    old_value: str,
    new_value: str,
) -> None:
    old_value_rdf: URIRef | Literal = (
        URIRef(old_value) if is_valid_url(old_value) else Literal(old_value)
    )
    validated_new, validated_old, error_message = validate_new_triple(
        op.subject,
        predicate,
        new_value,
        "update",
        old_value_rdf,
        entity_types=op.entity_type,
    )
    if error_message:
        raise ValueError(error_message)

    op.editor.update(
        op.subject,
        predicate,
        cast("Literal | URIRef", validated_old),
        cast("Literal | URIRef", validated_new),
        op.graph_uri,
    )


def rebuild_entity_order(
    editor: Editor,
    ordered_by_uri: URIRef,
    entities: list[URIRef],
    graph_uri: URIRef | None = None,
) -> Editor:
    for entity in entities:
        for _s, _p, o in list(
            get_triples_from_graph(editor.g_set, (entity, ordered_by_uri, None))
        ):
            editor.delete(
                entity, ordered_by_uri, cast("Literal | URIRef", o), graph_uri
            )

    # Then rebuild the chain with the entities
    for i in range(len(entities) - 1):
        current_entity = entities[i]
        next_entity = entities[i + 1]
        editor.create(current_entity, ordered_by_uri, next_entity, graph_uri)

    return editor


def delete_logic(
    op: ChangeOperation,
    predicate: URIRef | None = None,
    object_value: str | None = None,
) -> None:
    resolved_value: URIRef | Literal | None = None
    if predicate and object_value:
        old_val_rdf: URIRef | Literal = (
            URIRef(object_value)
            if is_valid_url(object_value)
            else Literal(object_value)
        )
        _, resolved_value, error_message = validate_new_triple(
            op.subject,
            predicate,
            None,
            "delete",
            old_val_rdf,
            entity_types=op.entity_type,
        )
        if error_message:
            raise ValueError(error_message)

    op.editor.delete(
        op.subject,
        predicate,
        cast("Literal | URIRef | None", resolved_value),
        op.graph_uri,
    )


def order_logic(
    op: ChangeOperation,
    predicate: URIRef,
    new_order: list[str],
    ordered_by: URIRef,
    temp_id_to_uri: dict[str, str] | None = None,
) -> Editor:
    current_entities = [
        o
        for _, _, o in get_triples_from_graph(
            op.editor.g_set, (op.subject, predicate, None)
        )
    ]

    old_to_new_mapping = {}

    for old_entity in current_entities:
        if str(old_entity) in new_order:
            entity_properties = list(
                get_triples_from_graph(
                    op.editor.g_set,
                    (cast("URIRef", old_entity), None, None),
                )
            )

            entity_type = next(
                (o for _, p, o in entity_properties if p == RDF.type), None
            )

            if entity_type is None:
                msg = f"Impossibile determinare il tipo dell'entità per {old_entity}"
                raise ValueError(msg)

            new_entity_uri = generate_unique_uri(str(entity_type))
            old_to_new_mapping[old_entity] = new_entity_uri

            op.editor.delete(
                op.subject,
                predicate,
                cast("Literal | URIRef", old_entity),
                op.graph_uri,
            )
            op.editor.delete(cast("URIRef", old_entity), graph=op.graph_uri)

            op.editor.create(op.subject, predicate, new_entity_uri, op.graph_uri)

            for _, p, o in entity_properties:
                if p not in (predicate, ordered_by):
                    op.editor.create(
                        new_entity_uri,
                        cast("URIRef", p),
                        cast("Literal | URIRef", o),
                        op.graph_uri,
                    )

    ordered_entities = []
    for entity in new_order:
        new_entity_uri = old_to_new_mapping.get(URIRef(entity))
        if not new_entity_uri:
            new_entity_uri = URIRef(
                temp_id_to_uri.get(entity, entity) if temp_id_to_uri else entity
            )
        ordered_entities.append(new_entity_uri)

    if ordered_entities:
        rebuild_entity_order(op.editor, ordered_by, ordered_entities, op.graph_uri)

    return op.editor


def index_logic(
    op: ChangeOperation,
    _predicate: URIRef,
    new_order: list[str],
    index_property: URIRef,
    temp_id_to_uri: dict[str, str] | None = None,
) -> Editor:
    for position, value in enumerate(new_order, start=1):
        entity = URIRef((temp_id_to_uri or {}).get(value, value))
        for _, _, index in list(
            get_triples_from_graph(op.editor.g_set, (entity, index_property, None))
        ):
            op.editor.delete(
                entity, index_property, cast("Literal | URIRef", index), op.graph_uri
            )
        op.editor.create(entity, index_property, Literal(position), op.graph_uri)
    return op.editor


@api_bp.route("/form-fields", methods=["GET"])
@login_required
def get_form_fields_for_entity() -> Response | tuple[Response, int]:
    """
    Get form_fields for a specific entity class and shape combination.
    Returns only the requested entity + immediate sub-entities (depth=2) to improve
    performance.

    Query parameters:
        entity_class: URI of the entity class
        entity_shape: URI of the entity shape

    Returns:
        JSON response with form_fields for the specified entity
    """

    try:
        entity_class_decoded = request.args.get("entity_class")
        entity_shape_decoded = request.args.get("entity_shape")

        if not entity_class_decoded or not entity_shape_decoded:
            return jsonify(
                {
                    "status": "error",
                    "message": (
                        "Missing required parameters: entity_class and entity_shape"
                    ),
                }
            ), 400

        all_form_fields = get_form_fields()

        if not all_form_fields:
            return jsonify(
                {"status": "error", "message": "Form fields not initialized"}
            ), 500

        entity_key = (entity_class_decoded, entity_shape_decoded)

        if entity_key not in all_form_fields:
            return jsonify(
                {
                    "status": "error",
                    "message": (
                        f"No form fields found for entity class"
                        f" {entity_class_decoded} with shape"
                        f" {entity_shape_decoded}"
                    ),
                }
            ), 404

        entity_form_fields = all_form_fields[entity_key]
        custom_filter = get_custom_filter()
        ordered_properties = [
            [
                prop,
                [field_with_labels(details, custom_filter) for details in details_list],
            ]
            for prop, details_list in entity_form_fields.items()
        ]

        return jsonify(
            {
                "status": "success",
                "form_fields": ordered_properties,
                "entity_key": [entity_class_decoded, entity_shape_decoded],
            }
        )

    except Exception as e:
        current_app.logger.exception(
            "Error loading form fields for %s/%s",
            entity_class_decoded,
            entity_shape_decoded,
        )

        return jsonify(
            {"status": "error", "message": f"Failed to load form fields: {e!s}"}
        ), 500


@api_bp.route("/draft-labels", methods=["POST"])
@login_required
def preview_draft_labels() -> Response | tuple[Response, int]:
    data = request.get_json()
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        return jsonify({"error": "Expected a list of draft entries"}), 400
    for entry in data["entries"]:
        if not isinstance(entry, dict) or not all(
            key in entry
            for key in ("parent_class", "parent_shape", "predicate", "entity")
        ):
            return jsonify({"error": "Invalid draft entry"}), 400
        entity = entry["entity"]
        if not isinstance(entity, dict) or not all(
            key in entity for key in ("entity_type", "entity_shape", "properties")
        ):
            return jsonify({"error": "Invalid draft entity"}), 400
    return jsonify({"labels": [draft_label(entry) for entry in data["entries"]]})
