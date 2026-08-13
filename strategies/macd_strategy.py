"""
MACD Strategy

Moving Average Convergence Divergence (MACD) crossover signal generator.
- MACD line crosses signal line upward -> BUY
- MACD line crosses signal line downward -> SELL
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from models.signal import Signal, SignalType
from strategies.base import BaseStrategy

logger = logging.getLogger("crypto_bot.strategy.macd")


class MACDStrategy(BaseStrategy):
    """MACD crossover strategy."""

    @property
    def name(self) -> str:
        return "macd_strategy"

    @property
    def description(self) -> str:
        return f"MACD Crossover ({self._signal_type})"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._signal_type = self.get_config("signal_type", "both")

    def analyze(self, df: pd.DataFrame) -> list[Signal]:
        """Generates signals based on MACD and Signal line values."""
        signals = []

        macd_col = self._find_column(
            df, ["MACD.macd", "macd_level", "MACD_LEVEL_12_26_9", "MACD"]
        )
        signal_col = self._find_column(
            df, ["MACD.signal", "macd_signal", "MACD_SIGNAL_12_26_9"]
        )

        if macd_col is None:
            logger.warning("MACD column not found, strategy skipped.")
            return signals

        name_col = self._find_column(df, ["name", "Name", "ticker", "Symbol"])
        price_col = self._find_column(df, ["close", "Close", "price", "Price"])

        for idx, row in df.iterrows():
            try:
                macd_value = row.get(macd_col)
                if macd_value is None or pd.isna(macd_value):
                    continue

                macd_value = float(macd_value)
                symbol = str(row.get(name_col, idx)) if name_col else str(idx)
                price = float(row.get(price_col, 0)) if price_col else 0.0

                signal = None

                if signal_col and signal_col in row.index:
                    signal_value = row.get(signal_col)
                    if signal_value is not None and not pd.isna(signal_value):
                        signal_value = float(signal_value)
                        histogram = macd_value - signal_value

                        if histogram > 0 and self._signal_type in ("bullish", "both"):
                            confidence = min(100, abs(histogram) * 10 + 40)
                            signal = Signal(
                                symbol=symbol,
                                signal_type=SignalType.BUY,
                                strategy_name=self.name,
                                price=price,
                                confidence=confidence,
                                message=(
                                    f"MACD bullish: {macd_value:.4f} > "
                                    f"Signal: {signal_value:.4f}"
                                ),
                                metadata={
                                    "macd": macd_value,
                                    "signal": signal_value,
                                    "histogram": histogram,
                                },
                            )

                        elif histogram < 0 and self._signal_type in ("bearish", "both"):
                            confidence = min(100, abs(histogram) * 10 + 40)
                            signal = Signal(
                                symbol=symbol,
                                signal_type=SignalType.SELL,
                                strategy_name=self.name,
                                price=price,
                                confidence=confidence,
                                message=(
                                    f"MACD bearish: {macd_value:.4f} < "
                                    f"Signal: {signal_value:.4f}"
                                ),
                                metadata={
                                    "macd": macd_value,
                                    "signal": signal_value,
                                    "histogram": histogram,
                                },
                            )
                else:
                    if macd_value > 0 and self._signal_type in ("bullish", "both"):
                        signal = Signal(
                            symbol=symbol,
                            signal_type=SignalType.BUY,
                            strategy_name=self.name,
                            price=price,
                            confidence=50,
                            message=f"MACD positive: {macd_value:.4f}",
                            metadata={"macd": macd_value},
                        )
                    elif macd_value < 0 and self._signal_type in ("bearish", "both"):
                        signal = Signal(
                            symbol=symbol,
                            signal_type=SignalType.SELL,
                            strategy_name=self.name,
                            price=price,
                            confidence=50,
                            message=f"MACD negative: {macd_value:.4f}",
                            metadata={"macd": macd_value},
                        )

                if signal:
                    signals.append(signal)

            except (ValueError, TypeError) as e:
                logger.debug(f"Row skipped ({idx}): {e}")
                continue

        return signals
