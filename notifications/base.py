"""
Base Notifier — Bildirim Arayüzü

Tüm bildirim kanalları bu abstract class'tan türer.
"""

from __future__ import annotations


from abc import ABC, abstractmethod

from models.signal import Signal
from models.scan_result import ScanResult


class BaseNotifier(ABC):
    """Bildirim kanalları için temel arayüz."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Bildirim kanalının adı."""
        pass

    @abstractmethod
    def send_signal(self, signal: Signal) -> bool:
        """
        Tek bir sinyal bildirimi gönderir.

        Returns:
            bool: Başarılı ise True
        """
        pass

    @abstractmethod
    def send_summary(self, result: ScanResult) -> bool:
        """
        Tarama özeti bildirimi gönderir.

        Returns:
            bool: Başarılı ise True
        """
        pass

    def send_signals(self, signals: list[Signal]) -> int:
        """
        Birden fazla sinyal gönderir.

        Returns:
            int: Başarıyla gönderilen sinyal sayısı
        """
        sent = 0
        for signal in signals:
            if self.send_signal(signal):
                sent += 1
        return sent
