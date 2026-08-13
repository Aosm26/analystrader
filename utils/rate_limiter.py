"""
Rate Limiter

API çağrılarını hız sınırına tabi tutar.
TradingView'in rate limit'ine takılmamak için.
"""

import time
import logging
from collections import deque
from threading import Lock

logger = logging.getLogger("crypto_bot.rate_limiter")


class RateLimiter:
    """
    Token bucket benzeri rate limiter.
    Belirli süre içinde maksimum çağrı sayısını sınırlar.
    """

    def __init__(self, max_calls: int = 10, period: float = 60.0):
        """
        Args:
            max_calls: Dönem içinde izin verilen maksimum çağrı
            period: Dönem süresi (saniye)
        """
        self.max_calls = max_calls
        self.period = period
        self._calls: deque = deque()
        self._lock = Lock()

    def wait_if_needed(self) -> None:
        """
        Rate limit'e takılacaksak, uygun süre kadar bekler.
        """
        with self._lock:
            now = time.time()

            # Süresi dolmuş kayıtları temizle
            while self._calls and self._calls[0] <= now - self.period:
                self._calls.popleft()

            if len(self._calls) >= self.max_calls:
                # En eski çağrının süresinin dolmasını bekle
                sleep_time = self._calls[0] - (now - self.period)
                if sleep_time > 0:
                    logger.debug(f"Rate limit: {sleep_time:.1f}s bekleniyor...")
                    time.sleep(sleep_time)

            self._calls.append(time.time())

    @property
    def remaining_calls(self) -> int:
        """Kalan çağrı hakkı."""
        now = time.time()
        while self._calls and self._calls[0] <= now - self.period:
            self._calls.popleft()
        return max(0, self.max_calls - len(self._calls))
