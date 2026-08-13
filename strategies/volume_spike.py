"""
Volume Spike Stratejisi

Anormal hacim artışlarını tespit eder.
Yüksek hacim genellikle büyük fiyat hareketlerinin habercisidir.
"""

from __future__ import annotations


import logging
from typing import Optional

import pandas as pd

from models.signal import Signal, SignalType
from strategies.base import BaseStrategy

logger = logging.getLogger("crypto_bot.strategy.volume_spike")


class VolumeSpikeStrategy(BaseStrategy):
    """Hacim patlaması stratejisi."""

    @property
    def name(self) -> str:
        return "volume_spike"

    @property
    def description(self) -> str:
        return f"Volume Spike (>{self._multiplier}x ortalama)"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._multiplier = self.get_config("multiplier", 3.0)

    def analyze(self, df: pd.DataFrame) -> list[Signal]:
        """Hacim anormalliklerini tespit eder."""
        signals = []

        # Hacim sütununu bul
        vol_col = self._find_column(
            df, ["volume", "Volume", "Vol", "24h_vol"]
        )

        if vol_col is None:
            logger.warning("Hacim sütunu bulunamadı, strateji atlanıyor.")
            return signals

        # İsim, fiyat ve değişim sütunlarını bul
        name_col = self._find_column(df, ["name", "Name", "ticker", "Symbol"])
        price_col = self._find_column(df, ["close", "Close", "price", "Price"])
        change_col = self._find_column(
            df, ["change_percent", "Change%", "change", "Perf.D"]
        )

        # Ortalama hacmi hesapla
        volumes = pd.to_numeric(df[vol_col], errors="coerce")
        avg_volume = volumes.median()  # Median daha sağlam bir ölçü

        if avg_volume is None or avg_volume <= 0:
            logger.warning("Ortalama hacim hesaplanamadı.")
            return signals

        for idx, row in df.iterrows():
            try:
                volume = row.get(vol_col)
                if volume is None or pd.isna(volume):
                    continue

                volume = float(volume)
                ratio = volume / avg_volume

                if ratio >= self._multiplier:
                    symbol = str(row.get(name_col, idx)) if name_col else str(idx)
                    price = float(row.get(price_col, 0)) if price_col else 0.0

                    # Fiyat değişimine göre yönü belirle
                    change = 0.0
                    if change_col:
                        change_val = row.get(change_col)
                        if change_val is not None and not pd.isna(change_val):
                            change = float(change_val)

                    if change > 0:
                        signal_type = SignalType.BUY
                        direction = "yükseliş"
                    elif change < 0:
                        signal_type = SignalType.SELL
                        direction = "düşüş"
                    else:
                        signal_type = SignalType.NEUTRAL
                        direction = "nötr"

                    confidence = min(100, (ratio / self._multiplier) * 30 + 40)

                    signal = Signal(
                        symbol=symbol,
                        signal_type=signal_type,
                        strategy_name=self.name,
                        price=price,
                        confidence=confidence,
                        message=(
                            f"Hacim patlaması: {ratio:.1f}x ortalama "
                            f"({direction}, %{change:+.2f})"
                        ),
                        metadata={
                            "volume": volume,
                            "avg_volume": avg_volume,
                            "volume_ratio": ratio,
                            "change_percent": change,
                        },
                    )
                    signals.append(signal)

            except (ValueError, TypeError) as e:
                logger.debug(f"Satır atlandı ({idx}): {e}")
                continue

        return signals
