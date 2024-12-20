import copy
import json
import os
import traceback
import urllib
from collections import OrderedDict, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from urllib.parse import unquote, urlparse, urlunparse

import click
import docker
import requests
import validators
import yaml
from config import Config, OrphanHandlingStrategy
from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_babel import Babel, gettext, refresh
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user, user_loaded_from_cookie)
from heritrace.editor import Editor
from heritrace.entity_sorter import *
from heritrace.filters import *
from heritrace.forms import *
from heritrace.get_info_from_shacl import get_form_fields_from_shacl
from heritrace.models import User
from heritrace.resource_lock_manager import LockStatus, ResourceLockManager
from heritrace.uri_generator.uri_generator import *
from rdflib import RDF, XSD, ConjunctiveGraph, Graph, Literal, URIRef
from rdflib.namespace import XSD
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.algebra import translateQuery, translateUpdate
from rdflib.plugins.sparql.parser import parseQuery, parseUpdate
from redis import Redis
from requests_oauthlib import OAuth2Session
from resources.datatypes import DATATYPE_MAPPING
from SPARQLWrapper import JSON, XML, SPARQLWrapper
from time_agnostic_library.agnostic_entity import AgnosticEntity
from time_agnostic_library.prov_entity import ProvEntity
from time_agnostic_library.support import generate_config_file

app = Flask(__name__)

app.config.from_object(Config)

babel = Babel()


with open("resources/context.json", "r") as config_file:
    context = json.load(config_file)["@context"]

display_rules_path = app.config["DISPLAY_RULES_PATH"]
display_rules = None
if display_rules_path:
    with open(display_rules_path, 'r') as f:
        display_rules: List[dict] = yaml.safe_load(f)['classes']

class_priorities = {}
if display_rules:
    for rule in display_rules:
        cls = rule['class']
        priority = rule.get('priority', 0)
        class_priorities[cls] = priority

shacl_path = app.config["SHACL_PATH"]
shacl = None
if shacl_path:
    if os.path.exists(shacl_path):
        shacl = Graph()
        shacl.parse(source=app.config["SHACL_PATH"], format="turtle")

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

form_fields_cache = None

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

def running_in_docker():
    return os.path.exists('/.dockerenv')

def adjust_endpoint_url(url):
    """
    Adjust endpoint URLs to work properly within Docker containers by replacing local address patterns
    with host.docker.internal.
    
    Args:
        url (str): The endpoint URL to adjust
        
    Returns:
        str: The adjusted URL if running in Docker, original URL otherwise
    """
    if not running_in_docker():
        return url
        
    local_patterns = [
        'localhost',
        '127.0.0.1',
        '0.0.0.0'
    ]
    
    parsed_url = urlparse(url)
    
    if any(pattern in parsed_url.netloc for pattern in local_patterns):
        netloc_parts = parsed_url.netloc.split(':')
        if len(netloc_parts) > 1:
            new_netloc = f'host.docker.internal:{netloc_parts[1]}'
        else:
            new_netloc = 'host.docker.internal'
            
        url_parts = list(parsed_url)
        url_parts[1] = new_netloc
        return urlunparse(url_parts)
        
    return url

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

def initialize_form_fields():
    """Initialize the form fields cache at application startup."""
    global form_fields_cache
    if shacl and form_fields_cache is None:
        form_fields_cache = get_form_fields_from_shacl(shacl, display_rules)

def get_cached_form_fields():
    """Get form fields from cache, initializing if necessary."""
    global form_fields_cache
    if form_fields_cache is None:
        initialize_form_fields()
    return form_fields_cache

def initialize_change_tracking_config(adjusted_dataset_endpoint=None, adjusted_provenance_endpoint=None):
    """
    Initialize and return the change tracking configuration JSON.
    Uses pre-adjusted endpoints if provided to avoid redundant adjustments.
    
    Args:
        adjusted_dataset_endpoint: Dataset endpoint URL already adjusted for Docker
        adjusted_provenance_endpoint: Provenance endpoint URL already adjusted for Docker
    
    Returns:
        dict: The loaded configuration dictionary
    """
    config_needs_generation = False
    config_path = None
    config = None

    # Check if we have a config path in app.config
    if 'CHANGE_TRACKING_CONFIG' in app.config:
        config_path = app.config['CHANGE_TRACKING_CONFIG']
        if not os.path.exists(config_path):
            app.logger.warning(f"Change tracking configuration file not found at specified path: {config_path}")
            config_needs_generation = True
    else:
        config_needs_generation = True
        config_path = os.path.join(app.instance_path, 'change_tracking_config.json')
        os.makedirs(app.instance_path, exist_ok=True)

    if config_needs_generation:
        # Usa gli endpoint già aggiustati se disponibili
        dataset_urls = [adjusted_dataset_endpoint] if adjusted_dataset_endpoint else []
        provenance_urls = [adjusted_provenance_endpoint] if adjusted_provenance_endpoint else []
        
        # Aggiusta solo gli endpoint della cache dato che gli altri sono già stati aggiustati
        cache_endpoint = adjust_endpoint_url(app.config.get('CACHE_ENDPOINT', ''))
        cache_update_endpoint = adjust_endpoint_url(app.config.get('CACHE_UPDATE_ENDPOINT', ''))
        
        db_triplestore = app.config.get('DATASET_DB_TRIPLESTORE', '').lower()
        text_index_enabled = app.config.get('DATASET_DB_TEXT_INDEX_ENABLED', False)
        
        blazegraph_search = db_triplestore == 'blazegraph' and text_index_enabled
        fuseki_search = db_triplestore == 'fuseki' and text_index_enabled
        virtuoso_search = db_triplestore == 'virtuoso' and text_index_enabled
        
        graphdb_connector = ''
        if db_triplestore == 'graphdb' and text_index_enabled:
            graphdb_connector = app.config.get('GRAPHDB_CONNECTOR_NAME', '')
        
        try:
            config = generate_config_file(
                config_path=config_path,
                dataset_urls=dataset_urls,
                dataset_dirs=app.config.get('DATASET_DIRS', []),
                dataset_is_quadstore=app.config.get('DATASET_IS_QUADSTORE', False),
                provenance_urls=provenance_urls,
                provenance_is_quadstore=app.config.get('PROVENANCE_IS_QUADSTORE', False),
                provenance_dirs=app.config.get('PROVENANCE_DIRS', []),
                blazegraph_full_text_search=blazegraph_search,
                fuseki_full_text_search=fuseki_search,
                virtuoso_full_text_search=virtuoso_search,
                graphdb_connector_name=graphdb_connector,
                cache_endpoint=cache_endpoint,
                cache_update_endpoint=cache_update_endpoint
            )
            app.logger.info(f"Generated new change tracking configuration at: {config_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to generate change tracking configuration: {str(e)}")

    # Load and validate the configuration
    try:
        if not config:
            with open(config_path, 'r', encoding='utf8') as f:
                config = json.load(f)
            
        # Aggiusta solo gli URL della cache nel config caricato se necessario
        if config['cache_triplestore_url'].get('endpoint'):
            config['cache_triplestore_url']['endpoint'] = adjust_endpoint_url(
                config['cache_triplestore_url']['endpoint']
            )
            
        if config['cache_triplestore_url'].get('update_endpoint'):
            config['cache_triplestore_url']['update_endpoint'] = adjust_endpoint_url(
                config['cache_triplestore_url']['update_endpoint']
            )
            
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid change tracking configuration JSON at {config_path}: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Error reading change tracking configuration at {config_path}: {str(e)}")

    # Update app config with the path
    app.config['CHANGE_TRACKING_CONFIG'] = config_path
    return config

def initialize_app():
    global initialization_done, dataset_endpoint, provenance_endpoint, sparql, provenance_sparql, change_tracking_config
    
    if not initialization_done:
        dataset_endpoint = adjust_endpoint_url(Config.DATASET_DB_URL)
        provenance_endpoint = adjust_endpoint_url(Config.PROVENANCE_DB_URL)

        change_tracking_config = initialize_change_tracking_config(
            adjusted_dataset_endpoint=dataset_endpoint,
            adjusted_provenance_endpoint=provenance_endpoint
        )
        
        sparql = SPARQLWrapper(dataset_endpoint)
        provenance_sparql = SPARQLWrapper(provenance_endpoint)

        initialize_counter_handler()
        initialize_form_fields()
        initialization_done = True

initialize_app()

custom_filter = Filter(context, display_rules, dataset_endpoint)

app.jinja_env.filters['human_readable_predicate'] = custom_filter.human_readable_predicate
app.jinja_env.filters['human_readable_entity'] = custom_filter.human_readable_entity
app.jinja_env.filters['human_readable_primary_source'] = custom_filter.human_readable_primary_source
app.jinja_env.filters['format_datetime'] = custom_filter.human_readable_datetime
app.jinja_env.filters['split_ns'] = custom_filter.split_ns
app.jinja_env.filters['format_source_reference'] = custom_filter.format_source_reference
app.jinja_env.filters['format_agent_reference'] = custom_filter.format_agent_reference

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

def unauthorized_callback():
    return redirect(url_for('login_page'))

login_manager.unauthorized_handler(unauthorized_callback)

@login_manager.user_loader
def load_user(user_id):
    user_name = session.get('user_name', 'Unknown User')
    return User(id=user_id, name=user_name, orcid=user_id)

@user_loaded_from_cookie.connect
def rotate_session_token(sender, user):
    session.modified = True

redis_client = Redis.from_url('redis://redis:6379', decode_responses=True)

@app.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('catalogue'))

    callback_url = url_for('callback', _external=True, _scheme='https')
    orcid = OAuth2Session(
        app.config['ORCID_CLIENT_ID'],
        redirect_uri=callback_url,
        scope=[app.config['ORCID_SCOPE'], 'openid']
    )
    authorization_url, state = orcid.authorization_url(
        app.config['ORCID_AUTHORIZE_URL'],
        prompt='login',  # Forza il re-login
        nonce=os.urandom(16).hex()  # Aggiungiamo un nonce per sicurezza
    )
    session['oauth_state'] = state
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    if request.url.startswith('http://'):
        secure_url = request.url.replace('http://', 'https://', 1)
    else:
        secure_url = request.url

    orcid = OAuth2Session(app.config['ORCID_CLIENT_ID'], state=session['oauth_state'])
    try:
        token = orcid.fetch_token(app.config['ORCID_TOKEN_URL'], client_secret=app.config['ORCID_CLIENT_SECRET'],
                                  authorization_response=secure_url)
    except Exception as e:
        flash(gettext('An error occurred during authentication. Please try again'), 'danger')
        return redirect(url_for('login'))
    orcid_id = token['orcid']
    
    if orcid_id not in app.config['ORCID_WHITELIST']:
        flash(gettext('Your ORCID is not authorized to access this application'), 'danger')
        return redirect(url_for('login'))
    session['user_name'] = token['name']
    user = User(id=orcid_id, name=token['name'], orcid=orcid_id)
    session.permanent = True
    app.permanent_session_lifetime = timedelta(days=30)
    login_user(user)
    flash(gettext('Welcome back %(name)s!', name=current_user.name), 'success')
    return redirect(url_for('catalogue'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash(gettext('You have been logged out'), 'info')
    return redirect(url_for('index'))

@app.route('/login')
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('login.jinja')

def get_highest_priority_class(subject_classes):
    max_priority = None
    highest_priority_class = None
    for cls in subject_classes:
        priority = class_priorities.get(str(cls), 0)
        if max_priority is None or priority < max_priority:
            max_priority = priority
            highest_priority_class = cls
    return highest_priority_class

def get_datatype_label(datatype_uri):
    for dt_uri, _, dt_label in DATATYPE_MAPPING:
        if str(dt_uri) == str(datatype_uri):
            return dt_label
    return custom_filter.human_readable_predicate(datatype_uri, [])

@app.route('/')
def index():
    return render_template('index.jinja')

def get_entities_for_class(selected_class, page, per_page, sort_property=None, sort_direction='ASC'):
    """
    Retrieve entities for a specific class with pagination and sorting.
    
    Args:
        selected_class (str): URI of the class to fetch entities for
        page (int): Current page number
        per_page (int): Number of items per page
        sort_property (str, optional): Property to sort by
        sort_direction (str, optional): Sort direction ('ASC' or 'DESC')
        
    Returns:
        tuple: (list of entities, total count)
    """
    offset = (page - 1) * per_page

    # Build sort clause if sort property is provided
    sort_clause = ""
    order_clause = "ORDER BY ?subject"
    if sort_property:
        sort_clause = build_sort_clause(sort_property, selected_class, display_rules)
        order_clause = f"ORDER BY {sort_direction}(?sortValue)"

    # Build query based on database type
    if is_virtuoso():
        entities_query = f"""
        SELECT DISTINCT ?subject {f"?sortValue" if sort_property else ""}
        WHERE {{
            GRAPH ?g {{
                ?subject a <{selected_class}> .
                {sort_clause}
            }}
            FILTER(?g NOT IN (<{'>, <'.join(VIRTUOSO_EXCLUDED_GRAPHS)}>))
        }}
        {order_clause}
        LIMIT {per_page} 
        OFFSET {offset}
        """
        
        # Count query for total number of entities
        count_query = f"""
        SELECT (COUNT(DISTINCT ?subject) as ?count)
        WHERE {{
            GRAPH ?g {{
                ?subject a <{selected_class}> .
            }}
            FILTER(?g NOT IN (<{'>, <'.join(VIRTUOSO_EXCLUDED_GRAPHS)}>))
        }}
        """
    else:
        entities_query = f"""
        SELECT DISTINCT ?subject {f"?sortValue" if sort_property else ""}
        WHERE {{
            ?subject a <{selected_class}> .
            {sort_clause}
        }}
        {order_clause}
        LIMIT {per_page} 
        OFFSET {offset}
        """
        
        count_query = f"""
        SELECT (COUNT(DISTINCT ?subject) as ?count)
        WHERE {{
            ?subject a <{selected_class}> .
        }}
        """

    # Execute count query
    sparql.setQuery(count_query)
    sparql.setReturnFormat(JSON)
    count_results = sparql.query().convert()
    total_count = int(count_results["results"]["bindings"][0]["count"]["value"])

    # Execute entities query
    sparql.setQuery(entities_query)
    entities_results = sparql.query().convert()
    
    entities = []
    for result in entities_results["results"]["bindings"]:
        subject_uri = result['subject']['value']
        entity_label = custom_filter.human_readable_entity(subject_uri, [selected_class])
        
        entities.append({
            'uri': subject_uri,
            'label': entity_label
        })

    return entities, total_count

def get_available_classes():
    """
    Fetch and format all available entity classes from the triplestore.
    
    Returns:
        list: List of dictionaries containing class information
    """
    if is_virtuoso():
        classes_query = f"""
            SELECT DISTINCT ?class (COUNT(DISTINCT ?subject) as ?count)
            WHERE {{
                GRAPH ?g {{
                    ?subject a ?class .
                }}
                FILTER(?g NOT IN (<{'>, <'.join(VIRTUOSO_EXCLUDED_GRAPHS)}>))
            }}
            GROUP BY ?class
            ORDER BY DESC(?count)
        """
    else:
        classes_query = """
            SELECT DISTINCT ?class (COUNT(DISTINCT ?subject) as ?count)
            WHERE {
                ?subject a ?class .
            }
            GROUP BY ?class
            ORDER BY DESC(?count)
        """
    
    sparql.setQuery(classes_query)
    sparql.setReturnFormat(JSON)
    classes_results = sparql.query().convert()

    available_classes = [
        {
            'uri': result['class']['value'],
            'label': custom_filter.human_readable_predicate(result['class']['value'], [result['class']['value']]),
            'count': int(result['count']['value'])
        }
        for result in classes_results["results"]["bindings"]
        if is_entity_type_visible(result['class']['value'])
    ]

    # Sort classes by label
    available_classes.sort(key=lambda x: x['label'].lower())
    return available_classes

def get_catalog_data(selected_class, page, per_page, sort_property=None, sort_direction='ASC'):
    """
    Get catalog data with pagination and sorting.
    
    Args:
        selected_class (str): Selected class URI
        page (int): Current page number
        per_page (int): Items per page
        sort_property (str, optional): Property to sort by
        sort_direction (str, optional): Sort direction ('ASC' or 'DESC')
        
    Returns:
        dict: Catalog data including entities, pagination info, and sort settings
    """
    entities = []
    total_count = 0
    sortable_properties = []

    if selected_class:
        entities, total_count = get_entities_for_class(
            selected_class, 
            page, 
            per_page,
            sort_property,
            sort_direction
        )
        
        # Get sortable properties for the class
        sortable_properties = get_sortable_properties(selected_class, display_rules, form_fields_cache)

    if not sort_property and sortable_properties:
        sort_property = sortable_properties[0]['property']

    return {
        'entities': entities,
        'total_pages': (total_count + per_page - 1) // per_page if total_count > 0 else 0,
        'current_page': page,
        'per_page': per_page,
        'total_count': total_count,
        'sort_property': sort_property,
        'sort_direction': sort_direction,
        'sortable_properties': sortable_properties,
        'selected_class': selected_class
    }

@app.route('/catalogue')
@login_required
def catalogue():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    selected_class = request.args.get('class')
    sort_property = request.args.get('sort_property')
    sort_direction = request.args.get('sort_direction', 'ASC')

    available_classes = get_available_classes()
    
    if not selected_class and available_classes:
        selected_class = available_classes[0]['uri']
    
    catalog_data = get_catalog_data(
        selected_class,
        page,
        per_page,
        sort_property,
        sort_direction
    )

    return render_template('catalogue.jinja',
                         available_classes=available_classes,
                         selected_class=selected_class,
                         page=page,
                         total_entity_pages=catalog_data['total_pages'],
                         per_page=per_page,
                         allowed_per_page=[50, 100, 200, 500],
                         sortable_properties=json.dumps(catalog_data['sortable_properties']),
                         current_sort_property=None,
                         current_sort_direction='ASC',
                         initial_entities=catalog_data['entities'])

@app.route('/api/catalogue')
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

def is_entity_type_visible(entity_type):
    for rule in display_rules:
        if rule['class'] == entity_type:
            return rule.get('shouldBeDisplayed', True)
    return True

@app.route('/time-vault')
@login_required
def time_vault():
    """
    Render the Time Vault page, which displays a list of deleted entities.
    """
    initial_page = request.args.get('page', 1, type=int)
    initial_per_page = request.args.get('per_page', 50, type=int)
    sort_property = request.args.get('sort_property', 'deletionTime')
    sort_direction = request.args.get('sort_direction', 'DESC')
    selected_class = request.args.get('class')

    allowed_per_page = [50, 100, 200, 500]


    initial_entities, available_classes, selected_class, _ = get_deleted_entities_with_filtering(
        initial_page, initial_per_page, sort_property, sort_direction, selected_class)

    sortable_properties = [{'property': 'deletionTime', 'displayName': 'Deletion Time', 'sortType': 'date'}]
    sortable_properties.extend(get_sortable_properties(selected_class, display_rules, form_fields_cache))
    sortable_properties = json.dumps(sortable_properties)

    return render_template('time_vault.jinja',
                           available_classes=available_classes,
                           selected_class=selected_class,
                           page=initial_page,
                           total_entity_pages=0,
                           per_page=initial_per_page,
                           allowed_per_page=allowed_per_page,
                           sortable_properties=sortable_properties,
                           current_sort_property=sort_property,
                           current_sort_direction=sort_direction,
                           initial_entities=initial_entities)

@app.route('/api/time-vault')
@login_required
def get_deleted_entities():
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
        page, per_page, sort_property, sort_direction, selected_class)

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

def get_deleted_entities_with_filtering(page=1, per_page=50, sort_property='deletionTime', sort_direction='DESC',
                                        selected_class=None):
    """
    Fetch and process deleted entities from the provenance graph, with filtering and sorting.
    """
    sortable_properties = [{'property': 'deletionTime', 'displayName': 'Deletion Time', 'sortType': 'date'}]

    if selected_class:
        sortable_properties.extend(get_sortable_properties(selected_class, display_rules, form_fields_cache))

    prov_query = """
    SELECT DISTINCT ?entity ?lastSnapshot ?deletionTime ?agent ?lastValidSnapshotTime
    WHERE {
        ?lastSnapshot a <http://www.w3.org/ns/prov#Entity> ;
                     <http://www.w3.org/ns/prov#specializationOf> ?entity ;
                     <http://www.w3.org/ns/prov#generatedAtTime> ?deletionTime ;
                     <http://www.w3.org/ns/prov#invalidatedAtTime> ?invalidationTime ;
                     <http://www.w3.org/ns/prov#wasDerivedFrom> ?lastValidSnapshot.

        ?lastValidSnapshot <http://www.w3.org/ns/prov#generatedAtTime> ?lastValidSnapshotTime .

        OPTIONAL { ?lastSnapshot <http://www.w3.org/ns/prov#wasAttributedTo> ?agent . }

        FILTER NOT EXISTS {
            ?laterSnapshot <http://www.w3.org/ns/prov#wasDerivedFrom> ?lastSnapshot .
        }
    }
    """
    provenance_sparql.setQuery(prov_query)
    provenance_sparql.setReturnFormat(JSON)
    prov_results = provenance_sparql.query().convert()

    results_bindings = prov_results["results"]["bindings"]
    if not results_bindings:
        return [], [], None, []

    # Process entities with parallel execution
    deleted_entities = []
    max_workers = max(1, min(32, len(results_bindings)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_entity = {
            executor.submit(process_deleted_entity, result, sortable_properties): result
            for result in results_bindings
        }
        for future in as_completed(future_to_entity):
            entity_info = future.result()
            if entity_info is not None:
                deleted_entities.append(entity_info)

    # Calculate class counts from filtered entities
    class_counts = {}
    for entity in deleted_entities:
        for type_uri in entity["entity_types"]:
            class_counts[type_uri] = class_counts.get(type_uri, 0) + 1

    available_classes = [
        {
            'uri': class_uri,
            'label': custom_filter.human_readable_predicate(class_uri, [class_uri]),
            'count': count
        }
        for class_uri, count in class_counts.items()
    ]

    # Determine the sort key based on sort_property
    reverse_sort = (sort_direction.upper() == 'DESC')
    if sort_property == 'deletionTime':
        deleted_entities.sort(key=lambda e: e["deletionTime"], reverse=reverse_sort)
    else:
        deleted_entities.sort(key=lambda e: e['sort_values'].get(sort_property, '').lower(), reverse=reverse_sort)

    # Paginate the results
    offset = (page - 1) * per_page
    paginated_entities = deleted_entities[offset:offset + per_page]

    available_classes.sort(key=lambda x: x['label'].lower())
    if not selected_class and available_classes:
        selected_class = available_classes[0]['uri']

    if selected_class:
        paginated_entities = [entity for entity in paginated_entities if selected_class in entity["entity_types"]]
    else:
        paginated_entities = []

    return paginated_entities, available_classes, selected_class, sortable_properties

def process_deleted_entity(result, sortable_properties):
    """
    Process a single deleted entity, filtering by visible classes.
    """
    entity_uri = result["entity"]["value"]
    last_valid_snapshot_time = result["lastValidSnapshotTime"]["value"]

    # Get entity state at its last valid time
    agnostic_entity = AgnosticEntity(res=entity_uri, config=change_tracking_config, related_entities_history=True)
    state, _, _ = agnostic_entity.get_state_at_time((last_valid_snapshot_time, last_valid_snapshot_time))

    if entity_uri not in state:
        return None

    last_valid_time = convert_to_datetime(last_valid_snapshot_time, stringify=True)
    last_valid_state: ConjunctiveGraph = state[entity_uri][last_valid_time]

    # Get entity types and filter for visible ones early
    entity_types = [str(o) for s, p, o in last_valid_state.triples((URIRef(entity_uri), RDF.type, None))]
    visible_types = [t for t in entity_types if is_entity_type_visible(t)]

    if not visible_types:
        return None

    # Get the highest priority class
    highest_priority_type = get_highest_priority_class(visible_types)
    if not highest_priority_type:
        return None

    # Extract sort values for sortable properties
    sort_values = {}
    for prop in sortable_properties:
        prop_uri = prop['property']
        values = [str(o) for s, p, o in last_valid_state.triples((URIRef(entity_uri), URIRef(prop_uri), None))]
        sort_values[prop_uri] = values[0] if values else ''

    return {
        "uri": entity_uri,
        "deletionTime": result["deletionTime"]["value"],
        "deletedBy": custom_filter.format_agent_reference(result.get("agent", {}).get("value", "")),
        "lastValidSnapshotTime": last_valid_snapshot_time,
        "type": custom_filter.human_readable_predicate(highest_priority_type, [highest_priority_type]),
        "label": custom_filter.human_readable_entity(entity_uri, [highest_priority_type], last_valid_state),
        "entity_types": visible_types,
        "sort_values": sort_values
    }

@app.route('/create-entity', methods=['GET', 'POST'])
@login_required
def create_entity():
    form_fields = get_cached_form_fields()

    entity_types = sorted(
        [entity_type for entity_type in form_fields.keys() if is_entity_type_visible(entity_type)],
        key=lambda et: class_priorities.get(et, 0),
        reverse=True
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

    if request.method == 'POST':
        structured_data = json.loads(request.form.get('structured_data', '{}'))
        validation_errors = validate_entity_data(structured_data, form_fields)

        if validation_errors:
            return jsonify({'status': 'error', 'errors': validation_errors}), 400

        editor = Editor(
            dataset_endpoint,
            provenance_endpoint,
            app.config['COUNTER_HANDLER'],
            URIRef(f'https://orcid.org/{current_user.orcid}'),
            app.config['PRIMARY_SOURCE'],
            app.config['DATASET_GENERATION_TIME']
        )
        
        if shacl:
            entity_type = structured_data.get('entity_type')
            properties = structured_data.get('properties', {})
            
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
                    property_shape = values[0].get('shape')

                # Filter field definitions to find the matching one based on shape
                matching_field_def = None
                for field_def in field_definitions:
                    if property_shape:
                        # If property has a shape, match it with the field definition's subjectShape
                        if field_def.get('subjectShape') == property_shape:
                            matching_field_def = field_def
                            break
                    else:
                        # If no shape specified, use the first field definition without a shape requirement
                        if not field_def.get('subjectShape'):
                            matching_field_def = field_def
                            break
                
                # If no matching field definition found, use the first one (default behavior)
                if not matching_field_def and field_definitions:
                    matching_field_def = field_definitions[0]

                ordered_by = matching_field_def.get('orderedBy') if matching_field_def else None

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
                            if isinstance(value, dict) and 'entity_type' in value:
                                nested_uri = generate_unique_uri(value['entity_type'])
                                editor.create(entity_uri, URIRef(predicate), nested_uri, default_graph_uri)
                                create_nested_entity(editor, nested_uri, value, default_graph_uri, form_fields)
                            else:
                                # If it's a direct URI value (reference to existing entity)
                                nested_uri = URIRef(value)
                                editor.create(entity_uri, URIRef(predicate), nested_uri, default_graph_uri)

                            if previous_entity:
                                editor.create(previous_entity, URIRef(ordered_by), nested_uri, default_graph_uri)
                            previous_entity = nested_uri
                else:
                    # Gestisci le proprietà non ordinate
                    for value in values:
                        if isinstance(value, dict) and 'entity_type' in value:
                            nested_uri = generate_unique_uri(value['entity_type'])
                            editor.create(entity_uri, URIRef(predicate), nested_uri, default_graph_uri)
                            create_nested_entity(editor, nested_uri, value, default_graph_uri, form_fields)
                        else:
                            # Handle both URI references and literal values
                            if validators.url(str(value)):
                                object_value = URIRef(value)
                            else:
                                datatype_uris = []
                                if matching_field_def:
                                    datatype_uris = matching_field_def.get('datatypes', [])
                                datatype = determine_datatype(value, datatype_uris)
                                object_value = Literal(value, datatype=datatype)
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
        datatype_options=datatype_options,
        dataset_db_triplestore=app.config['DATASET_DB_TRIPLESTORE'],
        dataset_db_text_index_enabled=app.config['DATASET_DB_TEXT_INDEX_ENABLED']
    )

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

def validate_entity_data(structured_data, form_fields):
    """
    Validates entity data against form field definitions, considering shape matching.
    
    Args:
        structured_data (dict): Data to validate containing entity_type and properties
        form_fields (dict): Form field definitions from SHACL shapes

    Returns:
        list: List of validation error messages, empty if validation passes
    """
    errors = []
    entity_type = structured_data.get('entity_type')
    if not entity_type:
        errors.append(gettext('Entity type is required'))
    elif entity_type not in form_fields:
        errors.append(gettext('Invalid entity type selected: %(entity_type)s', entity_type=entity_type))

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
                    'Unknown property %(prop_uri)s for entity type %(entity_type)s',
                    prop_uri=prop_uri,
                    entity_type=entity_type
                )
            )
            continue

        if not isinstance(prop_values, list):
            prop_values = [prop_values]

        # Get the shape from the property value if available
        property_shape = None
        if prop_values and isinstance(prop_values[0], dict):
            property_shape = prop_values[0].get('shape')

        # Filter field definitions to find the matching one based on shape
        matching_field_def = None
        for field_def in field_definitions:
            if property_shape:
                # If property has a shape, match it with the field definition's subjectShape
                if field_def.get('subjectShape') == property_shape:
                    matching_field_def = field_def
                    break
            else:
                # If no shape specified, use the first field definition without a shape requirement
                if not field_def.get('subjectShape'):
                    matching_field_def = field_def
                    break
        
        # If no matching field definition found, use the first one (default behavior)
        if not matching_field_def and field_definitions:
            matching_field_def = field_definitions[0]

        if matching_field_def:
            # Validate cardinality
            min_count = matching_field_def.get('min', 0)
            max_count = matching_field_def.get('max', None)
            value_count = len(prop_values)

            if value_count < min_count:
                value = gettext('values') if min_count > 1 else gettext('value')
                errors.append(
                    gettext(
                        'Property %(prop_uri)s requires at least %(min_count)d %(value)s',
                        prop_uri=custom_filter.human_readable_predicate(prop_uri, [entity_type]),
                        min_count=min_count,
                        value=value
                    )
                )
            if max_count is not None and value_count > max_count:
                value = gettext('values') if max_count > 1 else gettext('value')
                errors.append(
                    gettext(
                        'Property %(prop_uri)s allows at most %(max_count)d %(value)s',
                        prop_uri=custom_filter.human_readable_predicate(prop_uri, [entity_type]),
                        max_count=max_count,
                        value=value
                    )
                )

            # Validate mandatory values
            mandatory_values = matching_field_def.get('mandatory_values', [])
            for mandatory_value in mandatory_values:
                if mandatory_value not in prop_values:
                    errors.append(
                        gettext(
                            'Property %(prop_uri)s requires the value %(mandatory_value)s',
                            prop_uri=custom_filter.human_readable_predicate(prop_uri, [entity_type]),
                            mandatory_value=mandatory_value
                        )
                    )

            # Validate each value
            for value in prop_values:
                if isinstance(value, dict) and 'entity_type' in value:
                    nested_errors = validate_entity_data(value, form_fields)
                    errors.extend(nested_errors)
                else:
                    # Validate against datatypes
                    datatypes = matching_field_def.get('datatypes', [])
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
                                    'Value "%(value)s" for property %(prop_uri)s is not of expected type %(expected_types)s',
                                    value=value,
                                    prop_uri=custom_filter.human_readable_predicate(prop_uri, form_fields.keys()),
                                    expected_types=expected_types
                                )
                            )

                    # Validate against optional values
                    optional_values = matching_field_def.get('optionalValues', [])
                    if optional_values and value not in optional_values:
                        acceptable_values = ', '.join(
                            [custom_filter.human_readable_predicate(val, form_fields.keys()) for val in optional_values]
                        )
                        errors.append(
                            gettext(
                                'Value "%(value)s" is not permitted for property %(prop_uri)s. Acceptable values are: %(acceptable_values)s',
                                value=value,
                                prop_uri=custom_filter.human_readable_predicate(prop_uri, form_fields.keys()),
                                acceptable_values=acceptable_values
                            )
                        )

    return errors

def create_nested_entity(editor: Editor, entity_uri, entity_data, graph_uri=None, form_fields=None):
    # Add rdf:type
    editor.create(entity_uri, URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), URIRef(entity_data['entity_type']), graph_uri)

    entity_type = entity_data.get('entity_type')
    properties = entity_data.get('properties', {})

    # Add other properties
    for predicate, values in properties.items():
        if not isinstance(values, list):
            values = [values]
        field_definitions = form_fields.get(entity_type, {}).get(predicate, [])
        for value in values:
            if isinstance(value, dict) and 'entity_type' in value:
                if 'intermediateRelation' in value:
                    intermediate_uri = generate_unique_uri(value['intermediateRelation']['class'])
                    target_uri = generate_unique_uri(value['entity_type'])
                    editor.create(entity_uri, URIRef(predicate), intermediate_uri, graph_uri)
                    editor.create(intermediate_uri, URIRef(value['intermediateRelation']['property']), target_uri, graph_uri)
                    create_nested_entity(editor, target_uri, value, graph_uri, form_fields)
                else:
                    # Handle nested entities
                    nested_uri = generate_unique_uri(value['entity_type'])
                    editor.create(entity_uri, URIRef(predicate), nested_uri, graph_uri)
                    create_nested_entity(editor, nested_uri, value, graph_uri, form_fields)
            else:
                # Handle simple properties
                datatype = XSD.string  # Default to string if not specified
                datatype_uris = []
                if field_definitions:
                    datatype_uris = field_definitions[0].get('datatypes', [])
                datatype = determine_datatype(value, datatype_uris)
                object_value = URIRef(value) if validators.url(value) else Literal(value, datatype=datatype)
                editor.create(entity_uri, URIRef(predicate), object_value, graph_uri)

def generate_unique_uri(entity_type: URIRef|str =None):
    entity_type = str(entity_type)
    uri = Config.URI_GENERATOR.generate_uri(entity_type)
    if hasattr(Config.URI_GENERATOR, 'counter_handler'):
        Config.URI_GENERATOR.counter_handler.increment_counter(entity_type)
    return URIRef(uri)

@app.route('/about/<path:subject>')
@login_required
def about(subject):
    decoded_subject = urllib.parse.unquote(subject)
    agnostic_entity = AgnosticEntity(res=decoded_subject, config=change_tracking_config, related_entities_history=True)
    history, provenance = agnostic_entity.get_history(include_prov_metadata=True)
    
    is_deleted = False
    context_snapshot = None
    subject_classes = []
    
    if history.get(decoded_subject):
        sorted_timestamps = sorted(history[decoded_subject].keys())
        latest_snapshot = history[decoded_subject][sorted_timestamps[-1]]
        latest_metadata = next(
            (meta for _, meta in provenance[decoded_subject].items() 
             if meta['generatedAtTime'] == sorted_timestamps[-1]),
            None
        )

        is_deleted = latest_metadata and 'invalidatedAtTime' in latest_metadata and latest_metadata['invalidatedAtTime']
        
        if is_deleted and len(sorted_timestamps) > 1:
            context_snapshot = history[decoded_subject][sorted_timestamps[-2]]
            subject_classes = [o for _, _, o in context_snapshot.triples((URIRef(decoded_subject), RDF.type, None))]
        else:
            context_snapshot = None
    
    g = Graph()
    grouped_triples = {}
    can_be_added = []
    can_be_deleted = []
    datatypes = {}
    mandatory_values = {}
    optional_values = {}
    valid_predicates = []
    entity_type = None

    if not is_deleted:
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
            value = (Literal(triple['object']['value'], datatype=URIRef(triple['object']['datatype'])) 
                    if triple['object']['type'] == 'literal' and 'datatype' in triple['object'] 
                    else Literal(triple['object']['value'], datatype=XSD.string) 
                    if triple['object']['type'] == 'literal' 
                    else URIRef(triple['object']['value']))
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
    
    form_fields = get_cached_form_fields()
    entity_types = list(form_fields.keys())
    
    predicate_details_map = {}
    for entity_type, predicates in form_fields.items():
        for predicate_uri, details_list in predicates.items():
            for details in details_list:
                shape = details.get('nodeShape')
                key = (predicate_uri, entity_type, shape)
                predicate_details_map[key] = details
    
    entity_type = str(subject_classes[0]) if subject_classes else None
    
    inverse_references = get_inverse_references(decoded_subject)

    return render_template(
        'about.jinja', 
        subject=decoded_subject,
        history=history,
        can_be_added=can_be_added,
        can_be_deleted=can_be_deleted,
        datatypes=datatypes,
        update_form=update_form,
        create_form=create_form,
        mandatory_values=mandatory_values,
        optional_values=optional_values,
        shacl=True if shacl else False,
        grouped_triples=grouped_triples,
        subject_classes=[str(s_class) for s_class in subject_classes],
        display_rules=display_rules,
        form_fields=form_fields,
        entity_types=entity_types,
        entity_type=entity_type,
        predicate_details_map=predicate_details_map,
        dataset_db_triplestore=app.config['DATASET_DB_TRIPLESTORE'],
        dataset_db_text_index_enabled=app.config['DATASET_DB_TEXT_INDEX_ENABLED'],
        inverse_references=inverse_references,
        is_deleted=is_deleted,
        context=context_snapshot
    )

def get_inverse_references(subject_uri):
    if is_virtuoso():
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
        references.append({
            "subject": subject,
            "predicate": predicate,
            "types": types
        })
    
    return references

@app.before_request
def initialize_lock_manager():
    """Initialize the resource lock manager for each request."""
    if not hasattr(g, 'resource_lock'):
        g.resource_lock = ResourceLockManager(redis_client)

@app.teardown_appcontext
def close_redis_connection(error):
    """Close Redis connection when the request context ends."""
    if hasattr(g, 'resource_lock'):
        del g.resource_lock

@app.route('/api/check-lock', methods=['POST'])
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
            
        status, lock_info = g.resource_lock.check_lock_status(resource_uri)
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
        app.logger.error(f"Error in check_lock: {str(e)}")
        return jsonify({
            'status': 'error',
            'title': gettext('Error'),
            'message': gettext('An unexpected error occurred')
        }), 500

@app.route('/api/acquire-lock', methods=['POST'])
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
            
        success = g.resource_lock.acquire_lock(resource_uri)
        
        if success:
            return jsonify({'status': 'success'})
            
        return jsonify({
            'status': 'error',
            'message': gettext('Resource is locked by another user')
        }), 423
        
    except Exception as e:
        app.logger.error(f"Error in acquire_lock: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': gettext('An unexpected error occurred')
        }), 500

@app.route('/api/release-lock', methods=['POST'])
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
            
        success = g.resource_lock.release_lock(resource_uri)
        
        if success:
            return jsonify({'status': 'success'})
            
        return jsonify({
            'status': 'error',
            'message': gettext('Unable to release lock')
        }), 400
        
    except Exception as e:
        app.logger.error(f"Error in release_lock: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': gettext('An unexpected error occurred')
        }), 500

@app.route('/api/renew-lock', methods=['POST'])
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
            
        success = g.resource_lock.acquire_lock(resource_uri)
        
        if success:
            return jsonify({'status': 'success'})
            
        return jsonify({
            'status': 'error',
            'message': gettext('Unable to renew lock')
        }), 423
        
    except Exception as e:
        app.logger.error(f"Error in renew_lock: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': gettext('An unexpected error occurred')
        }), 500

# Funzione per la validazione dinamica dei valori con suggerimento di datatypes
@app.route('/validate-literal', methods=['POST'])
@login_required
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

@app.route('/apply_changes', methods=['POST'])
@login_required
def apply_changes():
    try:
        changes = request.json
        subject = changes[0]["subject"]
        orphaned_entities = changes[0].get("orphaned_entities", [])
        delete_orphans = changes[0].get("deleteOrphans", False)
        
        editor = Editor(
            dataset_endpoint, 
            provenance_endpoint, 
            app.config['COUNTER_HANDLER'], 
            URIRef(f'https://orcid.org/{current_user.orcid}'), 
            app.config['PRIMARY_SOURCE'], 
            app.config['DATASET_GENERATION_TIME']
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
        strategy = app.config.get('ORPHAN_HANDLING_STRATEGY', OrphanHandlingStrategy.KEEP)
        
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
        app.logger.error(error_message)
        return jsonify({"status": "error", "message": gettext("An error occurred while applying changes")}), 500
    
def import_entity_graph(editor: Editor, subject: str, max_depth: int = 5):
    """
    Recursively import the main subject and its connected entity graph up to a specified depth.

    This function imports the specified subject and all entities connected to it,
    directly or indirectly, up to the maximum depth specified. It traverses the
    graph of connected entities, importing each one into the editor.

    Args:
    editor (Editor): The Editor instance to use for importing.
    subject (str): The URI of the subject to start the import from.
    max_depth (int): The maximum depth of recursion (default is 5).

    Returns:
    Editor: The updated Editor instance with all imported entities.
    """
    imported_subjects = set()

    def recursive_import(current_subject: str, current_depth: int):
        if current_depth > max_depth or current_subject in imported_subjects:
            return

        imported_subjects.add(current_subject)
        editor.import_entity(URIRef(current_subject))

        query = f"""
            SELECT ?p ?o
            WHERE {{
                <{current_subject}> ?p ?o .
                FILTER(isIRI(?o))
            }}
        """
        
        sparql = SPARQLWrapper(editor.dataset_endpoint)
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        for result in results["results"]["bindings"]:
            object_entity = result["o"]["value"]
            recursive_import(object_entity, current_depth + 1)

    recursive_import(subject, 1)
    return editor

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

    # Get form fields if SHACL is present
    form_fields = get_cached_form_fields() if shacl else {}
    
    for predicate, values in properties.items():
        if not isinstance(values, list):
            values = [values]
        for value in values:
            if isinstance(value, dict) and 'entity_type' in value:
                nested_subject = generate_unique_uri(value['entity_type'])
                create_logic(editor, value, nested_subject, graph_uri, subject, predicate, temp_id_to_uri)
            else:
                if shacl and entity_type in form_fields:
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
    if shacl:
        if new_value is None:
            raise ValueError(report_text)
    else:
        new_value = Literal(new_value, datatype=old_value.datatype) if old_value.datatype and isinstance(old_value, Literal) else Literal(new_value, datatype=XSD.string) if isinstance(old_value, Literal) else URIRef(new_value)
    editor.update(URIRef(subject), URIRef(predicate), old_value, new_value, graph_uri)

@app.route('/check_orphans', methods=['POST'])
@login_required
def check_orphans():
    strategy = app.config.get('ORPHAN_HANDLING_STRATEGY', OrphanHandlingStrategy.KEEP)
    changes = request.json
    potential_orphans = []

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

def delete_logic(editor: Editor, subject, predicate, object_value, graph_uri=None):
    if shacl:
        data_graph = fetch_data_graph_for_subject(subject)
        _, can_be_deleted, _, _, _, _, _ = get_valid_predicates(list(data_graph.triples((URIRef(subject), None, None))))
        if predicate and predicate not in can_be_deleted:
            raise ValueError(gettext('This property cannot be deleted'))
    editor.delete(subject, predicate, object_value, graph_uri)

def find_orphaned_entities(subject, predicate=None, object_value=None):
    """
    Find entities that would become orphaned after deleting a triple or an entire entity.
    An entity is considered orphaned if:
    1. It has no incoming references from other entities (except from the entity being deleted)
    2. It does not reference any entities that are subjects of other triples
    
    Args:
        subject (str): The URI of the subject being deleted
        predicate (str, optional): The predicate being deleted. If None, entire entity is being deleted
        object_value (str, optional): The object value being deleted. If None, entire entity is being deleted
        
    Returns:
        list: A list of dictionaries containing URIs and types of orphaned entities
    """
    if predicate and object_value:
        query = f"""
        SELECT DISTINCT ?entity ?type
        WHERE {{
            # The entity we're checking
            <{subject}> <{predicate}> ?entity .
            FILTER(?entity = <{object_value}>)
            
            # Get entity type
            ?entity a ?type .
            
            # First condition: No incoming references from other entities
            FILTER NOT EXISTS {{
                ?other ?anyPredicate ?entity .
                FILTER(?other != <{subject}>)
            }}
            
            # Second condition: Does not reference any entities that are subjects
            FILTER NOT EXISTS {{
                # Find any outgoing connections from our entity
                ?entity ?outgoingPredicate ?connectedEntity .
                
                # Check if the connected entity is a subject in any triple
                ?connectedEntity ?furtherPredicate ?furtherObject .
            }}
        }}
        """
    else:
        query = f"""
        SELECT DISTINCT ?entity ?type
        WHERE {{
            # Find all entities referenced by the subject being deleted
            <{subject}> ?p ?entity .
            
            # Only consider URIs, not literal values
            FILTER(isIRI(?entity))
            
            # Get entity type
            ?entity a ?type .
            
            # First condition: No incoming references from other entities
            FILTER NOT EXISTS {{
                ?other ?anyPredicate ?entity .
                FILTER(?other != <{subject}>)
            }}
            
            # Second condition: Does not reference any entities that are subjects
            FILTER NOT EXISTS {{
                # Find any outgoing connections from our entity
                ?entity ?outgoingPredicate ?connectedEntity .
                
                # Check if the connected entity is a subject in any triple
                # (excluding the entity being deleted)
                ?connectedEntity ?furtherPredicate ?furtherObject .
                FILTER(?connectedEntity != <{subject}>)
            }}
        }}
        """
    
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    
    orphaned_entities = []
    for result in results["results"]["bindings"]:
        orphaned_entities.append({
            'uri': result["entity"]["value"],
            'type': result["type"]["value"]
        })
    
    return orphaned_entities

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

@app.route('/search')
@login_required
def search():
    subject = request.args.get('q')
    return redirect(url_for('about', subject=subject))

@app.route('/set-language/<lang_code>')
@login_required
def set_language(lang_code=None):
    session['lang'] = lang_code
    refresh()
    return redirect(request.referrer or url_for('index'))

@app.route('/endpoint')
@login_required
def endpoint():
    return render_template('endpoint.jinja', dataset_endpoint=dataset_endpoint)

@app.route('/dataset-endpoint', methods=['POST'])
@login_required
def sparql_proxy():
    query = request.form.get('query')
    response = requests.post(dataset_endpoint, data={'query': query}, headers={'Accept': 'application/sparql-results+json'})
    return response.content, response.status_code, {'Content-Type': 'application/sparql-results+json'}

def generate_modification_text(modifications, subject_classes, history=None, entity_uri=None, current_snapshot=None, current_snapshot_timestamp=None, custom_filter=custom_filter, form_fields=form_fields_cache):
    """
    Generate HTML text describing modifications to an entity, using form_fields to determine object display format.

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

    for mod_type, triples in modifications.items():
        modification_text += "<ul class='list-group mb-3'><p>"
        if mod_type == gettext('Additions'):
            modification_text += '<i class="bi bi-plus-circle-fill text-success"></i>'
        elif mod_type == gettext('Deletions'):
            modification_text += '<i class="bi bi-dash-circle-fill text-danger"></i>'
        modification_text += ' <em>' + gettext(mod_type) + '</em></p>'

        for triple in triples:
            predicate = triple[1]
            predicate_label = custom_filter.human_readable_predicate(predicate, subject_classes)
            object_value = triple[2]

            # Determine which snapshot to use for context
            relevant_snapshot = None
            if mod_type == gettext('Deletions') and history and entity_uri and current_snapshot_timestamp:
                sorted_timestamps = sorted(history[entity_uri].keys())
                current_index = sorted_timestamps.index(current_snapshot_timestamp)
                if current_index > 0:
                    relevant_snapshot = history[entity_uri][sorted_timestamps[current_index - 1]]
            else:
                relevant_snapshot = current_snapshot

            subject_class = get_highest_priority_class(subject_classes)

            object_label = get_object_label(
                object_value, 
                predicate,
                subject_class,
                form_fields,
                relevant_snapshot,
                custom_filter
            )

            modification_text += f"""
                <li class='d-flex align-items-center'>
                    <span class='flex-grow-1 d-flex flex-column justify-content-center ms-3 mb-2 w-100'>
                        <strong>{predicate_label}</strong>
                        <span class="object-value word-wrap">{object_label}</span>
                    </span>
                </li>"""

        modification_text += "</ul>"
    return modification_text

def get_object_label(object_value, predicate, entity_type, form_fields, snapshot, custom_filter: Filter):
    """
    Get appropriate display label for an object value based on form fields configuration.
    """
    entity_type = str(entity_type)
    predicate = str(predicate)

    if predicate == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type":
        return custom_filter.human_readable_predicate(object_value, [entity_type]).title()
    
    if form_fields and entity_type in form_fields:
        predicate_fields = form_fields[entity_type].get(predicate, [])
        for field in predicate_fields:
            # Check if this is an entity reference
            if field.get('nodeShape') or field.get('objectClass'):
                if validators.url(object_value):
                    # Get types for the referenced entity
                    object_classes = []
                    if snapshot:
                        object_classes = [str(o) for s, p, o in snapshot.triples((URIRef(object_value), RDF.type, None))]
                    if not object_classes and field.get('objectClass'):
                        object_classes = [field['objectClass']]
                    
                    return custom_filter.human_readable_entity(object_value, object_classes, snapshot)

            # Check for mandatory values
            if field.get('hasValue') == object_value:
                return custom_filter.human_readable_predicate(object_value, [entity_type])

            # Check for optional values from a predefined set
            if object_value in field.get('optionalValues', []):
                return custom_filter.human_readable_predicate(object_value, [entity_type])

    # Default to simple string representation for literal values
    if not validators.url(object_value):
        return object_value

    # For any other URIs, use human_readable_predicate
    return custom_filter.human_readable_predicate(object_value, [entity_type])

@app.route('/entity-history/<path:entity_uri>')
@login_required
def entity_history(entity_uri):
    agnostic_entity = AgnosticEntity(res=entity_uri, config=change_tracking_config, related_entities_history=True)
    history, provenance = agnostic_entity.get_history(include_prov_metadata=True)

    sorted_metadata = sorted(
        provenance[entity_uri].items(),
        key=lambda x: convert_to_datetime(x[1]['generatedAtTime'])
    )
    sorted_timestamps = [convert_to_datetime(meta['generatedAtTime'], stringify=True) for _, meta in sorted_metadata]

    # Otteniamo il contesto corretto per l'etichetta dell'entità
    latest_metadata = sorted_metadata[-1][1] if sorted_metadata else None
    is_latest_deletion = latest_metadata and 'invalidatedAtTime' in latest_metadata and latest_metadata['invalidatedAtTime']

    if is_latest_deletion and len(sorted_timestamps) > 1:
        context_snapshot = history[entity_uri][sorted_timestamps[-2]]
    else:
        context_snapshot = history[entity_uri][sorted_timestamps[-1]]

    entity_classes = set()
    classes = list(context_snapshot.triples((URIRef(entity_uri), RDF.type, None)))
    for triple in classes:
        entity_classes.add(str(triple[2]))
    entity_classes = [get_highest_priority_class(entity_classes)]

    events = []
    for i, (snapshot_uri, metadata) in enumerate(sorted_metadata):
        date = convert_to_datetime(metadata['generatedAtTime'])
        snapshot_timestamp_str = convert_to_datetime(metadata['generatedAtTime'], stringify=True)
        snapshot_graph = history[entity_uri][snapshot_timestamp_str]

        responsible_agent = custom_filter.format_agent_reference(metadata['wasAttributedTo'])
        primary_source = custom_filter.format_source_reference(metadata['hadPrimarySource'])
        
        modifications = metadata['hasUpdateQuery']
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
                form_fields=form_fields_cache
            )

        description = metadata['description'].replace(
            entity_uri, 
            custom_filter.human_readable_entity(entity_uri, entity_classes, context_snapshot)
        )

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
                    <p><strong>{gettext('Description')}:</strong> {description}</p>
                    <div class="modifications mb-3">
                        {modification_text}
                    </div>
                    <a href='/entity-version/{entity_uri}/{metadata['generatedAtTime']}' class='btn btn-outline-primary mt-2 view-version' target='_self'>{gettext('View version')}</a>
                """
            },
            "autolink": False
        }

        if i + 1 < len(sorted_metadata):
            next_date = convert_to_datetime(sorted_metadata[i + 1][1]['generatedAtTime'])
            event["end_date"] = {
                "year": next_date.year,
                "month": next_date.month,
                "day": next_date.day,
                "hour": next_date.hour,
                "minute": next_date.minute,
                "second": next_date.second
            }
        else:
            event["end_date"] = "Present"

        events.append(event)

    entity_label = custom_filter.human_readable_entity(entity_uri, entity_classes, context_snapshot)

    timeline_data = {
        "entityUri": entity_uri,
        "entityLabel": entity_label,
        "entityClasses": list(entity_classes),
        "events": events
    }

    return render_template('entity_history.jinja', 
                         timeline_data=timeline_data)

@app.route('/entity-version/<path:entity_uri>/<timestamp>')
@login_required
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

    agnostic_entity = AgnosticEntity(res=entity_uri, config=change_tracking_config, related_entities_history=True)
    history, provenance = agnostic_entity.get_history(include_prov_metadata=True)

    # Get the main entity's history and provenance
    main_entity_history = history.get(entity_uri, {})
    main_entity_provenance = provenance.get(entity_uri, {})

    # Convert the timestamps to datetime objects and sort them
    sorted_timestamps = sorted(
        main_entity_history.keys(),
        key=lambda t: convert_to_datetime(t)
    )
    timestamp_map = {t: convert_to_datetime(t) for t in sorted_timestamps}

    try:
        closest_timestamp = min(
            timestamp_map.keys(),
            key=lambda t: abs(timestamp_map[t].astimezone(timezone.utc) - timestamp_dt)
        )
    except ValueError:
        abort(404)

    version: Graph|ConjunctiveGraph = main_entity_history[closest_timestamp]

    triples = list(version.triples((URIRef(entity_uri), None, None)))

    is_deletion_snapshot = False
    closest_metadata = None
    min_time_diff = None
    
    latest_timestamp = max(sorted_timestamps)
    latest_metadata = None
    for se_uri, meta in main_entity_provenance.items():
        meta_time = convert_to_datetime(meta['generatedAtTime'])
        
        time_diff = abs((meta_time - timestamp_dt).total_seconds())
        if closest_metadata is None or time_diff < min_time_diff:
            closest_metadata = meta
            min_time_diff = time_diff
            
        if meta['generatedAtTime'] == latest_timestamp:
            latest_metadata = meta
            
    if closest_metadata is None or latest_metadata is None:
        abort(404)
        
    # A snapshot is a deletion snapshot if either:
    # 1. It's the latest snapshot AND has an invalidation time OR
    # 2. It has zero triples (indicating the entity was deleted at this point)
    is_deletion_snapshot = (
        (closest_timestamp == latest_timestamp and 
         'invalidatedAtTime' in latest_metadata and 
         latest_metadata['invalidatedAtTime']) 
        or len(triples) == 0
    )

    # Se è uno snapshot di cancellazione, usa il penultimo snapshot per il contesto
    context_version = version

    if is_deletion_snapshot and len(sorted_timestamps) > 1:
        current_index = sorted_timestamps.index(closest_timestamp)
        if current_index > 0:
            context_version = main_entity_history[sorted_timestamps[current_index - 1]]

    if is_deletion_snapshot and len(sorted_timestamps) > 1:
        subject_classes = [o for _, _, o in context_version.triples((URIRef(entity_uri), RDF.type, None))]
    else:
        subject_classes = [o for _, _, o in version.triples((URIRef(entity_uri), RDF.type, None))]

    subject_classes = [get_highest_priority_class(subject_classes)]

    relevant_properties = set()
    _, _, _, _, _, _, valid_predicates = get_valid_predicates(triples)

    grouped_triples, relevant_properties = get_grouped_triples(
        entity_uri, triples, subject_classes, valid_predicates, historical_snapshot=context_version
    )

    if relevant_properties:
        triples = [triple for triple in triples if str(triple[1]) in relevant_properties]

    snapshot_times = [convert_to_datetime(meta['generatedAtTime']) for meta in main_entity_provenance.values()]
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

    if closest_metadata.get('hasUpdateQuery'):
        sparql_query = closest_metadata['hasUpdateQuery']
        parsed_modifications = parse_sparql_update(sparql_query)
        modifications = generate_modification_text(
            parsed_modifications, 
            subject_classes, 
            history=history, 
            entity_uri=entity_uri, 
            current_snapshot=version,
            current_snapshot_timestamp=closest_timestamp,
            custom_filter=custom_filter,
            form_fields=form_fields_cache
        )
    else:
        modifications = ""

    if closest_metadata.get('description'):
        closest_metadata['description'] = closest_metadata['description'].replace(
            entity_uri, custom_filter.human_readable_entity(entity_uri, subject_classes, context_version)
        )

    closest_timestamp = closest_metadata['generatedAtTime']

    return render_template(
        'entity_version.jinja',
        subject=entity_uri,
        metadata={closest_timestamp: closest_metadata},
        timestamp=closest_timestamp,
        next_snapshot_timestamp=next_snapshot_timestamp,
        prev_snapshot_timestamp=prev_snapshot_timestamp,
        modifications=modifications,
        grouped_triples=grouped_triples,
        subject_classes=subject_classes,
        version_number=version_number,
        version=context_version
    )


def fetch_data_graph_recursively(subject_uri, max_depth=5, current_depth=0, visited=None):
    """
    Recursively fetch all quads associated with a subject and its connected entities.

    Args:
        subject_uri (str): The URI of the subject to fetch.
        max_depth (int): Maximum depth of recursion.
        current_depth (int): Current depth in recursion.
        visited (set): Set of visited URIs to avoid cycles.

    Returns:
        ConjunctiveGraph: A graph containing all fetched quads.
    """
    if visited is None:
        visited = set()
    if current_depth > max_depth or subject_uri in visited:
        return ConjunctiveGraph()

    visited.add(subject_uri)
    g = ConjunctiveGraph()

    # Fetch all quads where the subject is involved
    if is_dataset_quadstore():
        query = f"""
        SELECT ?s ?p ?o ?g
        WHERE {{
            GRAPH ?g {{
                ?s ?p ?o .
                VALUES (?s) {{(<{subject_uri}>)}}
            }}
        }}
        """
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
    sparql.setReturnFormat(JSON if is_dataset_quadstore() else XML)
    results = sparql.query().convert()

    if is_dataset_quadstore():
        for result in results["results"]["bindings"]:
            s = URIRef(result["s"]["value"])
            p = URIRef(result["p"]["value"])
            o = result["o"]
            g_context = URIRef(result["g"]["value"])

            if o["type"] == "uri":
                o_node = URIRef(o["value"])
            else:
                value = o["value"]
                lang = result.get("lang", {}).get("value")
                datatype = o.get("datatype")
                
                if lang:
                    o_node = Literal(value, lang=lang)
                elif datatype:
                    o_node = Literal(value, datatype=URIRef(datatype))
                else:
                    o_node = Literal(value, datatype=XSD.string)
            g.add((s, p, o_node, g_context))
    else:
        for triple in results:
            g.add(triple)

    # Recursively fetch connected entities
    for triple in g.quads((URIRef(subject_uri), None, None, None)):
        o = triple[2]
        if isinstance(o, URIRef) and o not in visited:
            if is_dataset_quadstore():
                for quad in fetch_data_graph_recursively(str(o), max_depth, current_depth + 1, visited).quads():
                    g.add(quad)
            else:
                for triple in fetch_data_graph_recursively(str(o), max_depth, current_depth + 1, visited):
                    g.add(triple)

    return g

def get_entity_graph(entity_uri, timestamp=None) -> Graph|ConjunctiveGraph:
    if timestamp:
        # Retrieve the historical snapshot
        agnostic_entity = AgnosticEntity(res=entity_uri, config=change_tracking_config, related_entities_history=True)
        history, provenance = agnostic_entity.get_history(include_prov_metadata=True)
        snapshot = history.get(entity_uri, {}).get(timestamp)
        if snapshot is None:
            abort(404)
        return snapshot, provenance
    else:
        # Retrieve the current state
        data_graph = fetch_data_graph_recursively(entity_uri)
        return data_graph, None

def compute_graph_differences(current_graph: Graph|ConjunctiveGraph, historical_graph: Graph|ConjunctiveGraph):
    if is_dataset_quadstore():
        current_data = set(current_graph.quads())
        historical_data = set(historical_graph.quads())
    else:
        current_data = set(current_graph.quads())
        historical_data = set(historical_graph.quads())
    triples_or_quads_to_delete = current_data - historical_data
    triples_or_quads_to_add = historical_data - current_data

    return triples_or_quads_to_delete, triples_or_quads_to_add

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
        generation_time = convert_to_datetime(metadata['generatedAtTime'])
        
        # Skip deletion snapshots (where generation time equals invalidation time)
        if (metadata.get('invalidatedAtTime') and 
            metadata['generatedAtTime'] == metadata['invalidatedAtTime']):
            continue
            
        # Only consider snapshots up to our target time
        if generation_time <= target_datetime:
            valid_snapshots.append((generation_time, snapshot_uri))
    
    if not valid_snapshots:
        return None
        
    # Sort by generation time and take the most recent one
    valid_snapshots.sort(key=lambda x: x[0])
    return valid_snapshots[-1][1]

def get_entities_to_restore(triples_or_quads_to_delete: set, triples_or_quads_to_add: set, main_entity_uri: str) -> set:
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
        if predicate == 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type':
            continue

        subject = str(item[0])
        obj = str(item[2])
        for uri in [subject, obj]:
            if uri != main_entity_uri and validators.url(uri):
                entities_to_restore.add(uri)
                
    return entities_to_restore

def prepare_entity_snapshots(entities_to_restore: set, provenance: dict, target_time: str) -> dict:
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
            key=lambda x: convert_to_datetime(x[1]['generatedAtTime'])
        )
        latest_snapshot = sorted_snapshots[-1][1]
        is_deleted = (
            latest_snapshot.get('invalidatedAtTime') and
            latest_snapshot['generatedAtTime'] == latest_snapshot['invalidatedAtTime']
        )
        
        entity_snapshots[entity_uri] = {
            'source': source_snapshot,
            'needs_restore': is_deleted
        }
        
    return entity_snapshots

@app.route('/restore-version/<path:entity_uri>/<timestamp>', methods=['POST'])
@login_required
def restore_version(entity_uri, timestamp):
    timestamp = convert_to_datetime(timestamp, stringify=True)
    agnostic_entity = AgnosticEntity(res=entity_uri, config=change_tracking_config, related_entities_history=True)
    history, provenance = agnostic_entity.get_history(include_prov_metadata=True)

    historical_graph = copy.deepcopy(history.get(entity_uri, {}).get(timestamp))
    if historical_graph is None:
        abort(404)

    current_graph = fetch_data_graph_recursively(entity_uri)
    is_deleted = current_graph is None or len(current_graph) == 0
    
    triples_or_quads_to_delete, triples_or_quads_to_add = compute_graph_differences(
        current_graph, historical_graph
    )
    
    # Get all entities that need restoration
    entities_to_restore = get_entities_to_restore(
        triples_or_quads_to_delete, 
        triples_or_quads_to_add,
        entity_uri
    )
    
    # Prepare snapshot information for all entities
    entity_snapshots = prepare_entity_snapshots(entities_to_restore, provenance, timestamp)
    
    editor = Editor(
        dataset_endpoint, 
        provenance_endpoint, 
        app.config['COUNTER_HANDLER'], 
        URIRef(f'https://orcid.org/{current_user.orcid}'), 
        None,
        app.config['DATASET_GENERATION_TIME']
    )

    if is_dataset_quadstore():
        for quad in current_graph:
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
            if entity_info['needs_restore']:
                editor.g_set.mark_as_restored(URIRef(subject))
            editor.g_set.entity_index[URIRef(subject)]['restoration_source'] = entity_info['source']

    # Apply additions
    for item in triples_or_quads_to_add:
        if len(item) == 4:
            editor.create(item[0], item[1], item[2], item[3])
        else:
            editor.create(item[0], item[1], item[2])

        subject = str(item[0])
        if subject in entity_snapshots:
            entity_info = entity_snapshots[subject]
            if entity_info['needs_restore']:
                editor.g_set.mark_as_restored(URIRef(subject))
                editor.g_set.entity_index[URIRef(subject)]['source'] = entity_info['source']

    # Handle main entity restoration
    if is_deleted and entity_uri in entity_snapshots:
        editor.g_set.mark_as_restored(URIRef(entity_uri))
        editor.g_set.entity_index[URIRef(subject)]['source'] = entity_info['source']
        
    try:
        editor.save()
        flash(gettext('Version restored successfully'), 'success')
    except Exception as e:
        flash(gettext('An error occurred while restoring the version: %(error)s', error=str(e)), 'error')

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

def validate_new_triple(subject, predicate, new_value, action: str, old_value = None):
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
        SELECT DISTINCT ?path ?datatype ?a_class ?classIn ?maxCount ?minCount (GROUP_CONCAT(DISTINCT COALESCE(?optionalValue, ""); separator=",") AS ?optionalValues)
        WHERE {{
            ?shape sh:targetClass ?type ;
                sh:property ?propertyShape .
            ?propertyShape sh:path ?path .
            FILTER(?path = <{predicate}>)
            VALUES ?type {{<{'> <'.join(s_types)}>}}
            OPTIONAL {{?propertyShape sh:datatype ?datatype .}}
            OPTIONAL {{?propertyShape sh:maxCount ?maxCount .}}
            OPTIONAL {{?propertyShape sh:minCount ?minCount .}}
            OPTIONAL {{?propertyShape sh:class ?a_class .}}
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
        GROUP BY ?path ?datatype ?a_class ?classIn ?maxCount ?minCount
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

    max_count = [row.maxCount for row in results if row.maxCount]
    min_count = [row.minCount for row in results if row.minCount]
    max_count = int(max_count[0]) if max_count else None
    min_count = int(min_count[0]) if min_count else None

    current_values = list(data_graph.triples((URIRef(subject), URIRef(predicate), None)))
    current_count = len(current_values)

    if action == 'create':
        new_count = current_count + 1
    elif action == 'delete':
        new_count = current_count - 1
    else:  # update
        new_count = current_count

    if max_count is not None and new_count > max_count:
        value = gettext('value') if max_count == 1 else gettext('values')
        return None, old_value, gettext(
            'The property %(predicate)s allows at most %(max_count)s %(value)s',
            predicate=custom_filter.human_readable_predicate(predicate, s_types),
            max_count=max_count,
            value=value
        )
    if min_count is not None and new_count < min_count:
        value = gettext('value') if min_count == 1 else gettext('values')
        return None, old_value, gettext(
            'The property %(predicate)s requires at least %(min_count)s %(value)s',
            predicate=custom_filter.human_readable_predicate(predicate, s_types),
            min_count=min_count,
            value=value
        )

    if optional_values and new_value not in optional_values:
        optional_value_labels = [custom_filter.human_readable_predicate(value, s_types) for value in optional_values]
        return None, old_value, gettext(
            '<code>%(new_value)s</code> is not a valid value. The <code>%(property)s</code> property requires one of the following values: %(o_values)s',
            new_value=custom_filter.human_readable_predicate(new_value, s_types),
            property=custom_filter.human_readable_predicate(predicate, s_types),
            o_values=', '.join([f'<code>{label}</code>' for label in optional_value_labels])
        )
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
            datatype_labels = [get_datatype_label(datatype) for datatype in datatypes]
            return None, old_value, gettext(
                '<code>%(new_value)s</code> is not a valid value. The <code>%(property)s</code> property requires values of type %(o_types)s',
                new_value=custom_filter.human_readable_predicate(new_value, s_types),
                property=custom_filter.human_readable_predicate(predicate, s_types),
                o_types=', '.join([f'<code>{label}</code>' for label in datatype_labels])
            )
        return valid_value, old_value, ''
    # Se non ci sono datatypes o classes specificati, determiniamo il tipo in base a old_value e new_value
    if isinstance(old_value, Literal):
        if old_value.datatype:
            valid_value = Literal(new_value, datatype=old_value.datatype)
        else:
            valid_value = Literal(new_value, datatype=XSD.string)
    elif isinstance(old_value, URIRef) or validators.url(new_value):
        valid_value = URIRef(new_value)
    else:
        valid_value = Literal(new_value, datatype=XSD.string)
    return valid_value, old_value, ''

def get_grouped_triples(subject, triples, subject_classes, valid_predicates_info, historical_snapshot=None):
    grouped_triples = OrderedDict()
    relevant_properties = set()
    fetched_values_map = dict()  # Map of original values to values returned by the query
    primary_properties = valid_predicates_info
    highest_priority_class = get_highest_priority_class(subject_classes)
    highest_priority_rules = [rule for rule in display_rules if rule['class'] == str(highest_priority_class)]
    for prop_uri in primary_properties:
        if display_rules and highest_priority_rules:
            matched_rules = []
            for rule in highest_priority_rules:
                for prop in rule['displayProperties']:
                    if prop['property'] == prop_uri:
                        matched_rules.append(rule)
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
                                process_display_rule(display_name, prop_uri, display_rule, subject, triples, grouped_triples, fetched_values_map, historical_snapshot)
                                
                                if is_ordered:
                                    grouped_triples[display_name]['is_draggable'] = True
                                    grouped_triples[display_name]['ordered_by'] = order_property
                                    process_ordering(subject, prop, order_property, grouped_triples, display_name, fetched_values_map, historical_snapshot)

                                if 'intermediateRelation' in prop:
                                    grouped_triples[display_name]['intermediateRelation'] = prop['intermediateRelation']
                        else:
                            display_name = prop.get('displayName', prop_uri)
                            relevant_properties.add(prop_uri)
                            process_display_rule(display_name, prop_uri, prop, subject, triples, grouped_triples, fetched_values_map, historical_snapshot)
                            
                            if is_ordered:
                                grouped_triples[display_name]['is_draggable'] = True
                                grouped_triples[display_name]['ordered_by'] = order_property
                                process_ordering(subject, prop, order_property, grouped_triples, display_name, fetched_values_map, historical_snapshot)

                            if 'intermediateRelation' in prop:
                                grouped_triples[display_name]['intermediateRelation'] = prop['intermediateRelation']
            else:
                process_default_property(prop_uri, triples, grouped_triples)
        else:
            process_default_property(prop_uri, triples, grouped_triples)

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
        
def process_display_rule(display_name, prop_uri, rule, subject, triples, grouped_triples, fetched_values_map, historical_snapshot=None):
    if display_name not in grouped_triples:
        grouped_triples[display_name] = {
            'property': prop_uri,
            'triples': [],
            'shape': rule.get('shape'),
            'intermediateRelation': rule.get('intermediateRelation')
        }
    for triple in triples:
        if str(triple[1]) == prop_uri:
            if rule.get('fetchValueFromQuery'):
                if historical_snapshot:
                    result, external_entity = execute_historical_query(rule['fetchValueFromQuery'], subject, triple[2], historical_snapshot)
                else:
                    result, external_entity = execute_sparql_query(rule['fetchValueFromQuery'], subject, triple[2])
                if result:
                    fetched_values_map[str(result)] = str(triple[2])
                    new_triple = (str(triple[0]), str(triple[1]), str(result))
                    new_triple_data = {
                        'triple': new_triple,
                        'external_entity': external_entity,
                        'object': str(triple[2]),
                        'shape': rule.get('shape')
                    }
                    grouped_triples[display_name]['triples'].append(new_triple_data)
            else:
                new_triple_data = {
                    'triple': (str(triple[0]), str(triple[1]), str(triple[2])),
                    'object': str(triple[2]),
                    'shape': rule.get('shape')
                }
                grouped_triples[display_name]['triples'].append(new_triple_data)

def process_ordering(subject, prop, order_property, grouped_triples, display_name, fetched_values_map, historical_snapshot: ConjunctiveGraph|Graph|None = None):
    def get_ordered_sequence(order_results):
        order_map = {}
        for res in order_results:
            if isinstance(res, dict):  # For live triplestore results
                ordered_entity = res['orderedEntity']['value']
                next_value = res['nextValue']['value']
            else:  # For historical snapshot results
                ordered_entity = str(res[0])
                next_value = str(res[1])

            order_map[str(ordered_entity)] = None if str(next_value) == "NONE" else str(next_value)

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
    
    decoded_subject = unquote(subject)

    order_query = f"""
        SELECT ?orderedEntity (COALESCE(?next, "NONE") AS ?nextValue)
        WHERE {{
            <{decoded_subject}> <{prop['property']}> ?orderedEntity.
            OPTIONAL {{
                ?orderedEntity <{order_property}> ?next.
            }}
        }}
    """
    if historical_snapshot:
        order_results = list(historical_snapshot.query(order_query))
    else:
        sparql.setQuery(order_query)
        sparql.setReturnFormat(JSON)
        order_results = sparql.query().convert().get("results", {}).get("bindings", [])

    order_sequences = get_ordered_sequence(order_results)
    for sequence in order_sequences:
        grouped_triples[display_name]['triples'].sort(
            key=lambda x: sequence.index(
                fetched_values_map.get(str(x['triple'][2]), str(x['triple'][2]))
            ) if fetched_values_map.get(str(x['triple'][2]), str(x['triple'][2])) in sequence else float('inf')
        )

def process_default_property(prop_uri, triples, grouped_triples):
    display_name = prop_uri
    grouped_triples[display_name] = {
        'property': prop_uri,
        'triples': [],
        'shape': None
    }
    triples_for_prop = [triple for triple in triples if str(triple[1]) == prop_uri]
    for triple in triples_for_prop:
        new_triple_data = {
            'triple': (str(triple[0]), str(triple[1]), str(triple[2])),
            'object': str(triple[2]),
            'shape': None
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
    editor = Editor(
        dataset_endpoint, 
        provenance_endpoint, 
        app.config['COUNTER_HANDLER'], 
        URIRef(f'https://orcid.org/{current_user.orcid}'), 
        app.config['PRIMARY_SOURCE'], 
        app.config['DATASET_GENERATION_TIME'])
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

    highest_priority_class = get_highest_priority_class(s_types)
    s_types = [highest_priority_class] if highest_priority_class else s_types

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
    mandatory_values = defaultdict(list)
    for valid_predicate in valid_predicates:
        for predicate, ranges in valid_predicate.items():
            if ranges["hasValue"]:
                mandatory_value_present = any(triple[2] == ranges["hasValue"] for triple in triples)
                mandatory_values[str(predicate)].append(str(ranges["hasValue"]))
            else:
                max_reached = (ranges["max"] is not None and int(ranges["max"]) <= predicate_counts.get(predicate, 0))

                if not max_reached:
                    can_be_added.add(predicate)
                if not (ranges["min"] is not None and int(ranges["min"]) == predicate_counts.get(predicate, 0)):
                    can_be_deleted.add(predicate)

    datatypes = defaultdict(list)
    for row in results:
        if row.datatype:
            datatypes[str(row.predicate)].append(str(row.datatype))
        else:
            datatypes[str(row.predicate)].append(str(XSD.string))

    optional_values = dict()
    for valid_predicate in valid_predicates:
        for predicate, ranges in valid_predicate.items():
            if "optionalValues" in ranges:
                optional_values.setdefault(str(predicate), list()).extend(ranges["optionalValues"])
    return list(can_be_added), list(can_be_deleted), dict(datatypes), mandatory_values, optional_values, s_types, {list(predicate_data.keys())[0] for predicate_data in valid_predicates}

def execute_sparql_query(query: str, subject: str, value: str) -> Tuple[str, str]:
    decoded_subject = unquote(subject)
    decoded_value = unquote(value)
    query = query.replace('[[subject]]', f'<{decoded_subject}>')
    query = query.replace('[[value]]', f'<{decoded_value}>')
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

def execute_historical_query(query: str, subject: str, value: str, historical_snapshot: Graph) -> Tuple[str, str]:
    decoded_subject = unquote(subject)
    decoded_value = unquote(value)
    query = query.replace('[[subject]]', f'<{decoded_subject}>')
    query = query.replace('[[value]]', f'<{decoded_value}>')
    results = historical_snapshot.query(query)
    if results:
        for result in results:
            return (str(result[0]), str(result[1]))
    return None, None

def convert_to_datetime(date_str, stringify=False):
    try:
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt if not stringify else dt.isoformat()
    except ValueError:
        return None

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

@app.route('/human-readable-entity', methods=['POST'])
def get_human_readable_entity():
    uri = request.form['uri']
    entity_class = request.form['entity_class']
    filter_instance = Filter(context, display_rules, dataset_endpoint)
    readable = filter_instance.human_readable_entity(uri, [entity_class])
    return readable