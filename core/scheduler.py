"""
Scheduler — Zamanlayıcı

Periyodik tarama döngüsünü yönetir.
"""

import logging
import signal
import time
from datetime import datetime
from typing import Callable, Optional

import schedule

from config.settings import Settings

logger = logging.getLogger("crypto_bot.scheduler")


class BotScheduler:
    """
    Periyodik görevleri yöneten zamanlayıcı.
    Graceful shutdown desteği ile.
    """

    def __init__(self):
        self.settings = Settings()
        self._running = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """SIGINT ve SIGTERM sinyallerini yakalar."""
        signal.signal(signal.SIGINT, self._shutdown_handler)
        signal.signal(signal.SIGTERM, self._shutdown_handler)

    def _shutdown_handler(self, signum, frame) -> None:
        """Graceful shutdown."""
        logger.info("🛑 Kapatma sinyali alındı, bot durduruluyor...")
        self._running = False

    def schedule_scan(
        self,
        scan_func: Callable,
        interval: Optional[int] = None,
    ) -> None:
        """
        Tarama fonksiyonunu belirli aralıklarla çalıştırmak üzere zamanlar.

        Args:
            scan_func: Çalıştırılacak tarama fonksiyonu
            interval: Tarama aralığı (saniye). None ise config'den alınır.
        """
        if interval is None:
            interval = self.settings.get("bot.scan_interval", 300)

        schedule.every(interval).seconds.do(scan_func)
        logger.info(f"⏰ Tarama zamanlandı: her {interval} saniyede bir")

    def run(self, run_immediately: bool = True) -> None:
        """
        Zamanlayıcıyı başlatır ve sonsuz döngüde çalıştırır.

        Args:
            run_immediately: True ise ilk taramayı hemen yapar
        """
        self._running = True
        bot_name = self.settings.get("bot.name", "CryptoBot")

        logger.info(f"🚀 {bot_name} başlatıldı — {datetime.now()}")

        if run_immediately:
            logger.info("📡 İlk tarama çalıştırılıyor...")
            schedule.run_all()

        logger.info("⏳ Zamanlayıcı döngüsü başladı...")
        while self._running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Zamanlayıcı hatası: {e}", exc_info=True)
                time.sleep(5)

        logger.info(f"🛑 {bot_name} durduruldu — {datetime.now()}")

    def stop(self) -> None:
        """Zamanlayıcıyı durdurur."""
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running
