"""
Volume Spike + RSI Breakout Strategy (Momentum Score)

Catches institutional algorithms and whale entries by detecting simultaneous
volume surges (>2.5x SMA20) and healthy RSI momentum breakouts (50 < RSI <= 65).

Calculates entry price, Take Profit (+1.50%), and Stop Loss (-0.75% / Candle Low).
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from models.signal import Signal, SignalType
from strategies.base import BaseStrategy

logger = logging.getLogger("crypto_bot.strategy.volume_rsi_breakout")


class VolumeRSIBreakoutStrategy(BaseStrategy):
    """Volume Spike + RSI Breakout Strategy."""

    @property
    def name(self) -> str:
        return "volume_rsi_breakout"

    @property
    def description(self) -> str:
        return (
            f"Volume Spike (>{self._vol_multiplier}x) + "
            f"RSI Breakout ({self._rsi_min}-{self._rsi_max})"
        )

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._vol_multiplier = float(self.get_config("volume_multiplier", 2.5))
        self._rsi_min = float(self.get_config("rsi_min", 50.0))
        self._rsi_max = float(self.get_config("rsi_max", 65.0))
        self._tp_percent = float(self.get_config("tp_percent", 1.50))
        self._sl_percent = float(self.get_config("sl_percent", 0.75))

    def analyze(self, df: pd.DataFrame) -> list[Signal]:
        """Analyzes market data for simultaneous volume spike & RSI momentum breakout."""
        signals = []

        # Find columns
        vol_col = self._find_column(df, ["volume", "Volume", "Vol", "24h_vol"])
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

        if vol_col is None or rsi_col is None:
            logger.warning(
                f"Missing required columns (Volume: {vol_col}, RSI: {rsi_col}). "
                "Strategy skipped."
            )
            return signals

        name_col = self._find_column(df, ["name", "Name", "ticker", "Symbol"])
        price_col = self._find_column(df, ["close", "Close", "price", "Price"])
        low_col = self._find_column(df, ["low", "Low", "price_low", "Price.Low"])

        # Calculate average volume
        volumes = pd.to_numeric(df[vol_col], errors="coerce")
        avg_volume = volumes.median()

        if avg_volume is None or avg_volume <= 0:
            logger.warning("Average volume could not be computed.")
            return signals

        for idx, row in df.iterrows():
            try:
                volume = row.get(vol_col)
                rsi = row.get(rsi_col)

                if volume is None or rsi is None or pd.isna(volume) or pd.isna(rsi):
                    continue

                volume = float(volume)
                rsi = float(rsi)
                vol_ratio = volume / avg_volume

                # Condition 1: Volume Spike (>2.5x average)
                vol_triggered = vol_ratio >= self._vol_multiplier

                # Condition 2: RSI Breakout (50 < RSI <= 65)
                rsi_triggered = self._rsi_min < rsi <= self._rsi_max

                if vol_triggered and rsi_triggered:
                    symbol = str(row.get(name_col, idx)) if name_col else str(idx)
                    entry_price = float(row.get(price_col, 0)) if price_col else 0.0

                    # Calculate TP (+1.50%) and SL (-0.75% or Candle Low)
                    tp_price = entry_price * (1 + (self._tp_percent / 100.0))

                    if low_col and row.get(low_col) and not pd.isna(row.get(low_col)):
                        candle_low = float(row.get(low_col))
                        sl_price = min(candle_low, entry_price * (1 - (self._sl_percent / 100.0)))
                    else:
                        sl_price = entry_price * (1 - (self._sl_percent / 100.0))

                    # Confidence calculation based on volume surge and RSI positioning
                    vol_score = min(50, (vol_ratio / self._vol_multiplier) * 30)
                    rsi_score = 50 - abs(rsi - 57.5) * 2  # Optimal center at 57.5
                    confidence = min(100.0, max(50.0, vol_score + rsi_score))

                    message = (
                        f"Whale Momentum Breakout: Vol {vol_ratio:.1f}x (>{self._vol_multiplier}x), "
                        f"RSI {rsi:.1f} | Entry: ${entry_price:,.4f} | "
                        f"TP (+{self._tp_percent}%): ${tp_price:,.4f} | "
                        f"SL (-{self._sl_percent}%): ${sl_price:,.4f}"
                    )

                    signal = Signal(
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        strategy_name=self.name,
                        price=entry_price,
                        confidence=confidence,
                        message=message,
                        metadata={
                            "volume_ratio": vol_ratio,
                            "rsi": rsi,
                            "entry_price": entry_price,
                            "tp_price": tp_price,
                            "sl_price": sl_price,
                            "tp_percent": self._tp_percent,
                            "sl_percent": self._sl_percent,
                            "risk_reward_ratio": round(self._tp_percent / self._sl_percent, 2),
                        },
                    )
                    signals.append(signal)

            except (ValueError, TypeError) as e:
                logger.debug(f"Row skipped ({idx}): {e}")
                continue

        return signals
