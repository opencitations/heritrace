# heritrace/routes/api.py

import traceback
from typing import Dict, Optional

import validators
from config import OrphanHandlingStrategy
from flask import Blueprint, current_app, g, jsonify, request
from flask_babel import gettext
from flask_login import current_user, login_required
from heritrace.editor import Editor
from heritrace.extensions import (get_custom_filter, get_dataset_endpoint,
                                  get_form_fields, get_provenance_endpoint,
                                  get_shacl_graph)
from heritrace.services.resource_lock_manager import LockStatus
from heritrace.utils.shacl_utils import (get_valid_predicates,
                                         validate_new_triple)
from heritrace.utils.sparql_utils import (fetch_data_graph_for_subject,
                                          find_orphaned_entities,
                                          get_available_classes,
                                          get_catalog_data,
                                          get_deleted_entities_with_filtering,
                                          import_entity_graph)
from rdflib import RDF, XSD, Literal, URIRef
from resources.datatypes import DATATYPE_MAPPING

api_bp = Blueprint('api', __name__)

@api_bp.route('/catalogue')
@login_required
def catalogue_api():
    selected_class = request.args.get('class')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    sort_property = request.args.get('sort_property')
    sort_direction = request.args.get('sort_direction', 'ASC')
    
    allowed_per_page = [50, 100, 200, 500]
    if per_page not in allowed_per_page:
        per_page = 100

    if not sort_property or sort_property.lower() == 'null':
        sort_property = None

    catalog_data = get_catalog_data(
        selected_class,
        page,
        per_page,
        sort_property,
        sort_direction
    )
    
    catalog_data['available_classes'] = get_available_classes()
    
    return jsonify(catalog_data)

@api_bp.route('/time-vault')
@login_required
def get_deleted_entities_api():
    """
    API endpoint to retrieve deleted entities with pagination and sorting.
    Only processes and returns entities whose classes are marked as visible.
    """
    selected_class = request.args.get('class')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    sort_property = request.args.get('sort_property', 'deletionTime')
    sort_direction = request.args.get('sort_direction', 'DESC')

    allowed_per_page = [50, 100, 200, 500]
    if per_page not in allowed_per_page:
        per_page = 100

    deleted_entities, available_classes, selected_class, sortable_properties = get_deleted_entities_with_filtering(
        page, per_page, sort_property, sort_direction, selected_class
    )

    return jsonify({
        'entities': deleted_entities,
        'total_pages': (len(deleted_entities) + per_page - 1) // per_page if deleted_entities else 0,
        'current_page': page,
        'per_page': per_page,
        'total_count': len(deleted_entities),
        'sort_property': sort_property,
        'sort_direction': sort_direction,
        'selected_class': selected_class,
        'available_classes': available_classes,
        'sortable_properties': sortable_properties
    })

@api_bp.route('/check-lock', methods=['POST'])
@login_required
def check_lock():
    try:
        data = request.get_json()
        resource_uri = data.get('resource_uri')
        if not resource_uri:
            return jsonify({
                'status': 'error',
                'title': gettext('Error'),
                'message': gettext('No resource URI provided')
            }), 400
            
        status, lock_info = g.resource_lock_manager.check_lock_status(resource_uri)
        if status == LockStatus.ERROR:
            return jsonify({
                'status': 'error',
                'title': gettext('Error'),
                'message': gettext('Error checking lock status')
            }), 500
            
        if status == LockStatus.LOCKED:
            return jsonify({
                'status': 'locked',
                'title': gettext('Resource Locked'),
                'message': gettext('This resource is currently being edited by %(user)s [orcid:%(orcid)s]. Please try again later', user=lock_info.user_name, orcid=lock_info.user_id)
            }), 423
            
        return jsonify({'status': 'unlocked'})
        
    except Exception as e:
        current_app.logger.error(f"Error in check_lock: {str(e)}")
        return jsonify({
            'status': 'error',
            'title': gettext('Error'),
            'message': gettext('An unexpected error occurred')
        }), 500

@api_bp.route('/acquire-lock', methods=['POST'])
@login_required
def acquire_lock():
    """Try to acquire a lock on a resource."""
    try:
        data = request.get_json()
        resource_uri = data.get('resource_uri')
        
        if not resource_uri:
            return jsonify({
                'status': 'error',
                'message': gettext('No resource URI provided')
            }), 400
            
        success = g.resource_lock_manager.acquire_lock(resource_uri)
        
        if success:
            return jsonify({'status': 'success'})
            
        return jsonify({
            'status': 'error',
            'message': gettext('Resource is locked by another user')
        }), 423
        
    except Exception as e:
        current_app.logger.error(f"Error in acquire_lock: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': gettext('An unexpected error occurred')
        }), 500

@api_bp.route('/release-lock', methods=['POST'])
@login_required
def release_lock():
    """Release a lock on a resource."""
    try:
        data = request.get_json()
        resource_uri = data.get('resource_uri')
        
        if not resource_uri:
            return jsonify({
                'status': 'error',
                'message': gettext('No resource URI provided')
            }), 400
            
        success = g.resource_lock_manager.release_lock(resource_uri)
        
        if success:
            return jsonify({'status': 'success'})
            
        return jsonify({
            'status': 'error',
            'message': gettext('Unable to release lock')
        }), 400
        
    except Exception as e:
        current_app.logger.error(f"Error in release_lock: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': gettext('An unexpected error occurred')
        }), 500

@api_bp.route('/renew-lock', methods=['POST'])
@login_required
def renew_lock():
    """Renew an existing lock on a resource."""
    try:
        data = request.get_json()
        resource_uri = data.get('resource_uri')
        
        if not resource_uri:
            return jsonify({
                'status': 'error',
                'message': gettext('No resource URI provided')
            }), 400
            
        success = g.resource_lock_manager.acquire_lock(resource_uri)
        
        if success:
            return jsonify({'status': 'success'})
            
        return jsonify({
            'status': 'error',
            'message': gettext('Unable to renew lock')
        }), 423
        
    except Exception as e:
        current_app.logger.error(f"Error in renew_lock: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': gettext('An unexpected error occurred')
        }), 500

@api_bp.route('/validate-literal', methods=['POST'])
@login_required
def validate_literal():
    """Validate a literal value and suggest appropriate datatypes."""
    value = request.json.get('value')
    if not value:
        return jsonify({"error": gettext("Value is required.")}), 400

    matching_datatypes = []
    for datatype, validation_func, _ in DATATYPE_MAPPING:
        if validation_func(value):
            matching_datatypes.append(str(datatype))

    if not matching_datatypes:
        return jsonify({"error": gettext("No matching datatypes found.")}), 400
    
    return jsonify({"valid_datatypes": matching_datatypes}), 200

@api_bp.route('/check_orphans', methods=['POST'])
@login_required
def check_orphans():
    strategy = current_app.config.get('ORPHAN_HANDLING_STRATEGY', OrphanHandlingStrategy.KEEP)
    changes = request.json
    potential_orphans = []
    custom_filter = get_custom_filter()
    current_app.logger.info(strategy, changes, custom_filter)

    if strategy in (OrphanHandlingStrategy.DELETE, OrphanHandlingStrategy.ASK):
        for change in changes:
            if change['action'] == 'delete':
                orphans = find_orphaned_entities(
                    change['subject'],
                    change.get('predicate'),
                    change.get('object')
                )
                potential_orphans.extend(orphans)

    # If we're keeping orphans or none were found, return empty list
    if strategy == OrphanHandlingStrategy.KEEP or not potential_orphans:
        return jsonify({'status': 'success', 'orphaned_entities': []})

    # Prepare orphan information for frontend
    orphan_info = [{
        'uri': entity['uri'],
        'label': custom_filter.human_readable_entity(
            entity['uri'], 
            [entity['type']]
        ),
        'type': custom_filter.human_readable_predicate(
            entity['type'], 
            [entity['type']]
        )
    } for entity in potential_orphans]

    # For DELETE strategy, return orphans with should_delete flag
    if strategy == OrphanHandlingStrategy.DELETE:
        return jsonify({
            'status': 'success',
            'orphaned_entities': orphan_info,
            'should_delete': True
        })

    # For ASK strategy, return orphans with confirmation required
    return jsonify({
        'status': 'confirmation_required',
        'orphaned_entities': orphan_info,
        'message': gettext('The following entities will become orphaned. Do you want to delete them?')
    })

@api_bp.route('/apply_changes', methods=['POST'])
@login_required
def apply_changes():
    try:
        changes = request.json
        subject = changes[0]["subject"]
        orphaned_entities = changes[0].get("orphaned_entities", [])
        delete_orphans = changes[0].get("deleteOrphans", False)
        
        editor = Editor(
            get_dataset_endpoint(), 
            get_provenance_endpoint(), 
            current_app.config['COUNTER_HANDLER'], 
            URIRef(f'https://orcid.org/{current_user.orcid}'), 
            current_app.config['PRIMARY_SOURCE'], 
            current_app.config['DATASET_GENERATION_TIME']
        )
        editor = import_entity_graph(editor, subject)
        editor.preexisting_finished()
        
        graph_uri = None
        if editor.dataset_is_quadstore:
            for quad in editor.g_set.quads((URIRef(subject), None, None)):
                graph_uri = quad[3]
                break
        
        # Gestisci prima le creazioni
        temp_id_to_uri = {}
        for change in changes:
            if change["action"] == "create":
                data = change.get("data")
                if data:
                    subject = create_logic(editor, data, subject, graph_uri, temp_id_to_uri=temp_id_to_uri)

        # Poi gestisci le altre modifiche
        strategy = current_app.config.get('ORPHAN_HANDLING_STRATEGY', OrphanHandlingStrategy.KEEP)
        
        for change in changes:
            if change["action"] == "delete":
                delete_logic(editor, change["subject"], change.get('predicate'), change.get('object'), graph_uri)
                
                if strategy == OrphanHandlingStrategy.DELETE or (
                    strategy == OrphanHandlingStrategy.ASK and delete_orphans
                ):
                    for orphan in orphaned_entities:
                        editor.delete(orphan['uri'])
                        
                
            elif change["action"] == "update":
                update_logic(
                    editor,
                    change["subject"],
                    change["predicate"],
                    change["object"],
                    change["newObject"],
                    graph_uri
                )
            elif change["action"] == "order":
                order_logic(
                    editor,
                    change["subject"],
                    change["predicate"],
                    change["object"],
                    change["newObject"],
                    graph_uri,
                    temp_id_to_uri
                )
                
        editor.save()
        return jsonify({"status": "success", "message": gettext("Changes applied successfully")}), 200
        
    except Exception as e:
        error_message = f"Error while applying changes: {str(e)}\n{traceback.format_exc()}"
        current_app.logger.error(error_message)
        return jsonify({"status": "error", "message": gettext("An error occurred while applying changes")}), 500

def generate_unique_uri(entity_type: URIRef|str =None):
    entity_type = str(entity_type)
    uri = current_app.config['URI_GENERATOR'].generate_uri(entity_type)
    if hasattr(current_app.config['URI_GENERATOR'], 'counter_handler'):
        current_app.config['URI_GENERATOR'].counter_handler.increment_counter(entity_type)
    return URIRef(uri)

def determine_datatype(value, datatype_uris):
    for datatype_uri in datatype_uris:
        validation_func = next(
            (d[1] for d in DATATYPE_MAPPING if str(d[0]) == str(datatype_uri)),
            None
        )
        if validation_func and validation_func(value):
            return URIRef(datatype_uri)
    # If none match, default to XSD.string
    return XSD.string

def create_logic(editor: Editor, data: Dict[str, dict], subject=None, graph_uri=None, parent_subject=None, parent_predicate=None, temp_id_to_uri=None):
    entity_type = data.get('entity_type')
    properties = data.get('properties', {})
    temp_id = data.get('tempId')

    if subject is None:
        subject = generate_unique_uri(entity_type)

    if temp_id and temp_id_to_uri is not None:
        temp_id_to_uri[temp_id] = str(subject)

    if parent_subject is not None:
        editor.create(URIRef(subject), RDF.type, URIRef(entity_type), graph_uri)

    if parent_subject and parent_predicate:
        editor.create(URIRef(parent_subject), URIRef(parent_predicate), URIRef(subject), graph_uri)

    form_fields = get_form_fields()
    
    for predicate, values in properties.items():
        if not isinstance(values, list):
            values = [values]
        for value in values:
            if isinstance(value, dict) and 'entity_type' in value:
                nested_subject = generate_unique_uri(value['entity_type'])
                create_logic(editor, value, nested_subject, graph_uri, subject, predicate, temp_id_to_uri)
            else:
                if form_fields and entity_type in form_fields:
                    # Get the field definitions for this predicate
                    field_definitions = form_fields[entity_type].get(predicate, [])
                    datatype_uris = []
                    if field_definitions:
                        datatype_uris = field_definitions[0].get('datatypes', [])
                    # Determine appropriate datatype
                    datatype = determine_datatype(value, datatype_uris)
                    object_value = URIRef(value) if validators.url(value) else Literal(value, datatype=datatype)
                else:
                    # Default behavior when no SHACL validation is present
                    object_value = URIRef(value) if validators.url(value) else Literal(value)
                    
                editor.create(URIRef(subject), URIRef(predicate), object_value, graph_uri)

    return subject

def update_logic(editor: Editor, subject, predicate, old_value, new_value, graph_uri=None):
    new_value, old_value, report_text = validate_new_triple(subject, predicate, new_value, old_value)
    if len(get_shacl_graph()):
        if new_value is None:
            raise ValueError(report_text)
    else:
        new_value = Literal(new_value, datatype=old_value.datatype) if old_value.datatype and isinstance(old_value, Literal) else Literal(new_value, datatype=XSD.string) if isinstance(old_value, Literal) else URIRef(new_value)
    editor.update(URIRef(subject), URIRef(predicate), old_value, new_value, graph_uri)

def delete_logic(editor: Editor, subject, predicate, object_value, graph_uri=None):
    if len(get_shacl_graph()):
        data_graph = fetch_data_graph_for_subject(subject)
        _, can_be_deleted, _, _, _, _, _ = get_valid_predicates(list(data_graph.triples((URIRef(subject), None, None))))
        if predicate and predicate not in can_be_deleted:
            raise ValueError(gettext('This property cannot be deleted'))
    editor.delete(subject, predicate, object_value, graph_uri)

def order_logic(editor: Editor, subject, predicate, new_order, ordered_by, graph_uri=None, temp_id_to_uri: Optional[Dict] = None):
    subject_uri = URIRef(subject)
    predicate_uri = URIRef(predicate)
    ordered_by_uri = URIRef(ordered_by)

    # Ottieni tutte le entità ordinate attuali direttamente dall'editor
    current_entities = [o for _, _, o in editor.g_set.triples((subject_uri, predicate_uri, None))]

    # Dizionario per mappare le vecchie entità alle nuove
    old_to_new_mapping = {}

    # Per ogni entità attuale
    for old_entity in current_entities:
        if str(old_entity) in new_order:  # Processa solo le entità preesistenti
            # Memorizza tutte le proprietà dell'entità attuale
            entity_properties = list(editor.g_set.triples((old_entity, None, None)))
            
            entity_type = next((o for _, p, o in entity_properties if p == RDF.type), None)

            if entity_type is None:
                raise ValueError(f"Impossibile determinare il tipo dell'entità per {old_entity}")

            # Crea una nuova entità
            new_entity_uri = generate_unique_uri(entity_type)
            old_to_new_mapping[old_entity] = new_entity_uri
            
            # Cancella la vecchia entità
            editor.delete(subject_uri, predicate_uri, old_entity, graph_uri)
            editor.delete(old_entity)
            
            # Ricrea il collegamento tra il soggetto principale e la nuova entità
            editor.create(subject_uri, predicate_uri, new_entity_uri, graph_uri)
            
            # Ripristina tutte le altre proprietà per la nuova entità
            for _, p, o in entity_properties:
                if p != predicate_uri and p != ordered_by_uri:
                    editor.create(new_entity_uri, p, o, graph_uri)

    # Aggiungi la proprietà legata all'ordine alle entità giuste
    for idx, entity in enumerate(new_order):
        new_entity_uri = old_to_new_mapping.get(URIRef(entity))
        if not new_entity_uri:
            new_entity_uri = URIRef(temp_id_to_uri.get(entity, entity))
        if idx < len(new_order) - 1:
            next_entity = new_order[idx + 1]
            next_entity = URIRef(temp_id_to_uri.get(next_entity, next_entity))
            next_entity_uri = old_to_new_mapping.get(URIRef(next_entity), URIRef(next_entity))
            editor.create(new_entity_uri, ordered_by_uri, next_entity_uri, graph_uri)

    return editor

@api_bp.route('/human-readable-entity', methods=['POST'])
@login_required
def get_human_readable_entity():
    custom_filter = get_custom_filter()

    uri = request.form['uri']
    entity_class = request.form['entity_class']
    filter_instance = custom_filter
    readable = filter_instance.human_readable_entity(uri, [entity_class])
    return readable