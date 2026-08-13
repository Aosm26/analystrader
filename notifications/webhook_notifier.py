"""
Webhook Notifier

Dispatches JSON payloads over HTTP POST requests to Webhook endpoints (n8n, Make, Discord, Slack).
"""

from __future__ import annotations

import logging
import requests

from models.scan_result import ScanResult
from models.signal import Signal
from notifications.base import BaseNotifier

logger = logging.getLogger("crypto_bot.notifier.webhook")


class WebhookNotifier(BaseNotifier):
    """Sends JSON webhook alerts over HTTP POST requests."""

    @property
    def name(self) -> str:
        return "webhook"

    def __init__(self, url: str):
        self.url = url

    def send_signal(self, signal: Signal) -> bool:
        """Dispatches an individual signal payload to Webhook URL."""
        payload = {
            "event": "signal",
            "data": signal.to_dict(),
        }
        return self._post(payload)

    def send_summary(self, result: ScanResult) -> bool:
        """Dispatches a scan summary payload to Webhook URL."""
        payload = {
            "event": "summary",
            "data": result.to_dict(),
        }
        return self._post(payload)

    def _post(self, payload: dict) -> bool:
        """Executes HTTP POST request to endpoint."""
        try:
            resp = requests.post(self.url, json=payload, timeout=10)
            if resp.status_code in (200, 201, 202, 204):
                logger.info(f"✅ Webhook payload sent to {self.url}")
                return True
            logger.error(f"Webhook HTTP error ({resp.status_code}): {resp.text}")
            return False
        except Exception as e:
            logger.error(f"Webhook dispatch error: {e}")
            return False
