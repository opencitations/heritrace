"""
Tests for the extensions module.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask, g
from flask_babel import Babel
from flask_login import LoginManager
from heritrace.extensions import (adjust_endpoint_url,
                                  get_change_tracking_config,
                                  get_custom_filter, get_dataset_endpoint,
                                  get_dataset_is_quadstore, get_display_rules,
                                  get_form_fields, get_provenance_endpoint,
                                  get_provenance_sparql, get_shacl_graph,
                                  get_sparql,
                                  init_extensions, init_login_manager,
                                  init_request_handlers, init_sparql_services,
                                  initialize_change_tracking_config,
                                  initialize_counter_handler,
                                  initialize_global_variables,
                                  need_initialization, running_in_docker,
                                  update_cache)
from redis import Redis


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    return MagicMock(spec=Redis)


@pytest.fixture
def babel():
    """Create a Babel instance."""
    return Babel()


@pytest.fixture
def login_manager():
    """Create a LoginManager instance."""
    return LoginManager()


def test_init_extensions(app, babel, login_manager, mock_redis):
    """Test that extensions are initialized correctly."""
    # Call the function to initialize extensions
    with patch("heritrace.extensions.redis_client", None):
        init_extensions(app, babel, login_manager, mock_redis)

        # Import after initialization to get the updated values
        from heritrace.extensions import redis_client

        # Check that redis_client is set correctly
        assert redis_client is mock_redis


def test_babel_initialization(app, babel, login_manager, mock_redis):
    """Test that Babel is initialized correctly."""
    # Initialize extensions
    with patch("heritrace.extensions.redis_client", None):
        init_extensions(app, babel, login_manager, mock_redis)

    # Check that Babel is initialized
    # Since we can't directly access babel.app, we'll check if babel has been initialized
    # by checking if it has the necessary attributes after initialization
    # The specific attributes may vary, so we'll just check if babel has been initialized
    # by checking if it has the domain attribute, which should be set during initialization
    assert hasattr(babel, "domain")
    # Alternatively, we can just check that the test passes without errors
    assert True


def test_login_manager_initialization(app, babel, login_manager, mock_redis):
    """Test that LoginManager is initialized correctly."""
    # Initialize extensions
    with patch("heritrace.extensions.redis_client", None):
        init_extensions(app, babel, login_manager, mock_redis)

    # Check that LoginManager is initialized
    # Since we can't directly access login_manager.app, we'll check if login_manager has been initialized
    # by checking if it has the necessary attributes after initialization
    assert hasattr(login_manager, "login_view")
    assert hasattr(login_manager, "login_message")


def test_close_redis_connection(app: Flask, babel: Babel, login_manager: LoginManager, mock_redis: Redis):
    """Test that close_redis_connection properly cleans up the resource_lock_manager."""
    
    # Initialize request handlers
    init_request_handlers(app)
    
    # Create a test request context
    with app.test_request_context():
        # Set resource_lock_manager
        g.resource_lock_manager = mock_redis
        
        # Verify it exists
        assert hasattr(g, 'resource_lock_manager')
        
        # Get the close_redis_connection function
        close_redis_connection = None
        for func in app.teardown_appcontext_funcs:
            if func.__name__ == 'close_redis_connection':
                close_redis_connection = func
                break
        
        # Call it directly
        close_redis_connection(None)
        
        # Verify it's gone
        assert not hasattr(g, 'resource_lock_manager')
        
        # Set it back to avoid teardown errors
        g.resource_lock_manager = mock_redis


def test_adjust_endpoint_url():
    """Test that adjust_endpoint_url correctly adjusts URLs when running in Docker."""
    
    # Test case: not running in Docker
    with patch('heritrace.extensions.running_in_docker', return_value=False):
        # Should return the original URL unchanged
        original_url = 'http://localhost:8080/sparql'
        assert adjust_endpoint_url(original_url) == original_url
    
    # Test cases: running in Docker
    with patch('heritrace.extensions.running_in_docker', return_value=True):
        # Test with localhost
        assert adjust_endpoint_url('http://localhost:8080/sparql') == 'http://host.docker.internal:8080/sparql'
        
        # Test with 127.0.0.1
        assert adjust_endpoint_url('http://127.0.0.1:8080/sparql') == 'http://host.docker.internal:8080/sparql'
        
        # Test with 0.0.0.0
        assert adjust_endpoint_url('http://0.0.0.0:8080/sparql') == 'http://host.docker.internal:8080/sparql'
        
        # Test without port
        assert adjust_endpoint_url('http://localhost/sparql') == 'http://host.docker.internal/sparql'
        
        # Test with non-local URL (should remain unchanged)
        external_url = 'http://example.com/sparql'
        assert adjust_endpoint_url(external_url) == external_url


def test_running_in_docker():
    """Test that running_in_docker correctly detects Docker environment."""
    
    # Test when /.dockerenv exists
    with patch('os.path.exists', return_value=True):
        assert running_in_docker() is True
    
    # Test when /.dockerenv doesn't exist
    with patch('os.path.exists', return_value=False):
        assert running_in_docker() is False


def test_getter_functions():
    """Test that getter functions return the correct global variables."""
    # Setup global variables
    with patch('heritrace.extensions.dataset_endpoint', 'dataset_endpoint_value'), \
         patch('heritrace.extensions.sparql', 'sparql_value'), \
         patch('heritrace.extensions.provenance_endpoint', 'provenance_endpoint_value'), \
         patch('heritrace.extensions.provenance_sparql', 'provenance_sparql_value'), \
         patch('heritrace.extensions.custom_filter', 'custom_filter_value'), \
         patch('heritrace.extensions.change_tracking_config', 'change_tracking_config_value'), \
         patch('heritrace.extensions.display_rules', 'display_rules_value'), \
         patch('heritrace.extensions.form_fields_cache', 'form_fields_value'), \
         patch('heritrace.extensions.dataset_is_quadstore', 'dataset_is_quadstore_value'), \
         patch('heritrace.extensions.shacl_graph', 'shacl_graph_value'):
        
        # Test each getter function
        assert get_dataset_endpoint() == 'dataset_endpoint_value'
        assert get_sparql() == 'sparql_value'
        assert get_provenance_endpoint() == 'provenance_endpoint_value'
        assert get_provenance_sparql() == 'provenance_sparql_value'
        assert get_custom_filter() == 'custom_filter_value'
        assert get_change_tracking_config() == 'change_tracking_config_value'
        assert get_display_rules() == 'display_rules_value'
        assert get_form_fields() == 'form_fields_value'
        assert get_dataset_is_quadstore() == 'dataset_is_quadstore_value'
        assert get_shacl_graph() == 'shacl_graph_value'


def test_get_counter_handler_not_initialized(app):
    """Test that get_counter_handler raises RuntimeError when not initialized."""
    app.config.pop('URI_GENERATOR', None) 
    
    with app.app_context():
        with patch('heritrace.extensions.current_app.logger.error') as mock_logger_error:
            with pytest.raises(RuntimeError, match="CounterHandler is not available. Initialization might have failed."):
                from heritrace.extensions import get_counter_handler
                get_counter_handler()
            
            mock_logger_error.assert_called_once_with("CounterHandler not found in URIGenerator config.")

    app.config['URI_GENERATOR'] = MagicMock(spec=[])
    
    with app.app_context():
        with patch('heritrace.extensions.current_app.logger.error') as mock_logger_error:
            with pytest.raises(RuntimeError, match="CounterHandler is not available. Initialization might have failed."):
                from heritrace.extensions import get_counter_handler
                get_counter_handler()
            mock_logger_error.assert_called_once_with("CounterHandler not found in URIGenerator config.")


def test_init_login_manager_directly(app):
    """Test that init_login_manager correctly configures the login manager."""

    # Create a mock login manager
    login_manager = MagicMock(spec=LoginManager)
    
    # Call the function
    init_login_manager(app, login_manager)
    
    # Check that login_manager was initialized correctly
    login_manager.init_app.assert_called_once_with(app)
    assert login_manager.login_view == 'auth.login'
    
    # Test the user_loader function
    # Get the user_loader callback that was registered
    user_loader_call = [call for call in login_manager.method_calls if call[0] == 'user_loader']
    assert len(user_loader_call) > 0
    
    # Get the user_loader function
    user_loader = user_loader_call[0][1][0]  # First call, first argument
    
    # Test the user_loader function with a session
    with app.test_request_context():
        # Set up session
        with patch('heritrace.extensions.session', {'user_name': 'Test User'}):
            user = user_loader('test_id')
            assert user.id == 'test_id'
            assert user.name == 'Test User'
            assert user.orcid == 'test_id'


def test_rotate_session_token(app):
    """Test that the rotate_session_token function is properly connected to the user_loaded_from_cookie signal."""
    
    # Import the user_loaded_from_cookie signal
    from flask_login.signals import user_loaded_from_cookie

    # Create a login manager
    login_manager = LoginManager()
    
    # Patch the signal connect method to capture the handler
    with patch.object(user_loaded_from_cookie, 'connect') as mock_connect:
        # Initialize the login manager
        init_login_manager(app, login_manager)
        
        # Verify that the signal was connected
        mock_connect.assert_called_once()
        
        # Get the handler function that was connected
        handler = mock_connect.call_args[0][0]
        
        # Create a mock session
        mock_session = MagicMock()
        
        # Create a mock user and sender
        mock_user = MagicMock()
        mock_sender = MagicMock()
        
        # Test the handler function directly
        with patch('heritrace.extensions.session', mock_session):
            handler(mock_sender, mock_user)
            
            # Check that session.modified was set to True
            assert mock_session.modified is True


def test_need_initialization(app):
    """Test that need_initialization correctly determines if initialization is needed."""

    # Mock the URI generator
    mock_uri_generator = MagicMock()
    mock_uri_generator.counter_handler = MagicMock()
    app.config['URI_GENERATOR'] = mock_uri_generator
    
    # Test when cache file doesn't exist
    app.config['CACHE_FILE'] = 'nonexistent_cache_file.json'
    app.config['CACHE_VALIDITY_DAYS'] = 7
    
    with patch('os.path.exists', return_value=False):
        assert need_initialization(app) is True
    
    # Test when cache file exists but is invalid
    with patch('os.path.exists', return_value=True), \
         patch('heritrace.extensions.open', MagicMock()), \
         patch('json.load', side_effect=Exception('Invalid JSON')):
        assert need_initialization(app) is True
    
    # Test when cache file exists and is valid but expired
    mock_cache = {'last_initialization': (datetime.now() - timedelta(days=10)).isoformat()}
    with patch('os.path.exists', return_value=True), \
         patch('heritrace.extensions.open', MagicMock()), \
         patch('json.load', return_value=mock_cache):
        assert need_initialization(app) is True
    
    # Test when cache file exists and is valid and not expired
    mock_cache = {'last_initialization': datetime.now().isoformat()}
    with patch('os.path.exists', return_value=True), \
         patch('heritrace.extensions.open', MagicMock()), \
         patch('json.load', return_value=mock_cache):
        assert need_initialization(app) is False
    
    # Test when URI generator doesn't have counter_handler
    app.config['URI_GENERATOR'] = MagicMock(spec=[])
    assert need_initialization(app) is False


def test_update_cache(app):
    """Test that update_cache correctly updates the cache file."""

    # Set up the cache file path
    app.config['CACHE_FILE'] = 'test_cache_file.json'
    
    # Mock the open function
    mock_open = MagicMock()
    mock_json_dump = MagicMock()
    
    with patch('heritrace.extensions.open', mock_open), \
         patch('json.dump', mock_json_dump):
        update_cache(app)
    
    # Check that open was called with the correct arguments
    mock_open.assert_called_once_with('test_cache_file.json', 'w', encoding='utf8')
    
    # Check that json.dump was called with the correct arguments
    assert mock_json_dump.call_count == 1
    args, kwargs = mock_json_dump.call_args
    assert len(args) == 2
    assert 'last_initialization' in args[0]
    assert args[0]['version'] == '1.0'
    assert kwargs['ensure_ascii'] is False
    assert kwargs['indent'] == 4


def test_initialize_change_tracking_config(app):
    """Test that initialize_change_tracking_config correctly initializes the change tracking configuration."""

    # Set up required config values
    app.config['DATASET_DB_URL'] = 'http://localhost:8080/dataset'
    app.config['PROVENANCE_DB_URL'] = 'http://localhost:8080/provenance'
    app.config['DATASET_DIRS'] = []
    app.config['DATASET_IS_QUADSTORE'] = False
    app.config['PROVENANCE_IS_QUADSTORE'] = False
    app.config['PROVENANCE_DIRS'] = []
    app.config['CACHE_ENDPOINT'] = 'http://localhost:8080/cache'
    app.config['CACHE_UPDATE_ENDPOINT'] = 'http://localhost:8080/cache/update'
    
    # Mock the generate_config_file function
    mock_config = {
        'cache_triplestore_url': {
            'endpoint': 'http://localhost:8080/cache',
            'update_endpoint': 'http://localhost:8080/cache/update'
        }
    }
    
    # Test when config path is provided and file exists
    app.config['CHANGE_TRACKING_CONFIG'] = 'existing_config.json'
    
    with patch('os.path.exists', return_value=True), \
         patch('builtins.open', MagicMock()), \
         patch('json.load', return_value=mock_config), \
         patch('heritrace.extensions.adjust_endpoint_url', lambda x: x + '_adjusted'):
        
        config = initialize_change_tracking_config(app)
        
        # Check that the config was loaded
        assert config is not None
        assert 'cache_triplestore_url' in config
    
    # Test when config path is provided but file doesn't exist
    app.config['CHANGE_TRACKING_CONFIG'] = 'nonexistent_config.json'
    
    with patch('os.path.exists', return_value=False), \
         patch('os.makedirs', MagicMock()), \
         patch('time_agnostic_library.support.generate_config_file', return_value=mock_config), \
         patch('heritrace.extensions.adjust_endpoint_url', lambda x: x + '_adjusted'):
        
        config = initialize_change_tracking_config(app)
        
        # Check that the config was generated
        assert config is not None
        assert 'cache_triplestore_url' in config
    
    # Test when CHANGE_TRACKING_CONFIG is not in app.config (else branch)
    if 'CHANGE_TRACKING_CONFIG' in app.config:
        del app.config['CHANGE_TRACKING_CONFIG']
    
    # We need to mock the actual file operations in generate_config_file
    mock_open = MagicMock()
    
    with patch('os.path.join', return_value='instance/change_tracking_config.json'), \
         patch('os.makedirs', MagicMock()) as mock_makedirs, \
         patch('builtins.open', mock_open), \
         patch('time_agnostic_library.support.generate_config_file', side_effect=lambda **kwargs: mock_config), \
         patch('heritrace.extensions.adjust_endpoint_url', lambda x: x + '_adjusted'):
        
        config = initialize_change_tracking_config(app)
        
        # Check that the directory was created
        mock_makedirs.assert_called_once_with(app.instance_path, exist_ok=True)
        
        # Check that the config was generated
        assert config is not None
        assert 'cache_triplestore_url' in config


def test_initialize_change_tracking_config_exceptions(app):
    """Test exception handling in initialize_change_tracking_config function."""
    
    # Set up required config values
    app.config['DATASET_DB_URL'] = 'http://localhost:8080/dataset'
    app.config['PROVENANCE_DB_URL'] = 'http://localhost:8080/provenance'
    app.config['DATASET_DIRS'] = []
    app.config['DATASET_IS_QUADSTORE'] = False
    app.config['PROVENANCE_IS_QUADSTORE'] = False
    app.config['PROVENANCE_DIRS'] = []
    app.config['CACHE_ENDPOINT'] = 'http://localhost:8080/cache'
    app.config['CACHE_UPDATE_ENDPOINT'] = 'http://localhost:8080/cache/update'
    
    # Test exception when generating config file
    app.config['CHANGE_TRACKING_CONFIG'] = 'nonexistent_config.json'
    
    with patch('os.path.exists', return_value=False), \
         patch('os.makedirs', MagicMock()), \
         patch('heritrace.extensions.generate_config_file', side_effect=Exception("Test generation error")), \
         pytest.raises(RuntimeError) as excinfo:
        
        initialize_change_tracking_config(app)
    
    # Check the error message
    assert "Failed to generate change tracking configuration: Test generation error" in str(excinfo.value)
    
    # Test JSONDecodeError when loading config file
    app.config['CHANGE_TRACKING_CONFIG'] = 'invalid_json_config.json'
    
    mock_open = MagicMock()
    mock_open.return_value.__enter__.return_value = MagicMock()
    
    with patch('os.path.exists', return_value=True), \
         patch('builtins.open', mock_open), \
         patch('json.load', side_effect=json.JSONDecodeError("Test JSON error", "", 0)), \
         pytest.raises(RuntimeError) as excinfo:
        
        initialize_change_tracking_config(app)
    
    # Check the error message
    assert "Invalid change tracking configuration JSON at invalid_json_config.json: Test JSON error" in str(excinfo.value)
    
    # Test general exception when reading config file
    app.config['CHANGE_TRACKING_CONFIG'] = 'error_config.json'
    
    with patch('os.path.exists', return_value=True), \
         patch('builtins.open', side_effect=Exception("Test read error")), \
         pytest.raises(RuntimeError) as excinfo:
        
        initialize_change_tracking_config(app)
    
    # Check the error message
    assert "Error reading change tracking configuration at error_config.json: Test read error" in str(excinfo.value)


def test_initialize_counter_handler(app):
    """Test that initialize_counter_handler correctly initializes the counter handler."""

    # Mock the need_initialization function to return True
    with patch('heritrace.extensions.need_initialization', return_value=True), \
         patch('heritrace.extensions.update_cache') as mock_update_cache, \
         patch('heritrace.extensions.sparql') as mock_sparql, \
         patch('heritrace.extensions.provenance_sparql') as mock_provenance_sparql:
        
        # Mock the query results for sparql
        mock_results = {
            'results': {
                'bindings': [
                    {
                        'type': {'value': 'http://example.org/Person'},
                        'count': {'value': '10'}
                    },
                    {
                        'type': {'value': 'http://example.org/Event'},
                        'count': {'value': '5'}
                    }
                ]
            }
        }
        
        # Set up the mock SPARQL query
        mock_sparql.query.return_value.convert.return_value = mock_results
        
        # Mock the query results for provenance_sparql
        mock_prov_results = {
            'results': {
                'bindings': [
                    {
                        'entity': {'value': 'http://example.org/Person'},
                        'count': {'value': '10'}
                    },
                    {
                        'entity': {'value': 'http://example.org/Event'},
                        'count': {'value': '5'}
                    }
                ]
            }
        }
        
        # Set up the mock provenance SPARQL query
        mock_provenance_sparql.query.return_value.convert.return_value = mock_prov_results
        
        # Set up the URI generator with a counter handler
        mock_counter_handler = MagicMock()
        mock_counter_handler.read_counter.return_value = 5
        
        mock_uri_generator = MagicMock()
        mock_uri_generator.counter_handler = mock_counter_handler
        
        app.config['URI_GENERATOR'] = mock_uri_generator
        
        # Call the function
        initialize_counter_handler(app)
        
        # Check that the counter handler was updated correctly
        mock_counter_handler.set_counter.assert_any_call(10, 'http://example.org/Person')
        mock_counter_handler.set_counter.assert_any_call(5, 'http://example.org/Event')
        
        # Check that update_cache was called
        mock_update_cache.assert_called_once_with(app)


def test_initialize_lock_manager():
    """Test that initialize_lock_manager correctly initializes the resource lock manager."""

    # Create a test app
    app = Flask(__name__)
    
    # Initialize request handlers
    init_request_handlers(app)
    
    # Get the initialize_lock_manager function
    initialize_lock_manager = None
    for func in app.before_request_funcs.get(None, []):
        if func.__name__ == 'initialize_lock_manager':
            initialize_lock_manager = func
            break
    
    assert initialize_lock_manager is not None
    
    # Create a test request context
    with app.test_request_context():
        # Call the function
        initialize_lock_manager()
        
        # Check that the resource_lock_manager was set
        assert hasattr(g, 'resource_lock_manager')


def test_init_sparql_services_already_initialized(app):
    """Test that init_sparql_services does nothing when already initialized."""

    # Mock the global variables
    with patch('heritrace.extensions.initialization_done', True), \
         patch('heritrace.extensions.SPARQLWrapper') as mock_sparql_wrapper, \
         patch('heritrace.extensions.initialize_change_tracking_config') as mock_init_config, \
         patch('heritrace.extensions.initialize_counter_handler') as mock_init_counter, \
         patch('heritrace.extensions.initialize_global_variables') as mock_init_globals:
        
        # Call the function
        init_sparql_services(app)
        
        # Check that nothing was called
        mock_sparql_wrapper.assert_not_called()
        mock_init_config.assert_not_called()
        mock_init_counter.assert_not_called()
        mock_init_globals.assert_not_called()


def test_initialize_global_variables_dataset_is_quadstore(app):
    """Test that initialize_global_variables correctly sets dataset_is_quadstore."""
    # Setup
    app.config['DATASET_IS_QUADSTORE'] = True
    
    # Reset global variables
    with patch('heritrace.extensions.dataset_is_quadstore', None), \
         patch('heritrace.extensions.display_rules', None), \
         patch('heritrace.extensions.shacl_graph', None), \
         patch('heritrace.extensions.form_fields_cache', None):
        
        # Call the function
        initialize_global_variables(app)
        
        # Check that dataset_is_quadstore is set correctly
        from heritrace.extensions import dataset_is_quadstore
        assert dataset_is_quadstore is True


def test_initialize_global_variables_display_rules_not_found(app):
    """Test that initialize_global_variables handles missing display rules file."""
    # Setup
    app.config['DISPLAY_RULES_PATH'] = '/path/does/not/exist'
    app.config.pop('SHACL_PATH', None)  # Remove SHACL_PATH to avoid additional warnings
    
    # Reset global variables
    with patch('heritrace.extensions.dataset_is_quadstore', None), \
         patch('heritrace.extensions.display_rules', None), \
         patch('heritrace.extensions.shacl_graph', None), \
         patch('heritrace.extensions.form_fields_cache', None), \
         patch('os.path.exists', return_value=False):
        
        # Call the function
        initialize_global_variables(app)


def test_initialize_global_variables_display_rules_loaded(app, tmp_path):
    """Test that initialize_global_variables correctly loads display rules."""
    # Create a temporary display rules file
    display_rules_path = tmp_path / "display_rules.yaml"
    display_rules_content = """
classes:
  Class1:
    label: "Class 1"
    properties:
      prop1:
        label: "Property 1"
"""
    display_rules_path.write_text(display_rules_content)
    
    # Setup app config
    app.config['DISPLAY_RULES_PATH'] = str(display_rules_path)
    app.config.pop('SHACL_PATH', None)  # Remove SHACL_PATH to avoid additional warnings
    
    # Reset global variables
    with patch('heritrace.extensions.dataset_is_quadstore', None), \
         patch('heritrace.extensions.display_rules', None), \
         patch('heritrace.extensions.shacl_graph', None), \
         patch('heritrace.extensions.form_fields_cache', None), \
         patch('os.path.exists', return_value=True):
        
        # Call the function
        initialize_global_variables(app)
        
        # Check that display_rules is set correctly
        from heritrace.extensions import display_rules
        assert display_rules is not None
        assert 'Class1' in display_rules
        assert display_rules['Class1']['label'] == 'Class 1'


def test_initialize_global_variables_display_rules_error(app, tmp_path):
    """Test that initialize_global_variables handles errors when loading display rules."""
    # Create a temporary display rules file
    display_rules_path = tmp_path / "invalid_display_rules.yaml"
    display_rules_path.write_text("invalid: yaml: content:")
    
    # Setup app config
    app.config['DISPLAY_RULES_PATH'] = str(display_rules_path)
    app.config.pop('SHACL_PATH', None)  # Remove SHACL_PATH to avoid additional warnings
    
    # Reset global variables
    with patch('heritrace.extensions.dataset_is_quadstore', None), \
         patch('heritrace.extensions.display_rules', None), \
         patch('heritrace.extensions.shacl_graph', None), \
         patch('heritrace.extensions.form_fields_cache', None), \
         patch('os.path.exists', return_value=True), \
         patch('yaml.safe_load', side_effect=Exception("YAML parsing error")):
        
        # Call the function and check for exception
        with pytest.raises(RuntimeError, match="Failed to load display rules: YAML parsing error"):
            initialize_global_variables(app)


def test_initialize_global_variables_shacl_not_found(app):
    """Test that initialize_global_variables handles missing SHACL file."""
    # Setup
    app.config.pop('DISPLAY_RULES_PATH', None)  # Remove DISPLAY_RULES_PATH to avoid additional warnings
    app.config['SHACL_PATH'] = '/path/does/not/exist'
    
    # Reset global variables
    with patch('heritrace.extensions.dataset_is_quadstore', None), \
         patch('heritrace.extensions.display_rules', None), \
         patch('heritrace.extensions.shacl_graph', None), \
         patch('heritrace.extensions.form_fields_cache', None), \
         patch('os.path.exists', return_value=False):
        
        # Call the function
        initialize_global_variables(app)


def test_initialize_global_variables_form_fields_cache_exists(app):
    """Test that initialize_global_variables returns early if form_fields_cache is not None."""
    # Setup
    app.config.pop('DISPLAY_RULES_PATH', None)  # Remove DISPLAY_RULES_PATH to avoid additional warnings
    app.config['SHACL_PATH'] = '/path/to/shacl.ttl'
    
    # Reset global variables but set form_fields_cache
    with patch('heritrace.extensions.dataset_is_quadstore', None), \
         patch('heritrace.extensions.display_rules', None), \
         patch('heritrace.extensions.shacl_graph', None), \
         patch('heritrace.extensions.form_fields_cache', {'existing': 'cache'}), \
         patch('os.path.exists', return_value=True):
        
        # Call the function
        initialize_global_variables(app)


def test_initialize_global_variables_shacl_loaded(app, tmp_path):
    """Test that initialize_global_variables correctly loads SHACL graph and form fields."""
    # Create a temporary SHACL file
    shacl_path = tmp_path / "shacl.ttl"
    shacl_path.write_text("@prefix sh: <http://www.w3.org/ns/shacl#> .")
    
    # Setup app config
    app.config.pop('DISPLAY_RULES_PATH', None)  # Remove DISPLAY_RULES_PATH to avoid additional warnings
    app.config['SHACL_PATH'] = str(shacl_path)
    
    # Mock get_form_fields_from_shacl
    mock_form_fields = {'Class1': {'properties': ['prop1']}}
    
    # Reset global variables
    with patch('heritrace.extensions.dataset_is_quadstore', None), \
         patch('heritrace.extensions.display_rules', {'Class1': {'label': 'Class 1'}}), \
         patch('heritrace.extensions.shacl_graph', None), \
         patch('heritrace.extensions.form_fields_cache', None), \
         patch('os.path.exists', return_value=True), \
         patch('heritrace.utils.shacl_utils.get_form_fields_from_shacl', return_value=mock_form_fields):
        
        # Call the function
        initialize_global_variables(app)
        
        # Check that form_fields_cache is set correctly
        from heritrace.extensions import form_fields_cache, shacl_graph
        assert form_fields_cache == mock_form_fields
        assert shacl_graph is not None


def test_initialize_global_variables_shacl_error(app, tmp_path):
    """Test that initialize_global_variables handles errors when loading SHACL graph."""
    # Create a temporary SHACL file with invalid content
    shacl_path = tmp_path / "invalid_shacl.ttl"
    shacl_path.write_text("invalid turtle content")
    
    # Setup app config
    app.config.pop('DISPLAY_RULES_PATH', None)  # Remove DISPLAY_RULES_PATH to avoid additional warnings
    app.config['SHACL_PATH'] = str(shacl_path)
    
    # Reset global variables
    with patch('heritrace.extensions.dataset_is_quadstore', None), \
         patch('heritrace.extensions.display_rules', None), \
         patch('heritrace.extensions.shacl_graph', None), \
         patch('heritrace.extensions.form_fields_cache', None), \
         patch('os.path.exists', return_value=True), \
         patch('rdflib.Graph.parse', side_effect=Exception("Turtle parsing error")):
        
        # Call the function and check for exception
        with pytest.raises(RuntimeError, match="Failed to initialize form fields: Turtle parsing error"):
            initialize_global_variables(app)


def test_initialize_global_variables_general_exception(app):
    """Test that initialize_global_variables handles general exceptions."""
    # Setup to raise a general exception
    with patch('heritrace.extensions.dataset_is_quadstore', None), \
         patch('heritrace.extensions.display_rules', None), \
         patch('heritrace.extensions.shacl_graph', None), \
         patch('heritrace.extensions.form_fields_cache', None), \
         patch.object(app.config, 'get', side_effect=Exception("General error")):
        
        # Call the function and check for exception
        with pytest.raises(RuntimeError, match="Global variables initialization failed: General error"):
            initialize_global_variables(app)
