# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import json
import os
from collections import defaultdict
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import cast
from urllib.parse import urlparse, urlunparse

import yaml
from flask import (
    Flask,
    Response,
    current_app,
    g,
    jsonify,
    redirect,
    request,
    session,
    url_for,
)
from flask_login import LoginManager
from flask_login.signals import user_loaded_from_cookie
from rdflib import Graph, URIRef
from rdflib_ocdm.counter_handler.counter_handler import CounterHandler
from redis import Redis
from redis.exceptions import RedisError
from SPARQLWrapper import JSON
from time_agnostic_library.support import generate_config_file
from werkzeug.wrappers import Response as WerkzeugResponse

from heritrace.configuration.entity import (
    META_SHAPES,
    PROVENANCE_FILE,
    SkolemURIGenerator,
    check_configuration,
    provenance_counter_handler,
)
from heritrace.configuration.runtime import SetupRequiredError, request_reload
from heritrace.configuration.store import SHACL_FILE
from heritrace.configuration.vocabulary import SH
from heritrace.counter_handler import CounterInitializationPolicy
from heritrace.editor import Backend, Editor, FileBackend, TriplestoreBackend
from heritrace.models import User
from heritrace.rdf_files import load_rdf_file
from heritrace.save_plugin import SavePlugin
from heritrace.services.resource_lock_manager import ResourceLockManager
from heritrace.sparql import (
    LocalSparql,
    SparqlEndpoint,
    SPARQLWrapperWithRetry,
    get_sparql_bindings,
)
from heritrace.uri_generator.uri_generator import CounterBasedURIGenerator, URIGenerator
from heritrace.utils.filters import Filter
from heritrace.utils.shacl_presentation import (
    ShapesPresentation,
    labels_use_inverse_relations,
    read_presentation,
)

# Class counts with the time they were computed and the dataset version they
# reflect.
ClassCounts = tuple[list[dict[str, str | int]], float, str | None]


# Everything the entity routes need about one store of entities: the dataset,
# or the configuration that admins edit as an entity.
@dataclass(frozen=True)
class AppState:
    sparql: SparqlEndpoint
    provenance_sparql: SparqlEndpoint
    backend: Backend
    new_counter_handler: Callable[[], CounterHandler]
    uri_generator: URIGenerator
    save_plugin: SavePlugin | None
    primary_source: URIRef | None
    generation_time: datetime | None
    change_tracking_config: dict
    custom_filter: Filter
    display_rules: list[dict]
    presentation: ShapesPresentation
    form_fields_cache: dict
    dataset_is_quadstore: bool
    is_virtuoso: bool
    shacl_graph: Graph
    classes_with_multiple_shapes: set[str]
    labels_use_inverse_relations: bool
    class_counts: dict[str, ClassCounts] = field(default_factory=dict)


def get_app_state() -> AppState:
    if "store" in g:
        return g.store
    return current_app.extensions["heritrace"]


def new_store_sparql() -> SparqlEndpoint:
    return get_app_state().backend.sparql()


@contextmanager
def use_state(state: AppState) -> Iterator[None]:
    g.store = state
    try:
        yield
    finally:
        g.pop("store")


def new_editor(resp_agent: URIRef, source: URIRef | None) -> Editor:
    state = get_app_state()
    return Editor(
        state.backend,
        state.new_counter_handler(),
        resp_agent,
        source,
        state.generation_time,
        save_plugin=state.save_plugin,
    )


def init_extensions(
    app: Flask, login_manager: LoginManager, redis: Redis, shacl_graph: Graph
) -> None:
    init_login_manager(app, login_manager)

    (
        dataset_endpoint,
        provenance_endpoint,
        sparql,
        provenance_sparql,
        change_tracking_config,
    ) = init_sparql_services(app)
    initialize_counter_handler(app, redis, sparql, provenance_sparql)

    counter_handler = cast("CounterHandler", app.config["COUNTER_HANDLER"])
    placeholder = AppState(
        sparql=sparql,
        provenance_sparql=provenance_sparql,
        backend=TriplestoreBackend(
            dataset_endpoint,
            provenance_endpoint,
            app.config["DATASET_IS_QUADSTORE"],
        ),
        new_counter_handler=lambda: counter_handler,
        uri_generator=app.config["URI_GENERATOR"],
        save_plugin=app.config["SAVE_PLUGIN"],
        primary_source=URIRef(app.config["PRIMARY_SOURCE"]),
        generation_time=app.config["DATASET_GENERATION_TIME"],
        change_tracking_config=change_tracking_config,
        custom_filter=cast("Filter", None),
        display_rules=[],
        presentation=read_presentation(Graph()),
        form_fields_cache={},
        dataset_is_quadstore=False,
        is_virtuoso=False,
        shacl_graph=Graph(),
        classes_with_multiple_shapes=set(),
        labels_use_inverse_relations=False,
    )
    app.extensions["heritrace"] = placeholder

    (
        display_rules,
        form_fields_cache,
        dataset_is_quadstore,
        classes_with_multiple_shapes,
    ) = initialize_global_variables(app, shacl_graph, app.config["DISPLAY_RULES_PATH"])
    presentation = read_presentation(shacl_graph)
    custom_filter = init_filters(presentation, placeholder.backend.sparql)
    init_request_handlers(app, redis)

    app.extensions["heritrace"] = replace(
        placeholder,
        custom_filter=custom_filter,
        display_rules=display_rules,
        presentation=presentation,
        form_fields_cache=form_fields_cache,
        dataset_is_quadstore=dataset_is_quadstore,
        is_virtuoso=app.config["DATASET_DB_TRIPLESTORE"].lower() == "virtuoso",
        shacl_graph=shacl_graph,
        classes_with_multiple_shapes=classes_with_multiple_shapes,
        labels_use_inverse_relations=labels_use_inverse_relations(presentation),
    )
    app.extensions["login_manager"] = login_manager
    app.extensions["redis_client"] = redis


def build_configuration_state(app: Flask) -> AppState:
    config_dir = app.config["CONFIG_DIR"]
    data_path = config_dir / SHACL_FILE
    provenance_path = config_dir / PROVENANCE_FILE
    meta_shapes = load_rdf_file(META_SHAPES)
    backend = FileBackend(
        data_path, provenance_path, check_configuration, request_reload
    )
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    placeholder = AppState(
        sparql=backend.sparql(),
        provenance_sparql=LocalSparql(lambda: load_rdf_file(provenance_path)),
        backend=backend,
        new_counter_handler=lambda: provenance_counter_handler(provenance_path),
        uri_generator=SkolemURIGenerator(),
        save_plugin=None,
        primary_source=None,
        generation_time=None,
        change_tracking_config=generate_config_file(
            config_path=str(
                Path(app.instance_path) / "configuration_change_tracking.json"
            ),
            dataset_dirs=[str(data_path)],
            dataset_is_quadstore=False,
            provenance_dirs=[str(provenance_path)],
            provenance_is_quadstore=True,
        ),
        custom_filter=cast("Filter", None),
        display_rules=[],
        presentation=read_presentation(Graph()),
        form_fields_cache={},
        dataset_is_quadstore=False,
        is_virtuoso=False,
        shacl_graph=Graph(),
        classes_with_multiple_shapes=set(),
        labels_use_inverse_relations=False,
    )
    with use_state(placeholder):
        display_rules, form_fields_cache, _, classes_with_multiple_shapes = (
            initialize_global_variables(app, meta_shapes, None)
        )
    presentation = read_presentation(meta_shapes)
    return replace(
        placeholder,
        custom_filter=init_filters(presentation, backend.sparql),
        display_rules=display_rules,
        presentation=presentation,
        form_fields_cache=form_fields_cache,
        shacl_graph=meta_shapes,
        classes_with_multiple_shapes=classes_with_multiple_shapes,
        labels_use_inverse_relations=labels_use_inverse_relations(presentation),
    )


def unauthorized() -> WerkzeugResponse | tuple[Response, int]:
    if request.path.startswith("/api/"):
        return jsonify({"status": "error", "message": "Authentication required"}), 401
    return redirect(url_for("auth.login"))


def init_login_manager(app: Flask, login_manager: LoginManager) -> None:
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"  # type: ignore[reportAttributeAccessIssue]
    login_manager.unauthorized_handler(unauthorized)

    @login_manager.user_loader
    def load_user(user_id: str) -> User:
        user_name = session.get("user_name", "Unknown User")
        return User(user_id=user_id, name=user_name, orcid=user_id)

    @user_loaded_from_cookie.connect
    def rotate_session_token(_sender: object, _user: object) -> None:
        session.modified = True


def initialize_change_tracking_config(
    app: Flask,
    adjusted_dataset_endpoint: str | None = None,
    adjusted_provenance_endpoint: str | None = None,
) -> dict:
    config_needs_generation = False
    config_path = None
    config = None

    if "CHANGE_TRACKING_CONFIG" in app.config:
        config_path = app.config["CHANGE_TRACKING_CONFIG"]
        if not Path(config_path).exists():
            app.logger.warning(
                "Change tracking configuration file not found at specified path: %s",
                config_path,
            )
            config_needs_generation = True
    else:
        config_needs_generation = True
        config_path = str(Path(app.instance_path) / "change_tracking_config.json")
        Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    if config_needs_generation:
        dataset_urls = [adjusted_dataset_endpoint] if adjusted_dataset_endpoint else []
        provenance_urls = (
            [adjusted_provenance_endpoint] if adjusted_provenance_endpoint else []
        )

        db_triplestore = app.config.get("DATASET_DB_TRIPLESTORE", "").lower()
        text_index_enabled = app.config.get("DATASET_DB_TEXT_INDEX_ENABLED", False)

        blazegraph_search = db_triplestore == "blazegraph" and text_index_enabled
        fuseki_search = db_triplestore == "fuseki" and text_index_enabled
        virtuoso_search = db_triplestore == "virtuoso" and text_index_enabled

        graphdb_connector = ""  # TODO(@arcangelo-massari): Add graphdb support
        # https://github.com/opencitations/heritrace/issues/1

        try:
            config = generate_config_file(
                config_path=config_path,
                dataset_urls=dataset_urls,
                dataset_dirs=app.config.get("DATASET_DIRS", []),
                dataset_is_quadstore=app.config.get("DATASET_IS_QUADSTORE", False),
                provenance_urls=provenance_urls,
                provenance_is_quadstore=app.config.get(
                    "PROVENANCE_IS_QUADSTORE", False
                ),
                provenance_dirs=app.config.get("PROVENANCE_DIRS", []),
                blazegraph_full_text_search=blazegraph_search,
                fuseki_full_text_search=fuseki_search,
                virtuoso_full_text_search=virtuoso_search,
                graphdb_connector_name=graphdb_connector,
            )
            app.logger.info(
                "Generated new change tracking configuration at: %s", config_path
            )
        except OSError as e:
            msg = f"Failed to generate change tracking configuration: {e!s}"
            raise RuntimeError(msg) from e

    try:
        if not config:
            with Path(config_path).open(encoding="utf8") as f:
                config = json.load(f)

    except json.JSONDecodeError as e:
        msg = f"Invalid change tracking configuration JSON at {config_path}: {e!s}"
        raise RuntimeError(msg) from e
    except OSError as e:
        msg = f"Error reading change tracking configuration at {config_path}: {e!s}"
        raise RuntimeError(msg) from e

    app.config["CHANGE_TRACKING_CONFIG"] = config_path
    return config


_COUNTERS_INITIALIZED = "heritrace:counters_initialized"


def need_initialization(app: Flask, redis: Redis) -> bool:
    if "REDIS_URL" in os.environ:
        app.logger.info(
            "Using external Redis at %s - skipping counter initialization",
            os.environ["REDIS_URL"],
        )
        return False

    # HERITRACE updates the counters on every change, so they only need to be
    # rebuilt when Redis has lost them.
    try:
        return not redis.exists(_COUNTERS_INITIALIZED)
    except RedisError:
        return True


def mark_counters_initialized(redis: Redis) -> None:
    redis.set(_COUNTERS_INITIALIZED, datetime.now(tz=timezone.utc).isoformat())


def initialize_counter_handler(
    app: Flask,
    redis: Redis,
    sparql: SPARQLWrapperWithRetry,
    provenance_sparql: SPARQLWrapperWithRetry,
) -> None:
    counter_handler = cast("CounterHandler", app.config["COUNTER_HANDLER"])
    if (
        isinstance(counter_handler, CounterInitializationPolicy)
        and not counter_handler.should_initialize_from_triplestore()
    ):
        return

    if not need_initialization(app, redis):
        return

    uri_generator = app.config["URI_GENERATOR"]
    if isinstance(uri_generator, CounterBasedURIGenerator):
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
        counter_handler.set_counter(count, entity)

    mark_counters_initialized(redis)


def identify_classes_with_multiple_shapes(shacl_graph: Graph) -> set[str]:
    shapes_by_class: defaultdict[str, set[str]] = defaultdict(set)
    for shape, class_uri in shacl_graph.subject_objects(SH.targetClass):
        shapes_by_class[str(class_uri)].add(str(shape))
    return {
        class_uri for class_uri, shapes in shapes_by_class.items() if len(shapes) > 1
    }


def initialize_global_variables(
    app: Flask, shacl_graph: Graph, display_rules_path: Path | None
) -> tuple[list[dict], dict, bool, set[str]]:
    try:
        dataset_is_quadstore = app.config.get("DATASET_IS_QUADSTORE", False)

        display_rules: list[dict] = []
        if display_rules_path is not None and not display_rules_path.exists():
            app.logger.warning(
                "Display rules file not found at: %s", display_rules_path
            )
        elif display_rules_path is not None:
            try:
                with display_rules_path.open() as f:
                    display_rules = yaml.safe_load(f)["rules"]
            except yaml.YAMLError as e:
                app.logger.exception("Error loading display rules")
                msg = f"Failed to load display rules: {e!s}"
                raise SetupRequiredError(msg) from e

        form_fields_cache: dict = {}
        if len(shacl_graph):
            from heritrace.utils.shacl_utils import (  # noqa: PLC0415
                get_form_fields_from_shacl,
            )

            try:
                form_fields_cache = get_form_fields_from_shacl(
                    shacl_graph, display_rules, app=app
                )
            except ValueError as e:
                app.logger.exception("Error initializing form fields from SHACL")
                msg = f"Failed to initialize form fields: {e!s}"
                raise SetupRequiredError(msg) from e

        classes_with_multiple_shapes = identify_classes_with_multiple_shapes(
            shacl_graph
        )

        app.logger.info("Global variables initialized successfully")

    except SetupRequiredError:
        raise
    except (OSError, yaml.YAMLError, ValueError) as e:
        app.logger.exception("Error during global variables initialization")
        msg = f"Global variables initialization failed: {e!s}"
        raise SetupRequiredError(msg) from e
    else:
        return (
            display_rules,
            form_fields_cache,
            dataset_is_quadstore,
            classes_with_multiple_shapes,
        )


def init_sparql_services(
    app: Flask,
) -> tuple[str, str, SPARQLWrapperWithRetry, SPARQLWrapperWithRetry, dict]:
    dataset_endpoint = adjust_endpoint_url(app.config["DATASET_DB_URL"])
    provenance_endpoint = adjust_endpoint_url(app.config["PROVENANCE_DB_URL"])

    sparql = SPARQLWrapperWithRetry(dataset_endpoint, timeout=30.0)
    provenance_sparql = SPARQLWrapperWithRetry(provenance_endpoint, timeout=30.0)

    change_tracking_config = initialize_change_tracking_config(
        app,
        adjusted_dataset_endpoint=dataset_endpoint,
        adjusted_provenance_endpoint=provenance_endpoint,
    )

    return (
        dataset_endpoint,
        provenance_endpoint,
        sparql,
        provenance_sparql,
        change_tracking_config,
    )


def init_filters(
    presentation: ShapesPresentation, new_sparql: Callable[[], SparqlEndpoint]
) -> Filter:
    with (Path(__file__).parent / "utils" / "context.json").open() as config_file:
        context = json.load(config_file)["@context"]

    return Filter(context, presentation, new_sparql)


def init_request_handlers(app: Flask, redis: Redis) -> None:
    @app.before_request
    def initialize_lock_manager() -> None:
        if not hasattr(g, "resource_lock_manager"):
            g.resource_lock_manager = ResourceLockManager(redis)

    @app.teardown_appcontext
    def close_redis_connection(_error: BaseException | None) -> None:
        if hasattr(g, "resource_lock_manager"):
            del g.resource_lock_manager


def adjust_endpoint_url(url: str) -> str:
    if not running_in_docker():
        return url

    local_patterns = ["localhost", "127.0.0.1", "0.0.0.0"]
    parsed_url = urlparse(url)

    if any(pattern in parsed_url.netloc for pattern in local_patterns):
        netloc_parts = parsed_url.netloc.split(":")
        new_netloc = (
            f"host.docker.internal:{netloc_parts[1]}"
            if len(netloc_parts) > 1
            else "host.docker.internal"
        )
        url_parts = list(parsed_url)
        url_parts[1] = new_netloc
        return urlunparse(url_parts)

    return url


def running_in_docker() -> bool:
    return Path("/.dockerenv").exists()


def get_sparql() -> SparqlEndpoint:
    return get_app_state().sparql


def get_provenance_sparql() -> SparqlEndpoint:
    return get_app_state().provenance_sparql


DATASET_VERSION_KEY = "heritrace:dataset_version"


def get_dataset_version() -> str | None:
    redis: Redis = current_app.extensions["redis_client"]
    return cast("str | None", redis.get(DATASET_VERSION_KEY))


def record_dataset_change() -> None:
    redis: Redis = current_app.extensions["redis_client"]
    redis.incr(DATASET_VERSION_KEY)


def get_primary_source() -> URIRef | None:
    return get_app_state().primary_source


def get_uri_generator() -> URIGenerator:
    return get_app_state().uri_generator


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


def get_labels_use_inverse_relations() -> bool:
    return get_app_state().labels_use_inverse_relations


def get_presentation() -> ShapesPresentation:
    return get_app_state().presentation


def get_shacl_graph() -> Graph:
    return get_app_state().shacl_graph


def get_classes_with_multiple_shapes() -> set[str]:
    return get_app_state().classes_with_multiple_shapes
