"""
Storage Base Interface

Abstract base class for all signal persistence engines.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from models.scan_result import ScanResult
from models.signal import Signal


class BaseStorage(ABC):
    """Abstract persistence interface."""

    @abstractmethod
    def save_signal(self, signal: Signal) -> bool:
        """Saves a single signal."""
        pass

    @abstractmethod
    def save_signals(self, signals: list[Signal]) -> int:
        """Saves multiple signals in batch."""
        pass

    @abstractmethod
    def get_signals(
        self,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[Signal]:
        """Queries stored signals by filters."""
        pass

    @abstractmethod
    def save_scan_log(
        self,
        scan_time: datetime,
        total_scanned: int,
        signal_count: int,
        errors: list[str],
    ) -> None:
        """Saves scan cycle log metrics."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Closes storage connection resources."""
        pass
