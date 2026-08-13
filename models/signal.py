"""
Signal Models & Enums

Defines Signal dataclass and SignalType enumeration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class SignalType(str, Enum):
    """Signal direction and strength enumeration."""

    BUY = "BUY"
    SELL = "SELL"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"
    NEUTRAL = "NEUTRAL"

    @property
    def is_buy(self) -> bool:
        return self in (SignalType.BUY, SignalType.STRONG_BUY)

    @property
    def is_sell(self) -> bool:
        return self in (SignalType.SELL, SignalType.STRONG_SELL)


@dataclass
class Signal:
    """Dataclass representing a quantitative signal."""

    symbol: str
    signal_type: SignalType
    strategy_name: str
    price: float
    confidence: float = 0.0
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converts Signal instance to dictionary representation."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "signal_type": self.signal_type.value,
            "strategy_name": self.strategy_name,
            "price": self.price,
            "confidence": self.confidence,
            "message": self.message,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }

    def __repr__(self) -> str:
        return (
            f"Signal({self.symbol} | {self.signal_type.value} | "
            f"price=${self.price:,.2f} | conf={self.confidence:.0f}% | "
            f"strategy={self.strategy_name})"
        )
