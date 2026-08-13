"""
RSI Strategy

Relative Strength Index (RSI) oversold/overbought signal generator.
- RSI <= oversold_threshold → BUY / STRONG_BUY signal
- RSI >= overbought_threshold → SELL / STRONG_SELL signal
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from models.signal import Signal, SignalType
from strategies.base import BaseStrategy

logger = logging.getLogger("crypto_bot.strategy.rsi")


class RSIStrategy(BaseStrategy):
    """RSI Oversold / Overbought Strategy."""

    @property
    def name(self) -> str:
        return "rsi_strategy"

    @property
    def description(self) -> str:
        return (
            f"RSI Oversold/Overbought "
            f"(< {self._oversold} BUY | > {self._overbought} SELL)"
        )

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._oversold = self.get_config("oversold_threshold", 30)
        self._overbought = self.get_config("overbought_threshold", 70)

    def analyze(self, df: pd.DataFrame) -> list[Signal]:
        """Generates trading signals based on RSI levels."""
        signals = []

        rsi_col = self._find_column(
            df,
            [
                "Relative Strength Index",
                "RSI",
                "RSI14",
                "relative_strength_index_14",
                "Recommend.Other",
            ],
        )

        if rsi_col is None:
            logger.warning("RSI column not found, strategy skipped.")
            return signals

        name_col = self._find_column(df, ["name", "Name", "ticker", "Symbol"])
        price_col = self._find_column(df, ["close", "Close", "price", "Price"])

        for idx, row in df.iterrows():
            try:
                rsi_value = row.get(rsi_col)
                if rsi_value is None or pd.isna(rsi_value):
                    continue

                rsi_value = float(rsi_value)
                symbol = str(row.get(name_col, idx)) if name_col else str(idx)
                price = float(row.get(price_col, 0)) if price_col else 0.0

                signal = None

                if rsi_value <= self._oversold:
                    confidence = min(100, (self._oversold - rsi_value) * 3 + 50)
                    strength = "STRONG_BUY" if rsi_value <= 20 else "BUY"

                    signal = Signal(
                        symbol=symbol,
                        signal_type=SignalType[strength],
                        strategy_name=self.name,
                        price=price,
                        confidence=confidence,
                        message=f"RSI oversold level: {rsi_value:.1f}",
                        metadata={"rsi": rsi_value, "threshold": self._oversold},
                    )

                elif rsi_value >= self._overbought:
                    confidence = min(100, (rsi_value - self._overbought) * 3 + 50)
                    strength = "STRONG_SELL" if rsi_value >= 80 else "SELL"

                    signal = Signal(
                        symbol=symbol,
                        signal_type=SignalType[strength],
                        strategy_name=self.name,
                        price=price,
                        confidence=confidence,
                        message=f"RSI overbought level: {rsi_value:.1f}",
                        metadata={"rsi": rsi_value, "threshold": self._overbought},
                    )

                if signal:
                    signals.append(signal)

            except (ValueError, TypeError) as e:
                logger.debug(f"Row skipped ({idx}): {e}")
                continue

        return signals
