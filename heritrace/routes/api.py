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
    render_template_string,
    request,
)
from flask_babel import gettext
from flask_login import current_user, login_required
from rdflib import RDF, XSD, Graph, Literal, URIRef

from heritrace.apis.orcid import get_responsible_agent_uri
from heritrace.editor import Editor, EndpointConfig
from heritrace.extensions import (
    get_custom_filter,
    get_dataset_endpoint,
    get_form_fields,
    get_provenance_endpoint,
)
from heritrace.services.resource_lock_manager import LockStatus
from heritrace.utils.datatypes import DATATYPE_MAPPING
from heritrace.utils.primary_source_utils import save_user_default_primary_source
from heritrace.utils.shacl_utils import determine_shape_for_classes
from heritrace.utils.shacl_validation import validate_new_triple
from heritrace.utils.sparql_utils import (
    CatalogQuery,
    DeletedEntitiesQuery,
    find_orphaned_entities,
    get_available_classes,
    get_catalog_data,
    get_deleted_entities_with_filtering,
    get_triples_from_graph,
    import_entity_graph,
    import_referenced_entities,
)
from heritrace.utils.strategies import OrphanHandlingStrategy, ProxyHandlingStrategy
from heritrace.utils.uri_utils import generate_unique_uri, is_valid_url
from heritrace.utils.virtual_properties import transform_changes_with_virtual_properties


@dataclass(frozen=True, slots=True)
class ChangeOperation:
    editor: Editor
    subject: URIRef
    graph_uri: URIRef | None = None
    entity_type: str | None = None
    entity_shape: str | None = None


api_bp = Blueprint("api", __name__)


@api_bp.route("/catalogue")
@login_required
def catalogue_api() -> Response:
    selected_class = request.args.get("class")
    selected_shape = request.args.get("shape")
    page = int(request.args.get("page", 1))
    per_page = int(
        request.args.get("per_page", current_app.config["CATALOGUE_DEFAULT_PER_PAGE"])
    )
    sort_property = request.args.get("sort_property")
    sort_direction = request.args.get("sort_direction", "ASC")

    allowed_per_page = current_app.config["CATALOGUE_ALLOWED_PER_PAGE"]
    if per_page not in allowed_per_page:
        per_page = current_app.config["CATALOGUE_DEFAULT_PER_PAGE"]

    if not sort_property or sort_property.lower() == "null":
        sort_property = None

    available_classes = get_available_classes()

    catalog_data = get_catalog_data(
        CatalogQuery(
            selected_class=selected_class,
            page=page,
            per_page=per_page,
            sort_property=sort_property,
            sort_direction=sort_direction,
            selected_shape=selected_shape,
        ),
        available_classes,
    )

    catalog_data["available_classes"] = available_classes
    return jsonify(catalog_data)


@api_bp.route("/time-vault")
@login_required
def get_deleted_entities_api() -> Response:
    """
    API endpoint to retrieve deleted entities with pagination and sorting.
    Only processes and returns entities whose classes are marked as visible.
    """
    selected_class = request.args.get("class")
    selected_shape = request.args.get("shape")
    page = int(request.args.get("page", 1))
    per_page = int(
        request.args.get("per_page", current_app.config["CATALOGUE_DEFAULT_PER_PAGE"])
    )
    sort_property = request.args.get("sort_property", "deletionTime")
    sort_direction = request.args.get("sort_direction", "DESC")

    allowed_per_page = current_app.config["CATALOGUE_ALLOWED_PER_PAGE"]
    if per_page not in allowed_per_page:
        per_page = current_app.config["CATALOGUE_DEFAULT_PER_PAGE"]

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
            sort_property,
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
            "sort_property": sort_property,
            "sort_direction": sort_direction,
            "selected_class": selected_class,
            "selected_shape": selected_shape,
            "available_classes": available_classes,
            "sortable_properties": sortable_properties,
        }
    )


@api_bp.route("/check-lock", methods=["POST"])
@login_required
def check_lock() -> Response | tuple[Response, int]:
    """Check if a resource is locked."""
    try:
        data = request.get_json()
        resource_uri = data.get("resource_uri")

        if not resource_uri:
            return (
                jsonify(
                    {"status": "error", "message": gettext("No resource URI provided")}
                ),
                400,
            )

        status, lock_info = g.resource_lock_manager.check_lock_status(resource_uri)

        if status == LockStatus.LOCKED:
            return jsonify(
                {
                    "status": "locked",
                    "title": gettext("Resource Locked"),
                    "message": gettext(
                        "This resource is currently being"
                        " edited by %(user)s [%(orcid)s]",
                        user=lock_info.user_name,
                        orcid=lock_info.user_id,
                    ),
                }
            )
        if status == LockStatus.ERROR:
            return (
                jsonify(
                    {
                        "status": "error",
                        "title": gettext("Error"),
                        "message": gettext("An error occurred while checking the lock"),
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
                    "title": gettext("Error"),
                    "message": gettext("An unexpected error occurred"),
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
                jsonify(
                    {"status": "error", "message": gettext("No resource URI provided")}
                ),
                400,
            )

        # First check if the resource or any related resource is locked by another user
        status, lock_info = g.resource_lock_manager.check_lock_status(resource_uri)
        if status == LockStatus.LOCKED:
            return (
                jsonify(
                    {
                        "status": "locked",
                        "title": gettext("Resource Locked"),
                        "message": gettext(
                            "This resource is currently"
                            " being edited by"
                            " %(user)s [%(orcid)s]",
                            user=lock_info.user_name,
                            orcid=lock_info.user_id,
                        ),
                    }
                ),
                200,
            )

        # Use the provided linked_resources
        success = g.resource_lock_manager.acquire_lock(resource_uri, linked_resources)

        if success:
            return jsonify({"status": "success"})

        return (
            jsonify(
                {
                    "status": "error",
                    "message": gettext("Resource is locked by another user"),
                }
            ),
            423,
        )

    except Exception:
        current_app.logger.exception("Error in acquire_lock")
        return (
            jsonify(
                {"status": "error", "message": gettext("An unexpected error occurred")}
            ),
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
                jsonify(
                    {"status": "error", "message": gettext("No resource URI provided")}
                ),
                400,
            )

        success = g.resource_lock_manager.release_lock(resource_uri)

        if success:
            return jsonify({"status": "success"})

        return (
            jsonify({"status": "error", "message": gettext("Unable to release lock")}),
            400,
        )

    except Exception:
        current_app.logger.exception("Error in release_lock")
        return (
            jsonify(
                {"status": "error", "message": gettext("An unexpected error occurred")}
            ),
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
                jsonify(
                    {"status": "error", "message": gettext("No resource URI provided")}
                ),
                400,
            )

        # When renewing a lock, we don't need to check for linked resources again
        # Just pass an empty list as we're only refreshing the existing lock
        success = g.resource_lock_manager.acquire_lock(resource_uri, [])

        if success:
            return jsonify({"status": "success"})

        return (
            jsonify({"status": "error", "message": gettext("Unable to renew lock")}),
            423,
        )

    except Exception:
        current_app.logger.exception("Error in renew_lock")
        return (
            jsonify(
                {"status": "error", "message": gettext("An unexpected error occurred")}
            ),
            500,
        )


@api_bp.route("/validate-literal", methods=["POST"])
@login_required
def validate_literal() -> tuple[Response, int]:
    """Validate a literal value and suggest appropriate datatypes."""
    value = request.json.get("value")
    if not value:
        return jsonify({"error": gettext("Value is required.")}), 400

    matching_datatypes = []
    for datatype, validation_func, _ in DATATYPE_MAPPING:
        if validation_func(value):
            matching_datatypes.append(str(datatype))

    if not matching_datatypes:
        return jsonify({"error": gettext("No matching datatypes found.")}), 400

    return jsonify({"valid_datatypes": matching_datatypes}), 200


def _collect_affected_entities(
    changes: list[dict],
    entity_type: str,
    *,
    check_for_orphans: bool,
    check_for_proxies: bool,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    orphans: list[dict[str, str]] = []
    intermediate_orphans: list[dict[str, str]] = []
    for change in changes:
        if change["action"] == "delete":
            found_orphans, found_intermediates = find_orphaned_entities(
                URIRef(change["subject"]),
                entity_type,
                URIRef(change["predicate"]) if change.get("predicate") else None,
                change.get("object"),
            )
            if check_for_orphans:
                orphans.extend(found_orphans)
            if check_for_proxies:
                intermediate_orphans.extend(found_intermediates)
    return orphans, intermediate_orphans


def _format_orphan_response(
    orphans: list[dict[str, str]],
    intermediate_orphans: list[dict[str, str]],
    entity_shape: str | None,
    orphan_strategy: OrphanHandlingStrategy,
    proxy_strategy: ProxyHandlingStrategy,
) -> Response:
    custom_filter = get_custom_filter()

    def format_entities(
        entities: list[dict[str, str]],
        *,
        is_intermediate: bool = False,
    ) -> list[dict[str, str | bool]]:
        return [
            {
                "uri": entity["uri"],
                "label": custom_filter.human_readable_entity(
                    entity["uri"], (entity["type"], entity_shape)
                ),
                "type": custom_filter.human_readable_class(
                    (entity["type"], entity_shape)
                ),
                "is_intermediate": is_intermediate,
            }
            for entity in entities
        ]

    affected_entities = format_entities(orphans) + format_entities(
        intermediate_orphans, is_intermediate=True
    )

    should_delete = (
        orphan_strategy == OrphanHandlingStrategy.DELETE
        and proxy_strategy == ProxyHandlingStrategy.DELETE
    )

    return jsonify(
        {
            "status": "success",
            "affected_entities": affected_entities,
            "should_delete": should_delete,
            "orphan_strategy": orphan_strategy.value,
            "proxy_strategy": proxy_strategy.value,
        }
    )


@api_bp.route("/check_orphans", methods=["POST"])
@login_required
def check_orphans() -> Response | tuple[Response, int]:
    try:
        orphan_strategy = current_app.config.get(
            "ORPHAN_HANDLING_STRATEGY", OrphanHandlingStrategy.KEEP
        )
        proxy_strategy = current_app.config.get(
            "PROXY_HANDLING_STRATEGY", ProxyHandlingStrategy.KEEP
        )

        data = request.json
        if not data or "changes" not in data or "entity_type" not in data:
            return (
                jsonify(
                    {
                        "status": "error",
                        "error_type": "validation",
                        "message": gettext(
                            "Invalid request: 'changes' and"
                            " 'entity_type' are required fields"
                        ),
                    }
                ),
                400,
            )

        changes = data.get("changes", [])
        entity_type = data.get("entity_type")
        entity_shape = data.get("entity_shape")

        check_for_orphans = orphan_strategy in (
            OrphanHandlingStrategy.DELETE,
            OrphanHandlingStrategy.ASK,
        )
        check_for_proxies = proxy_strategy in (
            ProxyHandlingStrategy.DELETE,
            ProxyHandlingStrategy.ASK,
        )

        orphans: list[dict[str, str]] = []
        intermediate_orphans: list[dict[str, str]] = []
        if check_for_orphans or check_for_proxies:
            orphans, intermediate_orphans = _collect_affected_entities(
                changes,
                entity_type,
                check_for_orphans=check_for_orphans,
                check_for_proxies=check_for_proxies,
            )

        if (orphan_strategy == OrphanHandlingStrategy.KEEP or not orphans) and (
            proxy_strategy == ProxyHandlingStrategy.KEEP or not intermediate_orphans
        ):
            return jsonify({"status": "success", "affected_entities": []})

        return _format_orphan_response(
            orphans,
            intermediate_orphans,
            entity_shape,
            orphan_strategy,
            proxy_strategy,
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
                    "message": gettext(
                        "An error occurred while checking for orphaned entities"
                    ),
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
                    "message": gettext(
                        "An error occurred while checking for orphaned entities"
                    ),
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
    proxy_strategy = current_app.config["PROXY_HANDLING_STRATEGY"]

    if entity["is_intermediate"]:
        return delete_affected and proxy_strategy in (
            ProxyHandlingStrategy.DELETE,
            ProxyHandlingStrategy.ASK,
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
    editor = Editor(
        EndpointConfig(
            dataset=get_dataset_endpoint(),
            provenance=get_provenance_endpoint(),
            is_quadstore=current_app.config["DATASET_IS_QUADSTORE"],
        ),
        current_app.config["COUNTER_HANDLER"],
        resp_agent,
        current_app.config["PRIMARY_SOURCE"],
        current_app.config["DATASET_GENERATION_TIME"],
        save_plugin=current_app.config.get("SAVE_PLUGIN"),
    )

    if primary_source and is_valid_url(primary_source):
        editor.set_primary_source(URIRef(primary_source))

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

    editor.preexisting_finished()

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
    orphan_strategy = current_app.config.get(
        "ORPHAN_HANDLING_STRATEGY", OrphanHandlingStrategy.KEEP
    )
    proxy_strategy = current_app.config.get(
        "PROXY_HANDLING_STRATEGY", ProxyHandlingStrategy.KEEP
    )
    # Separiamo le operazioni di delete in due fasi:
    # 1. Prima eliminiamo tutte le entità orfane/intermedie
    # 2. Poi eliminiamo le triple specifiche

    # Fase 1: Elimina le entità orfane/intermedie
    if not (affected_entities and delete_affected):
        return

    # Separa gli orfani dalle entità proxy
    orphans = [
        entity for entity in affected_entities if not entity.get("is_intermediate")
    ]
    proxies = [entity for entity in affected_entities if entity.get("is_intermediate")]

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

    # Gestione delle entità proxy secondo la strategia per i proxy
    should_delete_proxies = proxy_strategy == ProxyHandlingStrategy.DELETE or (
        proxy_strategy == ProxyHandlingStrategy.ASK and delete_affected
    )

    if should_delete_proxies and proxies:
        for proxy in proxies:
            proxy_uri = URIRef(proxy["uri"])
            if proxy_uri in deleted_entities:
                continue

            delete_logic(
                ChangeOperation(editor=editor, subject=proxy_uri, graph_uri=graph_uri)
            )
            deleted_entities.add(proxy_uri)


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
            order_logic(
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
        if is_valid_url(object_value) and URIRef(object_value) in deleted_entities:
            return

        delete_logic(op, change_predicate, object_value)


def _save_and_respond(editor: Editor) -> tuple[Response, int]:
    try:
        editor.save()
    except ValueError:
        current_app.logger.exception("Error during save operation")
        raise
    except Exception as save_error:
        current_app.logger.exception("Error during save operation")
        return jsonify(
            {
                "status": "error",
                "error_type": "database",
                "message": gettext("Failed to save changes to the database: {}").format(
                    str(save_error)
                ),
            }
        ), 500

    return (
        jsonify(
            {
                "status": "success",
                "message": gettext("Changes applied successfully"),
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

        changes = transform_changes_with_virtual_properties(changes)

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
                    "message": gettext("An error occurred while applying changes"),
                }
            ),
            500,
        )


def get_graph_uri_from_context(graph_context: Graph | URIRef) -> URIRef:
    if isinstance(graph_context, Graph):
        return cast("URIRef", graph_context.identifier)
    return cast("URIRef", graph_context)


def determine_datatype(value: str, datatype_uris: list[str]) -> URIRef:
    for datatype_uri in datatype_uris:
        validation_func = next(
            (d[1] for d in DATATYPE_MAPPING if str(d[0]) == str(datatype_uri)), None
        )
        if validation_func and validation_func(value):
            return URIRef(datatype_uri)
    # If none match, default to XSD.string
    return XSD.string


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


@api_bp.route("/human-readable-entity", methods=["POST"])
@login_required
def get_human_readable_entity() -> str | tuple[Response, int]:
    custom_filter = get_custom_filter()

    # Check if required parameters are present
    if "uri" not in request.form or "entity_class" not in request.form:
        return jsonify(
            {"status": "error", "message": "Missing required parameters"}
        ), 400

    uri = request.form["uri"]
    entity_class = request.form["entity_class"]
    shape = determine_shape_for_classes([entity_class])
    filter_instance = custom_filter
    return filter_instance.human_readable_entity(uri, (entity_class, shape))


@api_bp.route("/format-source", methods=["POST"])
@login_required
def format_source_api() -> Response | tuple[Response, int]:
    """
    API endpoint to format a source URL using the application's filters.
    Accepts POST request with JSON body: {"url": "source_url"}
    Returns JSON: {"formatted_html": "html_string"}
    """
    data = request.get_json()
    source_url = data.get("url")

    if not source_url or not is_valid_url(source_url):
        return jsonify({"error": gettext("Invalid or missing URL")}), 400

    try:
        custom_filter = get_custom_filter()
        formatted_html = custom_filter.format_source_reference(source_url)
        return jsonify({"formatted_html": formatted_html})
    except Exception:
        current_app.logger.exception(
            "Error formatting source URL '%s'",
            source_url,
        )
        fallback_html = f'<a href="{source_url}" target="_blank">{source_url}</a>'
        return jsonify({"formatted_html": fallback_html})


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

        # Convert OrderedDict to list of [property, details] pairs to preserve order
        ordered_properties = []
        for prop, details_list in entity_form_fields.items():
            ordered_properties.append([prop, details_list])

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


@api_bp.route("/render-form-fields", methods=["POST"])
@login_required
def render_form_fields_html() -> str | tuple[Response, int]:
    """
    Render form fields as HTML for dynamic loading.

    Expects JSON payload with:
    - entity_key: [entity_class, entity_shape] array

    Returns:
        HTML string of the rendered form fields
    """
    try:
        data = request.get_json()

        if not data or "entity_key" not in data:
            return jsonify(
                {"status": "error", "message": "Missing required field: entity_key"}
            ), 400

        entity_key = data["entity_key"]  # This is [entity_class, entity_shape] array
        entity_class, entity_shape = entity_key

        all_form_fields = get_form_fields()

        if not all_form_fields:
            return jsonify(
                {"status": "error", "message": "Form fields not initialized"}
            ), 500

        tuple_key = (entity_class, entity_shape)
        if tuple_key not in all_form_fields:
            return jsonify(
                {
                    "status": "error",
                    "message": (
                        f"No form fields found for entity"
                        f" {entity_class} with shape"
                        f" {entity_shape}"
                    ),
                }
            ), 404

        entity_form_fields = all_form_fields[tuple_key]

        form_fields_array = [
            [prop, details_list] for prop, details_list in entity_form_fields.items()
        ]

        template_string = """
        {% from 'macros.jinja' import render_form_field with context %}

        {% set entity_type = entity_class %}
        {% set entity_shape = entity_shape %}
        {% set group_id = ((entity_type, entity_shape) | human_readable_class +
        "_group") | replace(" ", "_") %}
        <div class="property-group mb-3" id="{{ group_id }}" data-uri="{{ entity_type
        }}" data-shape="{{ entity_shape }}">
            {% for prop_data in ordered_form_fields %}
                {% set prop = prop_data[0] %}
                {% set details_list = prop_data[1] %}
                {% for details in details_list %}
                    {{ render_form_field(entity_type, prop, details, all_form_fields) }}
                {% endfor %}
            {% endfor %}
        </div>
        """

        return render_template_string(
            template_string,
            entity_class=entity_class,
            entity_shape=entity_shape,
            ordered_form_fields=form_fields_array,
            all_form_fields=all_form_fields,
        )

    except Exception as e:
        current_app.logger.exception("Error rendering form fields HTML")

        return jsonify(
            {"status": "error", "message": f"Failed to render form fields: {e!s}"}
        ), 500


def _validate_nested_form_request() -> (
    tuple[str, str, str, str, str, int, bool, dict] | tuple[Response, int]
):
    data = request.get_json()

    required_fields = [
        "parent_entity_class",
        "parent_entity_shape",
        "entity_class",
        "entity_shape",
        "predicate_uri",
        "depth",
    ]

    if not data:
        return jsonify({"status": "error", "message": "No JSON data provided"}), 400

    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify(
            {
                "status": "error",
                "message": f"Missing required fields: {', '.join(required_fields)}",
            }
        ), 400

    parent_entity_class = data["parent_entity_class"]
    parent_entity_shape = data["parent_entity_shape"]
    entity_class = data["entity_class"]
    entity_shape = data["entity_shape"]
    predicate_uri = data["predicate_uri"]
    depth = int(data["depth"])
    is_template = data.get("is_template", False)

    all_form_fields = get_form_fields()

    if not all_form_fields:
        return jsonify(
            {"status": "error", "message": "Form fields not initialized"}
        ), 500

    parent_entity_key = (parent_entity_class, parent_entity_shape)
    if parent_entity_key not in all_form_fields:
        return jsonify(
            {
                "status": "error",
                "message": (
                    "No form fields found for parent"
                    f" entity {parent_entity_class}"
                    f" with shape {parent_entity_shape}"
                ),
            }
        ), 404

    parent_fields = all_form_fields[parent_entity_key]
    if predicate_uri not in parent_fields:
        return jsonify(
            {
                "status": "error",
                "message": (
                    "No field definition found for"
                    f" predicate {predicate_uri}"
                    " in parent entity"
                ),
            }
        ), 404

    return (
        parent_entity_class,
        parent_entity_shape,
        entity_class,
        entity_shape,
        predicate_uri,
        depth,
        is_template,
        all_form_fields,
    )


@api_bp.route("/render-nested-form", methods=["POST"])
@login_required
def render_nested_form_html() -> str | tuple[Response, int]:
    try:
        validated = _validate_nested_form_request()
        if isinstance(validated[0], Response):
            return validated  # type: ignore[return-value]

        (
            parent_entity_class,
            parent_entity_shape,
            entity_class,
            entity_shape,
            predicate_uri,
            depth,
            is_template,
            all_form_fields,
        ) = cast("tuple[str, str, str, str, str, int, bool, dict]", validated)

        parent_entity_key = (parent_entity_class, parent_entity_shape)
        parent_fields = all_form_fields[parent_entity_key]
        field_details_list = parent_fields[predicate_uri]

        target_details = None
        for details in field_details_list:
            if details.get("or"):
                for shape_info in details["or"]:
                    if (
                        shape_info.get("entityType") == entity_class
                        and shape_info.get("nodeShape") == entity_shape
                    ):
                        target_details = shape_info
                        break
                if target_details:
                    break

        if not target_details:
            return jsonify(
                {
                    "status": "error",
                    "message": (
                        "No matching shape info found for"
                        f" {entity_class}/{entity_shape}"
                        f" in parent predicate"
                        f" {predicate_uri}"
                    ),
                }
            ), 404

        template_string = """
        {% from 'macros.jinja' import render_form_field with context %}
        {{ render_form_field(parent_entity_class, predicate_uri, shape_info,
        all_form_fields, depth, is_template=is_template) }}
        """

        return render_template_string(
            template_string,
            parent_entity_class=parent_entity_class,
            predicate_uri=predicate_uri,
            shape_info=target_details,
            all_form_fields=all_form_fields,
            depth=depth,
            is_template=is_template,
        )

    except Exception as e:
        current_app.logger.exception("Error rendering nested form HTML")

        return jsonify(
            {"status": "error", "message": f"Failed to render nested form: {e!s}"}
        ), 500
