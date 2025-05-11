from flask import current_app
import validators

USER_DEFAULT_SOURCE_KEY = "user:{user_id}:default_primary_source"

def get_user_default_primary_source(user_id):
    """
    Get the user's default primary source from Redis
    
    Args:
        user_id: The user's ID (e.g. ORCID)
        
    Returns:
        The user's default primary source or None if not set or error
    """
    user_default_source = None
    if user_id:
        key = USER_DEFAULT_SOURCE_KEY.format(user_id=user_id)
        try:
            user_default_source = current_app.redis_client.get(key)
            if user_default_source and isinstance(user_default_source, bytes):
                user_default_source = user_default_source.decode('utf-8')
        except Exception as e:
            current_app.logger.error(f"Failed to get user default primary source from Redis: {e}")
            user_default_source = None  # Ensure it's None on error
    
    return user_default_source

def get_default_primary_source(user_id):
    """
    Get the default primary source to use, falling back to app config if user has none
    
    Args:
        user_id: The user's ID (e.g. ORCID)
        
    Returns:
        The primary source to use (user's default or app default)
    """
    user_default = get_user_default_primary_source(user_id)
    return user_default or current_app.config["PRIMARY_SOURCE"]

def save_user_default_primary_source(user_id, primary_source):
    """
    Save the user's default primary source to Redis
    
    Args:
        user_id: The user's ID (e.g. ORCID)
        primary_source: The URL to save as default primary source
        
    Returns:
        True if saved successfully, False otherwise
    """
    if not user_id or not primary_source or not validators.url(primary_source):
        return False
        
    key = USER_DEFAULT_SOURCE_KEY.format(user_id=user_id)
    try:
        current_app.redis_client.set(key, primary_source)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to save user default primary source to Redis: {e}")
        return False 