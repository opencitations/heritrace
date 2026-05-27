# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import json
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import cast
from urllib.parse import urlparse, urlunparse

import yaml
from flask import Flask, current_app, g, redirect, session, url_for
from flask_babel import Babel
from flask_login import LoginManager
from flask_login.signals import user_loaded_from_cookie
from heritrace.models import User
from heritrace.services.resource_lock_manager import ResourceLockManager
from heritrace.sparql import SPARQLWrapperWithRetry, get_sparql_bindings, select_results
from heritrace.uri_generator.uri_generator import CounterBasedURIGenerator
from heritrace.utils.filters import Filter
from rdflib import Graph
from rdflib_ocdm.counter_handler.counter_handler import CounterHandler
from redis import Redis
from SPARQLWrapper import JSON
from time_agnostic_library.support import generate_config_file


@dataclass(frozen=True)
class AppState:
    dataset_endpoint: str
    provenance_endpoint: str
    sparql: SPARQLWrapperWithRetry
    provenance_sparql: SPARQLWrapperWithRetry
    change_tracking_config: dict
    custom_filter: Filter
    display_rules: list[dict]
    form_fields_cache: dict
    dataset_is_quadstore: bool
    shacl_graph: Graph
    classes_with_multiple_shapes: set[str]


def get_app_state() -> AppState:
    return current_app.extensions['heritrace']


def init_extensions(app: Flask, babel: Babel, login_manager: LoginManager, redis: Redis):
    babel.init_app(
        app=app,
        locale_selector=lambda: session.get('lang', 'en'),
        default_translation_directories=app.config['BABEL_TRANSLATION_DIRECTORIES']
    )

    init_login_manager(app, login_manager)

    dataset_endpoint, provenance_endpoint, sparql, provenance_sparql, change_tracking_config = init_sparql_services(app)
    initialize_counter_handler(app, redis, sparql, provenance_sparql)

    # Preliminary state: Filter.__init__ calls get_sparql() during initialize_global_variables,
    # so sparql must be accessible via get_app_state() before the final AppState is built.
    app.extensions['heritrace'] = AppState(
        dataset_endpoint=dataset_endpoint,
        provenance_endpoint=provenance_endpoint,
        sparql=sparql,
        provenance_sparql=provenance_sparql,
        change_tracking_config=change_tracking_config,
        custom_filter=cast(Filter, None),
        display_rules=[],
        form_fields_cache={},
        dataset_is_quadstore=False,
        shacl_graph=Graph(),
        classes_with_multiple_shapes=set(),
    )

    display_rules, form_fields_cache, dataset_is_quadstore, shacl_graph, classes_with_multiple_shapes = initialize_global_variables(app)
    custom_filter = init_filters(app, display_rules, dataset_endpoint)
    init_request_handlers(app, redis)

    app.extensions['heritrace'] = AppState(
        dataset_endpoint=dataset_endpoint,
        provenance_endpoint=provenance_endpoint,
        sparql=sparql,
        provenance_sparql=provenance_sparql,
        change_tracking_config=change_tracking_config,
        custom_filter=custom_filter,
        display_rules=display_rules,
        form_fields_cache=form_fields_cache,
        dataset_is_quadstore=dataset_is_quadstore,
        shacl_graph=shacl_graph,
        classes_with_multiple_shapes=classes_with_multiple_shapes,
    )
    app.extensions["login_manager"] = login_manager
    app.extensions["redis_client"] = redis

def init_login_manager(app, login_manager: LoginManager):
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # type: ignore[reportAttributeAccessIssue]
    login_manager.unauthorized_handler(lambda: redirect(url_for('auth.login')))

    @login_manager.user_loader
    def load_user(user_id):
        user_name = session.get('user_name', 'Unknown User')
        return User(id=user_id, name=user_name, orcid=user_id)

    @user_loaded_from_cookie.connect
    def rotate_session_token(sender, user):
        session.modified = True

def initialize_change_tracking_config(app: Flask, adjusted_dataset_endpoint=None, adjusted_provenance_endpoint=None):
    config_needs_generation = False
    config_path = None
    config = None

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
            )
            app.logger.info(f"Generated new change tracking configuration at: {config_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to generate change tracking configuration: {str(e)}")

    try:
        if not config:
            with open(config_path, 'r', encoding='utf8') as f:
                config = json.load(f)

    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid change tracking configuration JSON at {config_path}: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Error reading change tracking configuration at {config_path}: {str(e)}")

    app.config['CHANGE_TRACKING_CONFIG'] = config_path
    return config

def need_initialization(app: Flask, redis: Redis):
    uri_generator = app.config['URI_GENERATOR']

    if not isinstance(uri_generator, CounterBasedURIGenerator):
        return False

    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    is_external_redis = redis_url != 'redis://localhost:6379/0'

    if is_external_redis:
        app.logger.info(f"Using external Redis at {redis_url} - skipping counter initialization")
        return False

    cache_validity_days = app.config['CACHE_VALIDITY_DAYS']

    try:
        last_init_raw: bytes | None = redis.get('heritrace:last_initialization')  # type: ignore[assignment]
        if not last_init_raw:
            return True

        last_init = datetime.fromisoformat(last_init_raw.decode('utf-8'))
        return datetime.now() - last_init > timedelta(days=cache_validity_days)
    except Exception:
        return True

def update_cache(app: Flask, redis: Redis):
    current_time = datetime.now().isoformat()
    redis.set('heritrace:last_initialization', current_time)
    redis.set('heritrace:cache_version', '1.0')

def initialize_counter_handler(app: Flask, redis: Redis, sparql: SPARQLWrapperWithRetry, provenance_sparql: SPARQLWrapperWithRetry):
    if not need_initialization(app, redis):
        return

    uri_generator: CounterBasedURIGenerator = app.config['URI_GENERATOR']

    uri_generator.initialize_counters(sparql)

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

    provenance_sparql.setQuery(prov_query)
    provenance_sparql.setReturnFormat(JSON)
    prov_bindings = get_sparql_bindings(provenance_sparql.query().convert())

    for result in prov_bindings:
        entity = result["entity"]["value"]
        count = int(result["count"]["value"])
        uri_generator.counter_handler.set_counter(count, entity)

    update_cache(app, redis)

def identify_classes_with_multiple_shapes(display_rules: list[dict], shacl_graph: Graph) -> set[str]:
    if not display_rules or not shacl_graph:
        return set()

    from heritrace.utils.display_rules_utils import is_entity_type_visible

    class_to_shapes: defaultdict[str, set[str]] = defaultdict(set)

    for rule in display_rules:
        target = rule.get("target", {})

        if "class" in target:
            class_uri = target["class"]
            query_string = f"""
                SELECT DISTINCT ?shape WHERE {{
                    ?shape <http://www.w3.org/ns/shacl#targetClass> <{class_uri}> .
                }}
            """
            results = shacl_graph.query(query_string)
            for row in select_results(results):
                shape_uri = str(row.shape)
                entity_key = (class_uri, shape_uri)
                if is_entity_type_visible(entity_key):
                    class_to_shapes[class_uri].add(shape_uri)

        elif "shape" in target:
            shape_uri = target["shape"]
            query_string = f"""
                SELECT DISTINCT ?class WHERE {{
                    <{shape_uri}> <http://www.w3.org/ns/shacl#targetClass> ?class .
                }}
            """
            results = shacl_graph.query(query_string)
            for row in select_results(results):
                class_uri = str(row[0])
                entity_key = (class_uri, shape_uri)
                if is_entity_type_visible(entity_key):
                    class_to_shapes[class_uri].add(shape_uri)

    return {class_uri for class_uri, shapes in class_to_shapes.items() if len(shapes) > 1}

def initialize_global_variables(app: Flask) -> tuple[list[dict], dict, bool, Graph, set[str]]:
    try:
        dataset_is_quadstore = app.config.get('DATASET_IS_QUADSTORE', False)

        display_rules: list[dict] = []
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

        shacl_graph = Graph()
        form_fields_cache: dict = {}
        if app.config.get('SHACL_PATH'):
            if not os.path.exists(app.config['SHACL_PATH']):
                app.logger.warning(f"SHACL file not found at: {app.config['SHACL_PATH']}")
            else:
                try:
                    shacl_graph.parse(source=app.config['SHACL_PATH'], format="turtle")

                    from heritrace.utils.shacl_utils import \
                        get_form_fields_from_shacl
                    form_fields_cache = get_form_fields_from_shacl(shacl_graph, display_rules, app=app)
                except Exception as e:
                    app.logger.error(f"Error initializing form fields from SHACL: {str(e)}")
                    raise RuntimeError(f"Failed to initialize form fields: {str(e)}")

        classes_with_multiple_shapes = identify_classes_with_multiple_shapes(display_rules, shacl_graph)

        app.logger.info("Global variables initialized successfully")
        return display_rules, form_fields_cache, dataset_is_quadstore, shacl_graph, classes_with_multiple_shapes

    except Exception as e:
        app.logger.error(f"Error during global variables initialization: {str(e)}")
        raise RuntimeError(f"Global variables initialization failed: {str(e)}")

def init_sparql_services(app: Flask) -> tuple[str, str, SPARQLWrapperWithRetry, SPARQLWrapperWithRetry, dict]:
    dataset_endpoint = adjust_endpoint_url(app.config['DATASET_DB_URL'])
    provenance_endpoint = adjust_endpoint_url(app.config['PROVENANCE_DB_URL'])

    sparql = SPARQLWrapperWithRetry(dataset_endpoint, timeout=30.0)
    provenance_sparql = SPARQLWrapperWithRetry(provenance_endpoint, timeout=30.0)

    change_tracking_config = initialize_change_tracking_config(
        app,
        adjusted_dataset_endpoint=dataset_endpoint,
        adjusted_provenance_endpoint=provenance_endpoint
    )

    return dataset_endpoint, provenance_endpoint, sparql, provenance_sparql, change_tracking_config

def init_filters(app: Flask, display_rules: list[dict], dataset_endpoint: str) -> Filter:
    with open(os.path.join(os.path.dirname(__file__), "utils", "context.json"), "r") as config_file:
        context = json.load(config_file)["@context"]

    custom_filter = Filter(context, display_rules or None, dataset_endpoint)

    app.jinja_env.filters['human_readable_predicate'] = custom_filter.human_readable_predicate
    app.jinja_env.filters['human_readable_class'] = custom_filter.human_readable_class
    app.jinja_env.filters['human_readable_entity'] = custom_filter.human_readable_entity
    app.jinja_env.filters['human_readable_primary_source'] = custom_filter.human_readable_primary_source
    app.jinja_env.filters['format_datetime'] = custom_filter.human_readable_datetime
    from heritrace.utils.filters import split_namespace
    app.jinja_env.filters['split_ns'] = split_namespace
    app.jinja_env.filters['format_source_reference'] = custom_filter.format_source_reference
    app.jinja_env.filters['format_agent_reference'] = custom_filter.format_agent_reference
    return custom_filter

def init_request_handlers(app: Flask, redis: Redis):
    @app.before_request
    def initialize_lock_manager():
        if not hasattr(g, 'resource_lock_manager'):
            g.resource_lock_manager = ResourceLockManager(redis)

    @app.teardown_appcontext
    def close_redis_connection(error):
        if hasattr(g, 'resource_lock_manager'):
            del g.resource_lock_manager

def adjust_endpoint_url(url: str) -> str:
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
    return os.path.exists('/.dockerenv')

def get_dataset_endpoint() -> str:
    return get_app_state().dataset_endpoint

def get_sparql() -> SPARQLWrapperWithRetry:
    return get_app_state().sparql

def get_provenance_endpoint() -> str:
    return get_app_state().provenance_endpoint

def get_provenance_sparql() -> SPARQLWrapperWithRetry:
    return get_app_state().provenance_sparql

def get_counter_handler() -> CounterHandler:
    uri_generator = current_app.config.get('URI_GENERATOR')
    if not isinstance(uri_generator, CounterBasedURIGenerator):
        current_app.logger.error("CounterHandler not found in URIGenerator config.")
        raise RuntimeError("CounterHandler is not available. Initialization might have failed.")
    return uri_generator.counter_handler

def get_custom_filter() -> Filter:
    return get_app_state().custom_filter

def get_change_tracking_config() -> dict:
    return get_app_state().change_tracking_config

def get_display_rules() -> list[dict]:
    return get_app_state().display_rules

def get_form_fields() -> dict:
    return get_app_state().form_fields_cache

def get_dataset_is_quadstore() -> bool:
    return get_app_state().dataset_is_quadstore

def get_shacl_graph() -> Graph:
    return get_app_state().shacl_graph

def get_classes_with_multiple_shapes() -> set[str]:
    return get_app_state().classes_with_multiple_shapes
