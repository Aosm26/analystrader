"""
RSI Stratejisi

RSI (Relative Strength Index) tabanlı aşırı alım/satım sinyalleri.
- RSI < oversold_threshold → BUY sinyali
- RSI > overbought_threshold → SELL sinyali
"""

from __future__ import annotations


import logging
from typing import Optional

import pandas as pd

from models.signal import Signal, SignalType
from strategies.base import BaseStrategy

logger = logging.getLogger("crypto_bot.strategy.rsi")


class RSIStrategy(BaseStrategy):
    """RSI aşırı alım/aşırı satım stratejisi."""

    @property
    def name(self) -> str:
        return "rsi_strategy"

    @property
    def description(self) -> str:
        return (
            f"RSI Oversold/Overbought "
            f"(< {self._oversold} AL | > {self._overbought} SAT)"
        )

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._oversold = self.get_config("oversold_threshold", 30)
        self._overbought = self.get_config("overbought_threshold", 70)

    def analyze(self, df: pd.DataFrame) -> list[Signal]:
        """RSI değerlerine göre sinyal üretir."""
        signals = []

        # RSI sütununu bul
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
            logger.warning("RSI sütunu bulunamadı, strateji atlanıyor.")
            return signals

        # İsim ve fiyat sütunlarını bul
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
                    # Aşırı satım → AL sinyali
                    # RSI ne kadar düşükse güvenilirlik o kadar yüksek
                    confidence = min(100, (self._oversold - rsi_value) * 3 + 50)
                    strength = "STRONG_BUY" if rsi_value <= 20 else "BUY"

                    signal = Signal(
                        symbol=symbol,
                        signal_type=SignalType[strength],
                        strategy_name=self.name,
                        price=price,
                        confidence=confidence,
                        message=f"RSI aşırı satım bölgesinde: {rsi_value:.1f}",
                        metadata={"rsi": rsi_value, "threshold": self._oversold},
                    )

                elif rsi_value >= self._overbought:
                    # Aşırı alım → SAT sinyali
                    confidence = min(100, (rsi_value - self._overbought) * 3 + 50)
                    strength = "STRONG_SELL" if rsi_value >= 80 else "SELL"

                    signal = Signal(
                        symbol=symbol,
                        signal_type=SignalType[strength],
                        strategy_name=self.name,
                        price=price,
                        confidence=confidence,
                        message=f"RSI aşırı alım bölgesinde: {rsi_value:.1f}",
                        metadata={"rsi": rsi_value, "threshold": self._overbought},
                    )

                if signal:
                    signals.append(signal)

            except (ValueError, TypeError) as e:
                logger.debug(f"Satır atlandı ({idx}): {e}")
                continue

        return signals
