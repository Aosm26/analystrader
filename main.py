#!/usr/bin/env python3
from __future__ import annotations
"""
CryptoScreenerBot — Ana Giriş Noktası

TVScreener kütüphanesi ile kripto piyasalarını tarar,
teknik analiz stratejileri ile sinyal üretir ve
bildirim gönderir.

Kullanım:
    python main.py              # Normal çalıştırma (periyodik tarama)
    python main.py --once       # Tek seferlik tarama
    python main.py --discover   # Kullanılabilir field'ları listele
"""

import argparse
import logging
import sys
from pathlib import Path

# Proje kök dizinini sys.path'e ekle
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import Settings
from config.logging_config import setup_logging
from core.scanner import CryptoScanner
from core.analyzer import Analyzer
from core.scheduler import BotScheduler
from strategies import RSIStrategy, MACDStrategy, VolumeSpikeStrategy
from notifications import ConsoleNotifier, TelegramNotifier, WebhookNotifier
from storage import SQLiteStorage


class CryptoBot:
    """Ana bot sınıfı — tüm bileşenleri birleştirir."""

    def __init__(self, config_path: str = "config.yaml"):
        # Konfigürasyon
        self.settings = Settings(config_path)
        self.logger = setup_logging()

        # Core bileşenler
        self.scanner = CryptoScanner()
        self.analyzer = Analyzer()
        self.scheduler = BotScheduler()

        # Storage
        self.storage = self._init_storage()

        # Notifier'lar
        self.notifiers = self._init_notifiers()

        # Stratejileri kaydet
        self._init_strategies()

        self.logger.info("🤖 CryptoBot başlatıldı.")

    def _init_storage(self) -> SQLiteStorage:
        """Storage backend'ini başlatır."""
        db_path = self.settings.get("storage.path", "data/signals.db")
        return SQLiteStorage(db_path)

    def _init_notifiers(self) -> list:
        """Bildirim kanallarını başlatır."""
        notifiers = []

        # Console
        if self.settings.get("notifications.console.enabled", True):
            colored = self.settings.get("notifications.console.colored", True)
            notifiers.append(ConsoleNotifier(colored=colored))

        # Telegram
        if self.settings.get("notifications.telegram.enabled", False):
            token = self.settings.get("notifications.telegram.bot_token", "")
            chat_id = self.settings.get("notifications.telegram.chat_id", "")
            if token and chat_id and token != "your_bot_token_here":
                notifier = TelegramNotifier(bot_token=token, chat_id=chat_id)
                if notifier.test_connection():
                    notifiers.append(notifier)
                else:
                    self.logger.warning("Telegram bağlantısı başarısız.")
            else:
                self.logger.warning(
                    "Telegram token/chat_id ayarlanmamış. "
                    ".env dosyasını kontrol edin."
                )

        # Webhook
        if self.settings.get("notifications.webhook.enabled", False):
            url = self.settings.get("notifications.webhook.url", "")
            if url:
                notifiers.append(WebhookNotifier(url=url))

        self.logger.info(
            f"Bildirim kanalları: {[n.name for n in notifiers]}"
        )
        return notifiers

    def _init_strategies(self) -> None:
        """Aktif stratejileri kayıt eder."""
        enabled = self.settings.get("strategies.enabled", [])

        strategy_map = {
            "rsi_strategy": RSIStrategy,
            "macd_strategy": MACDStrategy,
            "volume_spike": VolumeSpikeStrategy,
        }

        for strategy_name in enabled:
            if strategy_name in strategy_map:
                config = self.settings.get(f"strategies.{strategy_name}", {})
                strategy = strategy_map[strategy_name](config=config)
                self.analyzer.register_strategy(strategy)
            else:
                self.logger.warning(
                    f"Bilinmeyen strateji: {strategy_name}. Atlanıyor."
                )

        self.logger.info(
            f"Aktif stratejiler: {self.analyzer.strategy_names}"
        )

    def scan_cycle(self) -> None:
        """
        Tek bir tarama döngüsü çalıştırır:
        1. Tarama yap
        2. Analiz et
        3. Sinyalleri kaydet
        4. Bildirim gönder
        """
        try:
            # 1. Tarama
            df = self.scanner.scan_with_retry()

            if df.empty:
                self.logger.warning("Tarama sonucu boş, döngü atlanıyor.")
                return

            # 2. Analiz
            result = self.analyzer.analyze(df)

            # 3. Sinyalleri kaydet
            if result.has_signals:
                self.storage.save_signals(result.signals)

            # Tarama logunu kaydet
            self.storage.save_scan_log(
                scan_time=result.scan_time,
                total_scanned=result.total_coins_scanned,
                signal_count=result.signal_count,
                errors=result.errors,
            )

            # 4. Bildirimleri gönder
            for notifier in self.notifiers:
                try:
                    notifier.send_summary(result)
                except Exception as e:
                    self.logger.error(
                        f"Bildirim hatası ({notifier.name}): {e}"
                    )

        except Exception as e:
            self.logger.error(f"❌ Tarama döngüsü hatası: {e}", exc_info=True)

    def run(self, once: bool = False) -> None:
        """
        Botu çalıştırır.

        Args:
            once: True ise tek seferlik tarama yapar, False ise periyodik
        """
        if once:
            self.logger.info("📡 Tek seferlik tarama çalıştırılıyor...")
            self.scan_cycle()
        else:
            self.scheduler.schedule_scan(self.scan_cycle)
            self.scheduler.run(run_immediately=True)

        self.shutdown()

    def shutdown(self) -> None:
        """Kaynakları serbest bırakır."""
        self.logger.info("🛑 Bot kapatılıyor...")
        self.storage.close()
        self.logger.info("✅ Bot başarıyla kapatıldı.")


def discover_fields(keyword: str = "") -> None:
    """Kullanılabilir TVScreener field'larını listeler."""
    settings = Settings()
    scanner = CryptoScanner()

    if keyword:
        fields = scanner.discover_fields(keyword)
        print(f"\n'{keyword}' ile ilgili {len(fields)} field bulundu:\n")
        for f in fields:
            print(f"  • {f}")
    else:
        # Temel field'ları göster
        print("\nTemel field'lar:")
        for alias, real_name in sorted(CryptoScanner.FIELD_MAP.items()):
            print(f"  {alias:<35} → {real_name}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="CryptoScreenerBot — TVScreener tabanlı kripto sinyal botu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Tek seferlik tarama yap ve çık",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Konfigürasyon dosyası yolu (varsayılan: config.yaml)",
    )
    parser.add_argument(
        "--discover",
        type=str,
        nargs="?",
        const="",
        help="Kullanılabilir field'ları listele. Opsiyonel keyword ile filtrele.",
    )

    args = parser.parse_args()

    if args.discover is not None:
        Settings(args.config)
        discover_fields(args.discover)
        return

    bot = CryptoBot(config_path=args.config)
    bot.run(once=args.once)


if __name__ == "__main__":
    main()
