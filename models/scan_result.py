"""
Scan Result Model

Aggregates statistics and signals for a single scan execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

from models.signal import Signal


@dataclass
class ScanResult:
    """Dataclass holding scan summary metrics and signals."""

    scan_time: datetime
    total_coins_scanned: int
    signals: List[Signal] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def signal_count(self) -> int:
        return len(self.signals)

    @property
    def buy_signals_count(self) -> int:
        return sum(1 for s in self.signals if s.signal_type.is_buy)

    @property
    def sell_signals_count(self) -> int:
        return sum(1 for s in self.signals if s.signal_type.is_sell)

    @property
    def has_signals(self) -> bool:
        return len(self.signals) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Converts ScanResult instance to dictionary representation."""
        return {
            "scan_time": self.scan_time.isoformat(),
            "total_coins_scanned": self.total_coins_scanned,
            "signal_count": self.signal_count,
            "buy_signals_count": self.buy_signals_count,
            "sell_signals_count": self.sell_signals_count,
            "signals": [s.to_dict() for s in self.signals],
            "errors": self.errors,
        }
