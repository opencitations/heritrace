from unittest.mock import MagicMock, patch

from heritrace.utils.primary_source_utils import (
    USER_DEFAULT_SOURCE_KEY, get_default_primary_source,
    get_user_default_primary_source, save_user_default_primary_source)


@patch('heritrace.utils.primary_source_utils.current_app')
def test_get_user_default_primary_source_success(mock_current_app, app):
    """Test retrieving user default primary source successfully."""
    user_id = "0000-0000-0000-0001"
    expected_source = "http://user.example.com"
    key = USER_DEFAULT_SOURCE_KEY.format(user_id=user_id)
    mock_redis = MagicMock()
    mock_current_app.redis_client = mock_redis
    
    with app.app_context():
        mock_redis.get.return_value = expected_source.encode('utf-8')
        result = get_user_default_primary_source(user_id)
        
        mock_redis.get.assert_called_once_with(key)
        assert result == expected_source

@patch('heritrace.utils.primary_source_utils.current_app')
def test_get_user_default_primary_source_not_set(mock_current_app, app):
    """Test retrieving user default primary source when not set in Redis."""
    user_id = "0000-0000-0000-0002"
    key = USER_DEFAULT_SOURCE_KEY.format(user_id=user_id)
    mock_redis = MagicMock()
    mock_current_app.redis_client = mock_redis

    with app.app_context():
        mock_redis.get.return_value = None
        result = get_user_default_primary_source(user_id)

        mock_redis.get.assert_called_once_with(key)
        assert result is None

def test_get_user_default_primary_source_no_user_id(app):
    """Test retrieving user default primary source with no user_id provided."""
    with app.app_context():
        result = get_user_default_primary_source(None)
        assert result is None

@patch('heritrace.utils.primary_source_utils.current_app')
def test_get_user_default_primary_source_redis_error(mock_current_app, app):
    """Test retrieving user default primary source when Redis fails."""
    user_id = "0000-0000-0000-0003"
    key = USER_DEFAULT_SOURCE_KEY.format(user_id=user_id)
    mock_redis = MagicMock()
    mock_logger = MagicMock()
    mock_current_app.redis_client = mock_redis
    mock_current_app.logger = mock_logger
    
    with app.app_context():
        mock_redis.get.side_effect = Exception("Redis connection error")
        result = get_user_default_primary_source(user_id)

        mock_redis.get.assert_called_once_with(key)
        mock_logger.error.assert_called_once_with(f"Failed to get user default primary source from Redis: Redis connection error")
        assert result is None

@patch('heritrace.utils.primary_source_utils.get_user_default_primary_source')
def test_get_default_primary_source_user_set(mock_get_user_default, app):
    """Test getting default primary source when user has one set."""
    user_id = "0000-0000-0000-0004"
    user_source = "http://user.specific.source"
    
    with app.app_context():
        mock_get_user_default.return_value = user_source
        result = get_default_primary_source(user_id)
        
        mock_get_user_default.assert_called_once_with(user_id)
        assert result == user_source

@patch('heritrace.utils.primary_source_utils.get_user_default_primary_source')
def test_get_default_primary_source_user_not_set(mock_get_user_default, app):
    """Test getting default primary source falls back to app config."""
    user_id = "0000-0000-0000-0005"
    app_default_source = app.config["PRIMARY_SOURCE"]

    with app.app_context():
        mock_get_user_default.return_value = None
        result = get_default_primary_source(user_id)

        mock_get_user_default.assert_called_once_with(user_id)
        assert result == app_default_source

@patch('validators.url', return_value=True)
@patch('heritrace.utils.primary_source_utils.current_app')
def test_save_user_default_primary_source_success(mock_current_app, mock_validators_url, app):
    """Test saving user default primary source successfully."""
    user_id = "0000-0000-0000-0006"
    primary_source = "http://new.user.source"
    key = USER_DEFAULT_SOURCE_KEY.format(user_id=user_id)
    mock_redis = MagicMock()
    mock_logger = MagicMock()
    mock_current_app.redis_client = mock_redis
    mock_current_app.logger = mock_logger

    with app.app_context():
        result = save_user_default_primary_source(user_id, primary_source)

        mock_redis.set.assert_called_once_with(key, primary_source)
        mock_logger.info.assert_called_once()
        assert result is True

@patch('validators.url', return_value=True)
@patch('heritrace.utils.primary_source_utils.current_app')
def test_save_user_default_primary_source_no_user_id(mock_current_app, mock_validators_url, app):
    """Test saving user default primary source with no user_id."""
    mock_redis = MagicMock()
    mock_current_app.redis_client = mock_redis
    with app.app_context():
        result = save_user_default_primary_source(None, "http://some.url")
        mock_redis.set.assert_not_called()
        assert result is False

@patch('validators.url', return_value=True)
@patch('heritrace.utils.primary_source_utils.current_app')
def test_save_user_default_primary_source_no_source(mock_current_app, mock_validators_url, app):
    """Test saving user default primary source with no primary_source."""
    mock_redis = MagicMock()
    mock_current_app.redis_client = mock_redis
    with app.app_context():
        result = save_user_default_primary_source("user1", None)
        mock_redis.set.assert_not_called()
        assert result is False
        
@patch('validators.url', return_value=False)
@patch('heritrace.utils.primary_source_utils.current_app')
def test_save_user_default_primary_source_invalid_url(mock_current_app, mock_validators_url, app):
    """Test saving user default primary source with an invalid URL."""
    mock_redis = MagicMock()
    mock_current_app.redis_client = mock_redis
    with app.app_context():
        result = save_user_default_primary_source("user1", "invalid-url")
        mock_redis.set.assert_not_called()
        mock_validators_url.assert_called_once_with("invalid-url")
        assert result is False

@patch('validators.url', return_value=True)
@patch('heritrace.utils.primary_source_utils.current_app')
def test_save_user_default_primary_source_redis_error(mock_current_app, mock_validators_url, app):
    """Test saving user default primary source when Redis fails."""
    user_id = "0000-0000-0000-0007"
    primary_source = "http://another.user.source"
    key = USER_DEFAULT_SOURCE_KEY.format(user_id=user_id)
    mock_redis = MagicMock()
    mock_logger = MagicMock()
    mock_current_app.redis_client = mock_redis
    mock_current_app.logger = mock_logger
    
    with app.app_context():
        mock_redis.set.side_effect = Exception("Redis connection error")
        result = save_user_default_primary_source(user_id, primary_source)

        mock_redis.set.assert_called_once_with(key, primary_source)
        mock_logger.error.assert_called_once_with(f"Failed to save user default primary source to Redis: Redis connection error")
        assert result is False 