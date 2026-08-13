#!/usr/bin/env python3
from __future__ import annotations
"""
AnalyTrader Crypto Screener Bot — Main Entry Point

Scans crypto markets via TVScreener API, generates signals using technical
analysis strategies, and dispatches real-time alerts.

Usage:
    python main.py              # Normal periodic scanning
    python main.py --once       # Single scan cycle execution
    python main.py --discover   # List available fields
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import Settings
from config.logging_config import setup_logging
from core.scanner import CryptoScanner
from core.analyzer import Analyzer
from core.scheduler import BotScheduler
from strategies import RSIStrategy, MACDStrategy, VolumeSpikeStrategy
from notifications import ConsoleNotifier, TelegramNotifier, WebhookNotifier
from storage import SQLiteStorage


class CryptoBot:
    """Main Bot Orchestrator — Binds all core components together."""

    def __init__(self, config_path: str = "config.yaml"):
        self.settings = Settings(config_path)
        self.logger = setup_logging()

        self.scanner = CryptoScanner()
        self.analyzer = Analyzer()
        self.scheduler = BotScheduler()

        self.storage = self._init_storage()
        self.notifiers = self._init_notifiers()

        self._init_strategies()

        self.logger.info("🤖 CryptoBot initialized successfully.")

    def _init_storage(self) -> SQLiteStorage:
        """Initializes storage backend."""
        db_path = self.settings.get("storage.path", "data/signals.db")
        return SQLiteStorage(db_path)

    def _init_notifiers(self) -> list:
        """Initializes active notification channels."""
        notifiers = []

        if self.settings.get("notifications.console.enabled", True):
            colored = self.settings.get("notifications.console.colored", True)
            notifiers.append(ConsoleNotifier(colored=colored))

        if self.settings.get("notifications.telegram.enabled", False):
            token = self.settings.get("notifications.telegram.bot_token", "")
            chat_id = self.settings.get("notifications.telegram.chat_id", "")
            if token and chat_id and token != "your_bot_token_here":
                notifier = TelegramNotifier(bot_token=token, chat_id=chat_id)
                if notifier.test_connection():
                    notifiers.append(notifier)
                else:
                    self.logger.warning("Telegram connection test failed.")
            else:
                self.logger.warning(
                    "Telegram token/chat_id missing. "
                    "Check your .env file."
                )

        if self.settings.get("notifications.webhook.enabled", False):
            url = self.settings.get("notifications.webhook.url", "")
            if url:
                notifiers.append(WebhookNotifier(url=url))

        self.logger.info(
            f"Active notification channels: {[n.name for n in notifiers]}"
        )
        return notifiers

    def _init_strategies(self) -> None:
        """Registers enabled strategies from configuration."""
        enabled = self.settings.get("strategies.enabled", [])

        strategy_map = {
            "rsi_strategy": RSIStrategy,
            "macd_strategy": MACDStrategy,
            "volume_spike": VolumeSpikeStrategy,
        }

        for strategy_name in enabled:
            if strategy_name in strategy_map:
                config = self.settings.get(f"strategies.{strategy_name}", {})
                strategy = strategy_map[strategy_name](config=config)
                self.analyzer.register_strategy(strategy)
            else:
                self.logger.warning(
                    f"Unknown strategy: {strategy_name}. Skipping."
                )

        self.logger.info(
            f"Active strategies: {self.analyzer.strategy_names}"
        )

    def scan_cycle(self) -> None:
        """
        Executes a single scanning cycle:
        1. Market Scan
        2. Signal Analysis
        3. Database Persistence
        4. Alert Notifications
        """
        try:
            df = self.scanner.scan_with_retry()

            if df.empty:
                self.logger.warning("Scan result empty. Skipping cycle.")
                return

            result = self.analyzer.analyze(df)

            if result.has_signals:
                self.storage.save_signals(result.signals)

            self.storage.save_scan_log(
                scan_time=result.scan_time,
                total_scanned=result.total_coins_scanned,
                signal_count=result.signal_count,
                errors=result.errors,
            )

            for notifier in self.notifiers:
                try:
                    notifier.send_summary(result)
                except Exception as e:
                    self.logger.error(
                        f"Notification dispatch error ({notifier.name}): {e}"
                    )

        except Exception as e:
            self.logger.error(f"❌ Scan cycle error: {e}", exc_info=True)

    def run(self, once: bool = False) -> None:
        """
        Starts the bot.

        Args:
            once: If True, executes single scan cycle and exits. Otherwise runs periodically.
        """
        if once:
            self.logger.info("📡 Executing single scan cycle...")
            self.scan_cycle()
        else:
            self.scheduler.schedule_scan(self.scan_cycle)
            self.scheduler.run(run_immediately=True)

        self.shutdown()

    def shutdown(self) -> None:
        """Releases application resources."""
        self.logger.info("🛑 Shutting down bot...")
        self.storage.close()
        self.logger.info("✅ Bot shutdown completed.")


def discover_fields(keyword: str = "") -> None:
    """Lists available TVScreener fields."""
    scanner = CryptoScanner()
    all_fields = scanner.get_field_info()

    if keyword:
        keyword = keyword.lower()
        matched = [
            f for f in all_fields
            if keyword in f["name"].lower() or keyword in f["label"].lower()
        ]
        print(f"\nFound {len(matched)} fields matching '{keyword}':\n")
        for f in matched:
            print(f"  • {f['name']:<35} ({f['label']})")
    else:
        print(f"\nTotal Available Fields: {len(all_fields)}\n")
        for f in all_fields[:30]:
            print(f"  • {f['name']:<35} ({f['label']})")
        if len(all_fields) > 30:
            print(
                f"\n  ... and {len(all_fields) - 30} more. "
                "(Filter with: python main.py --discover <keyword>)"
            )
    print()


def main():
    parser = argparse.ArgumentParser(
        description="AnalyTrader — Quantitative TradingView Crypto Signal Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Execute single scan cycle and exit",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Configuration file path (default: config.yaml)",
    )
    parser.add_argument(
        "--discover",
        type=str,
        nargs="?",
        const="",
        help="List available fields. Optionally filter by keyword.",
    )

    args = parser.parse_args()

    if args.discover is not None:
        Settings(args.config)
        discover_fields(args.discover)
        return

    bot = CryptoBot(config_path=args.config)
    bot.run(once=args.once)


if __name__ == "__main__":
    main()
