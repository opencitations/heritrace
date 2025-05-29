# heritrace/extensions.py

import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict
from urllib.parse import urlparse, urlunparse

import yaml
from flask import Flask, current_app, g, redirect, session, url_for
from flask_babel import Babel
from flask_login import LoginManager
from flask_login.signals import user_loaded_from_cookie
from heritrace.models import User
from heritrace.services.resource_lock_manager import ResourceLockManager
from heritrace.uri_generator.uri_generator import URIGenerator
from heritrace.utils.filters import Filter
from rdflib import Graph
from rdflib_ocdm.counter_handler.counter_handler import CounterHandler
from redis import Redis
from SPARQLWrapper import JSON, SPARQLWrapper
from time_agnostic_library.support import generate_config_file

# Global variables
initialization_done = False
dataset_endpoint = None
provenance_endpoint = None
sparql = None
provenance_sparql = None
change_tracking_config = None
form_fields_cache = None
custom_filter = None
redis_client = None
display_rules = None
dataset_is_quadstore = None
shacl_graph = None


class SPARQLWrapperWithRetry(SPARQLWrapper):
    """
    Extension of SPARQLWrapper that includes automatic retry functionality and timeout handling.
    Uses SPARQLWrapper's built-in timeout functionality.
    """
    def __init__(self, endpoint, **kwargs):
        self.max_attempts = kwargs.pop('max_attempts', 3)
        self.initial_delay = kwargs.pop('initial_delay', 1.0)
        self.backoff_factor = kwargs.pop('backoff_factor', 2.0)
        query_timeout = kwargs.pop('timeout', 5.0)
        
        super().__init__(endpoint, **kwargs)
        
        self.setTimeout(int(query_timeout))
    
    def query(self):
        """
        Override the query method to include retry logic with SPARQLWrapper's built-in timeout.
        Returns the original SPARQLWrapper.QueryResult so that convert() can be called on it.
        """
        logger = logging.getLogger(__name__)
        
        attempt = 1
        delay = self.initial_delay
        last_exception = None
        
        while attempt <= self.max_attempts:
            try:
                result = super().query()
                return result
                    
            except Exception as e:
                last_exception = e
                logger.warning(f"SPARQL query attempt {attempt}/{self.max_attempts} failed: {str(e)}")
                
                if attempt < self.max_attempts:
                    logger.info(f"Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                    delay *= self.backoff_factor
                
                attempt += 1
        
        logger.error(f"All {self.max_attempts} SPARQL query attempts failed")
        raise last_exception

def init_extensions(app: Flask, babel: Babel, login_manager: LoginManager, redis: Redis):
    """
    Initialize Flask extensions and configure shared objects.
    
    Args:
        app: Flask application instance
        babel: Babel extension instance
        login_manager: LoginManager instance
        redis: Redis client instance
    """
    global redis_client

    redis_client = redis

    # Initialize Babel
    babel.init_app(
        app=app,
        locale_selector=lambda: session.get('lang', 'en'),
        default_translation_directories=app.config['BABEL_TRANSLATION_DIRECTORIES']
    )
    
    # Initialize LoginManager
    init_login_manager(app, login_manager)
    
    # Initialize SPARQL endpoints and other services
    init_sparql_services(app)
    
    # Initialize filters
    init_filters(app)
    
    # Register before_request handlers
    init_request_handlers(app)
    
    # Store extensions in app context
    app.babel = babel
    app.login_manager = login_manager
    app.redis_client = redis_client

def init_login_manager(app, login_manager: LoginManager):
    """Configure the Flask-Login extension."""
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.unauthorized_handler(lambda: redirect(url_for('auth.login')))
    
    @login_manager.user_loader
    def load_user(user_id):
        user_name = session.get('user_name', 'Unknown User')
        return User(id=user_id, name=user_name, orcid=user_id)
    
    @user_loaded_from_cookie.connect
    def rotate_session_token(sender, user):
        session.modified = True

def initialize_change_tracking_config(app: Flask, adjusted_dataset_endpoint=None, adjusted_provenance_endpoint=None):
    """
    Initialize and return the change tracking configuration JSON.
    Uses pre-adjusted endpoints if provided to avoid redundant adjustments.
    
    Args:
        app: Flask application instance
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
        dataset_urls = [adjusted_dataset_endpoint] if adjusted_dataset_endpoint else []
        provenance_urls = [adjusted_provenance_endpoint] if adjusted_provenance_endpoint else []
        
        cache_endpoint = adjust_endpoint_url(app.config.get('CACHE_ENDPOINT', ''))
        cache_update_endpoint = adjust_endpoint_url(app.config.get('CACHE_UPDATE_ENDPOINT', ''))
        
        db_triplestore = app.config.get('DATASET_DB_TRIPLESTORE', '').lower()
        text_index_enabled = app.config.get('DATASET_DB_TEXT_INDEX_ENABLED', False)
        
        blazegraph_search = db_triplestore == 'blazegraph' and text_index_enabled
        fuseki_search = db_triplestore == 'fuseki' and text_index_enabled
        virtuoso_search = db_triplestore == 'virtuoso' and text_index_enabled
        
        graphdb_connector = '' #TODO: Add graphdb support
        
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
            
        # Adjust cache URLs if needed
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

    app.config['CHANGE_TRACKING_CONFIG'] = config_path
    return config

def need_initialization(app: Flask):
    """
    Check if counter handler initialization is needed.
    """
    uri_generator = app.config['URI_GENERATOR']

    if not hasattr(uri_generator, "counter_handler"):
        return False

    cache_file = app.config['CACHE_FILE']
    cache_validity_days = app.config['CACHE_VALIDITY_DAYS']

    if not os.path.exists(cache_file):
        return True
    
    try:
        with open(cache_file, 'r', encoding='utf8') as f:
            cache = json.load(f)
        
        last_init = datetime.fromisoformat(cache['last_initialization'])
        return datetime.now() - last_init > timedelta(days=cache_validity_days)
    except Exception:
        return True

def update_cache(app: Flask):
    """
    Update the cache file with current initialization timestamp.
    """
    cache_file = app.config['CACHE_FILE']
    cache = {
        'last_initialization': datetime.now().isoformat(),
        'version': '1.0'
    }
    with open(cache_file, 'w', encoding='utf8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=4)

def initialize_counter_handler(app: Flask):
    """
    Initialize the counter handler for URI generation if needed.
    """
    if not need_initialization(app):
        return
    
    uri_generator: URIGenerator = app.config['URI_GENERATOR']
    counter_handler: CounterHandler = uri_generator.counter_handler

    # Inizializza i contatori specifici dell'URI generator
    uri_generator.initialize_counters(sparql)

    # Query per contare gli snapshot nella provenance
    # Contiamo il numero di wasDerivedFrom per ogni entità e aggiungiamo 1 
    # (poiché il primo snapshot non ha wasDerivedFrom)
    prov_query = """
        SELECT ?entity (COUNT(DISTINCT ?snapshot) as ?count)
        WHERE {
            ?snapshot a <http://www.w3.org/ns/prov#Entity> ;
                        <http://www.w3.org/ns/prov#specializationOf> ?entity .
            OPTIONAL {
                ?snapshot <http://www.w3.org/ns/prov#wasDerivedFrom> ?prev .
            }
        }
        GROUP BY ?entity
    """

    # Esegui query sulla provenance e imposta i contatori degli snapshot
    provenance_sparql.setQuery(prov_query)
    provenance_sparql.setReturnFormat(JSON)
    prov_results = provenance_sparql.query().convert()

    for result in prov_results["results"]["bindings"]:
        entity = result["entity"]["value"]
        count = int(result["count"]["value"])
        counter_handler.set_counter(count, entity)
            
    update_cache(app)

def initialize_global_variables(app: Flask):
    """
    Initialize all global variables including form fields cache, display rules,
    and dataset configuration from SHACL shapes graph and configuration files.
    
    Args:
        app: Flask application instance
    """
    global shacl_graph, form_fields_cache, display_rules, dataset_is_quadstore
    
    try:
        dataset_is_quadstore = app.config.get('DATASET_IS_QUADSTORE', False)
        
        if app.config.get('DISPLAY_RULES_PATH'):
            if not os.path.exists(app.config['DISPLAY_RULES_PATH']):
                app.logger.warning(f"Display rules file not found at: {app.config['DISPLAY_RULES_PATH']}")
            else:
                try:
                    with open(app.config['DISPLAY_RULES_PATH'], 'r') as f:
                        yaml_content = yaml.safe_load(f)
                        display_rules = yaml_content['rules']
                except Exception as e:
                    app.logger.error(f"Error loading display rules: {str(e)}")
                    raise RuntimeError(f"Failed to load display rules: {str(e)}")
        
        if app.config.get('SHACL_PATH'):
            if not os.path.exists(app.config['SHACL_PATH']):
                app.logger.warning(f"SHACL file not found at: {app.config['SHACL_PATH']}")
                return
                
            if form_fields_cache is not None:
                return
                
            try:
                shacl_graph = Graph()
                shacl_graph.parse(source=app.config['SHACL_PATH'], format="turtle")
                
                from heritrace.utils.shacl_utils import \
                    get_form_fields_from_shacl
                form_fields_cache = get_form_fields_from_shacl(shacl_graph, display_rules, app=app)
            except Exception as e:
                app.logger.error(f"Error initializing form fields from SHACL: {str(e)}")
                raise RuntimeError(f"Failed to initialize form fields: {str(e)}")
                
        app.logger.info("Global variables initialized successfully")
        
    except Exception as e:
        app.logger.error(f"Error during global variables initialization: {str(e)}")
        raise RuntimeError(f"Global variables initialization failed: {str(e)}")

def init_sparql_services(app: Flask):
    """Initialize SPARQL endpoints and related services."""
    global initialization_done, dataset_endpoint, provenance_endpoint, sparql, provenance_sparql, change_tracking_config

    if not initialization_done:
        dataset_endpoint = adjust_endpoint_url(app.config['DATASET_DB_URL'])
        provenance_endpoint = adjust_endpoint_url(app.config['PROVENANCE_DB_URL'])
        
        sparql = SPARQLWrapperWithRetry(dataset_endpoint)
        provenance_sparql = SPARQLWrapperWithRetry(provenance_endpoint)
        
        change_tracking_config = initialize_change_tracking_config(
            app,
            adjusted_dataset_endpoint=dataset_endpoint,
            adjusted_provenance_endpoint=provenance_endpoint
        )
        
        initialize_counter_handler(app)
        initialize_global_variables(app)
        initialization_done = True

def init_filters(app: Flask):
    """Initialize custom template filters."""
    global custom_filter
    
    with open(os.path.join("resources", "context.json"), "r") as config_file:
        context = json.load(config_file)["@context"]
    
    display_rules = None
    if app.config["DISPLAY_RULES_PATH"]:
        with open(app.config["DISPLAY_RULES_PATH"], 'r') as f:
            yaml_content = yaml.safe_load(f)
            display_rules = yaml_content.get('rules', [])
    
    custom_filter = Filter(context, display_rules, dataset_endpoint)
    
    app.jinja_env.filters['human_readable_predicate'] = custom_filter.human_readable_predicate
    app.jinja_env.filters['human_readable_class'] = custom_filter.human_readable_class
    app.jinja_env.filters['human_readable_entity'] = custom_filter.human_readable_entity
    app.jinja_env.filters['human_readable_primary_source'] = custom_filter.human_readable_primary_source
    app.jinja_env.filters['format_datetime'] = custom_filter.human_readable_datetime
    app.jinja_env.filters['split_ns'] = custom_filter.split_ns
    app.jinja_env.filters['format_source_reference'] = custom_filter.format_source_reference
    app.jinja_env.filters['format_agent_reference'] = custom_filter.format_agent_reference

def init_request_handlers(app):
    """Initialize before_request and teardown_request handlers."""
    
    @app.before_request
    def initialize_lock_manager():
        """Initialize the resource lock manager for each request."""
        if not hasattr(g, 'resource_lock_manager'):
            g.resource_lock_manager = ResourceLockManager(redis_client)
    
    @app.teardown_appcontext
    def close_redis_connection(error):
        """Close Redis connection when the request context ends."""
        if hasattr(g, 'resource_lock_manager'):
            del g.resource_lock_manager

def adjust_endpoint_url(url: str) -> str:
    """
    Adjust endpoint URLs to work properly within Docker containers.
    
    Args:
        url: The endpoint URL to adjust
        
    Returns:
        The adjusted URL if running in Docker, original URL otherwise
    """
    if not running_in_docker():
        return url
        
    local_patterns = ['localhost', '127.0.0.1', '0.0.0.0']
    parsed_url = urlparse(url)
    
    if any(pattern in parsed_url.netloc for pattern in local_patterns):
        netloc_parts = parsed_url.netloc.split(':')
        new_netloc = f'host.docker.internal:{netloc_parts[1]}' if len(netloc_parts) > 1 else 'host.docker.internal'
        url_parts = list(parsed_url)
        url_parts[1] = new_netloc
        return urlunparse(url_parts)
        
    return url

def running_in_docker() -> bool:
    """Check if the application is running inside a Docker container."""
    return os.path.exists('/.dockerenv')

def get_dataset_endpoint() -> str:
    """Get the configured dataset endpoint URL."""

    global dataset_endpoint
    return dataset_endpoint

def get_sparql() -> SPARQLWrapperWithRetry:
    """Get the configured SPARQL wrapper for the dataset endpoint with built-in retry mechanism."""

    global sparql
    return sparql

def get_provenance_endpoint() -> str:
    """Get the configured provenance endpoint URL."""

    global provenance_endpoint
    return provenance_endpoint

def get_provenance_sparql() -> SPARQLWrapperWithRetry:
    """Get the configured SPARQL wrapper for the provenance endpoint with built-in retry mechanism."""

    global provenance_sparql
    return provenance_sparql

def get_counter_handler() -> CounterHandler:
    """
    Get the configured CounterHandler instance from the URIGenerator.
    Assumes URIGenerator and its counter_handler are initialized in app.config.
    """
    uri_generator: URIGenerator = current_app.config.get('URI_GENERATOR')
    if uri_generator and hasattr(uri_generator, 'counter_handler'):
        return uri_generator.counter_handler
    else:
        # Handle cases where it might not be initialized yet or configured
        current_app.logger.error("CounterHandler not found in URIGenerator config.")
        raise RuntimeError("CounterHandler is not available. Initialization might have failed.")

def get_custom_filter() -> Filter:
    """Get the configured custom filter instance."""

    global custom_filter
    return custom_filter

def get_change_tracking_config() -> Dict:
    """Get the change tracking configuration."""

    global change_tracking_config
    return change_tracking_config

def get_display_rules() -> Dict:
    """Get the display_rules configuration."""

    global display_rules
    return display_rules

def get_form_fields() -> Dict:
    """Get the form_fields configuration."""

    global form_fields_cache    
    return form_fields_cache

def get_dataset_is_quadstore() -> bool:
    """Check if the dataset is a quadstore."""

    global dataset_is_quadstore
    return dataset_is_quadstore

def get_shacl_graph() -> Graph:
    """Get the SHACL shapes graph."""

    global shacl_graph
    return shacl_graph