"""
Dual EMA Trend Tracking Strategy (Pullback / Re-entry)

Identifies healthy dip pullbacks to key moving averages within an established
bullish trend (Price > EMA50 > EMA200), catching re-entries as price re-claims fast EMAs.

Calculates Entry Price, Take Profit (+1.20%), and Stop Loss (0.20% below EMA21).
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from models.signal import Signal, SignalType
from strategies.base import BaseStrategy

logger = logging.getLogger("crypto_bot.strategy.ema_pullback")


class EMAPullbackStrategy(BaseStrategy):
    """Dual EMA Trend Tracking & Dip Pullback Re-entry Strategy."""

    @property
    def name(self) -> str:
        return "ema_pullback"

    @property
    def description(self) -> str:
        return (
            "Dual EMA Trend Pullback "
            f"(Bull Trend: Price > EMA50/200 | TP: +{self._tp_percent}%)"
        )

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._tp_percent = float(self.get_config("tp_percent", 1.20))
        self._sl_offset = float(self.get_config("sl_ema_offset", 0.20))

    def analyze(self, df: pd.DataFrame) -> list[Signal]:
        """Analyzes market data for bull trend structure and pullback re-entry opportunities."""
        signals = []

        ema10_col = self._find_column(
            df,
            [
                "Exponential Moving Average (10)",
                "exponential_moving_average_10",
                "EXPONENTIAL_MOVING_AVERAGE_10",
                "EMA10",
                "EMA9",
            ],
        )
        ema20_col = self._find_column(
            df,
            [
                "Exponential Moving Average (20)",
                "exponential_moving_average_20",
                "EXPONENTIAL_MOVING_AVERAGE_20",
                "EMA20",
                "EMA21",
            ],
        )
        ema50_col = self._find_column(
            df,
            [
                "Exponential Moving Average (50)",
                "exponential_moving_average_50",
                "EXPONENTIAL_MOVING_AVERAGE_50",
                "EMA50",
            ],
        )
        ema200_col = self._find_column(
            df,
            [
                "Exponential Moving Average (200)",
                "exponential_moving_average_200",
                "EXPONENTIAL_MOVING_AVERAGE_200",
                "Simple Moving Average (200)",
                "simple_moving_average_200",
                "EMA200",
                "SMA200",
            ],
        )

        if ema50_col is None or ema10_col is None:
            logger.warning(
                f"Missing required EMA columns (EMA10: {ema10_col}, EMA50: {ema50_col}). "
                "Strategy skipped."
            )
            return signals

        name_col = self._find_column(df, ["name", "Name", "ticker", "Symbol"])
        price_col = self._find_column(df, ["close", "Close", "price", "Price"])

        for idx, row in df.iterrows():
            try:
                price_val = row.get(price_col)
                ema10_val = row.get(ema10_col)
                ema50_val = row.get(ema50_col)
                ema20_val = row.get(ema20_col) if ema20_col else ema10_val
                ema200_val = row.get(ema200_col) if ema200_col else None

                if price_val is None or ema10_val is None or ema50_val is None:
                    continue
                if pd.isna(price_val) or pd.isna(ema10_val) or pd.isna(ema50_val):
                    continue

                price = float(price_val)
                ema10 = float(ema10_val)
                ema20 = float(ema20_val) if ema20_val is not None and not pd.isna(ema20_val) else ema10
                ema50 = float(ema50_val)
                ema200 = float(ema200_val) if ema200_val is not None and not pd.isna(ema200_val) else None

                # 1. Bull Trend Filter: Price > EMA50 and (EMA50 > EMA200 if present)
                is_bull_trend = price > ema50
                if ema200 is not None:
                    is_bull_trend = is_bull_trend and (ema50 > ema200 or price > ema200)

                # 2. Pullback Re-entry Condition:
                # Price is reclaiming EMA10/EMA20 (within healthy 0% to 1.5% distance above EMA10)
                is_reclaiming = price >= ema10 and price <= (ema10 * 1.015)

                if is_bull_trend and is_reclaiming:
                    symbol = str(row.get(name_col, idx)) if name_col else str(idx)

                    entry_price = price

                    # Take Profit: +1.20%
                    tp_price = entry_price * (1 + (self._tp_percent / 100.0))

                    # Stop Loss: 0.20% below EMA21 (EMA20)
                    sl_base = min(ema20, entry_price)
                    sl_price = sl_base * (1 - (self._sl_offset / 100.0))

                    sl_percent = ((entry_price - sl_price) / entry_price) * 100.0 if entry_price > sl_price else 0.5
                    risk_reward = round(self._tp_percent / max(0.1, sl_percent), 2)

                    confidence = min(100.0, max(55.0, 70.0 + (ema10 - ema50) / price * 100.0))

                    message = (
                        f"Dual EMA Pullback Re-entry: Price ${price:,.4f} > EMA50 ${ema50:,.4f}, "
                        f"Reclaiming EMA10 ${ema10:,.4f} | Entry: ${entry_price:,.4f} | "
                        f"TP (+{self._tp_percent}%): ${tp_price:,.4f} | "
                        f"SL (-{self._sl_offset}% below EMA21): ${sl_price:,.4f}"
                    )

                    signal = Signal(
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        strategy_name=self.name,
                        price=entry_price,
                        confidence=confidence,
                        message=message,
                        metadata={
                            "ema10": ema10,
                            "ema20": ema20,
                            "ema50": ema50,
                            "ema200": ema200,
                            "entry_price": entry_price,
                            "tp_price": tp_price,
                            "sl_price": sl_price,
                            "tp_percent": self._tp_percent,
                            "sl_percent": round(sl_percent, 2),
                            "risk_reward_ratio": risk_reward,
                        },
                    )
                    signals.append(signal)

            except (ValueError, TypeError) as e:
                logger.debug(f"Row skipped ({idx}): {e}")
                continue

        return signals
