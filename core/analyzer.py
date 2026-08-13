"""
Analysis Engine — Strategy Execution & Signal Orchestration

Runs scanned DataFrames through active strategies and aggregates generated signals.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

import pandas as pd

from models.scan_result import ScanResult
from models.signal import Signal
from strategies.base import BaseStrategy

logger = logging.getLogger("crypto_bot.analyzer")


class Analyzer:
    """Strategy orchestration engine."""

    def __init__(self):
        self._strategies: List[BaseStrategy] = []

    def register_strategy(self, strategy: BaseStrategy) -> None:
        """Registers a new strategy instance."""
        if strategy not in self._strategies:
            self._strategies.append(strategy)
            logger.info(f"Registered strategy: {strategy.name}")

    def unregister_strategy(self, strategy_name: str) -> bool:
        """Unregisters a strategy by name."""
        for s in self._strategies:
            if s.name == strategy_name:
                self._strategies.remove(s)
                logger.info(f"Unregistered strategy: {strategy_name}")
                return True
        return False

    @property
    def strategy_names(self) -> List[str]:
        """Returns registered strategy names."""
        return [s.name for s in self._strategies]

    def analyze(self, df: pd.DataFrame) -> ScanResult:
        """
        Executes all active strategies against DataFrame and returns ScanResult.

        Args:
            df: Market scan data from CryptoScanner

        Returns:
            ScanResult: Consolidated scan metrics and generated signals
        """
        scan_time = datetime.now()
        total_coins = len(df) if df is not None and not df.empty else 0
        all_signals: List[Signal] = []
        errors: List[str] = []

        if df is None or df.empty:
            logger.warning("Empty DataFrame passed to analyzer.")
            return ScanResult(
                scan_time=scan_time,
                total_coins_scanned=0,
                signals=[],
                errors=["Empty DataFrame"],
            )

        logger.info(
            f"📊 Analysis starting: {total_coins} coins, "
            f"{len(self._strategies)} strategies"
        )

        for strategy in self._strategies:
            try:
                signals = strategy.analyze(df)
                all_signals.extend(signals)
                logger.info(
                    f"  ➤ {strategy.name}: {len(signals)} signals generated"
                )

            except Exception as e:
                err_msg = f"Strategy error ({strategy.name}): {e}"
                logger.error(err_msg, exc_info=True)
                errors.append(err_msg)

        # Sort signals by confidence score descending
        all_signals.sort(key=lambda s: s.confidence, reverse=True)

        result = ScanResult(
            scan_time=scan_time,
            total_coins_scanned=total_coins,
            signals=all_signals,
            errors=errors,
        )

        logger.info(
            f"📊 Scan Summary | {scan_time.strftime('%H:%M:%S')}\n"
            f"   Scanned: {result.total_coins_scanned} coins\n"
            f"   Signals: {result.signal_count} "
            f"(🟢 {result.buy_signals_count} BUY | 🔴 {result.sell_signals_count} SELL)\n"
            f"   Errors: {len(errors)}"
        )

        return result
