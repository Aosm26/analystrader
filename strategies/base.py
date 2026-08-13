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
        TVScreener sütun isimleri büyük/küçük harf, parantez, alt çizgi ve boşluk
        farklılıkları gösterebilir. Bu yüzden esnek ve akıllı arama yaparız.
        """
        import re

        def normalize(s: str) -> str:
            return re.sub(r"[^a-zA-Z0-9]", "", s).lower()

        # 1. Tam ve küçük harf eşleşmeleri
        df_cols_lower = {col.lower(): col for col in df.columns}
        for candidate in candidates:
            if candidate in df.columns:
                return candidate
            if candidate.lower() in df_cols_lower:
                return df_cols_lower[candidate.lower()]

        # 2. Normalize eşleşme (boşluklar, parantezler ve alt çizgiler olmadan)
        df_cols_norm = {normalize(col): col for col in df.columns}
        for candidate in candidates:
            cand_norm = normalize(candidate)
            if cand_norm in df_cols_norm:
                return df_cols_norm[cand_norm]

        # 3. Kısmi normalize eşleşme
        for candidate in candidates:
            cand_norm = normalize(candidate)
            if len(cand_norm) < 3:
                continue
            for norm_col, orig_col in df_cols_norm.items():
                if cand_norm in norm_col or norm_col in cand_norm:
                    return orig_col

        return None

    def __repr__(self) -> str:
        return f"<Strategy: {self.name}>"
