"""
Base Storage — Depolama Arayüzü

Tüm depolama backend'leri bu abstract class'tan türer.
"""

from __future__ import annotations


from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from models.signal import Signal


class BaseStorage(ABC):
    """Depolama arayüzü."""

    @abstractmethod
    def save_signal(self, signal: Signal) -> bool:
        """Tek bir sinyali kaydeder."""
        pass

    @abstractmethod
    def save_signals(self, signals: list[Signal]) -> int:
        """Birden fazla sinyali kaydeder. Kaydedilen sayısını döner."""
        pass

    @abstractmethod
    def get_signals(
        self,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[Signal]:
        """Filtrelere göre sinyalleri getirir."""
        pass

    @abstractmethod
    def get_signal_count(
        self,
        symbol: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> int:
        """Sinyal sayısını döner."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Bağlantıyı kapatır."""
        pass
