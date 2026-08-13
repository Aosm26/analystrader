"""
Notifier Interface

Base interface for all notification dispatch channels.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from models.scan_result import ScanResult
from models.signal import Signal


class BaseNotifier(ABC):
    """Abstract Base Class for Notification Engines."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Notifier unique name identifier."""
        pass

    @abstractmethod
    def send_signal(self, signal: Signal) -> bool:
        """Sends an individual signal notification."""
        pass

    @abstractmethod
    def send_summary(self, result: ScanResult) -> bool:
        """Sends a consolidated scan summary notification."""
        pass

    def __repr__(self) -> str:
        return f"<Notifier: {self.name}>"
