"""
Configuration Management

Loads settings from YAML files and environment variables (.env).
Uses Singleton pattern to provide a single instance across the app.
"""

import os
import re
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


class Settings:
    """Application Configuration — Singleton."""

    _instance = None
    _config: dict = {}

    def __new__(cls, config_path: str = "config.yaml"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load(config_path)
        return cls._instance

    def _load(self, config_path: str) -> None:
        """Loads YAML configuration and .env file."""
        env_path = Path(config_path).parent / ".env"
        load_dotenv(env_path)

        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_file, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)

        self._config = self._resolve_env_vars(raw_config)

    def _resolve_env_vars(self, obj: Any) -> Any:
        """Replaces ${ENV_VAR} references with environment variable values."""
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
        Retrieves setting value using dot notation.
        Example: settings.get("scanner.default_limit", 100)
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
        """Returns raw configuration dictionary."""
        return self._config

    @classmethod
    def reset(cls) -> None:
        """Resets singleton instance (for testing)."""
        cls._instance = None
        cls._config = {}

    def __repr__(self) -> str:
        return f"Settings(keys={list(self._config.keys())})"
