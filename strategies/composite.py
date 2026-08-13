"""
Composite (Confluence) Strategy

Combines signals from multiple strategies for a single asset.
Requires agreement across sub-strategies to generate high-confidence signals.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import pandas as pd

from models.signal import Signal, SignalType
from strategies.base import BaseStrategy

logger = logging.getLogger("crypto_bot.strategy.composite")


class CompositeStrategy(BaseStrategy):
    """Confluence Strategy requiring multi-strategy agreement."""

    @property
    def name(self) -> str:
        return "composite_strategy"

    @property
    def description(self) -> str:
        return f"Confluence Strategy ({len(self._sub_strategies)} sub-strategies)"

    def __init__(
        self,
        sub_strategies: List[BaseStrategy],
        config: Optional[dict] = None,
    ):
        super().__init__(config)
        self._sub_strategies = sub_strategies
        self._min_agreement = self.get_config("min_agreement", 2)

    def analyze(self, df: pd.DataFrame) -> list[Signal]:
        """Combines sub-strategy signals and evaluates agreement."""
        all_signals: list[Signal] = []
        for strategy in self._sub_strategies:
            all_signals.extend(strategy.analyze(df))

        symbol_signals: dict[str, list[Signal]] = {}
        for sig in all_signals:
            symbol_signals.setdefault(sig.symbol, []).append(sig)

        composite_signals: list[Signal] = []

        for symbol, sigs in symbol_signals.items():
            buy_count = sum(1 for s in sigs if s.signal_type.is_buy)
            sell_count = sum(1 for s in sigs if s.signal_type.is_sell)

            if buy_count >= self._min_agreement and buy_count > sell_count:
                avg_confidence = (
                    sum(s.confidence for s in sigs if s.signal_type.is_buy)
                    / buy_count
                )
                boosted = min(100.0, avg_confidence * 1.2)
                price = sigs[0].price

                composite_signals.append(
                    Signal(
                        symbol=symbol,
                        signal_type=SignalType.STRONG_BUY,
                        strategy_name=self.name,
                        price=price,
                        confidence=boosted,
                        message=f"Strong BUY confluence: {buy_count} sub-strategies agree",
                        metadata={
                            "buy_count": buy_count,
                            "strategies": [s.strategy_name for s in sigs if s.signal_type.is_buy],
                        },
                    )
                )

            elif sell_count >= self._min_agreement and sell_count > buy_count:
                avg_confidence = (
                    sum(s.confidence for s in sigs if s.signal_type.is_sell)
                    / sell_count
                )
                boosted = min(100.0, avg_confidence * 1.2)
                price = sigs[0].price

                composite_signals.append(
                    Signal(
                        symbol=symbol,
                        signal_type=SignalType.STRONG_SELL,
                        strategy_name=self.name,
                        price=price,
                        confidence=boosted,
                        message=f"Strong SELL confluence: {sell_count} sub-strategies agree",
                        metadata={
                            "sell_count": sell_count,
                            "strategies": [s.strategy_name for s in sigs if s.signal_type.is_sell],
                        },
                    )
                )

        return composite_signals
