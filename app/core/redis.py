import json
import os
from json import JSONDecodeError
from typing import cast

from fastapi import FastAPI
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app import logger


class RedisHelper:
    """Helper class for Redis operations."""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0) -> None:
        """Initialize Redis connection.

        Args:
        ----
            host: Redis host address
            port: Redis port number
            db: Redis database number

        """
        self.redis_client = Redis(
            host=host, port=port, db=db, decode_responses=True, password=os.getenv("REDIS_PASSWORD")
        )

    async def set(
        self,
        key: str,
        value: str | bytes | int | float | dict[str, object] | list[object] | bool,
        *,
        expire: int | None = None,
        to_json: bool = False,
    ) -> bool:
        """To Set key-value pair in Redis."""
        try:
            val_to_set: str | bytes | int | float
            if to_json:
                try:
                    val_to_set = json.dumps(value)
                except (TypeError, ValueError) as e:
                    logger.exception(f"Error Json Dumps in Redis Set: {e!r}")
                    return False
            else:
                if isinstance(value, bool):
                    val_to_set = str(value)
                elif isinstance(value, (str, bytes, int, float)):
                    val_to_set = value
                else:
                    # Fallback serialization for dict/list if to_json was False
                    try:
                        val_to_set = json.dumps(value)
                    except (TypeError, ValueError) as e:
                        logger.exception(f"Error encoding value for Redis: {e!r}")
                        return False

            await self.redis_client.set(key, val_to_set, ex=expire)
            return True
        except (RedisError, OSError) as e:
            logger.exception(f"Error setting Redis key: {e!r}")
            return False

    async def get(
        self, key: str, *, to_json: bool = False
    ) -> str | int | float | bool | dict[str, object] | list[object] | None:
        """Get value for key from Redis."""
        try:
            val: str | bytes | bytearray | None = await self.redis_client.get(key)
            if isinstance(val, bytearray | bytes):
                val = val.decode("utf-8")

            if val and to_json:
                try:
                    return cast(
                        "dict[str, object] | list[object] | str | int | float | bool", json.loads(val)
                    )
                except (JSONDecodeError, TypeError) as e:
                    logger.exception(f"Error decoding JSON from Redis: {e!r}")
                    return val

        except (RedisError, OSError) as e:
            logger.exception(f"Error getting Redis key: {e!r}")
            return None
        else:
            return val

    async def delete(self, key: str) -> bool:
        """Delete key from Redis.

        Args:
        ----
            key: Redis key

        Returns:
        -------
            bool: True if successful, False otherwise

        """
        try:
            return bool(await self.redis_client.delete(key))
        except (RedisError, OSError) as e:
            logger.exception(f"Error deleting Redis key: {e!r}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis.

        Args:
        ----
            key: Redis key

        Returns:
        -------
            bool: True if key exists, False otherwise

        """
        try:
            return bool(await self.redis_client.exists(key))
        except (RedisError, OSError) as e:
            logger.exception(f"Error checking Redis key: {e!r}")
            return False

    async def flush(self) -> bool:
        """Clear all keys from current database.

        Returns
        -------
            bool: True if successful, False otherwise

        """
        try:
            await self.redis_client.flushdb()
            return True
        except (RedisError, OSError) as e:
            logger.exception(f"Error flushing Redis db: {e!r}")
            return False


def add_cache_layer(app: FastAPI) -> None:
    try:
        app.state.cache = RedisHelper()
    except (RedisError, OSError, ValueError) as e:
        logger.error(e)
