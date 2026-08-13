"""
Telegram Notifier

Telegram üzerinden sinyal bildirimi gönderir.
python-telegram-bot kütüphanesini kullanır.
"""

from __future__ import annotations


import logging
from typing import Optional

import requests

from models.signal import Signal, SignalType
from models.scan_result import ScanResult
from notifications.base import BaseNotifier
from utils.helpers import format_price

logger = logging.getLogger("crypto_bot.notifier.telegram")


class TelegramNotifier(BaseNotifier):
    """Telegram bot bildirimi."""

    @property
    def name(self) -> str:
        return "telegram"

    def __init__(self, bot_token: str, chat_id: str):
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._api_base = f"https://api.telegram.org/bot{bot_token}"

    def _send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Telegram API'ye mesaj gönderir."""
        try:
            url = f"{self._api_base}/sendMessage"
            payload = {
                "chat_id": self._chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            }

            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()

            logger.debug("Telegram mesajı gönderildi.")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Telegram gönderim hatası: {e}")
            return False

    def _format_signal(self, signal: Signal) -> str:
        """Sinyali Telegram HTML formatına çevirir."""
        emoji = {
            SignalType.BUY: "🟢",
            SignalType.STRONG_BUY: "🟢🟢",
            SignalType.SELL: "🔴",
            SignalType.STRONG_SELL: "🔴🔴",
            SignalType.NEUTRAL: "⚪",
        }.get(signal.signal_type, "⚪")

        return (
            f"{emoji} <b>{signal.signal_type.value}</b>\n"
            f"📌 <code>{signal.symbol}</code>\n"
            f"💰 Fiyat: {format_price(signal.price)}\n"
            f"📊 Strateji: {signal.strategy_name}\n"
            f"🎯 Güven: {signal.confidence:.0f}%\n"
            f"💬 {signal.message}\n"
            f"⏰ {signal.timestamp.strftime('%H:%M:%S')}"
        )

    def send_signal(self, signal: Signal) -> bool:
        """Tek bir sinyali Telegram'a gönderir."""
        text = self._format_signal(signal)
        return self._send_message(text)

    def send_summary(self, result: ScanResult) -> bool:
        """Tarama özetini Telegram'a gönderir."""
        if not result.has_signals:
            return True  # Sinyal yoksa göndermeye gerek yok

        lines = [
            f"📊 <b>Tarama Raporu</b> — {result.scan_time.strftime('%H:%M:%S')}",
            f"Taranan: {result.total_coins_scanned} coin",
            f"Sinyal: {result.signal_count} "
            f"(🟢 {len(result.buy_signals)} | 🔴 {len(result.sell_signals)})",
            "",
        ]

        # En yüksek güvenilirlikli 10 sinyali göster
        top_signals = result.signals[:10]
        for signal in top_signals:
            emoji = "🟢" if signal.is_buy else "🔴" if signal.is_sell else "⚪"
            lines.append(
                f"{emoji} <code>{signal.symbol}</code> | "
                f"{format_price(signal.price)} | "
                f"Güven: {signal.confidence:.0f}%"
            )

        if len(result.signals) > 10:
            lines.append(f"\n... ve {len(result.signals) - 10} sinyal daha")

        text = "\n".join(lines)
        return self._send_message(text)

    def test_connection(self) -> bool:
        """Telegram bağlantısını test eder."""
        try:
            url = f"{self._api_base}/getMe"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            bot_name = data.get("result", {}).get("username", "?")
            logger.info(f"✅ Telegram bağlantısı başarılı: @{bot_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Telegram bağlantı hatası: {e}")
            return False
