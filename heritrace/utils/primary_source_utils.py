# SPDX-FileCopyrightText: 2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from typing import TYPE_CHECKING, cast

from flask import current_app
from redis import RedisError

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
        except RedisError:
            current_app.logger.exception(
                "Failed to get user default primary source from Redis"
            )
            user_default_source = None

    return user_default_source


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
    except RedisError:
        current_app.logger.exception(
            "Failed to save user default primary source to Redis"
        )
        return False
    else:
        return True
