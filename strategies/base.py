"""
Base Strategy — Strateji Arayüzü

Tüm stratejiler bu abstract class'tan türemelidir.
Yeni strateji eklemek için:
    1. Bu sınıftan türeyin
    2. analyze() ve name property'sini implemente edin
    3. config.yaml'da stratejinizi etkinleştirin
"""

from __future__ import annotations


from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd

from models.signal import Signal


class BaseStrategy(ABC):
    """Tüm stratejiler için temel arayüz."""

    def __init__(self, config: Optional[dict] = None):
        """
        Args:
            config: Stratejiye özel konfigürasyon (config.yaml'dan gelir)
        """
        self._config = config or {}

    @property
    @abstractmethod
    def name(self) -> str:
        """Stratejinin benzersiz adı."""
        pass

    @property
    def description(self) -> str:
        """Stratejinin açıklaması (opsiyonel)."""
        return ""

    @abstractmethod
    def analyze(self, df: pd.DataFrame) -> list[Signal]:
        """
        DataFrame'i analiz eder ve sinyal listesi döner.

        Args:
            df: Scanner'dan gelen tarama sonuçları

        Returns:
            list[Signal]: Üretilen sinyaller (boş liste olabilir)
        """
        pass

    def get_config(self, key: str, default=None):
        """Strateji konfigürasyonundan değer alır."""
        return self._config.get(key, default)

    def _find_column(self, df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
        """
        DataFrame'de belirtilen isimlerdeki sütunu bulur.
        TVScreener sütun isimleri büyük/küçük harf ve format farklılıkları
        gösterebilir, bu yüzden esnek arama yaparız.
        """
        df_cols_lower = {col.lower(): col for col in df.columns}
        for candidate in candidates:
            # Direkt eşleşme
            if candidate in df.columns:
                return candidate
            # Küçük harf eşleşme
            if candidate.lower() in df_cols_lower:
                return df_cols_lower[candidate.lower()]
            # Kısmi eşleşme
            for col in df.columns:
                if candidate.lower() in col.lower():
                    return col
        return None

    def __repr__(self) -> str:
        return f"<Strategy: {self.name}>"
