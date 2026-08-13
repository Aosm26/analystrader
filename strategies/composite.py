"""
Composite Strategy — Birleşik Strateji

Birden fazla stratejiyi kombine eder.
Sadece birden fazla strateji aynı anda sinyal verirse
nihai sinyal üretir (confluence/birleşim).
"""

from __future__ import annotations


import logging
from collections import defaultdict
from typing import Optional

import pandas as pd

from models.signal import Signal, SignalType
from strategies.base import BaseStrategy

logger = logging.getLogger("crypto_bot.strategy.composite")


class CompositeStrategy(BaseStrategy):
    """
    Birden fazla stratejiyi birleştiren meta-strateji.

    Sadece minimum_agreement sayıda strateji aynı coin için
    aynı yönde sinyal verirse nihai sinyal üretir.
    """

    @property
    def name(self) -> str:
        return "composite"

    @property
    def description(self) -> str:
        strategy_names = [s.name for s in self._sub_strategies]
        return (
            f"Composite ({', '.join(strategy_names)}) - "
            f"min {self._min_agreement} uyum"
        )

    def __init__(
        self,
        strategies: list[BaseStrategy],
        min_agreement: int = 2,
        config: Optional[dict] = None,
    ):
        """
        Args:
            strategies: Alt stratejiler
            min_agreement: Sinyal üretmek için minimum kaç strateji
                          aynı yönde olmalı
            config: Ek konfigürasyon
        """
        super().__init__(config)
        self._sub_strategies = strategies
        self._min_agreement = min_agreement

    def analyze(self, df: pd.DataFrame) -> list[Signal]:
        """
        Alt stratejileri çalıştırır, uyumlu sinyalleri birleştirir.
        """
        # Her stratejiyi çalıştır ve sinyalleri topla
        all_signals: dict[str, list[Signal]] = defaultdict(list)

        for strategy in self._sub_strategies:
            try:
                signals = strategy.analyze(df)
                for signal in signals:
                    all_signals[signal.symbol].append(signal)
            except Exception as e:
                logger.warning(f"Alt strateji hatası ({strategy.name}): {e}")

        # Confluence kontrolü
        composite_signals = []

        for symbol, symbol_signals in all_signals.items():
            buy_signals = [s for s in symbol_signals if s.is_buy]
            sell_signals = [s for s in symbol_signals if s.is_sell]

            # Buy confluence
            if len(buy_signals) >= self._min_agreement:
                avg_confidence = sum(s.confidence for s in buy_signals) / len(buy_signals)
                # Confluence ile güvenilirlik artar
                boosted_confidence = min(100, avg_confidence * 1.2)

                strategies_agreed = [s.strategy_name for s in buy_signals]
                first_signal = buy_signals[0]

                composite_signal = Signal(
                    symbol=symbol,
                    signal_type=SignalType.STRONG_BUY,
                    strategy_name=self.name,
                    price=first_signal.price,
                    confidence=boosted_confidence,
                    message=(
                        f"🎯 Confluence AL: {len(buy_signals)} strateji uyumlu "
                        f"({', '.join(strategies_agreed)})"
                    ),
                    metadata={
                        "sub_signals": [s.to_dict() for s in buy_signals],
                        "strategies_agreed": strategies_agreed,
                        "agreement_count": len(buy_signals),
                    },
                )
                composite_signals.append(composite_signal)

            # Sell confluence
            if len(sell_signals) >= self._min_agreement:
                avg_confidence = sum(s.confidence for s in sell_signals) / len(sell_signals)
                boosted_confidence = min(100, avg_confidence * 1.2)

                strategies_agreed = [s.strategy_name for s in sell_signals]
                first_signal = sell_signals[0]

                composite_signal = Signal(
                    symbol=symbol,
                    signal_type=SignalType.STRONG_SELL,
                    strategy_name=self.name,
                    price=first_signal.price,
                    confidence=boosted_confidence,
                    message=(
                        f"🎯 Confluence SAT: {len(sell_signals)} strateji uyumlu "
                        f"({', '.join(strategies_agreed)})"
                    ),
                    metadata={
                        "sub_signals": [s.to_dict() for s in sell_signals],
                        "strategies_agreed": strategies_agreed,
                        "agreement_count": len(sell_signals),
                    },
                )
                composite_signals.append(composite_signal)

        return composite_signals
