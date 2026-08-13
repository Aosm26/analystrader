"""
Signal Modeli

Bir strateji tarafından üretilen sinyali temsil eder.
"""

from __future__ import annotations


from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class SignalType(Enum):
    """Sinyal türü."""
    BUY = "BUY"
    SELL = "SELL"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"
    NEUTRAL = "NEUTRAL"


@dataclass
class Signal:
    """Tek bir trade sinyali."""

    symbol: str                          # Coin sembolü (ör: BTCUSDT)
    signal_type: SignalType              # BUY, SELL, vs.
    strategy_name: str                   # Sinyali üreten strateji
    price: float                         # Sinyal anındaki fiyat
    confidence: float = 0.0             # Güvenilirlik skoru (0-100)
    message: str = ""                    # Açıklama mesajı
    metadata: dict = field(default_factory=dict)  # Ek veriler (RSI değeri, hacim vs.)
    timestamp: datetime = field(default_factory=datetime.now)
    id: Optional[int] = None            # DB ID (storage tarafından atanır)

    @property
    def is_buy(self) -> bool:
        return self.signal_type in (SignalType.BUY, SignalType.STRONG_BUY)

    @property
    def is_sell(self) -> bool:
        return self.signal_type in (SignalType.SELL, SignalType.STRONG_SELL)

    def to_dict(self) -> dict:
        """Sinyali sözlük olarak döner (JSON serileştirme için)."""
        return {
            "symbol": self.symbol,
            "signal_type": self.signal_type.value,
            "strategy_name": self.strategy_name,
            "price": self.price,
            "confidence": self.confidence,
            "message": self.message,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }

    def __str__(self) -> str:
        emoji = "🟢" if self.is_buy else "🔴" if self.is_sell else "⚪"
        return (
            f"{emoji} {self.signal_type.value} | {self.symbol} | "
            f"${self.price:,.2f} | {self.strategy_name} | "
            f"Güven: {self.confidence:.0f}%"
        )
