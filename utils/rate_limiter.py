"""
Rate Limiter Utility

Enforces rate limits to prevent API throttling and 429 status codes.
"""

from __future__ import annotations

import logging
import time
from collections import deque

logger = logging.getLogger("crypto_bot.utils.rate_limiter")


class RateLimiter:
    """Thread-safe rate limiter based on sliding window."""

    def __init__(self, max_calls: int = 5, period: float = 60.0):
        self.max_calls = max_calls
        self.period = period
        self.timestamps = deque()

    def wait_if_needed(self) -> None:
        """Blocks thread execution if max_calls limit within period is reached."""
        now = time.time()

        while self.timestamps and (now - self.timestamps[0]) > self.period:
            self.timestamps.popleft()

        if len(self.timestamps) >= self.max_calls:
            sleep_time = self.period - (now - self.timestamps[0]) + 0.5
            if sleep_time > 0:
                logger.info(
                    f"⏳ Rate limit threshold reached ({self.max_calls} calls/{self.period}s). "
                    f"Waiting {sleep_time:.1f}s..."
                )
                time.sleep(sleep_time)
                now = time.time()

                while self.timestamps and (now - self.timestamps[0]) > self.period:
                    self.timestamps.popleft()

        self.timestamps.append(now)
