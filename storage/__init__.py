"""Storage package - Veri depolama."""

from storage.base import BaseStorage
from storage.sqlite_storage import SQLiteStorage

__all__ = ["BaseStorage", "SQLiteStorage"]
