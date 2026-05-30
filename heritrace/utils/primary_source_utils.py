# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from typing import TYPE_CHECKING, cast

from flask import current_app

from heritrace.utils.uri_utils import is_valid_url

if TYPE_CHECKING:
    from redis import Redis

USER_DEFAULT_SOURCE_KEY = "user:{user_id}:default_primary_source"


def get_user_default_primary_source(user_id: str) -> str | None:
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
            redis_client: Redis = current_app.extensions["redis_client"]  # type: ignore[type-arg]
            user_default_source = cast("str | None", redis_client.get(key))
        except Exception as e:
            current_app.logger.error(
                f"Failed to get user default primary source from Redis: {e}"
            )
            user_default_source = None  # Ensure it's None on error

    return user_default_source


def get_default_primary_source(user_id: str) -> str:
    """
    Get the default primary source to use, falling back to app config if user has none

    Args:
        user_id: The user's ID (e.g. ORCID)

    Returns:
        The primary source to use (user's default or app default)
    """
    user_default = get_user_default_primary_source(user_id)
    return user_default or current_app.config["PRIMARY_SOURCE"]


def save_user_default_primary_source(user_id: str, primary_source: str) -> bool | None:
    """
    Save the user's default primary source to Redis

    Args:
        user_id: The user's ID (e.g. ORCID)
        primary_source: The URL to save as default primary source

    Returns:
        True if saved successfully, False otherwise
    """
    if not user_id or not primary_source or not is_valid_url(primary_source):
        return False

    key = USER_DEFAULT_SOURCE_KEY.format(user_id=user_id)
    try:
        redis_client: Redis = current_app.extensions["redis_client"]  # type: ignore[type-arg]
        redis_client.set(key, primary_source)
    except Exception as e:
        current_app.logger.error(
            f"Failed to save user default primary source to Redis: {e}"
        )
        return False
    else:
        return True
