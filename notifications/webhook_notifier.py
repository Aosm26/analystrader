"""
Webhook Notifier

HTTP webhook üzerinden sinyal gönderir.
Discord, Slack, n8n, Make.com vb. ile entegre edilebilir.
"""

from __future__ import annotations


import logging
import json

import requests

from models.signal import Signal
from models.scan_result import ScanResult
from notifications.base import BaseNotifier

logger = logging.getLogger("crypto_bot.notifier.webhook")


class WebhookNotifier(BaseNotifier):
    """Webhook bildirimi."""

    @property
    def name(self) -> str:
        return "webhook"

    def __init__(self, url: str, headers: dict = None):
        self._url = url
        self._headers = headers or {"Content-Type": "application/json"}

    def send_signal(self, signal: Signal) -> bool:
        """Sinyali webhook'a POST eder."""
        try:
            payload = {
                "event": "signal",
                "data": signal.to_dict(),
            }

            response = requests.post(
                self._url,
                json=payload,
                headers=self._headers,
                timeout=10,
            )
            response.raise_for_status()
            logger.debug(f"Webhook gönderildi: {signal.symbol}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Webhook hatası: {e}")
            return False

    def send_summary(self, result: ScanResult) -> bool:
        """Tarama özetini webhook'a gönderir."""
        try:
            payload = {
                "event": "scan_summary",
                "data": {
                    "scan_time": result.scan_time.isoformat(),
                    "total_scanned": result.total_coins_scanned,
                    "signal_count": result.signal_count,
                    "buy_count": len(result.buy_signals),
                    "sell_count": len(result.sell_signals),
                    "signals": [s.to_dict() for s in result.signals[:20]],
                },
            }

            response = requests.post(
                self._url,
                json=payload,
                headers=self._headers,
                timeout=10,
            )
            response.raise_for_status()
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Webhook özet hatası: {e}")
            return False
