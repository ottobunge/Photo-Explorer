"""Redis-based rate limiter for API calls."""

import asyncio
import logging
import time
from typing import Optional

from redis import asyncio as aioredis

from app.config import get_settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Redis-based sliding window rate limiter.

    Implements two limits:
    - Per-second limit (e.g., 50 requests/second)
    - Per-day limit (e.g., 10,000 requests/day)
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        key_prefix: str = "rate_limit",
        per_second_limit: int = 50,
        per_day_limit: int = 10000,
    ):
        """
        Initialize rate limiter.

        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for Redis keys
            per_second_limit: Maximum requests per second
            per_day_limit: Maximum requests per day
        """
        settings = get_settings()
        self._redis_url = redis_url or settings.redis_url
        self._key_prefix = key_prefix
        self._per_second_limit = per_second_limit
        self._per_day_limit = per_day_limit
        self._redis: Optional[aioredis.Redis] = None

    async def _get_redis(self) -> aioredis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = await aioredis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    async def check_rate_limit(self, identifier: str) -> tuple[bool, Optional[float]]:
        """
        Check if request is within rate limits.

        Args:
            identifier: Unique identifier for the rate limit (e.g., "google_photos:connector_123")

        Returns:
            Tuple of (allowed, wait_time_seconds)
            - allowed: True if request is allowed, False if rate limited
            - wait_time_seconds: If rate limited, how long to wait before retrying
        """
        redis = await self._get_redis()

        # Check per-second limit
        second_key = f"{self._key_prefix}:{identifier}:second"
        second_count = await redis.incr(second_key)

        if second_count == 1:
            # First request in this second, set expiry
            await redis.expire(second_key, 1)

        if second_count > self._per_second_limit:
            logger.warning(
                f"Rate limit hit for {identifier}: {second_count}/{self._per_second_limit} per second",
                extra={
                    "identifier": identifier,
                    "limit_type": "per_second",
                    "count": second_count,
                    "limit": self._per_second_limit,
                },
            )
            return False, 1.0  # Wait 1 second

        # Check per-day limit
        day_key = f"{self._key_prefix}:{identifier}:day"
        day_count = await redis.incr(day_key)

        if day_count == 1:
            # First request of the day, set expiry to 24 hours
            await redis.expire(day_key, 86400)

        if day_count > self._per_day_limit:
            # Calculate time until daily limit resets
            ttl = await redis.ttl(day_key)
            wait_time = max(ttl, 60)  # At least 60 seconds

            logger.warning(
                f"Daily rate limit hit for {identifier}: {day_count}/{self._per_day_limit}",
                extra={
                    "identifier": identifier,
                    "limit_type": "per_day",
                    "count": day_count,
                    "limit": self._per_day_limit,
                    "reset_in_seconds": ttl,
                },
            )
            return False, wait_time

        return True, None

    async def wait_if_limited(self, identifier: str, max_retries: int = 3) -> bool:
        """
        Check rate limit and wait if necessary.

        Args:
            identifier: Unique identifier for the rate limit
            max_retries: Maximum number of retry attempts

        Returns:
            True if request can proceed, False if max retries exceeded
        """
        for retry in range(max_retries):
            allowed, wait_time = await self.check_rate_limit(identifier)

            if allowed:
                return True

            if wait_time and retry < max_retries - 1:
                logger.info(
                    f"Rate limited, waiting {wait_time}s before retry {retry + 1}/{max_retries}",
                    extra={
                        "identifier": identifier,
                        "wait_time": wait_time,
                        "retry": retry + 1,
                        "max_retries": max_retries,
                    },
                )
                await asyncio.sleep(wait_time)
            else:
                break

        return False

    async def increment(self, identifier: str) -> None:
        """
        Manually increment rate limit counters.

        Useful when you want to track rate limits without blocking.

        Args:
            identifier: Unique identifier for the rate limit
        """
        redis = await self._get_redis()

        # Increment per-second counter
        second_key = f"{self._key_prefix}:{identifier}:second"
        second_count = await redis.incr(second_key)
        if second_count == 1:
            await redis.expire(second_key, 1)

        # Increment per-day counter
        day_key = f"{self._key_prefix}:{identifier}:day"
        day_count = await redis.incr(day_key)
        if day_count == 1:
            await redis.expire(day_key, 86400)

    async def get_current_usage(self, identifier: str) -> dict:
        """
        Get current rate limit usage.

        Args:
            identifier: Unique identifier for the rate limit

        Returns:
            Dictionary with usage statistics
        """
        redis = await self._get_redis()

        second_key = f"{self._key_prefix}:{identifier}:second"
        day_key = f"{self._key_prefix}:{identifier}:day"

        second_count = await redis.get(second_key) or "0"
        day_count = await redis.get(day_key) or "0"
        day_ttl = await redis.ttl(day_key)

        return {
            "per_second": {
                "count": int(second_count),
                "limit": self._per_second_limit,
                "remaining": max(0, self._per_second_limit - int(second_count)),
            },
            "per_day": {
                "count": int(day_count),
                "limit": self._per_day_limit,
                "remaining": max(0, self._per_day_limit - int(day_count)),
                "reset_in_seconds": day_ttl if day_ttl > 0 else 0,
            },
        }

    async def reset(self, identifier: str) -> None:
        """
        Reset rate limit counters for an identifier.

        Args:
            identifier: Unique identifier for the rate limit
        """
        redis = await self._get_redis()

        second_key = f"{self._key_prefix}:{identifier}:second"
        day_key = f"{self._key_prefix}:{identifier}:day"

        await redis.delete(second_key, day_key)
        logger.info(f"Reset rate limit counters for {identifier}")

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
