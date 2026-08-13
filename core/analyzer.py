"""
Analyzer — Analiz Motoru

Scanner'dan gelen verileri kayıtlı stratejilere gönderir
ve sinyalleri toplar.
"""

from __future__ import annotations


import logging
from typing import Optional

import pandas as pd

from config.settings import Settings
from models.signal import Signal
from models.scan_result import ScanResult
from strategies.base import BaseStrategy

logger = logging.getLogger("crypto_bot.analyzer")


class Analyzer:
    """
    Stratejileri yöneten ve sinyalleri toplayan ana analiz motoru.
    """

    def __init__(self):
        self.settings = Settings()
        self._strategies: list[BaseStrategy] = []

    def register_strategy(self, strategy: BaseStrategy) -> None:
        """Bir stratejiyi kayıt eder."""
        self._strategies.append(strategy)
        logger.info(f"Strateji kaydedildi: {strategy.name}")

    def unregister_strategy(self, strategy_name: str) -> None:
        """Bir stratejiyi kaldırır."""
        self._strategies = [
            s for s in self._strategies if s.name != strategy_name
        ]
        logger.info(f"Strateji kaldırıldı: {strategy_name}")

    @property
    def strategies(self) -> list[BaseStrategy]:
        """Kayıtlı stratejiler."""
        return self._strategies

    @property
    def strategy_names(self) -> list[str]:
        """Kayıtlı strateji isimleri."""
        return [s.name for s in self._strategies]

    def analyze(self, df: pd.DataFrame) -> ScanResult:
        """
        DataFrame'i tüm stratejilere gönderir, sonuçları toplar.

        Args:
            df: Scanner'dan gelen tarama verileri

        Returns:
            ScanResult: Toplanan tüm sinyaller
        """
        result = ScanResult(
            total_coins_scanned=len(df) if df is not None else 0,
            dataframe=df,
        )

        if df is None or df.empty:
            logger.warning("Analiz için veri yok.")
            return result

        if not self._strategies:
            logger.warning("Kayıtlı strateji yok!")
            return result

        logger.info(
            f"📊 Analiz başlıyor: {len(df)} coin, "
            f"{len(self._strategies)} strateji"
        )

        for strategy in self._strategies:
            try:
                signals = strategy.analyze(df)
                if signals:
                    result.signals.extend(signals)
                    logger.info(
                        f"  ➤ {strategy.name}: {len(signals)} sinyal üretildi"
                    )
                else:
                    logger.debug(f"  ➤ {strategy.name}: sinyal yok")

            except Exception as e:
                error_msg = f"{strategy.name} hatası: {e}"
                logger.error(f"  ❌ {error_msg}", exc_info=True)
                result.errors.append(error_msg)

        # Sinyalleri güvenilirlik skoruna göre sırala
        result.signals.sort(key=lambda s: s.confidence, reverse=True)

        logger.info(result.summary())
        return result

    def analyze_single(
        self, df: pd.DataFrame, strategy_name: str
    ) -> list[Signal]:
        """Tek bir strateji ile analiz yapar."""
        strategy = next(
            (s for s in self._strategies if s.name == strategy_name), None
        )
        if strategy is None:
            logger.error(f"Strateji bulunamadı: {strategy_name}")
            return []

        try:
            return strategy.analyze(df)
        except Exception as e:
            logger.error(f"{strategy_name} hatası: {e}", exc_info=True)
            return []
