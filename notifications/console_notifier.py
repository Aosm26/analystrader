"""
Console Notifier

Formats and prints scan results and signals directly to standard output.
"""

from __future__ import annotations

import logging
from models.scan_result import ScanResult
from models.signal import Signal, SignalType
from notifications.base import BaseNotifier

logger = logging.getLogger("crypto_bot.notifier.console")


class ConsoleNotifier(BaseNotifier):
    """Formats and prints signals with ANSI colors to terminal."""

    # ANSI Color Codes
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @property
    def name(self) -> str:
        return "console"

    def __init__(self, colored: bool = True):
        self.colored = colored

    def _c(self, text: str, color_code: str) -> str:
        """Applies ANSI color if colored output is enabled."""
        if self.colored:
            return f"{color_code}{text}{self.RESET}"
        return text

    def send_signal(self, signal: Signal) -> bool:
        """Prints single signal to console."""
        icon = "🟢" if signal.signal_type.is_buy else "🔴"
        color = self.GREEN if signal.signal_type.is_buy else self.RED

        type_str = self._c(f"{icon} {signal.signal_type.value:<10}", color)
        sym_str = self._c(f"{signal.symbol:<15}", self.BOLD)
        price_str = f"${signal.price:,.4f}" if signal.price < 1 else f"${signal.price:,.2f}"
        conf_str = f"Conf: {signal.confidence:.0f}%"

        print(f"  {type_str} │ {sym_str} │ {price_str:<14} │ {signal.strategy_name:<16} │ {conf_str}")
        print(f"     └─ {signal.message}")
        return True

    def send_summary(self, result: ScanResult) -> bool:
        """Prints structured scan summary report."""
        divider = "═" * 80
        thin_divider = "─" * 76

        time_str = result.scan_time.strftime("%H:%M:%S")

        print(f"\n{divider}")
        print(
            f"📊 Scan Summary | {time_str}\n"
            f"   Scanned: {result.total_coins_scanned} coins\n"
            f"   Signals: {result.signal_count} "
            f"(🟢 {result.buy_signals_count} BUY | 🔴 {result.sell_signals_count} SELL)\n"
            f"   Errors: {len(result.errors)}"
        )
        print(divider)

        if result.has_signals:
            header = f"     {'TYPE':<12} │ {'SYMBOL':<15} │ {'PRICE':<14} │ {'STRATEGY':<16} │ CONFIDENCE"
            print(header)
            print(f"  {thin_divider}")

            for signal in result.signals:
                self.send_signal(signal)

            print(f"{divider}\n")
        else:
            print("  ℹ️ No signals generated during this scan.\n")

        return True
