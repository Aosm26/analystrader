"""
Console Notifier

Konsola renkli sinyal çıktısı yazdırır.
"""

from __future__ import annotations


import logging

from models.signal import Signal, SignalType
from models.scan_result import ScanResult
from notifications.base import BaseNotifier
from utils.helpers import format_price, format_number

logger = logging.getLogger("crypto_bot.notifier.console")


class ConsoleNotifier(BaseNotifier):
    """Terminal/konsol bildirimi."""

    @property
    def name(self) -> str:
        return "console"

    def __init__(self, colored: bool = True):
        self._colored = colored

    def _colorize(self, text: str, signal_type: SignalType) -> str:
        """ANSI renk kodları ile metni renklendirir."""
        if not self._colored:
            return text

        colors = {
            SignalType.BUY: "\033[92m",       # Yeşil
            SignalType.STRONG_BUY: "\033[92;1m",  # Koyu yeşil
            SignalType.SELL: "\033[91m",       # Kırmızı
            SignalType.STRONG_SELL: "\033[91;1m",  # Koyu kırmızı
            SignalType.NEUTRAL: "\033[93m",    # Sarı
        }
        reset = "\033[0m"
        color = colors.get(signal_type, "")
        return f"{color}{text}{reset}"

    def send_signal(self, signal: Signal) -> bool:
        """Sinyali konsola yazdırır."""
        try:
            emoji = {
                SignalType.BUY: "🟢",
                SignalType.STRONG_BUY: "🟢🟢",
                SignalType.SELL: "🔴",
                SignalType.STRONG_SELL: "🔴🔴",
                SignalType.NEUTRAL: "⚪",
            }.get(signal.signal_type, "⚪")

            line = (
                f"  {emoji} {signal.signal_type.value:<12} "
                f"│ {signal.symbol:<15} "
                f"│ {format_price(signal.price):<14} "
                f"│ {signal.strategy_name:<16} "
                f"│ Güven: {signal.confidence:.0f}%"
            )

            colored_line = self._colorize(line, signal.signal_type)
            print(colored_line)

            if signal.message:
                detail = f"     └─ {signal.message}"
                print(self._colorize(detail, signal.signal_type))

            return True

        except Exception as e:
            logger.error(f"Konsol çıktı hatası: {e}")
            return False

    def send_summary(self, result: ScanResult) -> bool:
        """Tarama özetini konsola yazdırır."""
        try:
            separator = "═" * 80
            print(f"\n{separator}")
            print(result.summary())
            print(f"{separator}")

            if result.has_signals:
                header = (
                    f"  {'':2} {'TİP':<12} "
                    f"│ {'SEMBOL':<15} "
                    f"│ {'FİYAT':<14} "
                    f"│ {'STRATEJİ':<16} "
                    f"│ GÜVENİLİRLİK"
                )
                print(header)
                print(f"  {'─' * 76}")

                for signal in result.signals:
                    self.send_signal(signal)

            print(f"{separator}\n")
            return True

        except Exception as e:
            logger.error(f"Konsol özet hatası: {e}")
            return False
