"""
Bollinger Bands Squeeze & Breakout Strategy (Volatility Breakout)

Detects periods of low volatility (Bollinger Bands squeeze) followed by a sharp
upside breakout above the Upper Bollinger Band.

Calculates Entry Price, Take Profit (+2.00%), and Stop Loss (Middle Band / 20 SMA).
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from models.signal import Signal, SignalType
from strategies.base import BaseStrategy

logger = logging.getLogger("crypto_bot.strategy.bollinger_squeeze")


class BollingerSqueezeStrategy(BaseStrategy):
    """Bollinger Bands Volatility Squeeze and Breakout Strategy."""

    @property
    def name(self) -> str:
        return "bollinger_squeeze"

    @property
    def description(self) -> str:
        return (
            f"Bollinger Bands Squeeze (BW <= {self._bw_threshold:.0%}) & "
            f"Upper Band Breakout"
        )

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._bw_threshold = float(self.get_config("bandwidth_threshold", 0.10))
        self._tp_percent = float(self.get_config("tp_percent", 2.00))

    def analyze(self, df: pd.DataFrame) -> list[Signal]:
        """Analyzes market data for Bollinger Band compression and upside breakout."""
        signals = []

        ub_col = self._find_column(
            df,
            [
                "Bollinger Upper Band (20)",
                "bollinger_upper_band_20",
                "BOLLINGER_UPPER_BAND_20",
                "BB.upper",
            ],
        )
        lb_col = self._find_column(
            df,
            [
                "Bollinger Lower Band (20)",
                "bollinger_lower_band_20",
                "BOLLINGER_LOWER_BAND_20",
                "BB.lower",
            ],
        )

        if ub_col is None or lb_col is None:
            logger.warning(
                f"Missing required Bollinger columns (Upper: {ub_col}, Lower: {lb_col}). "
                "Strategy skipped."
            )
            return signals

        name_col = self._find_column(df, ["name", "Name", "ticker", "Symbol"])
        price_col = self._find_column(df, ["close", "Close", "price", "Price"])

        for idx, row in df.iterrows():
            try:
                ub = row.get(ub_col)
                lb = row.get(lb_col)
                price_val = row.get(price_col)

                if ub is None or lb is None or price_val is None:
                    continue
                if pd.isna(ub) or pd.isna(lb) or pd.isna(price_val):
                    continue

                upper_band = float(ub)
                lower_band = float(lb)
                price = float(price_val)

                # Middle Band (20 SMA) = (Upper + Lower) / 2
                middle_band = (upper_band + lower_band) / 2.0

                if middle_band <= 0:
                    continue

                # Bandwidth = (Upper - Lower) / Middle
                bandwidth = (upper_band - lower_band) / middle_band

                # 1. Squeeze Condition: Bandwidth is compressed
                is_squeezed = bandwidth <= self._bw_threshold

                # 2. Breakout Condition: Price breaks above Upper Band
                is_breakout = price > upper_band

                if is_squeezed and is_breakout:
                    symbol = str(row.get(name_col, idx)) if name_col else str(idx)

                    # Entry Price = Current close price
                    entry_price = price

                    # Take Profit = Entry + 2.00%
                    tp_price = entry_price * (1 + (self._tp_percent / 100.0))

                    # Stop Loss = Middle Band (20 SMA)
                    sl_price = middle_band

                    # Risk / Reward calculation
                    sl_percent = ((entry_price - sl_price) / entry_price) * 100.0 if entry_price > sl_price else 1.0
                    risk_reward = round(self._tp_percent / max(0.1, sl_percent), 2)

                    # Confidence calculation based on compression tightness and breakout strength
                    tightness_score = min(50.0, (self._bw_threshold / max(0.01, bandwidth)) * 25.0)
                    breakout_dist = ((price - upper_band) / upper_band) * 100.0
                    breakout_score = min(50.0, breakout_dist * 20.0 + 35.0)
                    confidence = min(100.0, max(50.0, tightness_score + breakout_score))

                    message = (
                        f"Bollinger Breakout: BW {bandwidth:.1%} (Squeezed <= {self._bw_threshold:.0%}), "
                        f"Price ${price:,.4f} > Upper Band ${upper_band:,.4f} | "
                        f"Entry: ${entry_price:,.4f} | TP (+{self._tp_percent}%): ${tp_price:,.4f} | "
                        f"SL (Middle Band): ${sl_price:,.4f}"
                    )

                    signal = Signal(
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        strategy_name=self.name,
                        price=entry_price,
                        confidence=confidence,
                        message=message,
                        metadata={
                            "bandwidth": round(bandwidth, 4),
                            "upper_band": upper_band,
                            "middle_band": middle_band,
                            "lower_band": lower_band,
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
