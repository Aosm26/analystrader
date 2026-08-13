"""
Konfigürasyon Yönetimi

YAML dosyasından ve .env'den ayarları yükler.
Singleton pattern kullanarak tüm uygulama boyunca tek instance sağlar.
"""

import os
import re
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


class Settings:
    """Uygulama konfigürasyonu — Singleton."""

    _instance = None
    _config: dict = {}

    def __new__(cls, config_path: str = "config.yaml"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load(config_path)
        return cls._instance

    def _load(self, config_path: str) -> None:
        """YAML konfigürasyonunu ve .env dosyasını yükler."""
        # .env dosyasını yükle
        env_path = Path(config_path).parent / ".env"
        load_dotenv(env_path)

        # YAML dosyasını oku
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Konfigürasyon dosyası bulunamadı: {config_path}")

        with open(config_file, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)

        # Ortam değişkenlerini çözümle
        self._config = self._resolve_env_vars(raw_config)

    def _resolve_env_vars(self, obj: Any) -> Any:
        """
        YAML içindeki ${ENV_VAR} referanslarını gerçek değerlerle değiştirir.
        """
        if isinstance(obj, str):
            pattern = re.compile(r"\$\{(\w+)\}")
            matches = pattern.findall(obj)
            for var_name in matches:
                env_value = os.getenv(var_name, "")
                obj = obj.replace(f"${{{var_name}}}", env_value)
            return obj
        elif isinstance(obj, dict):
            return {k: self._resolve_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._resolve_env_vars(item) for item in obj]
        return obj

    def get(self, key: str, default: Any = None) -> Any:
        """
        Noktalı notasyon ile ayar değeri alır.
        Örnek: settings.get("scanner.default_limit", 100)
        """
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    @property
    def config(self) -> dict:
        """Ham konfigürasyon sözlüğünü döner."""
        return self._config

    @classmethod
    def reset(cls) -> None:
        """Singleton instance'ı sıfırlar (test amaçlı)."""
        cls._instance = None
        cls._config = {}

    def __repr__(self) -> str:
        return f"Settings(keys={list(self._config.keys())})"
