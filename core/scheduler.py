"""
Scheduler Module — Periodic Task Execution

Manages periodic scanning loops and handles graceful shutdown signals.
"""

from __future__ import annotations

import logging
import signal
import sys
import time
from typing import Callable, Optional

import schedule

from config.settings import Settings

logger = logging.getLogger("crypto_bot.scheduler")


class BotScheduler:
    """Manages interval-based periodic execution."""

    def __init__(self):
        self.settings = Settings()
        self.interval = self.settings.get("bot.scan_interval", 300)
        self._running = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Sets up graceful exit handlers for SIGINT (Ctrl+C) and SIGTERM."""
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)

    def _handle_exit(self, signum, frame) -> None:
        """Handles termination signals."""
        logger.info(f"Received exit signal ({signum}). Stopping scheduler...")
        self.stop()

    def schedule_scan(self, job: Callable[[], None]) -> None:
        """Schedules periodic scan job at configured intervals."""
        schedule.clear()
        schedule.every(self.interval).seconds.do(job)
        logger.info(
            f"⏰ Periodic scan scheduled every {self.interval} seconds."
        )

    def run(self, run_immediately: bool = True) -> None:
        """
        Starts the scheduler loop.

        Args:
            run_immediately: Runs job once immediately before starting interval loop
        """
        self._running = True
        logger.info("🚀 Scheduler loop started.")

        if run_immediately:
            logger.info("⚡ Executing initial scan immediately...")
            schedule.run_all()

        while self._running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received. Stopping...")
                self.stop()
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}", exc_info=True)
                time.sleep(5)

        logger.info("🛑 Scheduler loop terminated.")

    def stop(self) -> None:
        """Stops the scheduler loop gracefully."""
        self._running = False
