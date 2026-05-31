# SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import json
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import yaml
from flask import Flask, g
from flask_babel import Babel
from flask_login import LoginManager
from flask_login.signals import user_loaded_from_cookie
from rdflib import Graph
from redis import Redis
from SPARQLWrapper import SPARQLWrapper

from heritrace.extensions import (
    AppState,
    adjust_endpoint_url,
    get_change_tracking_config,
    get_classes_with_multiple_shapes,
    get_counter_handler,
    get_custom_filter,
    get_dataset_endpoint,
    get_dataset_is_quadstore,
    get_display_rules,
    get_form_fields,
    get_provenance_endpoint,
    get_provenance_sparql,
    get_shacl_graph,
    get_sparql,
    init_extensions,
    init_login_manager,
    init_request_handlers,
    initialize_change_tracking_config,
    initialize_counter_handler,
    initialize_global_variables,
    need_initialization,
    running_in_docker,
    update_cache,
)
from heritrace.sparql import SPARQLWrapperWithRetry


@pytest.fixture
def mock_redis():
    return MagicMock(spec=Redis)


@pytest.fixture
def babel():
    return Babel()


@pytest.fixture
def login_manager():
    return LoginManager()


@pytest.fixture
def cleanup_nonexistent_config():
    yield
    nonexistent_config = Path("nonexistent_config.json")
    if nonexistent_config.exists():
        nonexistent_config.unlink()


@pytest.fixture
def lightweight_app():
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SECRET_KEY="test",
        DATASET_DB_URL="http://localhost:9999/sparql",
        PROVENANCE_DB_URL="http://localhost:9999/sparql",
        DATASET_DIRS=[],
        PROVENANCE_DIRS=[],
        DATASET_IS_QUADSTORE=False,
        PROVENANCE_IS_QUADSTORE=False,
        CACHE_VALIDITY_DAYS=7,
    )
    return app


def test_init_extensions(lightweight_app, babel, login_manager, mock_redis) -> None:
    with (
        lightweight_app.app_context(),
        patch("heritrace.extensions.init_sparql_services") as mock_sparql,
        patch("heritrace.extensions.initialize_counter_handler"),
        patch(
            "heritrace.extensions.initialize_global_variables",
            return_value=([], {}, False, Graph(), set()),
        ),
        patch("heritrace.extensions.init_filters", return_value=MagicMock()),
    ):
        mock_sparql.return_value = (
            "http://ds",
            "http://prov",
            MagicMock(),
            MagicMock(),
            {},
        )
        init_extensions(lightweight_app, babel, login_manager, mock_redis)

        assert lightweight_app.extensions["redis_client"] is mock_redis
        assert isinstance(lightweight_app.extensions["heritrace"], AppState)


def test_babel_initialization(
    lightweight_app, babel, login_manager, mock_redis
) -> None:
    with (
        lightweight_app.app_context(),
        patch("heritrace.extensions.init_sparql_services") as mock_sparql,
        patch("heritrace.extensions.initialize_counter_handler"),
        patch(
            "heritrace.extensions.initialize_global_variables",
            return_value=([], {}, False, Graph(), set()),
        ),
        patch("heritrace.extensions.init_filters", return_value=MagicMock()),
    ):
        mock_sparql.return_value = (
            "http://ds",
            "http://prov",
            MagicMock(),
            MagicMock(),
            {},
        )
        init_extensions(lightweight_app, babel, login_manager, mock_redis)

        assert hasattr(babel, "domain")


def test_login_manager_initialization(
    lightweight_app, babel, login_manager, mock_redis
) -> None:
    with (
        lightweight_app.app_context(),
        patch("heritrace.extensions.init_sparql_services") as mock_sparql,
        patch("heritrace.extensions.initialize_counter_handler"),
        patch(
            "heritrace.extensions.initialize_global_variables",
            return_value=([], {}, False, Graph(), set()),
        ),
        patch("heritrace.extensions.init_filters", return_value=MagicMock()),
    ):
        mock_sparql.return_value = (
            "http://ds",
            "http://prov",
            MagicMock(),
            MagicMock(),
            {},
        )
        init_extensions(lightweight_app, babel, login_manager, mock_redis)

        assert hasattr(login_manager, "login_view")
        assert hasattr(login_manager, "login_message")


def test_close_redis_connection(app: Flask, mock_redis: Redis) -> None:
    init_request_handlers(app, mock_redis)

    with app.test_request_context():
        g.resource_lock_manager = mock_redis

        assert hasattr(g, "resource_lock_manager")

        close_redis_connection = None
        for func in app.teardown_appcontext_funcs:
            if func.__name__ == "close_redis_connection":
                close_redis_connection = func
                break

        assert close_redis_connection is not None
        close_redis_connection(None)

        assert not hasattr(g, "resource_lock_manager")

        g.resource_lock_manager = mock_redis


def test_adjust_endpoint_url() -> None:
    with patch("heritrace.extensions.running_in_docker", return_value=False):
        original_url = "http://localhost:8080/sparql"
        assert adjust_endpoint_url(original_url) == original_url

    with patch("heritrace.extensions.running_in_docker", return_value=True):
        assert (
            adjust_endpoint_url("http://localhost:8080/sparql")
            == "http://host.docker.internal:8080/sparql"
        )
        assert (
            adjust_endpoint_url("http://127.0.0.1:8080/sparql")
            == "http://host.docker.internal:8080/sparql"
        )
        assert (
            adjust_endpoint_url("http://0.0.0.0:8080/sparql")
            == "http://host.docker.internal:8080/sparql"
        )
        assert (
            adjust_endpoint_url("http://localhost/sparql")
            == "http://host.docker.internal/sparql"
        )

        external_url = "http://example.com/sparql"
        assert adjust_endpoint_url(external_url) == external_url


def test_running_in_docker() -> None:
    with patch("pathlib.Path.exists", return_value=True):
        assert running_in_docker() is True

    with patch("pathlib.Path.exists", return_value=False):
        assert running_in_docker() is False


def test_getter_functions(app) -> None:
    mock_state = AppState(
        dataset_endpoint="dataset_endpoint_value",
        provenance_endpoint="provenance_endpoint_value",
        sparql=MagicMock(spec=SPARQLWrapperWithRetry),
        provenance_sparql=MagicMock(spec=SPARQLWrapperWithRetry),
        change_tracking_config={"key": "value"},
        custom_filter=MagicMock(),
        display_rules=[{"rule": 1}],
        form_fields_cache={"field": "data"},
        dataset_is_quadstore=True,
        shacl_graph=Graph(),
        classes_with_multiple_shapes={"http://example.org/Class1"},
    )
    app.extensions["heritrace"] = mock_state

    assert get_dataset_endpoint() == "dataset_endpoint_value"
    assert get_sparql() is mock_state.sparql
    assert get_provenance_endpoint() == "provenance_endpoint_value"
    assert get_provenance_sparql() is mock_state.provenance_sparql
    assert get_custom_filter() is mock_state.custom_filter
    assert get_change_tracking_config() == {"key": "value"}
    assert get_display_rules() == [{"rule": 1}]
    assert get_form_fields() == {"field": "data"}
    assert get_dataset_is_quadstore() is True
    assert get_shacl_graph() is mock_state.shacl_graph
    assert get_classes_with_multiple_shapes() == {"http://example.org/Class1"}


def test_get_counter_handler_not_initialized(app) -> None:
    app.config.pop("URI_GENERATOR", None)

    with (
        patch("heritrace.extensions.current_app.logger.error") as mock_logger_error,
        pytest.raises(
            TypeError,
            match=(
                r"CounterHandler is not available\."
                r" Initialization might have failed\."
            ),
        ),
    ):
        get_counter_handler()
    mock_logger_error.assert_called_once_with(
        "CounterHandler not found in URIGenerator config."
    )

    app.config["URI_GENERATOR"] = MagicMock(spec=[])

    with (
        patch("heritrace.extensions.current_app.logger.error") as mock_logger_error,
        pytest.raises(
            TypeError,
            match=(
                r"CounterHandler is not available\."
                r" Initialization might have failed\."
            ),
        ),
    ):
        get_counter_handler()
    mock_logger_error.assert_called_once_with(
        "CounterHandler not found in URIGenerator config."
    )


def test_get_counter_handler_success(app) -> None:
    mock_counter_handler = MagicMock()

    mock_uri_generator = MagicMock()
    mock_uri_generator.counter_handler = mock_counter_handler
    mock_uri_generator.initialize_counters = MagicMock()

    app.config["URI_GENERATOR"] = mock_uri_generator

    result = get_counter_handler()

    assert result is mock_counter_handler


def test_init_login_manager_directly(app) -> None:
    login_manager = MagicMock(spec=LoginManager)

    init_login_manager(app, login_manager)

    login_manager.init_app.assert_called_once_with(app)
    assert login_manager.login_view == "auth.login"

    user_loader_call = [
        call for call in login_manager.method_calls if call[0] == "user_loader"
    ]
    assert len(user_loader_call) > 0

    user_loader = user_loader_call[0][1][0]

    with (
        app.test_request_context(),
        patch("heritrace.extensions.session", {"user_name": "Test User"}),
    ):
        user = user_loader("test_id")
        assert user.id == "test_id"
        assert user.name == "Test User"
        assert user.orcid == "test_id"


def test_rotate_session_token(app) -> None:
    login_manager = LoginManager()

    with patch.object(user_loaded_from_cookie, "connect") as mock_connect:
        init_login_manager(app, login_manager)

        mock_connect.assert_called_once()

        handler = mock_connect.call_args[0][0]

        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_sender = MagicMock()

        with patch("heritrace.extensions.session", mock_session):
            handler(mock_sender, mock_user)
            assert mock_session.modified is True


def test_need_initialization(app) -> None:
    mock_uri_generator = MagicMock()
    mock_uri_generator.counter_handler = MagicMock()
    mock_uri_generator.initialize_counters = MagicMock()
    app.config["URI_GENERATOR"] = mock_uri_generator
    app.config["CACHE_VALIDITY_DAYS"] = 7

    mock_redis = MagicMock()

    mock_redis.get.return_value = None
    assert need_initialization(app, mock_redis) is True

    mock_redis.get.side_effect = Exception("Redis error")
    assert need_initialization(app, mock_redis) is True

    expired_time = (datetime.now(tz=timezone.utc) - timedelta(days=10)).isoformat()
    mock_redis.get.return_value = expired_time.encode("utf-8")
    mock_redis.get.side_effect = None
    assert need_initialization(app, mock_redis) is True

    current_time = datetime.now(tz=timezone.utc).isoformat()
    mock_redis.get.return_value = current_time.encode("utf-8")
    assert need_initialization(app, mock_redis) is False

    app.config["URI_GENERATOR"] = MagicMock(spec=[])
    assert need_initialization(app, mock_redis) is False


def test_update_cache(app) -> None:
    mock_redis = MagicMock()

    update_cache(app, mock_redis)

    assert mock_redis.set.call_count == 2

    calls = mock_redis.set.call_args_list

    first_call_args = calls[0][0]
    assert first_call_args[0] == "heritrace:last_initialization"
    assert isinstance(first_call_args[1], str)

    second_call_args = calls[1][0]
    assert second_call_args[0] == "heritrace:cache_version"
    assert second_call_args[1] == "1.0"


def test_initialize_change_tracking_config(app, cleanup_nonexistent_config) -> None:
    app.config["DATASET_DB_URL"] = "http://localhost:8080/dataset"
    app.config["PROVENANCE_DB_URL"] = "http://localhost:8080/provenance"
    app.config["DATASET_DIRS"] = []
    app.config["DATASET_IS_QUADSTORE"] = False
    app.config["PROVENANCE_IS_QUADSTORE"] = False
    app.config["PROVENANCE_DIRS"] = []
    mock_config = {
        "dataset": {"is_quadstore": False},
    }

    app.config["CHANGE_TRACKING_CONFIG"] = "existing_config.json"

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.open", MagicMock()),
        patch("json.load", return_value=mock_config),
    ):
        config = initialize_change_tracking_config(app)

        assert config is not None
        assert "dataset" in config

    app.config["CHANGE_TRACKING_CONFIG"] = "nonexistent_config.json"

    with (
        patch("pathlib.Path.exists", return_value=False),
        patch("pathlib.Path.mkdir", MagicMock()),
        patch(
            "time_agnostic_library.support.generate_config_file",
            return_value=mock_config,
        ),
    ):
        config = initialize_change_tracking_config(app)

        assert config is not None
        assert "dataset" in config

    if "CHANGE_TRACKING_CONFIG" in app.config:
        del app.config["CHANGE_TRACKING_CONFIG"]

    mock_open = MagicMock()

    with (
        patch("pathlib.Path.mkdir", MagicMock()),
        patch("pathlib.Path.open", mock_open),
        patch(
            "time_agnostic_library.support.generate_config_file",
            side_effect=lambda **_kwargs: mock_config,
        ),
    ):
        config = initialize_change_tracking_config(app)

        assert config is not None
        assert "dataset" in config


def test_initialize_change_tracking_config_exceptions(
    app, cleanup_nonexistent_config
) -> None:
    app.config["DATASET_DB_URL"] = "http://localhost:8080/dataset"
    app.config["PROVENANCE_DB_URL"] = "http://localhost:8080/provenance"
    app.config["DATASET_DIRS"] = []
    app.config["DATASET_IS_QUADSTORE"] = False
    app.config["PROVENANCE_IS_QUADSTORE"] = False
    app.config["PROVENANCE_DIRS"] = []
    app.config["CHANGE_TRACKING_CONFIG"] = "nonexistent_config.json"

    with (
        patch("pathlib.Path.exists", return_value=False),
        patch("pathlib.Path.mkdir", MagicMock()),
        patch(
            "heritrace.extensions.generate_config_file",
            side_effect=OSError("Test generation error"),
        ),
        pytest.raises(RuntimeError) as excinfo,
    ):
        initialize_change_tracking_config(app)

    assert (
        "Failed to generate change tracking configuration: Test generation error"
        in str(excinfo.value)
    )

    app.config["CHANGE_TRACKING_CONFIG"] = "invalid_json_config.json"

    mock_open = MagicMock()
    mock_open.return_value.__enter__.return_value = MagicMock()

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.open", mock_open),
        patch("json.load", side_effect=json.JSONDecodeError("Test JSON error", "", 0)),
        pytest.raises(RuntimeError) as excinfo,
    ):
        initialize_change_tracking_config(app)

    assert (
        "Invalid change tracking configuration JSON at"
        " invalid_json_config.json: Test JSON error"
    ) in str(excinfo.value)

    app.config["CHANGE_TRACKING_CONFIG"] = "error_config.json"

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.open", side_effect=OSError("Test read error")),
        pytest.raises(RuntimeError) as excinfo,
    ):
        initialize_change_tracking_config(app)

    assert (
        "Error reading change tracking configuration at"
        " error_config.json: Test read error"
    ) in str(excinfo.value)


def test_initialize_counter_handler(app) -> None:
    mock_redis = MagicMock(spec=Redis)
    mock_sparql = MagicMock(spec=SPARQLWrapperWithRetry)
    mock_provenance_sparql = MagicMock(spec=SPARQLWrapperWithRetry)

    mock_prov_results = {
        "results": {
            "bindings": [
                {
                    "entity": {"value": "http://example.org/Person"},
                    "count": {"value": "10"},
                },
                {
                    "entity": {"value": "http://example.org/Event"},
                    "count": {"value": "5"},
                },
            ]
        }
    }

    mock_provenance_sparql.query.return_value.convert.return_value = mock_prov_results

    mock_counter_handler = MagicMock()
    mock_counter_handler.read_counter.return_value = 5

    mock_uri_generator = MagicMock()
    mock_uri_generator.counter_handler = mock_counter_handler

    app.config["URI_GENERATOR"] = mock_uri_generator

    with (
        patch("heritrace.extensions.need_initialization", return_value=True),
        patch("heritrace.extensions.update_cache") as mock_update_cache,
    ):
        initialize_counter_handler(app, mock_redis, mock_sparql, mock_provenance_sparql)

        mock_counter_handler.set_counter.assert_any_call(
            10, "http://example.org/Person"
        )
        mock_counter_handler.set_counter.assert_any_call(5, "http://example.org/Event")

        mock_update_cache.assert_called_once_with(app, mock_redis)


def test_initialize_lock_manager() -> None:
    app = Flask(__name__)
    mock_redis = MagicMock(spec=Redis)

    init_request_handlers(app, mock_redis)

    initialize_lock_manager = None
    for func in app.before_request_funcs.get(None, []):
        if func.__name__ == "initialize_lock_manager":
            initialize_lock_manager = func
            break

    assert initialize_lock_manager is not None

    with app.test_request_context():
        initialize_lock_manager()
        assert hasattr(g, "resource_lock_manager")


def test_initialize_global_variables_dataset_is_quadstore(app) -> None:
    app.config["DATASET_IS_QUADSTORE"] = True

    (
        _display_rules,
        _form_fields_cache,
        dataset_is_quadstore,
        _shacl_graph,
        _classes_with_multiple_shapes,
    ) = initialize_global_variables(app)

    assert dataset_is_quadstore is True


def test_initialize_global_variables_display_rules_not_found(app) -> None:
    app.config["DISPLAY_RULES_PATH"] = Path("/path/does/not/exist")
    app.config.pop("SHACL_PATH", None)

    (
        display_rules,
        _form_fields_cache,
        _dataset_is_quadstore,
        _shacl_graph,
        _classes_with_multiple_shapes,
    ) = initialize_global_variables(app)

    assert display_rules == []


def test_initialize_global_variables_display_rules_loaded(app, tmp_path) -> None:
    display_rules_path = tmp_path / "display_rules.yaml"
    display_rules_content = """
rules:
  - target:
      class: "Class1"
    displayName: "Class 1"
    displayProperties:
      - property: "prop1"
        displayName: "Property 1"
"""
    display_rules_path.write_text(display_rules_content)

    app.config["DISPLAY_RULES_PATH"] = display_rules_path
    app.config.pop("SHACL_PATH", None)

    (
        display_rules,
        _form_fields_cache,
        _dataset_is_quadstore,
        _shacl_graph,
        _classes_with_multiple_shapes,
    ) = initialize_global_variables(app)

    assert any(
        rule.get("target", {}).get("class") == "Class1" for rule in display_rules
    )
    assert any(
        rule.get("displayName") == "Class 1"
        for rule in display_rules
        if rule.get("target", {}).get("class") == "Class1"
    )


def test_initialize_global_variables_display_rules_error(app, tmp_path) -> None:
    display_rules_path = tmp_path / "invalid_display_rules.yaml"
    display_rules_path.write_text("invalid: yaml: content:")

    app.config["DISPLAY_RULES_PATH"] = display_rules_path
    app.config.pop("SHACL_PATH", None)

    with (
        patch("yaml.safe_load", side_effect=yaml.YAMLError("YAML parsing error")),
        pytest.raises(
            RuntimeError, match="Failed to load display rules: YAML parsing error"
        ),
    ):
        initialize_global_variables(app)


def test_initialize_global_variables_shacl_not_found(app) -> None:
    app.config.pop("DISPLAY_RULES_PATH", None)
    app.config["SHACL_PATH"] = Path("/path/does/not/exist")

    (
        _display_rules,
        form_fields_cache,
        _dataset_is_quadstore,
        _shacl_graph,
        _classes_with_multiple_shapes,
    ) = initialize_global_variables(app)

    assert form_fields_cache == {}


def test_initialize_global_variables_shacl_loaded(app, tmp_path) -> None:
    shacl_path = tmp_path / "shacl.ttl"
    shacl_path.write_text("@prefix sh: <http://www.w3.org/ns/shacl#> .")

    app.config.pop("DISPLAY_RULES_PATH", None)
    app.config["SHACL_PATH"] = shacl_path

    mock_form_fields = {"Class1": {"properties": ["prop1"]}}

    with patch(
        "heritrace.utils.shacl_utils.get_form_fields_from_shacl",
        return_value=mock_form_fields,
    ):
        (
            _display_rules,
            form_fields_cache,
            _dataset_is_quadstore,
            shacl_graph,
            _classes_with_multiple_shapes,
        ) = initialize_global_variables(app)

    assert form_fields_cache == mock_form_fields
    assert shacl_graph is not None


def test_initialize_global_variables_shacl_error(app, tmp_path) -> None:
    shacl_path = tmp_path / "invalid_shacl.ttl"
    shacl_path.write_text("invalid turtle content")

    app.config.pop("DISPLAY_RULES_PATH", None)
    app.config["SHACL_PATH"] = shacl_path

    with (
        patch("rdflib.Graph.parse", side_effect=ValueError("Turtle parsing error")),
        pytest.raises(
            RuntimeError, match="Failed to initialize form fields: Turtle parsing error"
        ),
    ):
        initialize_global_variables(app)


def test_initialize_global_variables_general_exception(app) -> None:
    with (
        patch.object(app.config, "get", side_effect=ValueError("General error")),
        pytest.raises(
            RuntimeError, match="Global variables initialization failed: General error"
        ),
    ):
        initialize_global_variables(app)


def test_initialize_counter_handler_no_initialization_needed(app) -> None:
    mock_redis = MagicMock(spec=Redis)
    mock_sparql = MagicMock(spec=SPARQLWrapperWithRetry)
    mock_provenance_sparql = MagicMock(spec=SPARQLWrapperWithRetry)

    mock_counter_handler = MagicMock()
    mock_uri_generator = MagicMock()
    mock_uri_generator.counter_handler = mock_counter_handler
    app.config["URI_GENERATOR"] = mock_uri_generator

    with patch(
        "heritrace.extensions.need_initialization", return_value=False
    ) as mock_need_initialization:
        initialize_counter_handler(app, mock_redis, mock_sparql, mock_provenance_sparql)

        mock_need_initialization.assert_called_once_with(app, mock_redis)

        mock_counter_handler.set_counter.assert_not_called()
        mock_uri_generator.initialize_counters.assert_not_called()
        mock_provenance_sparql.setQuery.assert_not_called()


def test_need_initialization_without_counter_handler(app) -> None:
    mock_uri_generator = MagicMock(spec=[])
    app.config["URI_GENERATOR"] = mock_uri_generator
    mock_redis = MagicMock(spec=Redis)

    assert need_initialization(app, mock_redis) is False

    mock_uri_generator = MagicMock()
    mock_uri_generator.counter_handler = None
    mock_uri_generator.initialize_counters = MagicMock()
    app.config["URI_GENERATOR"] = mock_uri_generator

    app.config["CACHE_FILE"] = "nonexistent_cache_file.json"
    app.config["CACHE_VALIDITY_DAYS"] = 7

    with patch("os.path.exists", return_value=False):
        assert need_initialization(app, mock_redis) is True


class TestSPARQLWrapperWithRetry:
    def test_init_default_values(self) -> None:
        wrapper = SPARQLWrapperWithRetry("http://example.com/sparql")

        assert wrapper.max_attempts == 3
        assert wrapper.initial_delay == 1.0
        assert wrapper.backoff_factor == 2.0
        assert wrapper.timeout == 5

    def test_init_custom_values(self) -> None:
        wrapper = SPARQLWrapperWithRetry(
            "http://example.com/sparql",
            max_attempts=5,
            initial_delay=2.0,
            backoff_factor=3.0,
            timeout=10.0,
        )

        assert wrapper.max_attempts == 5
        assert wrapper.initial_delay == 2.0
        assert wrapper.backoff_factor == 3.0
        assert wrapper.timeout == 10

    def test_query_success_first_attempt(self) -> None:
        wrapper = SPARQLWrapperWithRetry("http://example.com/sparql")
        mock_result = MagicMock()

        with patch.object(SPARQLWrapper, "query", return_value=mock_result):
            result = wrapper.query()
            assert result == mock_result

    def test_query_timeout_then_success(self) -> None:
        wrapper = SPARQLWrapperWithRetry(
            "http://example.com/sparql", max_attempts=2, initial_delay=0.1
        )
        mock_result = MagicMock()

        timeout_error = TimeoutError("The read operation timed out")
        side_effects = [timeout_error, mock_result]

        with (
            patch.object(SPARQLWrapper, "query", side_effect=side_effects),
            patch("time.sleep") as mock_sleep,
            patch("logging.getLogger") as mock_get_logger,
        ):
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            result = wrapper.query()

            assert result == mock_result
            mock_logger.warning.assert_called_once()
            mock_logger.info.assert_called_once_with("Retrying in %.2f seconds...", 0.1)
            mock_sleep.assert_called_once_with(0.1)

    def test_query_all_attempts_fail_with_timeout(self) -> None:
        wrapper = SPARQLWrapperWithRetry(
            "http://example.com/sparql", max_attempts=2, initial_delay=0.1
        )

        timeout_error = TimeoutError("The read operation timed out")
        side_effects = [timeout_error, timeout_error]

        with (
            patch.object(SPARQLWrapper, "query", side_effect=side_effects),
            patch("time.sleep") as mock_sleep,
            patch("logging.getLogger") as mock_get_logger,
        ):
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            with pytest.raises(socket.timeout):
                wrapper.query()

            assert mock_logger.warning.call_count == 2
            mock_logger.info.assert_called_once_with("Retrying in %.2f seconds...", 0.1)
            mock_logger.error.assert_called_once_with(
                "All %d SPARQL query attempts failed", 2
            )
            mock_sleep.assert_called_once_with(0.1)

    def test_query_all_attempts_fail_with_exception(self) -> None:
        wrapper = SPARQLWrapperWithRetry(
            "http://example.com/sparql", max_attempts=3, initial_delay=0.1
        )

        test_exception = Exception("Connection failed")
        side_effects = [test_exception, test_exception, test_exception]

        with (
            patch.object(SPARQLWrapper, "query", side_effect=side_effects),
            patch("time.sleep") as mock_sleep,
            patch("logging.getLogger") as mock_get_logger,
        ):
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            with pytest.raises(Exception, match="Connection failed"):
                wrapper.query()

            assert mock_logger.warning.call_count == 3
            assert mock_logger.info.call_count == 2
            mock_logger.error.assert_called_once_with(
                "All %d SPARQL query attempts failed", 3
            )

            expected_calls = [call(0.1), call(0.2)]
            mock_sleep.assert_has_calls(expected_calls)

    def test_query_mixed_exceptions(self) -> None:
        wrapper = SPARQLWrapperWithRetry(
            "http://example.com/sparql", max_attempts=3, initial_delay=0.1
        )
        mock_result = MagicMock()

        side_effects = [
            TimeoutError("The read operation timed out"),
            Exception("Connection error"),
            mock_result,
        ]

        with (
            patch.object(SPARQLWrapper, "query", side_effect=side_effects),
            patch("time.sleep"),
            patch("logging.getLogger") as mock_get_logger,
        ):
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            result = wrapper.query()

            assert result == mock_result
            assert mock_logger.warning.call_count == 2
            assert mock_logger.info.call_count == 2

    def test_query_delay_backoff(self) -> None:
        wrapper = SPARQLWrapperWithRetry(
            "http://example.com/sparql",
            max_attempts=4,
            initial_delay=0.1,
            backoff_factor=2.5,
        )
        mock_result = MagicMock()

        side_effects = [
            Exception("Error"),
            Exception("Error"),
            Exception("Error"),
            mock_result,
        ]

        with (
            patch.object(SPARQLWrapper, "query", side_effect=side_effects),
            patch("time.sleep") as mock_sleep,
            patch("logging.getLogger") as mock_get_logger,
        ):
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            result = wrapper.query()

            assert result == mock_result
            expected_calls = [call(0.1), call(0.25), call(0.625)]
            mock_sleep.assert_has_calls(expected_calls)

    def test_timeout_set_correctly(self) -> None:
        with patch.object(SPARQLWrapper, "setTimeout") as mock_set_timeout:
            SPARQLWrapperWithRetry("http://example.com/sparql", timeout=15.0)
            mock_set_timeout.assert_called_once_with(15)
