# heritrace/routes/api.py

import traceback
from typing import Dict, Optional

import validators
from flask import Blueprint, current_app, g, jsonify, request
from flask_babel import gettext
from flask_login import current_user, login_required
from heritrace.editor import Editor
from heritrace.extensions import (get_custom_filter, get_dataset_endpoint,
                                  get_provenance_endpoint)
from heritrace.services.resource_lock_manager import LockStatus
from heritrace.utils.shacl_utils import determine_shape_for_classes
from heritrace.utils.primary_source_utils import \
    save_user_default_primary_source
from heritrace.utils.shacl_validation import validate_new_triple
from heritrace.utils.sparql_utils import (find_orphaned_entities,
                                          get_available_classes,
                                          get_catalog_data,
                                          get_deleted_entities_with_filtering,
                                          import_entity_graph)
from heritrace.utils.strategies import (OrphanHandlingStrategy,
                                        ProxyHandlingStrategy)
from heritrace.utils.uri_utils import generate_unique_uri
from rdflib import RDF, XSD, Graph, URIRef
from resources.datatypes import DATATYPE_MAPPING

api_bp = Blueprint("api", __name__)


@api_bp.route("/catalogue")
@login_required
def catalogue_api():
    selected_class = request.args.get("class")
    selected_shape = request.args.get("shape")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    sort_property = request.args.get("sort_property")
    sort_direction = request.args.get("sort_direction", "ASC")

    allowed_per_page = [50, 100, 200, 500]
    if per_page not in allowed_per_page:
        per_page = 50

    if not sort_property or sort_property.lower() == "null":
        sort_property = None

    available_classes = get_available_classes()
    
    catalog_data = get_catalog_data(
        selected_class=selected_class,
        page=page,
        per_page=per_page,
        sort_property=sort_property,
        sort_direction=sort_direction,
        selected_shape=selected_shape
    )

    catalog_data["available_classes"] = available_classes
    return jsonify(catalog_data)


@api_bp.route("/time-vault")
@login_required
def get_deleted_entities_api():
    """
    API endpoint to retrieve deleted entities with pagination and sorting.
    Only processes and returns entities whose classes are marked as visible.
    """
    selected_class = request.args.get("class")
    selected_shape = request.args.get("shape")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    sort_property = request.args.get("sort_property", "deletionTime")
    sort_direction = request.args.get("sort_direction", "DESC")

    allowed_per_page = [50, 100, 200, 500]
    if per_page not in allowed_per_page:
        per_page = 50

    deleted_entities, available_classes, selected_class, selected_shape, sortable_properties, total_count = (
        get_deleted_entities_with_filtering(
            page, per_page, sort_property, sort_direction, selected_class, selected_shape
        )
    )

    return jsonify(
        {
            "entities": deleted_entities,
            "total_pages": (total_count + per_page - 1) // per_page if total_count > 0 else 0,
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
def check_lock():
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
                        "This resource is currently being edited by %(user)s [%(orcid)s]",
                        user=lock_info.user_name,
                        orcid=lock_info.user_id,
                    ),
                }
            )
        elif status == LockStatus.ERROR:
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
        else:
            return jsonify({"status": "available"})

    except Exception as e:
        current_app.logger.error(f"Error in check_lock: {str(e)}")
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
def acquire_lock():
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
                            "This resource is currently being edited by %(user)s [%(orcid)s]",
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

    except Exception as e:
        current_app.logger.error(f"Error in acquire_lock: {str(e)}")
        return (
            jsonify(
                {"status": "error", "message": gettext("An unexpected error occurred")}
            ),
            500,
        )


@api_bp.route("/release-lock", methods=["POST"])
@login_required
def release_lock():
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

    except Exception as e:
        current_app.logger.error(f"Error in release_lock: {str(e)}")
        return (
            jsonify(
                {"status": "error", "message": gettext("An unexpected error occurred")}
            ),
            500,
        )


@api_bp.route("/renew-lock", methods=["POST"])
@login_required
def renew_lock():
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

    except Exception as e:
        current_app.logger.error(f"Error in renew_lock: {str(e)}")
        return (
            jsonify(
                {"status": "error", "message": gettext("An unexpected error occurred")}
            ),
            500,
        )


@api_bp.route("/validate-literal", methods=["POST"])
@login_required
def validate_literal():
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


@api_bp.route("/check_orphans", methods=["POST"])
@login_required
def check_orphans():
    """
    Check for orphaned entities and intermediate relations (proxies) that would result from the requested changes.
    Applies separate handling strategies for orphans and proxies, but returns a unified report.
    """
    try:
        # Get strategies from configuration
        orphan_strategy = current_app.config.get(
            "ORPHAN_HANDLING_STRATEGY", OrphanHandlingStrategy.KEEP
        )
        proxy_strategy = current_app.config.get(
            "PROXY_HANDLING_STRATEGY", ProxyHandlingStrategy.KEEP
        )

        data = request.json
        # Validate required fields
        if not data or "changes" not in data or "entity_type" not in data:
            return (
                jsonify(
                    {
                        "status": "error",
                        "error_type": "validation",
                        "message": gettext(
                            "Invalid request: 'changes' and 'entity_type' are required fields"
                        ),
                    }
                ),
                400,
            )

        changes = data.get("changes", [])
        entity_type = data.get("entity_type")
        entity_shape = data.get("entity_shape")
        custom_filter = get_custom_filter()

        orphans = []
        intermediate_orphans = []

        # Check for orphans and proxies based on their respective strategies
        check_for_orphans = orphan_strategy in (
            OrphanHandlingStrategy.DELETE,
            OrphanHandlingStrategy.ASK,
        )
        check_for_proxies = proxy_strategy in (
            ProxyHandlingStrategy.DELETE,
            ProxyHandlingStrategy.ASK,
        )
        if check_for_orphans or check_for_proxies:
            for change in changes:
                if change["action"] == "delete":
                    found_orphans, found_intermediates = find_orphaned_entities(
                        change["subject"],
                        entity_type,
                        change.get("predicate"),
                        change.get("object"),
                    )
                    # Only collect orphans if we need to handle them
                    if check_for_orphans:
                        orphans.extend(found_orphans)

                    # Only collect proxies if we need to handle them
                    if check_for_proxies:
                        intermediate_orphans.extend(found_intermediates)

        # If both strategies are KEEP or no entities found, return empty result
        if (orphan_strategy == OrphanHandlingStrategy.KEEP or not orphans) and (
            proxy_strategy == ProxyHandlingStrategy.KEEP or not intermediate_orphans
        ):
            return jsonify({"status": "success", "affected_entities": []})

        # Format entities for display
        def format_entities(entities, is_intermediate=False):
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

        # Create a unified list of affected entities
        affected_entities = format_entities(orphans) + format_entities(
            intermediate_orphans, is_intermediate=True
        )

        # Determine if we should automatically delete entities
        should_delete_orphans = orphan_strategy == OrphanHandlingStrategy.DELETE
        should_delete_proxies = proxy_strategy == ProxyHandlingStrategy.DELETE

        # If both strategies are DELETE, we can automatically delete everything
        if should_delete_orphans and should_delete_proxies:
            return jsonify(
                {
                    "status": "success",
                    "affected_entities": affected_entities,
                    "should_delete": True,
                    "orphan_strategy": orphan_strategy.value,
                    "proxy_strategy": proxy_strategy.value,
                }
            )

        # If at least one strategy is ASK, we need to ask the user
        return jsonify(
            {
                "status": "success",
                "affected_entities": affected_entities,
                "should_delete": False,
                "orphan_strategy": orphan_strategy.value,
                "proxy_strategy": proxy_strategy.value,
            }
        )
    except ValueError as e:
        # Handle validation errors specifically
        error_message = str(e)
        current_app.logger.warning(
            f"Validation error in check_orphans: {error_message}"
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
        # Handle other errors
        error_message = f"Error checking orphans: {str(e)}"
        current_app.logger.error(f"{error_message}\n{traceback.format_exc()}")
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


@api_bp.route("/apply_changes", methods=["POST"])
@login_required
def apply_changes():
    """Apply changes to entities.

    Request body:
    {
        "subject": (str) Main entity URI being modified,
        "changes": (list) List of changes to apply,
        "primary_source": (str) Primary source to use for provenance,
        "save_default_source": (bool) Whether to save primary_source as default for current user,
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

        first_change = changes[0] if changes else {}
        subject = first_change.get("subject")
        affected_entities = first_change.get("affected_entities", [])
        delete_affected = first_change.get("delete_affected", False)
        primary_source = first_change.get("primary_source")
        save_default_source = first_change.get("save_default_source", False)
        
        if primary_source and not validators.url(primary_source):
            return jsonify({"error": "Invalid primary source URL"}), 400
        
        if save_default_source and primary_source and validators.url(primary_source):
            save_user_default_primary_source(current_user.orcid, primary_source)
        
        deleted_entities = set()
        editor = Editor(
            get_dataset_endpoint(),
            get_provenance_endpoint(),
            current_app.config["COUNTER_HANDLER"],
            URIRef(f"https://orcid.org/{current_user.orcid}"),
            current_app.config["PRIMARY_SOURCE"],
            current_app.config["DATASET_GENERATION_TIME"],
            dataset_is_quadstore=current_app.config["DATASET_IS_QUADSTORE"],
        )
        
        if primary_source and validators.url(primary_source):
            editor.set_primary_source(primary_source)
        
        has_entity_deletion = any(
            change["action"] == "delete" and not change.get("predicate") 
            for change in changes
        )
        
        editor = import_entity_graph(
            editor, 
            subject, 
            include_referencing_entities=has_entity_deletion
        )
        editor.preexisting_finished()

        graph_uri = None
        if editor.dataset_is_quadstore:
            for quad in editor.g_set.quads((URIRef(subject), None, None, None)):
                graph_context = quad[3]
                graph_uri = get_graph_uri_from_context(graph_context)
                break

        temp_id_to_uri = {}
        for change in changes:
            if change["action"] == "create":
                data = change.get("data")
                if data:
                    subject = create_logic(
                        editor,
                        data,
                        subject,
                        graph_uri,
                        temp_id_to_uri=temp_id_to_uri,
                        parent_entity_type=None,
                    )

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
        if affected_entities and delete_affected:
            # Separa gli orfani dalle entità proxy
            orphans = [entity for entity in affected_entities if not entity.get("is_intermediate")]
            proxies = [entity for entity in affected_entities if entity.get("is_intermediate")]
            
            # Gestione degli orfani secondo la strategia per gli orfani
            should_delete_orphans = (
                orphan_strategy == OrphanHandlingStrategy.DELETE
                or (orphan_strategy == OrphanHandlingStrategy.ASK and delete_affected)
            )
            
            if should_delete_orphans and orphans:
                for orphan in orphans:
                    orphan_uri = orphan["uri"]
                    if orphan_uri in deleted_entities:
                        continue
                    
                    delete_logic(editor, orphan_uri, graph_uri=graph_uri)
                    deleted_entities.add(orphan_uri)
            
            # Gestione delle entità proxy secondo la strategia per i proxy
            should_delete_proxies = (
                proxy_strategy == ProxyHandlingStrategy.DELETE
                or (proxy_strategy == ProxyHandlingStrategy.ASK and delete_affected)
            )
            
            if should_delete_proxies and proxies:
                for proxy in proxies:
                    proxy_uri = proxy["uri"]
                    if proxy_uri in deleted_entities:
                        continue
                    
                    delete_logic(editor, proxy_uri, graph_uri=graph_uri)
                    deleted_entities.add(proxy_uri)
        
        # Fase 2: Processa tutte le altre modifiche
        for change in changes:
            if change["action"] == "delete":
                subject_uri = change["subject"]
                predicate = change.get("predicate")
                object_value = change.get("object")
                
                # Se stiamo eliminando un'intera entità
                if not predicate:
                    if subject_uri in deleted_entities:
                        continue
                    
                    delete_logic(editor, subject_uri, graph_uri=graph_uri, entity_type=change.get("entity_type"))
                    deleted_entities.add(subject_uri)
                # Se stiamo eliminando una tripla specifica
                elif object_value:
                    # Controlla se l'oggetto è un'entità che è già stata eliminata
                    if object_value in deleted_entities:
                        continue
                    
                    delete_logic(editor, subject_uri, predicate, object_value, graph_uri, change.get("entity_type"))

                # La gestione degli orfani e dei proxy è stata spostata all'inizio del ciclo

            elif change["action"] == "update":
                update_logic(
                    editor,
                    change["subject"],
                    change["predicate"],
                    change["object"],
                    change["newObject"],
                    graph_uri,
                    change.get("entity_type"),
                )
            elif change["action"] == "order":
                order_logic(
                    editor,
                    change["subject"],
                    change["predicate"],
                    change["object"],
                    change["newObject"],
                    graph_uri,
                    temp_id_to_uri,
                )

        try:
            editor.save()
        except ValueError as ve:
            # Re-raise ValueError so it can be caught by the outer try-except block
            current_app.logger.error(f"Error during save operation: {str(ve)}")
            raise
        except Exception as save_error:
            current_app.logger.error(f"Error during save operation: {str(save_error)}")
            return jsonify(
                {
                    "status": "error",
                    "error_type": "database",
                    "message": gettext("Failed to save changes to the database: {}").format(str(save_error)),
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

    except ValueError as e:
        # Handle validation errors specifically
        error_message = str(e)
        current_app.logger.warning(f"Validation error: {error_message}")
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
        # Handle other errors
        error_message = (
            f"Error while applying changes: {str(e)}\n{traceback.format_exc()}"
        )
        current_app.logger.error(error_message)
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


def get_graph_uri_from_context(graph_context):
    """Extract the graph URI from a graph context.
    
    Args:
        graph_context: Either a Graph object or a direct URI reference
        
    Returns:
        The graph URI
    """
    if isinstance(graph_context, Graph):
        return graph_context.identifier
    else:
        return graph_context


def determine_datatype(value, datatype_uris):
    for datatype_uri in datatype_uris:
        validation_func = next(
            (d[1] for d in DATATYPE_MAPPING if str(d[0]) == str(datatype_uri)), None
        )
        if validation_func and validation_func(value):
            return URIRef(datatype_uri)
    # If none match, default to XSD.string
    return XSD.string


def create_logic(
    editor: Editor,
    data: Dict[str, dict],
    subject=None,
    graph_uri=None,
    parent_subject=None,
    parent_predicate=None,
    temp_id_to_uri=None,
    parent_entity_type=None,
):
    entity_type = data.get("entity_type")
    properties = data.get("properties", {})
    temp_id = data.get("tempId")

    if subject is None:
        subject = generate_unique_uri(entity_type)

    if temp_id and temp_id_to_uri is not None:
        temp_id_to_uri[temp_id] = str(subject)

    # Create the entity type using validate_new_triple
    if parent_subject is not None:
        type_value, _, error_message = validate_new_triple(
            subject, RDF.type, entity_type, "create", entity_types=entity_type
        )
        if error_message:
            raise ValueError(error_message)

        if type_value is not None:
            editor.create(URIRef(subject), RDF.type, type_value, graph_uri)

    # Create the relationship to the parent using validate_new_triple
    if parent_subject and parent_predicate:
        # When creating a relationship, we need to validate that the parent can have this relationship
        # with an entity of our type. Pass our entity_type as the object_entity_type for validation
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
            editor.create(
                URIRef(parent_subject),
                URIRef(parent_predicate),
                parent_value,
                graph_uri,
            )

    for predicate, values in properties.items():
        if not isinstance(values, list):
            values = [values]
        for value in values:
            if isinstance(value, dict) and "entity_type" in value:
                # For nested entities, create them first
                nested_subject = generate_unique_uri(value["entity_type"])
                create_logic(
                    editor,
                    value,
                    nested_subject,
                    graph_uri,
                    subject,
                    predicate,
                    temp_id_to_uri,
                    parent_entity_type=entity_type,  # Pass the current entity type as parent_entity_type
                )
            else:
                # Use validate_new_triple to validate and get the correctly typed value
                object_value, _, error_message = validate_new_triple(
                    subject, predicate, value, "create", entity_types=entity_type
                )
                if error_message:
                    raise ValueError(error_message)

                if object_value is not None:
                    editor.create(
                        URIRef(subject), URIRef(predicate), object_value, graph_uri
                    )

    return subject


def update_logic(
    editor: Editor,
    subject,
    predicate,
    old_value,
    new_value,
    graph_uri=None,
    entity_type=None,
):
    new_value, old_value, error_message = validate_new_triple(
        subject, predicate, new_value, "update", old_value, entity_types=entity_type
    )
    if error_message:
        raise ValueError(error_message)

    editor.update(URIRef(subject), URIRef(predicate), old_value, new_value, graph_uri)


def rebuild_entity_order(
    editor: Editor,
    ordered_by_uri: URIRef,
    entities: list,
    graph_uri=None
):
    """
    Rebuild the ordering chain for a list of entities.
    
    Args:
        editor: The editor instance
        ordered_by_uri: The property used for ordering
        entities: List of entities to be ordered
        graph_uri: Optional graph URI
    """
    # First, remove all existing ordering relationships
    for entity in entities:
        for s, p, o in list(editor.g_set.triples((entity, ordered_by_uri, None))):
            editor.delete(entity, ordered_by_uri, o, graph_uri)
    
    # Then rebuild the chain with the entities
    for i in range(len(entities) - 1):
        current_entity = entities[i]
        next_entity = entities[i + 1]
        editor.create(current_entity, ordered_by_uri, next_entity, graph_uri)
    
    return editor


def delete_logic(
    editor: Editor,
    subject,
    predicate=None,
    object_value=None,
    graph_uri=None,
    entity_type=None,
):
    # Ensure we have the correct data types for all values
    subject_uri = URIRef(subject)
    predicate_uri = URIRef(predicate) if predicate else None

    # Validate and get correctly typed object value if we have a predicate
    if predicate and object_value:
        # Use validate_new_triple to validate the deletion and get the correctly typed object
        _, object_value, error_message = validate_new_triple(
            subject, predicate, None, "delete", object_value, entity_types=entity_type
        )
        if error_message:
            raise ValueError(error_message)

    editor.delete(subject_uri, predicate_uri, object_value, graph_uri)


def order_logic(
    editor: Editor,
    subject,
    predicate,
    new_order,
    ordered_by,
    graph_uri=None,
    temp_id_to_uri: Optional[Dict] = None,
):
    subject_uri = URIRef(subject)
    predicate_uri = URIRef(predicate)
    ordered_by_uri = URIRef(ordered_by)
    # Ottieni tutte le entità ordinate attuali direttamente dall'editor
    current_entities = [
        o for _, _, o in editor.g_set.triples((subject_uri, predicate_uri, None))
    ]

    # Dizionario per mappare le vecchie entità alle nuove
    old_to_new_mapping = {}

    # Per ogni entità attuale
    for old_entity in current_entities:
        if str(old_entity) in new_order:  # Processa solo le entità preesistenti
            # Memorizza tutte le proprietà dell'entità attuale
            entity_properties = list(editor.g_set.triples((old_entity, None, None)))

            entity_type = next(
                (o for _, p, o in entity_properties if p == RDF.type), None
            )

            if entity_type is None:
                raise ValueError(
                    f"Impossibile determinare il tipo dell'entità per {old_entity}"
                )

            # Crea una nuova entità
            new_entity_uri = generate_unique_uri(entity_type)
            old_to_new_mapping[old_entity] = new_entity_uri

            # Cancella la vecchia entità
            editor.delete(subject_uri, predicate_uri, old_entity, graph_uri)
            editor.delete(old_entity, graph=graph_uri)

            # Ricrea il collegamento tra il soggetto principale e la nuova entità
            editor.create(subject_uri, predicate_uri, new_entity_uri, graph_uri)

            # Ripristina tutte le altre proprietà per la nuova entità
            for _, p, o in entity_properties:
                if p != predicate_uri and p != ordered_by_uri:
                    editor.create(new_entity_uri, p, o, graph_uri) 

    # Prepara la lista delle entità nel nuovo ordine
    ordered_entities = []
    for entity in new_order:
        new_entity_uri = old_to_new_mapping.get(URIRef(entity))
        if not new_entity_uri:
            new_entity_uri = URIRef(temp_id_to_uri.get(entity, entity))
        ordered_entities.append(new_entity_uri)
    
    # Ricostruisci l'ordine
    if ordered_entities:
        rebuild_entity_order(editor, ordered_by_uri, ordered_entities, graph_uri)

    return editor


@api_bp.route("/human-readable-entity", methods=["POST"])
@login_required
def get_human_readable_entity():
    custom_filter = get_custom_filter()

    # Check if required parameters are present
    if "uri" not in request.form or "entity_class" not in request.form:
        return jsonify({"status": "error", "message": "Missing required parameters"}), 400

    uri = request.form["uri"]
    entity_class = request.form["entity_class"]
    shape = determine_shape_for_classes([entity_class])
    filter_instance = custom_filter
    readable = filter_instance.human_readable_entity(uri, (entity_class, shape))
    return readable


@api_bp.route('/format-source', methods=['POST'])
@login_required
def format_source_api():
    """
    API endpoint to format a source URL using the application's filters.
    Accepts POST request with JSON body: {"url": "source_url"}
    Returns JSON: {"formatted_html": "html_string"}
    """
    data = request.get_json()
    source_url = data.get('url')

    if not source_url or not validators.url(source_url):
        return jsonify({"error": gettext("Invalid or missing URL")}), 400

    try:
        custom_filter = get_custom_filter()
        formatted_html = custom_filter.format_source_reference(source_url)
        return jsonify({"formatted_html": formatted_html})
    except Exception as e:
        current_app.logger.error(f"Error formatting source URL '{source_url}': {e}")
        fallback_html = f'<a href="{source_url}" target="_blank">{source_url}</a>'
        return jsonify({"formatted_html": fallback_html})
