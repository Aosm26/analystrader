"""
Scan Result Modeli

Bir tarama döngüsünün sonucunu temsil eder.
"""

from __future__ import annotations


from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import pandas as pd

from models.signal import Signal


@dataclass
class ScanResult:
    """Bir tarama döngüsünün sonucu."""

    scan_time: datetime = field(default_factory=datetime.now)
    total_coins_scanned: int = 0
    dataframe: Optional[pd.DataFrame] = None
    signals: list[Signal] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def signal_count(self) -> int:
        return len(self.signals)

    @property
    def buy_signals(self) -> list[Signal]:
        return [s for s in self.signals if s.is_buy]

    @property
    def sell_signals(self) -> list[Signal]:
        return [s for s in self.signals if s.is_sell]

    @property
    def has_signals(self) -> bool:
        return len(self.signals) > 0

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def summary(self) -> str:
        return (
            f"📊 Tarama Özeti | {self.scan_time.strftime('%H:%M:%S')}\n"
            f"   Taranan: {self.total_coins_scanned} coin\n"
            f"   Sinyal: {self.signal_count} "
            f"(🟢 {len(self.buy_signals)} AL | 🔴 {len(self.sell_signals)} SAT)\n"
            f"   Hata: {len(self.errors)}"
        )
