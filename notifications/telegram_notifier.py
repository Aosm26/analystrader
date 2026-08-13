"""
Telegram Notifier

Sends formatted alerts and summary reports to Telegram via Bot API.
"""

from __future__ import annotations

import logging
from typing import Optional

import requests

from models.scan_result import ScanResult
from models.signal import Signal
from notifications.base import BaseNotifier

logger = logging.getLogger("crypto_bot.notifier.telegram")


class TelegramNotifier(BaseNotifier):
    """Sends HTML formatted messages to Telegram chats."""

    @property
    def name(self) -> str:
        return "telegram"

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    def test_connection(self) -> bool:
        """Tests Telegram Bot token and connection."""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200 and resp.json().get("ok"):
                logger.info("✅ Telegram bot connection successful.")
                return True
            logger.warning(f"Telegram connection failed: {resp.text}")
            return False
        except Exception as e:
            logger.error(f"Telegram connection test error: {e}")
            return False

    def _send_message(self, html_text: str) -> bool:
        """Sends HTML payload to Telegram API."""
        try:
            payload = {
                "chat_id": self.chat_id,
                "text": html_text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }
            resp = requests.post(self.api_url, json=payload, timeout=10)
            if resp.status_code == 200:
                return True
            logger.error(f"Telegram API error ({resp.status_code}): {resp.text}")
            return False
        except Exception as e:
            logger.error(f"Telegram dispatch error: {e}")
            return False

    def send_signal(self, signal: Signal) -> bool:
        """Dispatches an individual signal alert to Telegram."""
        icon = "🟢" if signal.signal_type.is_buy else "🔴"
        price_str = f"${signal.price:,.4f}" if signal.price < 1 else f"${signal.price:,.2f}"

        msg = (
            f"<b>{icon} {signal.signal_type.value} ALERT — {signal.symbol}</b>\n\n"
            f"<b>Price:</b> <code>{price_str}</code>\n"
            f"<b>Strategy:</b> <code>{signal.strategy_name}</code>\n"
            f"<b>Confidence:</b> <code>{signal.confidence:.0f}%</code>\n"
            f"<b>Details:</b> {signal.message}\n"
            f"<b>Time:</b> <code>{signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</code>"
        )
        return self._send_message(msg)

    def send_summary(self, result: ScanResult) -> bool:
        """Dispatches consolidated scan summary report to Telegram."""
        if not result.has_signals:
            return True

        time_str = result.scan_time.strftime("%H:%M:%S")
        lines = [
            f"<b>📊 SCAN REPORT | {time_str}</b>",
            f"Coins Scanned: <code>{result.total_coins_scanned}</code>",
            f"Signals: <code>{result.signal_count}</code> (🟢 {result.buy_signals_count} BUY | 🔴 {result.sell_signals_count} SELL)",
            "───────────────",
        ]

        top_signals = result.signals[:10]
        for sig in top_signals:
            icon = "🟢" if sig.signal_type.is_buy else "🔴"
            price_str = f"${sig.price:,.4f}" if sig.price < 1 else f"${sig.price:,.2f}"
            lines.append(
                f"{icon} <b>{sig.symbol}</b> | {sig.signal_type.value} | <code>{price_str}</code> | {sig.confidence:.0f}%"
            )

        if len(result.signals) > 10:
            lines.append(f"\n<i>... and {len(result.signals) - 10} more signals.</i>")

        return self._send_message("\n".join(lines))
