"""
Base Strategy Interface

All strategies must inherit from BaseStrategy.
To add a new strategy:
    1. Inherit from BaseStrategy
    2. Implement name property and analyze() method
    3. Enable strategy in config.yaml
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd

from models.signal import Signal


class BaseStrategy(ABC):
    """Base interface for all quantitative trading strategies."""

    def __init__(self, config: Optional[dict] = None):
        """
        Args:
            config: Strategy-specific configuration dictionary from config.yaml
        """
        self._config = config or {}

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique strategy name identifier."""
        pass

    @property
    def description(self) -> str:
        """Human-readable strategy description."""
        return ""

    @abstractmethod
    def analyze(self, df: pd.DataFrame) -> list[Signal]:
        """
        Analyzes market DataFrame and returns generated signals.

        Args:
            df: Scanned market data from CryptoScanner

        Returns:
            list[Signal]: List of generated Signal instances
        """
        pass

    def get_config(self, key: str, default=None):
        """Retrieves a configuration value for the strategy."""
        return self._config.get(key, default)

    def _find_column(self, df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
        """
        Finds matching column in DataFrame flexibly handling casing, spaces,
        underscores, and parentheses differences in TVScreener columns.
        """
        import re

        def normalize(s: str) -> str:
            return re.sub(r"[^a-zA-Z0-9]", "", s).lower()

        # 1. Exact and lowercase match
        df_cols_lower = {col.lower(): col for col in df.columns}
        for candidate in candidates:
            if candidate in df.columns:
                return candidate
            if candidate.lower() in df_cols_lower:
                return df_cols_lower[candidate.lower()]

        # 2. Normalized match (without spaces, brackets, underscores)
        df_cols_norm = {normalize(col): col for col in df.columns}
        for candidate in candidates:
            cand_norm = normalize(candidate)
            if cand_norm in df_cols_norm:
                return df_cols_norm[cand_norm]

        # 3. Partial normalized match
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
