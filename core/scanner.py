"""
Scanner Module — TVScreener Integration

Scans cryptocurrency markets via TVScreener API and returns dataframes.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import pandas as pd

from config.settings import Settings
from utils.rate_limiter import RateLimiter

logger = logging.getLogger("crypto_bot.scanner")


class CryptoScanner:
    """Crypto Screener class wrapping tvscreener."""

    def __init__(self):
        self.settings = Settings()
        self.rate_limiter = RateLimiter(max_calls=5, period=60.0)

    def _build_screener(
        self,
        fields: Optional[List] = None,
        limit: int = 100,
        exchanges: Optional[list[str]] = None,
    ):
        """
        Creates a fresh CryptoScreener instance per scan.
        (v0.0.11 API is stateful, so a new instance is required each time).
        """
        try:
            import tvscreener as tvs
            from tvscreener.field.crypto import CryptoField
            from tvscreener.filter import FilterOperator
        except ImportError:
            raise ImportError(
                "tvscreener library is not installed. "
                "Install with: pip install tvscreener"
            )

        screener = tvs.CryptoScreener()

        if fields:
            screener.specific_fields = fields

        if exchanges and len(exchanges) == 1:
            try:
                screener.add_filter("exchange", FilterOperator.MATCH, exchanges[0])
            except Exception as e:
                logger.debug(f"API exchange filter warning: {e}")

        screener.set_range(0, limit)
        return screener

    def _resolve_field_list(self, field_names: list[str]) -> list:
        """Resolves config field names to CryptoField enum instances."""
        try:
            from tvscreener.field.crypto import CryptoField
        except ImportError:
            return []

        resolved = []
        for name in field_names:
            enum_name = name.upper()
            try:
                field = CryptoField[enum_name]
                resolved.append(field)
            except KeyError:
                alias_map = {
                    "RSI": "RELATIVE_STRENGTH_INDEX_14",
                    "RSI14": "RELATIVE_STRENGTH_INDEX_14",
                    "RSI7": "RELATIVE_STRENGTH_INDEX_7",
                    "MACD_LEVEL": "MACD_LEVEL_12_26",
                    "MACD_SIGNAL": "MACD_SIGNAL_12_26",
                    "EMA_20": "EXPONENTIAL_MOVING_AVERAGE_20",
                    "EMA_50": "EXPONENTIAL_MOVING_AVERAGE_50",
                    "SMA_200": "SIMPLE_MOVING_AVERAGE_200",
                    "RECOMMENDATION": "TECHNICAL_RATING",
                    "RECOMMENDATION_MARK": "TECHNICAL_RATING",
                    "CLOSE": "PRICE",
                }
                mapped = alias_map.get(enum_name)
                if mapped:
                    try:
                        field = CryptoField[mapped]
                        resolved.append(field)
                    except KeyError:
                        logger.warning(f"Field not found: {name}")
                else:
                    logger.warning(f"Field not found: {name} -> {enum_name}")

        return resolved if resolved else None

    FIELD_MAP = {
        "name": "NAME",
        "close": "PRICE",
        "price": "PRICE",
        "volume": "VOLUME",
        "change_percent": "CHANGE_PERCENT",
        "rsi": "RELATIVE_STRENGTH_INDEX_14",
        "rsi14": "RELATIVE_STRENGTH_INDEX_14",
        "rsi7": "RELATIVE_STRENGTH_INDEX_7",
        "macd_level": "MACD_LEVEL_12_26",
        "macd_signal": "MACD_SIGNAL_12_26",
        "ema_20": "EXPONENTIAL_MOVING_AVERAGE_20",
        "ema_50": "EXPONENTIAL_MOVING_AVERAGE_50",
        "sma_200": "SIMPLE_MOVING_AVERAGE_200",
        "recommendation_mark": "TECHNICAL_RATING",
    }

    def scan(
        self,
        limit: Optional[int] = None,
        custom_fields: Optional[list[str]] = None,
        exchanges: Optional[list[str]] = None,
    ) -> pd.DataFrame:
        """
        Scans cryptocurrency market and returns a Pandas DataFrame.

        Args:
            limit: Maximum result count
            custom_fields: Custom field list (defaults to config if None)
            exchanges: Target exchange names (e.g. ["BINANCE", "KCEX"])

        Returns:
            pd.DataFrame: Scan results
        """
        self.rate_limiter.wait_if_needed()

        if limit is None:
            limit = self.settings.get("scanner.default_limit", 100)

        target_exchanges = (
            exchanges
            if exchanges is not None
            else self.settings.get("scanner.exchanges", [])
        )

        field_names = custom_fields or self.settings.get("scanner.fields", [])
        fields = self._resolve_field_list(field_names) if field_names else None

        fetch_limit = limit * 4 if target_exchanges else limit

        screener = self._build_screener(
            fields=fields, limit=fetch_limit, exchanges=target_exchanges
        )

        try:
            logger.info(f"📡 Scan initiated (limit={limit})...")
            df = screener.get()

            if df is not None and not df.empty:
                logger.info(f"✅ {len(df)} coins fetched. Columns: {list(df.columns)}")

                if target_exchanges:
                    ex_upper = [e.upper() for e in target_exchanges]

                    def is_allowed_exchange(row):
                        sym = str(row.get("Symbol", "")).upper()
                        ex_col = str(row.get("Exchange", "")).upper()
                        if ex_col and ex_col in ex_upper:
                            return True
                        return any(sym.startswith(f"{ex}:") for ex in ex_upper)

                    initial_count = len(df)
                    df = df[df.apply(is_allowed_exchange, axis=1)].reset_index(drop=True)
                    if limit and len(df) > limit:
                        df = df.iloc[:limit].reset_index(drop=True)

                    logger.info(
                        f"🔍 Exchange filter applied ({', '.join(ex_upper)}): "
                        f"{initial_count} -> {len(df)} coins remaining."
                    )
            else:
                logger.warning("Scan result returned empty dataframe.")
                df = pd.DataFrame()

            return df

        except Exception as e:
            logger.error(f"❌ Scan error: {e}", exc_info=True)
            return pd.DataFrame()

    def scan_with_retry(
        self, max_retries: int = 3, **kwargs
    ) -> pd.DataFrame:
        """Executes scan with exponential retry on failure."""
        import time

        for attempt in range(1, max_retries + 1):
            try:
                return self.scan(**kwargs)
            except Exception as e:
                logger.warning(
                    f"Scan attempt {attempt}/{max_retries} failed: {e}"
                )
                if attempt < max_retries:
                    wait_time = attempt * 5
                    logger.info(f"⏳ Retrying in {wait_time}s...")
                    time.sleep(wait_time)

        logger.error("❌ All scan attempts failed.")
        return pd.DataFrame()

    @staticmethod
    def list_available_fields() -> list[str]:
        """Lists available CryptoField names."""
        try:
            from tvscreener.field.crypto import CryptoField
            return [f.name for f in CryptoField]
        except ImportError:
            return []

    @staticmethod
    def get_field_info() -> list[dict]:
        """Returns detailed field metadata."""
        try:
            from tvscreener.field.crypto import CryptoField
            info = []
            for f in CryptoField:
                info.append({
                    "name": f.name,
                    "label": f.value[0] if isinstance(f.value, tuple) else str(f.value),
                })
            return info
        except ImportError:
            return []

    def discover_fields(self, keyword: str = "") -> list[str]:
        """Returns matching field names based on keyword search."""
        fields = self.list_available_fields()
        if not keyword:
            return fields
        kw = keyword.lower()
        return [f for f in fields if kw in f.lower()]
