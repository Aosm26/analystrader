"""
Loglama Konfigürasyonu

Renkli konsol çıktısı ve dosya loglaması.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config.settings import Settings


def setup_logging() -> logging.Logger:
    """Uygulama genelinde loglama sistemini kurar."""
    settings = Settings()
    log_level = settings.get("logging.level", "INFO")
    log_file = settings.get("logging.file", "data/logs/bot.log")
    max_size_mb = settings.get("logging.max_size_mb", 10)
    backup_count = settings.get("logging.backup_count", 5)

    # Log dizinini oluştur
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Root logger
    logger = logging.getLogger("crypto_bot")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Formatlayıcı
    fmt = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt=date_fmt)

    # Konsol handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Dosya handler (rotating)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_size_mb * 1024 * 1024,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
