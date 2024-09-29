import atexit
import json
import os
import signal
import sys
import time
import traceback
import urllib
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import click
import docker
import requests
import validators
import yaml
from config import Config
from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_babel import Babel, gettext, refresh
from rdflib import RDF, XSD, ConjunctiveGraph, Graph, Literal, URIRef
from rdflib.namespace import XSD
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.algebra import translateQuery, translateUpdate
from rdflib.plugins.sparql.parser import parseQuery, parseUpdate
from resources.datatypes import DATATYPE_MAPPING
from SPARQLWrapper import JSON, XML, SPARQLWrapper
from time_agnostic_library.agnostic_entity import (
    AgnosticEntity, _filter_timestamps_by_interval)
from time_agnostic_library.prov_entity import ProvEntity
from time_agnostic_library.sparql import Sparql
from time_agnostic_library.support import convert_to_datetime

from heritrace.editor import Editor
from heritrace.filters import *
from heritrace.forms import *
from heritrace.uri_generator.uri_generator import *

app = Flask(__name__)

app.config.from_object(Config)

babel = Babel()


with open("resources/context.json", "r") as config_file:
    context = json.load(config_file)["@context"]

display_rules_path = app.config["DISPLAY_RULES_PATH"]
display_rules = None
if display_rules_path:
    with open(display_rules_path, 'r') as f:
        display_rules = yaml.safe_load(f)

change_tracking_config = app.config["CHANGE_TRACKING_CONFIG"]
if change_tracking_config:
    with open(change_tracking_config, 'r', encoding='utf8') as f:
        change_tracking_config = json.load(f)

shacl_path = app.config["SHACL_PATH"]
shacl = None
if shacl_path:
    if os.path.exists(shacl_path):
        shacl = Graph()
        shacl.parse(source=app.config["SHACL_PATH"], format="turtle")

custom_filter = Filter(context, display_rules)

app.jinja_env.filters['human_readable_predicate'] = custom_filter.human_readable_predicate
app.jinja_env.filters['human_readable_primary_source'] = custom_filter.human_readable_primary_source
app.jinja_env.filters['format_datetime'] = custom_filter.human_readable_datetime
app.jinja_env.filters['split_ns'] = custom_filter.split_ns

CACHE_FILE = app.config['CACHE_FILE']
CACHE_VALIDITY_DAYS = app.config['CACHE_VALIDITY_DAYS']

VIRTUOSO_EXCLUDED_GRAPHS = [
    "http://localhost:8890/DAV/",
    "http://www.openlinksw.com/schemas/virtrdf#",
    "http://www.w3.org/2002/07/owl#",
    "http://www.w3.org/ns/ldp#",
    "urn:activitystreams-owl:map",
    "urn:core:services:sparql"
]

containers = []
initialization_done = False

def stop_containers():
    client = docker.from_env()
    for container_name in containers:
        try:
            container = client.containers.get(container_name)
            if container.status == 'running':
                print(f"Stopping container: {container_name}")
                container.stop()
            else:
                print(f"Container {container_name} is not running")
        except docker.errors.NotFound:
            print(f"Container not found: {container_name}")
        except Exception as e:
            print(f"Error stopping container {container_name}: {str(e)}")

# def signal_handler(sig, frame):
#     print("Shutting down...")
#     stop_containers()
#     sys.exit(0)

# signal.signal(signal.SIGINT, signal_handler)
# signal.signal(signal.SIGTERM, signal_handler)

# atexit.register(stop_containers)

def setup_database(db_type, db_triplestore, db_url, docker_image, docker_port, docker_isql_port, volume_path):
    global containers
    if db_type == 'docker':
        client = docker.from_env()
        container_name = f"{db_triplestore}_container_{docker_port}"
        
        # Ensure the volume directory exists
        os.makedirs(volume_path, exist_ok=True)
        
        try:
            # Check for an existing container with the same name
            container = client.containers.get(container_name)
            if container.status != "running":
                print(f"Starting existing container: {container_name}")
                container.start()
                # Wait for the container to be ready only if it was just started
                time.sleep(5)
            else:
                print(f"Container {container_name} is already running")
                
        except docker.errors.NotFound:
            print(f"Creating a new container: {container_name}")
            # If the container doesn't exist, create a new one
            if db_triplestore == 'virtuoso':
                ports = {
                    f'{docker_port}/tcp': docker_port,
                    f'{docker_isql_port}/tcp': docker_isql_port,
                }
                environment = {
                    'DBA_PASSWORD': 'dba',  # Set a secure password in production
                    'SPARQL_UPDATE': 'true',
                }
                volumes = {
                    volume_path: {'bind': '/database', 'mode': 'rw'}
                }
            elif db_triplestore == 'blazegraph':
                ports = {
                    f'{docker_port}/tcp': docker_port,
                }
                environment = {}  # Blazegraph doesn't need special environment variables
                volumes = {
                    volume_path: {'bind': '/data', 'mode': 'rw'}
                }
            else:
                raise ValueError(f"Unsupported triplestore: {db_triplestore}")

            container = client.containers.run(
                docker_image,
                name=container_name,
                detach=True,
                ports=ports,
                environment=environment,
                volumes=volumes
            )
            # Wait for the new container to be ready
            time.sleep(5)
        
        # Add the container name to the global list only if it's not already there
        if container_name not in containers:
            containers.append(container_name)
        
        if db_triplestore == 'virtuoso':
            return f"http://localhost:{docker_port}/sparql"
        elif db_triplestore == 'blazegraph':
            return f"http://localhost:{docker_port}/bigdata/sparql"
    else:
        return db_url

def need_initialization():
    uri_generator: URIGenerator = app.config['URI_GENERATOR']

    if not hasattr(uri_generator, "counter_handler"):
        return False

    if not os.path.exists(CACHE_FILE):
        return True
    
    with open(CACHE_FILE, 'r', encoding='utf8') as f:
        cache = json.load(f)
    
    last_init = datetime.fromisoformat(cache['last_initialization'])
    return datetime.now() - last_init > timedelta(days=CACHE_VALIDITY_DAYS)

def update_cache():
    cache = {
        'last_initialization': datetime.now().isoformat(),
        'version': '1.0'
    }
    with open(CACHE_FILE, 'w', encoding='utf8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=4)

def is_virtuoso():
    return Config.DATASET_DB_TRIPLESTORE.lower() == 'virtuoso'

def is_dataset_quadstore():
    return Config.DATASET_IS_QUADSTORE

def is_provenance_quadstore():
    return Config.PROVENANCE_IS_QUADSTORE

def initialize_counter_handler():
    if not need_initialization():
        return
    
    uri_generator: URIGenerator = app.config['URI_GENERATOR']
    counter_handler = uri_generator.counter_handler

    # Query SPARQL per ottenere tutti i tipi di entità e il loro conteggio
    if is_virtuoso():
        query = f"""
            SELECT ?type (COUNT(DISTINCT ?s) as ?count)
            WHERE {{
                GRAPH ?g {{
                    ?s a ?type .
                }}
                FILTER(?g NOT IN (<{'>, <'.join(VIRTUOSO_EXCLUDED_GRAPHS)}>))
            }}
            GROUP BY ?type
        """
    else:
        query = """
            SELECT ?type (COUNT(DISTINCT ?s) as ?count)
            WHERE {
                ?s a ?type .
            }
            GROUP BY ?type
        """
    
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    # Dizionario per tenere traccia del conteggio massimo per ogni tipo di entità
    max_counts = defaultdict(int)

    for result in results["results"]["bindings"]:
        entity_type = result["type"]["value"]
        count = int(result["count"]["value"])   
        max_counts[entity_type] = max(max_counts[entity_type], count)

    # Aggiorna il counter_handler per ogni tipo di entità
    for entity_type, count in max_counts.items():
        current_count = counter_handler.read_counter(entity_type)
        if current_count is not None and current_count <= count:
            counter_handler.set_counter(count + 1, entity_type)

def initialize_app():
    global initialization_done
    if not initialization_done:
        # Setup database connections
        global dataset_endpoint, provenance_endpoint, sparql, provenance_sparql
        dataset_endpoint = setup_database(
            Config.DATASET_DB_TYPE,
            Config.DATASET_DB_TRIPLESTORE,
            Config.DATASET_DB_URL,
            Config.DATASET_DB_DOCKER_IMAGE,
            Config.DATASET_DB_DOCKER_PORT,
            Config.DATASET_DB_DOCKER_ISQL_PORT,
            Config.DATASET_DB_VOLUME_PATH
        )

        provenance_endpoint = setup_database(
            Config.PROVENANCE_DB_TYPE,
            Config.PROVENANCE_DB_TRIPLESTORE,
            Config.PROVENANCE_DB_URL,
            Config.PROVENANCE_DB_DOCKER_IMAGE,
            Config.PROVENANCE_DB_DOCKER_PORT,
            Config.PROVENANCE_DB_DOCKER_ISQL_PORT,
            Config.PROVENANCE_DB_VOLUME_PATH
        )

        sparql = SPARQLWrapper(dataset_endpoint)
        provenance_sparql = SPARQLWrapper(provenance_endpoint)

        initialize_counter_handler()
        initialization_done = True

initialize_app()

@app.route('/')
def index():
    return render_template('index.jinja')

@app.route('/catalogue')
def catalogue():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 100))
    offset = (page - 1) * per_page

    if is_virtuoso():
        query = f"""
        SELECT DISTINCT ?subject WHERE {{
            GRAPH ?g {{
                ?subject ?predicate ?object.
            }}
            FILTER(?g NOT IN (<{'>, <'.join(VIRTUOSO_EXCLUDED_GRAPHS)}>))
        }} LIMIT {per_page} OFFSET {offset}
        """
    else:
        query = f"""
        SELECT DISTINCT ?subject WHERE {{
            ?subject ?predicate ?object.
        }} LIMIT {per_page} OFFSET {offset}
        """

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    subjects = sparql.query().convert().get("results", {}).get("bindings", [])
    return render_template('entities.jinja', subjects=subjects, page=page)

@app.route('/create-entity', methods=['GET', 'POST'])
def create_entity():
    form_fields = get_form_fields_from_shacl()

    entity_types = list(form_fields.keys())

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

    if request.method == 'POST':
        structured_data = json.loads(request.form.get('structured_data', '{}'))

        validation_errors = validate_entity_data(structured_data, form_fields)

        if validation_errors:
            return jsonify({'status': 'error', 'errors': validation_errors}), 400

        editor = Editor(
            dataset_endpoint,
            provenance_endpoint,
            app.config['COUNTER_HANDLER'],
            app.config['RESPONSIBLE_AGENT'],
            app.config['PRIMARY_SOURCE'],
            app.config['DATASET_GENERATION_TIME']
        )
        
        if shacl:
            entity_type = structured_data.get('entity_type')
            properties = structured_data.get('properties', {})
            
            entity_uri = generate_unique_uri(entity_type)
            editor.import_entity(entity_uri)
            editor.preexisting_finished()

            default_graph_uri = (
                URIRef(f"{entity_uri}/graph") if editor.dataset_is_quadstore else None
            )

            editor.create(
                entity_uri,
                URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'),
                URIRef(entity_type),
                default_graph_uri
            )

            for predicate, values in properties.items():
                if not isinstance(values, list):
                    values = [values]
                
                # Check if this predicate needs to be ordered
                ordered_by = None
                for field_details in form_fields[entity_type][predicate]:
                    if field_details['uri'] == predicate:
                        ordered_by = field_details.get('orderedBy')
                        break

                if ordered_by:
                    # Gestisci le proprietà ordinate per shape
                    values_by_shape = {}
                    for value in values:
                        # Ottieni la shape dell'entità
                        shape = value.get('shape')
                        if not shape:
                            shape = 'default_shape'
                        if shape not in values_by_shape:
                            values_by_shape[shape] = []
                        values_by_shape[shape].append(value)

                    # Ora processa ogni gruppo di valori per shape separatamente
                    for shape, shape_values in values_by_shape.items():
                        previous_entity = None
                        for value in shape_values:
                            nested_uri = generate_unique_uri(value['entity_type'])
                            editor.create(entity_uri, URIRef(predicate), nested_uri, default_graph_uri)
                            create_nested_entity(editor, nested_uri, value, default_graph_uri)

                            if previous_entity:
                                editor.create(previous_entity, URIRef(ordered_by), nested_uri, default_graph_uri)
                            previous_entity = nested_uri
                else:
                    # Gestisci le proprietà non ordinate
                    for value in values:
                        if isinstance(value, dict) and 'entity_type' in value:
                            nested_uri = generate_unique_uri(value['entity_type'])
                            editor.create(entity_uri, URIRef(predicate), nested_uri, default_graph_uri)
                            create_nested_entity(editor, nested_uri, value, default_graph_uri)
                        else:
                            object_value = URIRef(value) if validators.url(value) else Literal(value)
                            editor.create(entity_uri, URIRef(predicate), object_value, default_graph_uri)
        else:
            properties = structured_data.get('properties', {})
            
            entity_uri = generate_unique_uri()
            editor.import_entity(entity_uri)
            editor.preexisting_finished()

            default_graph_uri = URIRef(f"{entity_uri}/graph") if editor.dataset_is_quadstore else None

            for predicate, values in properties.items():
                if not isinstance(values, list):
                    values = [values]
                for value_dict in values:
                    if value_dict['type'] == 'uri':
                        editor.create(entity_uri, URIRef(predicate), URIRef(value_dict['value']), default_graph_uri)
                    elif value_dict['type'] == 'literal':
                        datatype = URIRef(value_dict['datatype']) if 'datatype' in value_dict else XSD.string
                        editor.create(entity_uri, URIRef(predicate), Literal(value_dict['value'], datatype=datatype), default_graph_uri)

        try:
            editor.save()
            response = jsonify({
                'status': 'success',
                'redirect_url': url_for('about', subject=str(entity_uri))
            })
            flash(gettext('Entity created successfully'), 'success')
            return response, 200
        except Exception as e:
            error_message = gettext('An error occurred while creating the entity: %(error)s', error=str(e))
            return jsonify({'status': 'error', 'errors': [error_message]}), 500

    return render_template(
        'create_entity.jinja',
        shacl=bool(shacl),
        entity_types=entity_types,
        form_fields=form_fields,
        datatype_options=datatype_options
    )

def validate_entity_data(structured_data, form_fields):
    errors = []
    entity_type = structured_data.get('entity_type')
    if not entity_type:
        errors.append(gettext('Entity type is required.'))
    elif entity_type not in form_fields:
        errors.append(gettext('Invalid entity type selected.'))

    if errors:
        return errors

    entity_fields = form_fields.get(entity_type, {})
    properties = structured_data.get('properties', {})

    for prop_uri, prop_values in properties.items():
        if URIRef(prop_uri) == RDF.type:
            continue
        field_definitions = entity_fields.get(prop_uri)
        if not field_definitions:
            errors.append(
                gettext(
                    'Unknown property %(prop_uri)s for entity type %(entity_type)s.',
                    prop_uri=prop_uri,
                    entity_type=entity_type
                )
            )
            continue

        for field_def in field_definitions:
            min_count = field_def.get('min', 0)
            max_count = field_def.get('max', None)
            prop_value_list = prop_values if isinstance(prop_values, list) else [prop_values]
            value_count = len(prop_value_list)
            if value_count < min_count:
                errors.append(
                    gettext(
                        'Property %(prop_uri)s requires at least %(min_count)d value(s).',
                        prop_uri=custom_filter.human_readable_predicate(prop_uri, [entity_type]),
                        min_count=min_count
                    )
                )
            if max_count is not None and value_count > max_count:
                errors.append(
                    gettext(
                        'Property %(prop_uri)s allows at most %(max_count)d value(s).',
                        prop_uri=custom_filter.human_readable_predicate(prop_uri, [entity_type]),
                        max_count=max_count
                    )
                )

            for value in prop_value_list:
                if isinstance(value, dict) and 'entity_type' in value:
                    nested_errors = validate_entity_data(value, form_fields)
                    errors.extend(nested_errors)
                else:
                    datatypes = field_def.get('datatypes', [])
                    if datatypes:
                        is_valid_datatype = False
                        for dtype in datatypes:
                            validation_func = next(
                                (d[1] for d in DATATYPE_MAPPING if d[0] == URIRef(dtype)),
                                None
                            )
                            if validation_func and validation_func(value):
                                is_valid_datatype = True
                                break
                        if not is_valid_datatype:
                            expected_types = ', '.join(
                                [custom_filter.human_readable_predicate(dtype, form_fields.keys()) for dtype in datatypes]
                            )
                            errors.append(
                                gettext(
                                    'Value "%(value)s" for property %(prop_uri)s is not of expected type %(expected_types)s.',
                                    value=value,
                                    prop_uri=custom_filter.human_readable_predicate(prop_uri, form_fields.keys()),
                                    expected_types=expected_types
                                )
                            )
                    optional_values = field_def.get('optionalValues', [])
                    if optional_values and value not in optional_values:
                        acceptable_values = ', '.join(
                            [custom_filter.human_readable_predicate(val, form_fields.keys()) for val in optional_values]
                        )
                        errors.append(
                            gettext(
                                'Value "%(value)s" is not permitted for property %(prop_uri)s. Acceptable values are: %(acceptable_values)s.',
                                value=value,
                                prop_uri=custom_filter.human_readable_predicate(prop_uri, form_fields.keys()),
                                acceptable_values=acceptable_values
                            )
                        )

    return errors

def create_nested_entity(editor: Editor, entity_uri, entity_data, graph_uri=None):
    # Add rdf:type
    editor.create(entity_uri, URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), URIRef(entity_data['entity_type']), graph_uri)

    # Add other properties
    for predicate, values in entity_data.get('properties', {}).items():
        if not isinstance(values, list):
            values = [values]
        for value in values:
            if isinstance(value, dict) and 'entity_type' in value:
                if 'intermediateRelation' in value:
                    intermediate_uri = generate_unique_uri(value['intermediateRelation']['class'])
                    target_uri = generate_unique_uri(value['entity_type'])
                    editor.create(entity_uri, URIRef(predicate), intermediate_uri, graph_uri)
                    editor.create(intermediate_uri, URIRef(value['intermediateRelation']['property']), target_uri, graph_uri)
                    create_nested_entity(editor, target_uri, value, graph_uri)
                else:
                    # Handle nested entities
                    nested_uri = generate_unique_uri(value['entity_type'])
                    editor.create(entity_uri, URIRef(predicate), nested_uri, graph_uri)
                    create_nested_entity(editor, nested_uri, value, graph_uri)
            else:
                # Handle simple properties
                object_value = URIRef(value) if validators.url(value) else Literal(value)
                editor.create(entity_uri, URIRef(predicate), object_value, graph_uri)

def generate_unique_uri(entity_type=None):
    uri = Config.URI_GENERATOR.generate_uri(entity_type)
    if hasattr(Config.URI_GENERATOR, 'counter_handler'):
        Config.URI_GENERATOR.counter_handler.increment_counter(entity_type)
    return URIRef(uri)

@app.route('/about/<path:subject>')
def about(subject):
    decoded_subject = urllib.parse.unquote(subject)
    agnostic_entity = AgnosticEntity(res=decoded_subject, config=change_tracking_config)
    history, _ = agnostic_entity.get_history(include_prov_metadata=True)
    g = Graph()

    if is_virtuoso():
        query = f"""
        SELECT ?predicate ?object WHERE {{
            GRAPH ?g {{
                <{decoded_subject}> ?predicate ?object.
            }}
            FILTER(?g NOT IN (<{'>, <'.join(VIRTUOSO_EXCLUDED_GRAPHS)}>))
        }}
        """
    else:
        query = f"""
        SELECT ?predicate ?object WHERE {{
            <{decoded_subject}> ?predicate ?object.
        }}
        """

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    triples = sparql.query().convert().get("results", {}).get("bindings", [])
    for triple in triples:
        value = Literal(triple['object']['value'], datatype=URIRef(triple['object']['datatype'])) if triple['object']['type'] == 'literal' and 'datatype' in triple['object'] else Literal(triple['object']['value'], datatype=XSD.string) if triple['object']['type'] == 'literal' else URIRef(triple['object']['value'])
        g.add((URIRef(decoded_subject), URIRef(triple['predicate']['value']), value))
    triples = list(g.triples((None, None, None)))

    can_be_added, can_be_deleted, datatypes, mandatory_values, optional_values, subject_classes, valid_predicates = get_valid_predicates(triples)

    grouped_triples, relevant_properties = get_grouped_triples(subject, triples, subject_classes, valid_predicates)

    can_be_added = [uri for uri in can_be_added if uri in relevant_properties]
    can_be_deleted = [uri for uri in can_be_deleted if uri in relevant_properties]

    update_form = UpdateTripleForm()
    create_form = CreateTripleFormWithSelect() if can_be_added else CreateTripleFormWithInput()
    if can_be_added:
        create_form.predicate.choices = [(p, custom_filter.human_readable_predicate(p, subject_classes)) for p in can_be_added]
    return render_template('about.jinja', subject=decoded_subject, history=history, can_be_added=can_be_added, can_be_deleted=can_be_deleted, datatypes=datatypes, update_form=update_form, create_form=create_form, mandatory_values=mandatory_values, optional_values=optional_values, shacl=True if shacl else False, grouped_triples=grouped_triples, subject_classes=[str(s_class) for s_class in subject_classes], display_rules=display_rules)

# Funzione per la validazione dinamica dei valori con suggerimento di datatypes
@app.route('/validate-literal', methods=['POST'])
def validate_literal():
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

@app.route('/add_triple', methods=['POST'])
def add_triple():
    subject = request.form.get('subject')
    predicate = request.form.get('predicate')
    object_value = request.form.get('object')
    object_value, _, report_text = validate_new_triple(subject, predicate, object_value)
    if shacl:
        data_graph = fetch_data_graph_for_subject(subject)
        can_be_added, _, _, _, _, s_types, _ = get_valid_predicates(list(data_graph.triples((None, None, None))))
        if predicate not in can_be_added and URIRef(predicate) in data_graph.predicates():
            flash(gettext('This resource cannot have any other %(predicate)s properties', predicate=custom_filter.human_readable_predicate(predicate, s_types)))
            return redirect(url_for('about', subject=subject))
        if object_value is None:
            flash(report_text)
            return redirect(url_for('about', subject=subject))
    else:
        object_value = URIRef(object_value) if validators.url(object_value) else Literal(object_value, datatype=XSD.string)
    editor = Editor(dataset_endpoint, provenance_endpoint, app.config['COUNTER_HANDLER'], app.config['RESPONSIBLE_AGENT'], app.config['PRIMARY_SOURCE'], app.config['DATASET_GENERATION_TIME'])
    editor.import_entity(URIRef(subject))
    editor.preexisting_finished()
    editor.create(URIRef(subject), URIRef(predicate), object_value)
    editor.save()
    return redirect(url_for('about', subject=subject))

@app.route('/apply_changes', methods=['POST'])
def apply_changes():
    try:
        changes = request.json
        subject = changes[0]["subject"]
        editor = Editor(dataset_endpoint, provenance_endpoint, app.config['COUNTER_HANDLER'], app.config['RESPONSIBLE_AGENT'], app.config['PRIMARY_SOURCE'], app.config['DATASET_GENERATION_TIME'])
        editor.import_entity(URIRef(subject))
        editor.preexisting_finished()

        graph_uri = None
        if editor.dataset_is_quadstore:
            for quad in editor.g_set.quads((URIRef(subject), None, None)):
                graph_uri = quad[3]
                break

        for change in changes:
            action = change["action"]
            predicate = change["predicate"]
            object_value = change["object"]
            if action == "create":
                # Handle create action if needed
                pass
            elif action == "delete":
                delete_logic(editor, subject, predicate, object_value, graph_uri)
            elif action == "update":
                new_object_value = change["newObject"]
                update_logic(editor, subject, predicate, object_value, new_object_value, graph_uri)
            elif action == "order":
                new_order = change["object"]
                ordered_by = change["newObject"]
                order_logic(editor, subject, predicate, new_order, ordered_by, graph_uri)
        editor.save()
        return jsonify(status="success", message=gettext("Changes applied successfully")), 201
    except ValueError as ve:
        return jsonify(status="error", message=str(ve)), 400 
    except Exception as e:
        error_message = f"Error while applying changes: {str(e)}\n{traceback.format_exc()}"
        app.logger.error(error_message)
        return jsonify(status="error", message=gettext("An error occurred while applying changes")), 500

def update_logic(editor: Editor, subject, predicate, old_value, new_value, graph_uri=None):
    new_value, old_value, report_text = validate_new_triple(subject, predicate, new_value, old_value)
    if shacl:
        if new_value is None:
            raise ValueError(report_text)
    else:
        new_value = Literal(new_value, datatype=old_value.datatype) if old_value.datatype and isinstance(old_value, Literal) else Literal(new_value, datatype=XSD.string) if isinstance(old_value, Literal) else URIRef(new_value)
    editor.update(URIRef(subject), URIRef(predicate), old_value, new_value, graph_uri)

def delete_logic(editor: Editor, subject, predicate, object_value, graph_uri=None):
    if shacl:
        data_graph = fetch_data_graph_for_subject(subject)
        _, can_be_deleted, _, _, _, _, _ = get_valid_predicates(list(data_graph.triples((URIRef(subject), None, None))))
        if predicate not in can_be_deleted:
            raise ValueError(gettext('This property cannot be deleted'))
    editor.delete(subject, predicate, object_value, graph_uri)

def order_logic(editor: Editor, subject, predicate, new_order, ordered_by, graph_uri=None):
    def order_by_next(data):
        # Costruisci una mappa dove la chiave è l'entity e il valore è il next
        next_map = {entity: next_val for entity, next_val in data}
        # Trova l'elemento iniziale (quello che non ha un predecessore)
        start = None
        for entity in next_map:
            if entity not in next_map.values():
                start = entity
                break
        # Ordina la lista seguendo la catena di next
        ordered_list = []
        while start:
            ordered_list.append(start)
            start = next_map.get(start)
        return ordered_list
    
    query_current_order = f'''
        SELECT ?entity ?next
        WHERE {{
            <{subject}> <{predicate}> ?entity.
            ?entity <{ordered_by}> ?next.
        }}
    '''
    sparql.setQuery(query_current_order)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    old_order = order_by_next([(result["entity"]["value"], result["next"]["value"]) for result in results["results"]["bindings"]])
    old_next_map = {entity: next_val for entity, next_val in zip(old_order, old_order[1:] + [None])}
    for old_entity in old_order:
        editor.import_entity(URIRef(old_entity))
    editor.preexisting_finished()
    for entity, next_val in old_next_map.items():
        if next_val is not None:
            editor.delete(URIRef(entity), URIRef(ordered_by), next_val, graph_uri)
    
    for idx, entity in enumerate(new_order):
        if idx < len(new_order) - 1:
            next_entity = new_order[idx + 1]
            editor.create(URIRef(entity), URIRef(ordered_by), URIRef(next_entity), graph_uri)

@app.route('/search')
def search():
    subject = request.args.get('q')
    return redirect(url_for('about', subject=subject))

@app.route('/set-language/<lang_code>')
def set_language(lang_code=None):
    session['lang'] = lang_code
    refresh()
    return redirect(request.referrer or url_for('index'))

@app.route('/endpoint')
def endpoint():
    return render_template('endpoint.jinja', dataset_endpoint=dataset_endpoint)

@app.route('/dataset-endpoint', methods=['POST'])
def sparql_proxy():
    query = request.form.get('query')
    response = requests.post(dataset_endpoint, data={'query': query}, headers={'Accept': 'application/sparql-results+json'})
    return response.content, response.status_code, {'Content-Type': 'application/sparql-results+json'}

@app.route('/entity-history/<path:entity_uri>')
def entity_history(entity_uri):
    agnostic_entity = AgnosticEntity(res=entity_uri, config=change_tracking_config)
    history, provenance = agnostic_entity.get_history(include_prov_metadata=True)
    subject_classes = [subject_class[2] for subject_class in list(history[entity_uri].values())[0].triples((URIRef(entity_uri), RDF.type, None))]
    # Trasforma i dati in formato TimelineJS useless
    events = []
    sorted_metadata = sorted(provenance[entity_uri].items(), key=lambda x: x[1]['generatedAtTime'])  # Ordina gli eventi per data

    for i, (snapshot_uri, metadata) in enumerate(sorted_metadata):
        date = datetime.fromisoformat(metadata['generatedAtTime'])
        responsible_agent = f"<a href='{metadata['wasAttributedTo']}' alt='{gettext('Link to the responsible agent description')} target='_blank'>{metadata['wasAttributedTo']}</a>" if validators.url(metadata['wasAttributedTo']) else metadata['wasAttributedTo']
        primary_source = custom_filter.human_readable_primary_source(metadata['hadPrimarySource'])
        modifications = metadata['hasUpdateQuery']
        modification_text = ""
        if modifications:
            modifications = parse_sparql_update(modifications)
            for mod_type, triples in modifications.items():
                modification_text += f"<h4>{mod_type}</h4><ul>"
                for triple in triples:
                    modification_text += f"<li><strong>{custom_filter.human_readable_predicate(triple[1], subject_classes)}:</strong> {custom_filter.human_readable_predicate(triple[2], subject_classes)}</li>"
                modification_text += "</ul>"
        
        event = {
            "start_date": {
                "year": date.year,
                "month": date.month,
                "day": date.day,
                "hour": date.hour,
                "minute": date.minute,
                "second": date.second
            },
            "text": {
                "headline": gettext('Snapshot') + ' ' + str(i + 1),
                "text": f"""
                    <p><strong>{gettext('Responsible agent')}:</strong> {responsible_agent}</p>
                    <p><strong>{gettext('Primary source')}:</strong> {primary_source}</p>
                    <p><strong>{gettext('Description')}:</strong> {metadata['description']}</p>
                    <div class="modifications mb-3">
                        {modification_text}
                    </div>
                """
            },
            "autolink": False
        }

        if i + 1 < len(sorted_metadata):
            next_date = datetime.fromisoformat(sorted_metadata[i + 1][1]['generatedAtTime'])
            event["end_date"] = {
                "year": next_date.year,
                "month": next_date.month,
                "day": next_date.day,
                "hour": next_date.hour,
                "minute": next_date.minute,
                "second": next_date.second
            }
        else:
            now = datetime.now()
            event["end_date"] = {
                "year": now.year,
                "month": now.month,
                "day": now.day,
                "hour": now.hour,
                "minute": now.minute,
                "second": now.second
            }

        view_version_button = f"<a href='/entity-version/{entity_uri}/{metadata['generatedAtTime']}' class='btn btn-primary mt-2 view-version' target='_self'>{gettext('View version')}</a>"
        event["text"]["text"] += f"{view_version_button}"
        events.append(event)

    timeline_data = {
        "title": {
            "text": {
                "headline": gettext('Version history for') + ' ' + entity_uri
            }
        },
        "events": events
    }

    return render_template('entity_history.jinja', entity_uri=entity_uri, timeline_data=timeline_data)

@app.route('/entity-version/<path:entity_uri>/<timestamp>')
def entity_version(entity_uri, timestamp):
    try:
        timestamp_dt = datetime.fromisoformat(timestamp)
    except ValueError:
        query_timestamp = f'''
            SELECT ?generation_time
            WHERE {{
                <{entity_uri}/prov/se/{timestamp}> <{ProvEntity.iri_generated_at_time}> ?generation_time.
            }}
        '''
        provenance_sparql.setQuery(query_timestamp)
        provenance_sparql.setReturnFormat(JSON)
        try:
            generation_time = provenance_sparql.queryAndConvert()['results']['bindings'][0]['generation_time']['value']
        except IndexError:
            abort(404)
        timestamp = generation_time
        timestamp_dt = datetime.fromisoformat(generation_time)
    agnostic_entity = AgnosticEntity(res=entity_uri, config=change_tracking_config)
    history, metadata, other_snapshots_metadata = agnostic_entity.get_state_at_time(time=(None, timestamp), include_prov_metadata=True)
    all_snapshots = list(metadata.items()) + list(other_snapshots_metadata.items())
    sorted_all_snapshots = sorted(all_snapshots, key=lambda x: x[1]['generatedAtTime'])
    last_snapshot_timestamp = sorted_all_snapshots[-1][1]['generatedAtTime'] if sorted_all_snapshots else None
    if last_snapshot_timestamp and timestamp > last_snapshot_timestamp:
        abort(404)
    if not timestamp_dt.tzinfo:
        timestamp_dt = timestamp_dt.replace(tzinfo=timezone.utc)
    history = {k: v for k, v in history.items()}
    for key, value in metadata.items():
        value['generatedAtTime'] = datetime.fromisoformat(value['generatedAtTime']).astimezone(timezone.utc).isoformat()
    try:
        closest_timestamp = min(history.keys(), key=lambda t: abs(datetime.fromisoformat(t).astimezone(timezone.utc) - timestamp_dt))
    except ValueError:
        abort(404)
    version: Graph = history[closest_timestamp]
    triples = list(version.triples((None, None, None)))
    relevant_properties = set()
    _, _, _, _, _, subject_classes, valid_predicates = get_valid_predicates(triples)

    grouped_triples, relevant_properties = get_grouped_triples(entity_uri, triples, subject_classes, valid_predicates)

    if relevant_properties:
        triples = [triple for triple in triples if str(triple[1]) in relevant_properties]

    sorted_snapshots = sorted(other_snapshots_metadata.items(), key=lambda x: x[1]['generatedAtTime'])

    next_snapshot_timestamp = None
    prev_snapshot_timestamp = None
    for snapshot_uri, meta in sorted_snapshots:
        if meta['generatedAtTime'] >= timestamp:
            next_snapshot_timestamp = meta['generatedAtTime']
            break
    for snapshot_uri, meta in reversed(sorted_snapshots):
        if meta['generatedAtTime'] < timestamp:
            prev_snapshot_timestamp = meta['generatedAtTime']
            break
    if not prev_snapshot_timestamp:
        sorted_metadata = sorted(metadata.items(), key=lambda x: x[1]['generatedAtTime'], reverse=True)
        for snapshot_uri, meta in sorted_metadata:
            if meta['generatedAtTime'] < timestamp and not datetime.fromisoformat(meta['generatedAtTime']).replace(tzinfo=None) == datetime.fromisoformat(closest_timestamp):
                prev_snapshot_timestamp = meta['generatedAtTime']
                break
    closest_metadata_key = min(metadata.keys(), key=lambda k: abs(datetime.fromisoformat(metadata[k]['generatedAtTime']).astimezone(timezone.utc) - timestamp_dt))
    closest_metadata = {closest_metadata_key: metadata[closest_metadata_key]}
    if closest_metadata[closest_metadata_key]['hasUpdateQuery']:
        sparql_query = closest_metadata[closest_metadata_key]['hasUpdateQuery']
        modifications = parse_sparql_update(sparql_query)
    else:
        modifications = None
    return render_template('entity_version.jinja', subject=entity_uri, metadata=closest_metadata, timestamp=closest_timestamp, next_snapshot_timestamp=next_snapshot_timestamp, prev_snapshot_timestamp=prev_snapshot_timestamp, modifications=modifications, grouped_triples=grouped_triples, subject_classes=subject_classes)

@app.route('/restore-version/<path:entity_uri>/<timestamp>', methods=['POST'])
def restore_version(entity_uri, timestamp):
    query_snapshots = f"""
        SELECT ?time ?updateQuery ?snapshot
        WHERE {{
            ?snapshot <{ProvEntity.iri_specialization_of}> <{entity_uri}>;
                <{ProvEntity.iri_generated_at_time}> ?time
            OPTIONAL {{
                ?snapshot <{ProvEntity.iri_has_update_query}> ?updateQuery.
            }}
        }}
    """
    results = list(Sparql(query_snapshots, config=change_tracking_config).run_select_query())
    results.sort(key=lambda x:convert_to_datetime(x[0]), reverse=True)
    relevant_results = _filter_timestamps_by_interval((timestamp, timestamp), results, time_index=0)
    sum_update_queries = ""
    for relevant_result in relevant_results:
        for result in results:
            if result[1]:
                if convert_to_datetime(result[0]) > convert_to_datetime(relevant_result[0]):
                    sum_update_queries += (result[1]) +  ";"
        primary_source = URIRef(relevant_result[2])
    inverted_query = invert_sparql_update(sum_update_queries)
    editor = Editor(dataset_endpoint, provenance_endpoint, app.config['COUNTER_HANDLER'], app.config['RESPONSIBLE_AGENT'], primary_source, app.config['DATASET_GENERATION_TIME'])
    editor.execute(inverted_query)
    editor.save()
    query = f"""
        SELECT ?predicate ?object WHERE {{
            <{entity_uri}> ?predicate ?object.
        }}
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return redirect(url_for('about', subject=entity_uri))
    
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.jinja'), 404

def parse_sparql_update(query):
    parsed = parseUpdate(query)
    translated = translateUpdate(parsed).algebra
    modifications = {}

    def extract_quads(quads):
        result = []
        if isinstance(quads, defaultdict):
            for graph, triples in quads.items():
                for triple in triples:
                    result.append((triple[0], triple[1], triple[2]))
        else:
            # Fallback for triples
            result.extend(quads)
        return result

    for operation in translated:
        if operation.name == "DeleteData":
            if hasattr(operation, 'quads'):
                deletions = extract_quads(operation.quads)
            else:
                deletions = operation.triples
            if deletions:
                modifications.setdefault(gettext('Deletions'), list()).extend(deletions)
        elif operation.name == "InsertData":
            if hasattr(operation, 'quads'):
                additions = extract_quads(operation.quads)
            else:
                additions = extract_quads(operation.quads)
            if additions:
                modifications.setdefault(gettext('Additions'), list()).extend(additions)

    return modifications

def validate_new_triple(subject, predicate, new_value, old_value = None):
    data_graph = fetch_data_graph_for_subject(subject)
    if old_value is not None:
        old_value = [triple[2] for triple in data_graph.triples((URIRef(subject), URIRef(predicate), None)) if str(triple[2]) == str(old_value)][0]
    if shacl is None:
        # Se non c'è SHACL, accettiamo qualsiasi valore
        if validators.url(new_value):
            return URIRef(new_value), old_value, ''
        else:
            return Literal(new_value), old_value, ''
    
    s_types = [triple[2] for triple in data_graph.triples((URIRef(subject), RDF.type, None))]
    query = f"""
        PREFIX sh: <http://www.w3.org/ns/shacl#>
        SELECT DISTINCT ?path ?datatype ?a_class ?classIn (GROUP_CONCAT(DISTINCT COALESCE(?optionalValue, ""); separator=",") AS ?optionalValues)
        WHERE {{
            ?shape sh:targetClass ?type ;
                sh:property ?propertyShape .
            ?propertyShape sh:path ?path .
            FILTER(?path = <{predicate}>)
            VALUES ?type {{<{'> <'.join(s_types)}>}}
            OPTIONAL {{?propertyShape  sh:datatype ?datatype .}}
            OPTIONAL {{?propertyShape  sh:class ?a_class .}}
            OPTIONAL {{
                ?propertyShape sh:or ?orList .
                ?orList rdf:rest*/rdf:first ?orConstraint .
                ?orConstraint sh:datatype ?datatype .
                OPTIONAL {{?orConstraint sh:class ?class .}}
            }}
            OPTIONAL {{
                ?propertyShape  sh:classIn ?classInList .
                ?classInList rdf:rest*/rdf:first ?classIn .
            }}
            OPTIONAL {{
                ?propertyShape sh:in ?list .
                ?list rdf:rest*/rdf:first ?optionalValue .
            }}
        }}
        GROUP BY ?path ?datatype ?a_class ?classIn
    """
    results = shacl.query(query)
    property_exists = [row.path for row in results]
    if not property_exists:
        return None, old_value, gettext('The property %(predicate)s is not allowed for resources of type %(s_type)s', predicate=custom_filter.human_readable_predicate(predicate, s_types), s_type=custom_filter.human_readable_predicate(s_types[0], s_types))
    datatypes = [row.datatype for row in results if row.datatype is not None]
    classes = [row.a_class for row in results if row.a_class]
    classes.extend([row.classIn for row in results if row.classIn])
    optional_values_str = [row.optionalValues for row in results if row.optionalValues]
    optional_values_str = optional_values_str[0] if optional_values_str else ''
    optional_values = [value for value in optional_values_str.split(',') if value]
    if optional_values and new_value not in optional_values:
        return None, old_value, gettext('<code>%(new_value)s</code> is not a valid value. The <code>%(property)s</code> property requires one of the following values: %(o_values)s', new_value=custom_filter.human_readable_predicate(new_value, s_types), property=custom_filter.human_readable_predicate(predicate, s_types), o_values=', '.join([f'<code>{custom_filter.human_readable_predicate(value, s_types)}</code>' for value in optional_values]))
    if classes:
        if not validators.url(new_value):
            return None, old_value, gettext('<code>%(new_value)s</code> is not a valid value. The <code>%(property)s</code> property requires values of type %(o_types)s', new_value=custom_filter.human_readable_predicate(new_value, s_types), property=custom_filter.human_readable_predicate(predicate, s_types), o_types=', '.join([f'<code>{custom_filter.human_readable_predicate(o_class, s_types)}</code>' for o_class in classes]))
        valid_value = convert_to_matching_class(new_value, classes)
        if valid_value is None:
            return None, old_value, gettext('<code>%(new_value)s</code> is not a valid value. The <code>%(property)s</code> property requires values of type %(o_types)s', new_value=custom_filter.human_readable_predicate(new_value, s_types), property=custom_filter.human_readable_predicate(predicate, s_types), o_types=', '.join([f'<code>{custom_filter.human_readable_predicate(o_class, s_types)}</code>' for o_class in classes]))
        return valid_value, old_value, ''
    elif datatypes:
        valid_value = convert_to_matching_literal(new_value, datatypes)
        if valid_value is None:
            return None, old_value, gettext('<code>%(new_value)s</code> is not a valid value. The <code>%(property)s</code> property requires values of type %(o_types)s', new_value=custom_filter.human_readable_predicate(new_value, s_types), property=custom_filter.human_readable_predicate(predicate, s_types), o_types=', '.join([f'<code>{custom_filter.human_readable_predicate(datatype, s_types)}</code>' for datatype in datatypes]))
        return valid_value, old_value, ''
    # Se non ci sono datatypes o classes specificati, determiniamo il tipo in base a old_value e new_value
    if isinstance(old_value, Literal):
        if old_value.datatype:
            valid_value = Literal(new_value, datatype=old_value.datatype)
        else:
            valid_value = Literal(new_value)
    elif isinstance(old_value, URIRef) or validators.url(new_value):
        valid_value = URIRef(new_value)
    else:
        valid_value = Literal(new_value)
    return valid_value, old_value, ''

def get_grouped_triples(subject, triples, subject_classes, valid_predicates_info):
    grouped_triples = OrderedDict()
    relevant_properties = set()
    fetched_values_map = dict()  # Map of original values to values returned by the query
    primary_properties = valid_predicates_info

    for prop_uri in primary_properties:
        if display_rules:
            matched_rules = [rule for rule in display_rules if URIRef(rule['class']) in subject_classes and any(p['property'] == prop_uri for p in rule['displayProperties'])]
            if matched_rules:
                rule = matched_rules[0]
                for prop in rule['displayProperties']:
                    if prop['property'] == prop_uri:
                        is_ordered = 'orderedBy' in prop
                        order_property = prop.get('orderedBy')
                        
                        if 'displayRules' in prop:
                            for display_rule in prop['displayRules']:
                                display_name = display_rule.get('displayName', prop_uri)
                                relevant_properties.add(prop_uri)
                                process_display_rule(display_name, prop_uri, display_rule, subject, triples, grouped_triples, fetched_values_map)
                                
                                if is_ordered:
                                    grouped_triples[display_name]['is_draggable'] = True
                                    grouped_triples[display_name]['ordered_by'] = order_property
                                    process_ordering(subject, prop, order_property, grouped_triples, display_name, fetched_values_map)
                        else:
                            display_name = prop.get('displayName', prop_uri)
                            relevant_properties.add(prop_uri)
                            process_display_rule(display_name, prop_uri, prop, subject, triples, grouped_triples, fetched_values_map)
                            
                            if is_ordered:
                                grouped_triples[display_name]['is_draggable'] = True
                                grouped_triples[display_name]['ordered_by'] = order_property
                                process_ordering(subject, prop, order_property, grouped_triples, display_name, fetched_values_map)
            else:
                process_default_property(prop_uri, triples, grouped_triples)
        else:
            process_default_property(prop_uri, triples, grouped_triples)

    # Ordering logic remains the same
    if display_rules:
        ordered_display_names = []
        for rule in display_rules:
            if URIRef(rule['class']) in subject_classes:
                for prop in rule['displayProperties']:
                    if 'displayRules' in prop:
                        for display_rule in prop['displayRules']:
                            display_name = display_rule.get('displayName', prop['property'])
                            if display_name in grouped_triples:
                                ordered_display_names.append(display_name)
                    else:
                        display_name = prop.get('displayName', prop['property'])
                        if display_name in grouped_triples:
                            ordered_display_names.append(display_name)
        for display_name in grouped_triples.keys():
            if display_name not in ordered_display_names:
                ordered_display_names.append(display_name)
    else:
        ordered_display_names = list(grouped_triples.keys())

    grouped_triples = OrderedDict((k, grouped_triples[k]) for k in ordered_display_names)
    return grouped_triples, relevant_properties
        
def process_display_rule(display_name, prop_uri, rule, subject, triples, grouped_triples, fetched_values_map):
    if display_name not in grouped_triples:
        grouped_triples[display_name] = {
            'property': prop_uri,
            'triples': []
        }
    for triple in triples:
        if str(triple[1]) == prop_uri:
            if rule.get('fetchValueFromQuery'):
                result, external_entity = execute_sparql_query(rule['fetchValueFromQuery'], subject, triple[2])
                if result:
                    fetched_values_map[result] = str(triple[2])
                    new_triple = (str(triple[0]), str(triple[1]), str(result))
                    existing_values = [t['triple'][2] for t in grouped_triples[display_name]['triples']]
                    if new_triple[2] not in existing_values:
                        new_triple_data = {
                            'triple': new_triple,
                            'external_entity': external_entity,
                            'object': str(triple[2])
                        }
                        grouped_triples[display_name]['triples'].append(new_triple_data)
            else:
                new_triple_data = {
                    'triple': (str(triple[0]), str(triple[1]), str(triple[2])),
                    'object': str(triple[2])
                }
                grouped_triples[display_name]['triples'].append(new_triple_data)

def process_ordering(subject, prop, order_property, grouped_triples, display_name, fetched_values_map):
    def get_ordered_sequence(order_results):
        order_map = {}
        for res in order_results:
            next_value = res['nextValue']['value']
            order_map[res['orderedEntity']['value']] = None if next_value == "NONE" else next_value
        all_sequences = []
        start_elements = set(order_map.keys()) - set(order_map.values())
        while start_elements:
            sequence = []
            current_element = start_elements.pop()
            while current_element in order_map:
                sequence.append(current_element)
                current_element = order_map[current_element]
            all_sequences.append(sequence)
        return all_sequences
        
    order_query = f"""
        SELECT ?orderedEntity (COALESCE(?next, "NONE") AS ?nextValue)
        WHERE {{
            <{subject}> <{prop['property']}> ?orderedEntity.
            OPTIONAL {{
                ?orderedEntity <{order_property}> ?next.
            }}
        }}
    """
    sparql.setQuery(order_query)
    sparql.setReturnFormat(JSON)
    order_results = sparql.query().convert().get("results", {}).get("bindings", [])
    order_sequences = get_ordered_sequence(order_results)
    for sequence in order_sequences:
        grouped_triples[display_name]['triples'].sort(
            key=lambda x: sequence.index(fetched_values_map.get(x['triple'][2], x['triple'][2])) if fetched_values_map.get(x['triple'][2], x['triple'][2]) in sequence else float('inf'))

def process_default_property(prop_uri, triples, grouped_triples):
    display_name = prop_uri
    grouped_triples[display_name] = {
        'property': prop_uri,
        'triples': []
    }
    triples_for_prop = [triple for triple in triples if str(triple[1]) == prop_uri]
    for triple in triples_for_prop:
        new_triple_data = {
            'triple': (str(triple[0]), str(triple[1]), str(triple[2])),
            'object': str(triple[2])
        }
        grouped_triples[display_name]['triples'].append(new_triple_data)

def fetch_data_graph_for_subject(subject_uri):
    if is_dataset_quadstore():
        query = f"""
        SELECT ?g ?p ?o (LANG(?o) AS ?lang)
        WHERE {{
            GRAPH ?g {{
                <{subject_uri}> ?p ?o .
            }}
        }}
        """
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        try:
            results = sparql.query().convert()
            g = ConjunctiveGraph()
            for result in results["results"]["bindings"]:
                s = URIRef(subject_uri)
                p = URIRef(result["p"]["value"])
                obj_data = result["o"]
                
                if obj_data["type"] == "uri":
                    o = URIRef(obj_data["value"])
                else:
                    value = obj_data["value"]
                    lang = result.get("lang", {}).get("value")
                    datatype = obj_data.get("datatype")
                    
                    if lang:
                        o = Literal(value, lang=lang)
                    elif datatype:
                        o = Literal(value, datatype=URIRef(datatype))
                    else:
                        o = Literal(value)
                
                g_context = URIRef(result["g"]["value"])
                g.add((s, p, o, g_context))
            return g
        except Exception as e:
            app.logger.error(f"Error fetching data for {subject_uri}: {str(e)}")
            return None
    else:
        query = f"""
        CONSTRUCT {{
            <{subject_uri}> ?p ?o .
        }}
        WHERE {{
            <{subject_uri}> ?p ?o .
        }}
        """
        sparql.setQuery(query)
        sparql.setReturnFormat(XML)
        try:
            result = sparql.query().convert()
            return result
        except Exception as e:
            app.logger.error(f"Error fetching data for {subject_uri}: {str(e)}")
            return None
            
def is_valid_uri(uri):
    parsed_uri = urlparse(uri)
    return all([parsed_uri.scheme, parsed_uri.netloc])

def fetch_data_graph_for_subject_recursively(subject_uri):
    """
    Fetch all triples associated with subject and all triples of all the entities that the subject points to.
    """
    query_str = f'''
        PREFIX eea: <https://jobu_tupaki/>
        CONSTRUCT {{
            ?s ?p ?o .
        }}
        WHERE {{
            {{
                <{subject_uri}> ?p ?o .
                ?s ?p ?o .
            }} UNION {{
                <{subject_uri}> (<eea:everything_everywhere_allatonce>|!<eea:everything_everywhere_allatonce>)* ?s.
                ?s ?p ?o. 
            }}
        }}
    '''
    sparql.setQuery(query_str)
    sparql.setReturnFormat(XML)
    result = sparql.queryAndConvert()
    return result

def convert_to_matching_class(object_value, classes):
    data_graph = fetch_data_graph_for_subject(object_value)
    o_types = {c[2] for c in data_graph.triples((URIRef(object_value), RDF.type, None))}
    if o_types.intersection(classes):
        return URIRef(object_value)

def convert_to_matching_literal(object_value, datatypes):
    for datatype in datatypes:
        validation_func = next((d[1] for d in DATATYPE_MAPPING if d[0] == datatype), None)
        if validation_func is None:
            return Literal(object_value, datatype=XSD.string)
        is_valid_datatype = validation_func(object_value)
        if is_valid_datatype:
            return Literal(object_value, datatype=datatype)

def invert_sparql_update(sparql_query: str) -> str:
    inverted_query = sparql_query.replace('INSERT', 'TEMP_REPLACE').replace('DELETE', 'INSERT').replace('TEMP_REPLACE', 'DELETE')
    return inverted_query

def execute_sparql_update(sparql_query: str):
    editor = Editor(dataset_endpoint, provenance_endpoint, app.config['COUNTER_HANDLER'], app.config['RESPONSIBLE_AGENT'], app.config['PRIMARY_SOURCE'], app.config['DATASET_GENERATION_TIME'])
    editor.execute(sparql_query)
    editor.save()

def prioritize_datatype(datatypes):
    for datatype in DATATYPE_MAPPING:
        if datatype[0] in datatypes:
            return datatype[0]
    return DATATYPE_MAPPING[0][0]

def get_valid_predicates(triples):
    existing_predicates = [triple[1] for triple in triples]
    predicate_counts = {str(predicate): existing_predicates.count(predicate) for predicate in set(existing_predicates)}
    default_datatypes = {str(predicate): XSD.string for predicate in existing_predicates}
    s_types = [triple[2] for triple in triples if triple[1] == RDF.type]
    valid_predicates = [{str(predicate): {"min": None, "max": None, "hasValue": None, "optionalValues": []}} for predicate in set(existing_predicates)]
    if not s_types:
        return existing_predicates, existing_predicates, default_datatypes, dict(), dict(), [], [str(predicate) for predicate in existing_predicates]
    if not shacl:
        return existing_predicates, existing_predicates, default_datatypes, dict(), dict(), s_types, [str(predicate) for predicate in existing_predicates]
    query = prepareQuery(f"""
        SELECT ?predicate ?datatype ?maxCount ?minCount ?hasValue (GROUP_CONCAT(?optionalValue; separator=",") AS ?optionalValues) WHERE {{
            ?shape sh:targetClass ?type ;
                   sh:property ?property .
            VALUES ?type {{<{'> <'.join(s_types)}>}}
            ?property sh:path ?predicate .
            OPTIONAL {{?property sh:datatype ?datatype .}}
            OPTIONAL {{?property sh:maxCount ?maxCount .}}
            OPTIONAL {{?property sh:minCount ?minCount .}}
            OPTIONAL {{?property sh:hasValue ?hasValue .}}
            OPTIONAL {{
                ?property sh:in ?list .
                ?list rdf:rest*/rdf:first ?optionalValue .
            }}
            OPTIONAL {{
                ?property sh:or ?orList .
                ?orList rdf:rest*/rdf:first ?orConstraint .
                ?orConstraint sh:datatype ?datatype .
            }}
            FILTER (isURI(?predicate))
        }}
        GROUP BY ?predicate ?datatype ?maxCount ?minCount ?hasValue
    """, initNs={"sh": "http://www.w3.org/ns/shacl#", "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"})
    results = shacl.query(query)
    valid_predicates = [{
        str(row.predicate): {
            "min": 0 if row.minCount is None else int(row.minCount), 
            "max": None if row.maxCount is None else str(row.maxCount),
            "hasValue": row.hasValue,
            "optionalValues": row.optionalValues.split(",") if row.optionalValues else []
        }
    } for row in results]
    can_be_added = set()
    can_be_deleted = set()
    for valid_predicate in valid_predicates:
        for predicate, ranges in valid_predicate.items():
            if ranges["hasValue"]:
                mandatory_value_present = any(triple[2] == str(ranges["hasValue"]) for triple in triples)
                if not mandatory_value_present:
                    can_be_added.add(predicate)
            else:
                max_reached_for_generic = (ranges["max"] is not None and int(ranges["max"]) <= predicate_counts.get(predicate, 0))
                max_reached_for_optional = (ranges["max"] is not None and int(ranges["max"]) <= sum(1 for triple in triples if triple[2] in ranges["optionalValues"])) if ranges["optionalValues"] else max_reached_for_generic
                if not max_reached_for_generic or not max_reached_for_optional:
                    can_be_added.add(predicate)
                if not (ranges["min"] is not None and int(ranges["min"]) == predicate_counts.get(predicate, 0)):
                    can_be_deleted.add(predicate)
    datatypes = defaultdict(list)
    for row in results:
        if row.datatype:
            datatypes[str(row.predicate)].append(str(row.datatype))
        else:
            datatypes[str(row.predicate)].append(str(XSD.string))
    mandatory_values = {}
    for valid_predicate in valid_predicates:
        for predicate, ranges in valid_predicate.items():
            if ranges["hasValue"]:
                mandatory_values[str(predicate)] = str(ranges["hasValue"])
    optional_values = dict()
    for valid_predicate in valid_predicates:
        for predicate, ranges in valid_predicate.items():
            if "optionalValues" in ranges:
                optional_values.setdefault(str(predicate), list()).extend(ranges["optionalValues"])
    return list(can_be_added), list(can_be_deleted), dict(datatypes), mandatory_values, optional_values, s_types, {list(predicate_data.keys())[0] for predicate_data in valid_predicates}

def get_form_fields_from_shacl():
    """
    Analizza le shape SHACL per estrarre i campi del form per ogni tipo di entità.

    Restituisce:
        OrderedDict: Un dizionario dove le chiavi sono i tipi di entità e i valori sono dizionari
                     dei campi del form con le loro proprietà.
    """
    if not shacl:
        return dict()
    
    # Step 1: Ottieni i campi iniziali dalle shape SHACL
    form_fields = extract_shacl_form_fields()

    # Step 2: Processa le shape annidate per ogni campo
    processed_shapes = set()
    for entity_type in form_fields:
        for predicate in form_fields[entity_type]:
            for field_info in form_fields[entity_type][predicate]:
                if field_info.get("nodeShape"):
                    field_info["nestedShape"] = process_nested_shapes(
                        field_info["nodeShape"], 
                        processed_shapes=processed_shapes
                    )
    
    # Step 3: Applica le regole di visualizzazione ai campi del form
    if display_rules:
        form_fields = apply_display_rules(form_fields)

    # Step 4: Ordina i campi del form secondo le regole di visualizzazione
    ordered_form_fields = order_form_fields(form_fields)

    return ordered_form_fields

def extract_shacl_form_fields():
    """
    Estrae i campi del form dalle shape SHACL.

    Restituisce:
        defaultdict: Un dizionario dove le chiavi sono i tipi di entità e i valori sono dizionari
                     dei campi del form con le loro proprietà.
    """
    if not shacl:
        return dict()
    
    query = prepareQuery("""
        SELECT ?type ?predicate ?nodeShape ?datatype ?maxCount ?minCount ?hasValue ?objectClass ?conditionPath ?conditionValue ?pattern ?message
        (GROUP_CONCAT(?optionalValue; separator=",") AS ?optionalValues)
        WHERE {
            ?shape sh:targetClass ?type ;
                   sh:property ?property .
            ?property sh:path ?predicate .
            OPTIONAL {
                ?property sh:node ?nodeShape .
                OPTIONAL {?nodeShape sh:targetClass ?objectClass .}
            }
            OPTIONAL { ?property sh:datatype ?datatype . }
            OPTIONAL { ?property sh:maxCount ?maxCount . }
            OPTIONAL { ?property sh:minCount ?minCount . }
            OPTIONAL { ?property sh:hasValue ?hasValue . }
            OPTIONAL {
                    ?property sh:or ?orList .
                    ?orList rdf:rest*/rdf:first ?orConstraint .
                    ?orConstraint sh:datatype ?datatype .
            }
            OPTIONAL {
                ?property sh:in ?list .
                ?list rdf:rest*/rdf:first ?optionalValue .
            }
            OPTIONAL {
                ?property sh:condition ?conditionNode .
                ?conditionNode sh:path ?conditionPath ;
                               sh:hasValue ?conditionValue .
            }
            OPTIONAL { ?property sh:pattern ?pattern . }
            OPTIONAL { ?property sh:message ?message . }
            FILTER (isURI(?predicate))
        }
        GROUP BY ?type ?predicate ?nodeShape ?datatype ?maxCount ?minCount ?hasValue ?objectClass ?conditionPath ?conditionValue ?pattern ?message
    """, initNs={"sh": "http://www.w3.org/ns/shacl#", "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"})

    results = shacl.query(query)
    form_fields = defaultdict(dict)

    for row in results:
        if str(row.predicate) == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" and not row.optionalValues:
            continue
        
        entity_type = str(row.type)
        predicate = str(row.predicate)
        nodeShape = str(row.nodeShape) if row.nodeShape else None
        hasValue = str(row.hasValue) if row.hasValue else None
        objectClass = str(row.objectClass) if row.objectClass else None
        minCount = 0 if row.minCount is None else int(row.minCount)
        maxCount = None if row.maxCount is None else int(row.maxCount)
        datatype = str(row.datatype) if row.datatype else None
        optionalValues = row.optionalValues.split(",") if row.optionalValues else []

        condition_entry = {}
        if row.conditionPath and row.conditionValue:
            condition_entry['condition'] = {
                "path": str(row.conditionPath),
                "value": str(row.conditionValue)
            }
        if row.pattern:
            condition_entry['pattern'] = str(row.pattern)
        if row.message:
            condition_entry['message'] = str(row.message)

        if predicate not in form_fields[entity_type]:
            form_fields[entity_type][predicate] = []

        # Cerca un campo esistente con gli stessi attributi (eccetto datatype)
        existing_field = None
        for field in form_fields[entity_type][predicate]:
            if (field['nodeShape'] == nodeShape and
                field['hasValue'] == hasValue and
                field['objectClass'] == objectClass and
                field['min'] == minCount and
                field['max'] == maxCount and
                field['optionalValues'] == optionalValues):
                existing_field = field
                break

        if existing_field:
            # Aggiorna la lista dei datatypes
            if row.datatype and str(row.datatype) not in existing_field["datatypes"]:
                existing_field["datatypes"].append(str(row.datatype))
            if condition_entry:
                existing_field.setdefault('conditions', []).append(condition_entry)
        else:
            field_info = {
                "entityType": entity_type,
                "uri": predicate,
                "nodeShape": nodeShape,
                "datatypes": [datatype] if datatype else [],
                "min": minCount,
                "max": maxCount,
                "hasValue": hasValue,
                "objectClass": objectClass,
                "optionalValues": optionalValues,
                "conditions": [condition_entry] if condition_entry else []
            }
            form_fields[entity_type][predicate].append(field_info)

    return form_fields

def process_nested_shapes(shape_uri, depth=0, processed_shapes=None):
    """
    Processa ricorsivamente le shape annidate.

    Argomenti:
        shape_uri (str): L'URI della shape da processare.
        depth (int): La profondità corrente della ricorsione.
        processed_shapes (set): Un insieme delle shape già processate.

    Restituisce:
        list: Una lista di dizionari dei campi annidati.
    """
    if processed_shapes is None:
        processed_shapes = set()

    if depth > 5 or shape_uri in processed_shapes:
        return [{"_reference": shape_uri}]
    
    processed_shapes.add(shape_uri)

    nested_query = prepareQuery("""
        SELECT ?type ?predicate ?nodeShape ?datatype ?maxCount ?minCount ?hasValue ?objectClass ?conditionPath ?conditionValue ?pattern ?message
        (GROUP_CONCAT(?optionalValue; separator=",") AS ?optionalValues)
        WHERE {
            ?shape sh:targetClass ?type ;
                   sh:property ?property .
            ?property sh:path ?predicate .
            OPTIONAL {
                ?property sh:node ?nodeShape .
                OPTIONAL {?nodeShape sh:targetClass ?objectClass .}
            }
            OPTIONAL { ?property sh:datatype ?datatype . }
            OPTIONAL { ?property sh:maxCount ?maxCount . }
            OPTIONAL { ?property sh:minCount ?minCount . }
            OPTIONAL { ?property sh:hasValue ?hasValue . }
            OPTIONAL {
                ?property sh:or ?orList .
                ?orList rdf:rest*/rdf:first ?orConstraint .
                ?orConstraint sh:datatype ?datatype .
            }
            OPTIONAL {
                ?property sh:in ?list .
                ?list rdf:rest*/rdf:first ?optionalValue .
            }
            OPTIONAL {
                ?property sh:condition ?conditionNode .
                ?conditionNode sh:path ?conditionPath ;
                               sh:hasValue ?conditionValue .
            }
            OPTIONAL { ?property sh:pattern ?pattern . }
            OPTIONAL { ?property sh:message ?message . }
            FILTER (isURI(?predicate))
        }
        GROUP BY ?type ?predicate ?nodeShape ?datatype ?maxCount ?minCount ?hasValue ?objectClass ?conditionPath ?conditionValue ?pattern ?message
    """, initNs={"sh": "http://www.w3.org/ns/shacl#", "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"})

    nested_results = shacl.query(nested_query, initBindings={'shape': URIRef(shape_uri)})

    nested_fields = []
    entity_type = None

    for row in nested_results:
        if str(row.predicate) == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" and not row.optionalValues:
            continue

        predicate = str(row.predicate)
        nodeShape = str(row.nodeShape) if row.nodeShape else None
        hasValue = str(row.hasValue) if row.hasValue else None
        objectClass = str(row.objectClass) if row.objectClass else None
        minCount = 0 if row.minCount is None else int(row.minCount)
        maxCount = None if row.maxCount is None else int(row.maxCount)
        datatype = str(row.datatype) if row.datatype else None
        optionalValues = row.optionalValues.split(",") if row.optionalValues else []

        condition_entry = {}
        if row.conditionPath and row.conditionValue:
            condition_entry['condition'] = {
                "path": str(row.conditionPath),
                "value": str(row.conditionValue)
            }
        if row.pattern:
            condition_entry['pattern'] = str(row.pattern)
        if row.message:
            condition_entry['message'] = str(row.message)

        if row.type:
            entity_type = str(row.type)

        # Cerca un campo esistente con gli stessi attributi (eccetto datatype)
        existing_field = None
        for field in nested_fields:
            if (field['uri'] == predicate and
                field['nodeShape'] == nodeShape and
                field['hasValue'] == hasValue and
                field['objectClass'] == objectClass and
                field['min'] == minCount and
                field['max'] == maxCount and
                field['optionalValues'] == optionalValues):
                existing_field = field
                break

        if existing_field:
            # Aggiorna la lista dei datatypes
            if row.datatype and str(row.datatype) not in existing_field["datatypes"]:
                existing_field["datatypes"].append(str(row.datatype))
            if condition_entry:
                existing_field.setdefault('conditions', []).append(condition_entry)
        else:
            field_info = {
                "entityType": entity_type,
                "uri": predicate,
                "nodeShape": nodeShape,
                "datatypes": [datatype] if datatype else [],
                "min": minCount,
                "max": maxCount,
                "hasValue": hasValue,
                "objectClass": objectClass,
                "optionalValues": optionalValues,
                "conditions": [condition_entry] if condition_entry else []
            }
            if nodeShape:
                field_info["nestedShape"] = process_nested_shapes(nodeShape, depth + 1, processed_shapes)
            nested_fields.append(field_info)

    # Ottieni l'ordine delle proprietà dalle regole di visualizzazione
    property_order = get_property_order(entity_type)

    # Ordina i campi se l'ordine delle proprietà è disponibile
    if property_order:
        nested_fields = order_fields(nested_fields, property_order)

    processed_shapes.remove(shape_uri)
    return nested_fields

def get_property_order(entity_type):
    """
    Recupera l'ordine delle proprietà per un tipo di entità dalle regole di visualizzazione.

    Argomenti:
        entity_type (str): L'URI del tipo di entità.

    Restituisce:
        list: Una lista di URI di proprietà nell'ordine desiderato.
    """
    if display_rules:
        for rule in display_rules:
            if rule['class'] == entity_type:
                return [prop['property'] for prop in rule.get('displayProperties', [])]
    return []

def order_fields(fields, property_order):
    """
    Ordina i campi secondo l'ordine specificato delle proprietà.

    Argomenti:
        fields (list): Una lista di dizionari dei campi da ordinare.
        property_order (list): Una lista di URI di proprietà nell'ordine desiderato.

    Restituisce:
        list: Una lista ordinata di dizionari dei campi.
    """
    ordered_fields = []
    field_dict = {field['uri']: field for field in fields}
    
    for prop in property_order:
        if prop in field_dict:
            ordered_fields.append(field_dict[prop])
            del field_dict[prop]
    
    # Aggiungi eventuali campi rimanenti non specificati nell'ordine
    ordered_fields.extend(field_dict.values())
    
    return ordered_fields

def apply_display_rules(form_fields):
    """
    Applica le regole di visualizzazione ai campi del form.

    Argomenti:
        form_fields (dict): I campi del form iniziali estratti dalle shape SHACL.

    Restituisce:
        dict: I campi del form dopo aver applicato le regole di visualizzazione.
    """
    for rule in display_rules:
        entity_class = rule.get('class')
        if entity_class and entity_class in form_fields:
            for prop in rule.get('displayProperties', []):
                prop_uri = prop['property']
                if prop_uri in form_fields[entity_class]:
                    for field_info in form_fields[entity_class][prop_uri]:
                        add_display_information(field_info, prop)
                        # Chiamata ricorsiva per le nestedShape
                        if 'nestedShape' in field_info:
                            apply_display_rules_to_nested_shapes(field_info['nestedShape'], prop)
                        if 'intermediateRelation' in prop:
                            handle_intermediate_relation(form_fields, field_info, prop)
                    if 'displayRules' in prop:
                        handle_sub_display_rules(form_fields, entity_class, form_fields[entity_class][prop_uri], prop)
    return form_fields

def apply_display_rules_to_nested_shapes(nested_fields, parent_prop):
    for field_info in nested_fields:
        # Trova la regola di visualizzazione corrispondente
        matching_rule = None
        for rule in display_rules:
            if rule.get('class') == field_info.get('entityType'):
                for prop in rule.get('displayProperties', []):
                    if prop['property'] == field_info['uri']:
                        matching_rule = prop
                        break
        if matching_rule:
            add_display_information(field_info, matching_rule)
        else:
            # Usa il displayName del parent se non c'è una regola specifica
            if 'displayName' in parent_prop and 'displayName' not in field_info:
                field_info['displayName'] = parent_prop['displayName']
        # Chiamata ricorsiva se ci sono altre nestedShape
        if 'nestedShape' in field_info:
            apply_display_rules_to_nested_shapes(field_info['nestedShape'], field_info)

def add_display_information(field_info, prop):
    """
    Aggiunge informazioni di visualizzazione dal display_rules ad un campo.

    Argomenti:
        field_info (dict): Le informazioni del campo da aggiornare.
        prop (dict): Le informazioni della proprietà dalle display_rules.
    """
    if 'displayName' in prop:
        field_info['displayName'] = prop['displayName']
    if 'shouldBeDisplayed' in prop:
        field_info['shouldBeDisplayed'] = prop.get('shouldBeDisplayed', True)
    if 'orderedBy' in prop:
        field_info['orderedBy'] = prop['orderedBy']

def handle_intermediate_relation(form_fields, field_info, prop):
    """
    Processa 'intermediateRelation' nelle display_rules e aggiorna il campo.

    Argomenti:
        field_info (dict): Le informazioni del campo da aggiornare.
        prop (dict): Le informazioni della proprietà dalle display_rules.
    """
    intermediate_relation = prop['intermediateRelation']
    target_entity_type = intermediate_relation.get('targetEntityType')
    intermediate_class = intermediate_relation.get('class')

    # Query SPARQL per trovare la proprietà collegante
    connecting_property_query = prepareQuery("""
        SELECT ?property
        WHERE {
            ?shape sh:targetClass ?intermediateClass ;
                   sh:property ?propertyShape .
            ?propertyShape sh:path ?property ;
                           sh:node ?targetNode .
            ?targetNode sh:targetClass ?targetClass.
        }
    """, initNs={"sh": "http://www.w3.org/ns/shacl#"})
    
    connecting_property_results = shacl.query(connecting_property_query, initBindings={
        'intermediateClass': URIRef(intermediate_class),
        'targetClass': URIRef(target_entity_type)
    })
    
    connecting_property = next((str(row.property) for row in connecting_property_results), None)

    field_info['intermediateRelation'] = {
        "class": intermediate_class,
        "targetEntityType": target_entity_type,
        "connectingProperty": connecting_property,
        "properties": form_fields.get(target_entity_type, {}),
    }

def handle_sub_display_rules(form_fields, entity_class, field_info_list, prop):
    """
    Gestisce 'displayRules' nelle display_rules, applicando la regola corretta in base allo shape.

    Argomenti:
        form_fields (dict): I campi del form da aggiornare.
        entity_class (str): La classe dell'entità.
        field_info_list (list): Le informazioni del campo originale.
        prop (dict): Le informazioni della proprietà dalle display_rules.
    """
    new_field_info_list = []

    for original_field in field_info_list:
        # Trova la display rule corrispondente allo shape del campo
        matching_rule = next((rule for rule in prop['displayRules'] if rule['shape'] == original_field['nodeShape']), None)

        if matching_rule:
            new_field = {
                "entityType": entity_class,
                "objectClass": original_field.get("objectClass"),
                "uri": prop['property'],
                "datatype": original_field.get("datatype"),
                "min": original_field.get("min"),
                "max": original_field.get("max"),
                "hasValue": original_field.get("hasValue"),
                "nodeShape": original_field.get("nodeShape"),
                "nestedShape": original_field.get("nestedShape"),
                "displayName": matching_rule['displayName'],
                "optionalValues": original_field.get("optionalValues", []),
                "orderedBy": original_field.get('orderedBy')
            }

            if 'intermediateRelation' in original_field:
                new_field['intermediateRelation'] = original_field['intermediateRelation']

            # Aggiungi proprietà aggiuntive dalla shape SHACL
            if 'shape' in matching_rule:
                shape_uri = matching_rule['shape']
                additional_properties = extract_additional_properties(shape_uri)
                if additional_properties:
                    new_field['additionalProperties'] = additional_properties

            new_field_info_list.append(new_field)
        else:
            # Se non c'è una regola corrispondente, mantieni il campo originale
            new_field_info_list.append(original_field)

    form_fields[entity_class][prop['property']] = new_field_info_list

def extract_additional_properties(shape_uri):
    """
    Estrae proprietà aggiuntive da una shape SHACL.

    Argomenti:
        shape_uri (str): L'URI della shape SHACL.

    Restituisce:
        dict: Un dizionario delle proprietà aggiuntive.
    """
    additional_properties_query = prepareQuery("""
        SELECT ?predicate ?hasValue
        WHERE {
            ?shape a sh:NodeShape ;
                   sh:property ?property .
            ?property sh:path ?predicate ;
                     sh:hasValue ?hasValue .
        }
    """, initNs={"sh": "http://www.w3.org/ns/shacl#"})

    additional_properties_results = shacl.query(additional_properties_query, initBindings={
        'shape': URIRef(shape_uri)
    })

    additional_properties = {}
    for row in additional_properties_results:
        predicate = str(row.predicate)
        has_value = str(row.hasValue)
        additional_properties[predicate] = has_value

    return additional_properties

def order_form_fields(form_fields):
    """
    Ordina i campi del form secondo le regole di visualizzazione.

    Argomenti:
        form_fields (dict): I campi del form con possibili modifiche dalle regole di visualizzazione.

    Restituisce:
        OrderedDict: I campi del form ordinati.
    """
    ordered_form_fields = OrderedDict()
    if display_rules:
        for rule in display_rules:
            entity_class = rule.get('class')
            if entity_class and entity_class in form_fields:
                ordered_properties = [prop_rule['property'] for prop_rule in rule.get('displayProperties', [])]
                ordered_form_fields[entity_class] = OrderedDict()
                for prop in ordered_properties:
                    if prop in form_fields[entity_class]:
                        ordered_form_fields[entity_class][prop] = form_fields[entity_class][prop]
                # Aggiungi le proprietà rimanenti non specificate nell'ordine
                for prop in form_fields[entity_class]:
                    if prop not in ordered_properties:
                        ordered_form_fields[entity_class][prop] = form_fields[entity_class][prop]
    else:
        ordered_form_fields = form_fields
    return ordered_form_fields

def execute_sparql_query(query: str, subject: str, value: str) -> Tuple[str, str]:
    query = query.replace('[[subject]]', f'<{subject}>')
    query = query.replace('[[value]]', f'<{value}>')
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert().get("results", {}).get("bindings", [])
    if results:
        parsed_query = parseQuery(query)
        algebra_query = translateQuery(parsed_query).algebra
        variable_order = algebra_query['PV']
        result = results[0]
        values = [result.get(str(var_name), {}).get("value", None) for var_name in variable_order]
        first_value = values[0] if len(values) > 0 else None
        second_value = values[1] if len(values) > 1 else None
        return (first_value, second_value)
    return None, None

@app.cli.group()
def translate():
    """Translation and localization commands."""
    pass

@translate.command()
def update():
    """Update all languages."""
    if os.system('pybabel extract -F babel/babel.cfg -k lazy_gettext -o babel/messages.pot .'):
        raise RuntimeError('extract command failed')
    if os.system('pybabel update -i babel/messages.pot -d babel/translations'):
        raise RuntimeError('update command failed')
    os.remove('babel/messages.pot')

@translate.command()
def compile():
    """Compile all languages."""
    if os.system('pybabel compile -d babel/translations'):
        raise RuntimeError('compile command failed')

@translate.command()
@click.argument('lang')
def init(lang):
    """Initialize a new language."""
    if os.system('pybabel extract -F babel/babel.cfg -k _l -o messages.pot .'):
        raise RuntimeError('extract command failed')
    if os.system(
            'pybabel init -i messages.pot -d babel/translations -l ' + lang):
        raise RuntimeError('init command failed')
    os.remove('messages.pot')

def get_locale():
    return session.get('lang', 'en')

babel.init_app(app=app, locale_selector=get_locale, default_translation_directories=app.config['BABEL_TRANSLATION_DIRECTORIES'])
