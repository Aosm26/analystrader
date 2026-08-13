"""
Crypto Scanner

TVScreener kütüphanesini saran wrapper modül.
CryptoScreener üzerinden TradingView verisi çeker.

TVScreener v0.0.11 API'si:
    - CryptoScreener() → screener oluştur
    - screener.specific_fields = CryptoField (veya liste)
    - screener.add_filter(field, FilterOperator.XXX, value)
    - screener.set_range(0, 100)
    - df = screener.get()
"""

from __future__ import annotations


import logging
from typing import Optional, List

import pandas as pd

from config.settings import Settings
from utils.rate_limiter import RateLimiter

logger = logging.getLogger("crypto_bot.scanner")


class CryptoScanner:
    """
    TradingView Screener üzerinden kripto verisi çeken ana modül.

    TVScreener v0.0.11 ile uyumlu wrapper.
    """

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
        Her tarama için taze bir CryptoScreener oluşturur.
        (v0.0.11 API'si state tuttuğu için her seferinde yeni instance.)
        """
        try:
            import tvscreener as tvs
            from tvscreener.field.crypto import CryptoField
            from tvscreener.filter import FilterOperator
        except ImportError:
            raise ImportError(
                "tvscreener kütüphanesi yüklü değil. "
                "Yüklemek için: pip install tvscreener"
            )

        screener = tvs.CryptoScreener()

        # Field'ları ayarla (None ise tüm varsayılan field'lar kullanılır)
        if fields:
            screener.specific_fields = fields
        # else: varsayılan CryptoField kullanılır (tüm field'lar)

        # Borsa filtresi (Tek bir borsa tanımlandıysa API seviyesinde filtrele)
        if exchanges and len(exchanges) == 1:
            try:
                screener.add_filter("exchange", FilterOperator.MATCH, exchanges[0])
            except Exception as e:
                logger.debug(f"API borsa filtresi ekleme uyarısı: {e}")

        # Sonuç aralığını ayarla
        screener.set_range(0, limit)

        return screener

    def _resolve_field_list(self, field_names: list[str]) -> list:
        """
        Config'deki field isimlerini CryptoField enum değerlerine çevirir.
        """
        try:
            from tvscreener.field.crypto import CryptoField
        except ImportError:
            return []

        resolved = []
        for name in field_names:
            # CryptoField enum adıyla eşleştir (büyük harfe çevir)
            enum_name = name.upper()
            try:
                field = CryptoField[enum_name]
                resolved.append(field)
            except KeyError:
                # Alias desteği
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
                        logger.warning(f"Field bulunamadı: {name}")
                else:
                    logger.warning(f"Field bulunamadı: {name} -> {enum_name}")

        return resolved if resolved else None  # None = tüm field'lar

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
        Kripto piyasasını tarar ve DataFrame döner.

        Args:
            limit: Maksimum sonuç sayısı
            custom_fields: Özel field listesi (None ise config'den alınır)
            exchanges: İstenen borsa isimleri listesi (Örn: ["BINANCE", "KCEX"])

        Returns:
            pd.DataFrame: Tarama sonuçları
        """
        self.rate_limiter.wait_if_needed()

        # Parametreleri belirle
        if limit is None:
            limit = self.settings.get("scanner.default_limit", 100)

        target_exchanges = (
            exchanges
            if exchanges is not None
            else self.settings.get("scanner.exchanges", [])
        )

        # Field'ları çözümle
        field_names = custom_fields or self.settings.get("scanner.fields", [])
        fields = self._resolve_field_list(field_names) if field_names else None

        # Borsa filtresi varsa daha fazla satır çek ki filtreleme sonrası istenen miktara ulaşılsın
        fetch_limit = limit * 4 if target_exchanges else limit

        # Screener oluştur
        screener = self._build_screener(
            fields=fields, limit=fetch_limit, exchanges=target_exchanges
        )

        # Veriyi çek
        try:
            logger.info(f"📡 Tarama başlatılıyor (limit={limit})...")
            df = screener.get()

            if df is not None and not df.empty:
                logger.info(f"✅ {len(df)} coin çekildi. Sütunlar: {list(df.columns)}")

                # Borsa filtresi uygula (Symbol index veya Exchange sütunu)
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
                        f"🔍 Borsa filtresi uygulandı ({', '.join(ex_upper)}): "
                        f"{initial_count} -> {len(df)} coin kaldı."
                    )
            else:
                logger.warning("Tarama sonucu boş döndü.")
                df = pd.DataFrame()

            return df

        except Exception as e:
            logger.error(f"❌ Tarama hatası: {e}", exc_info=True)
            return pd.DataFrame()

    def scan_with_retry(
        self, max_retries: int = 3, **kwargs
    ) -> pd.DataFrame:
        """
        Hata durumunda tekrar deneyen tarama.
        """
        import time

        for attempt in range(1, max_retries + 1):
            try:
                return self.scan(**kwargs)
            except Exception as e:
                logger.warning(
                    f"Tarama denemesi {attempt}/{max_retries} başarısız: {e}"
                )
                if attempt < max_retries:
                    wait_time = attempt * 5  # 5s, 10s, 15s
                    logger.info(f"⏳ {wait_time}s sonra tekrar denenecek...")
                    time.sleep(wait_time)

        logger.error("❌ Tüm tarama denemeleri başarısız.")
        return pd.DataFrame()

    @staticmethod
    def list_available_fields() -> list[str]:
        """Kullanılabilir CryptoField isimlerini listeler."""
        try:
            from tvscreener.field.crypto import CryptoField
            return [f.name for f in CryptoField]
        except ImportError:
            return []

    @staticmethod
    def get_field_info() -> list[dict]:
        """Her field hakkında detaylı bilgi döner."""
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
        """Arama kelimesine göre kullanılabilir field isimlerini döner."""
        fields = self.list_available_fields()
        if not keyword:
            return fields
        kw = keyword.lower()
        return [f for f in fields if kw in f.lower()]
