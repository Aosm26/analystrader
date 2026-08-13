"""
SQLite Storage

Sinyalleri SQLite veritabanında saklar.
Hafif, dosya tabanlı, kurulum gerektirmeyen depolama.
"""

from __future__ import annotations


import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from models.signal import Signal, SignalType
from storage.base import BaseStorage

logger = logging.getLogger("crypto_bot.storage.sqlite")


class SQLiteStorage(BaseStorage):
    """SQLite tabanlı sinyal depolama."""

    def __init__(self, db_path: str = "data/signals.db"):
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()
        logger.info(f"SQLite veritabanı açıldı: {db_path}")

    def _create_tables(self) -> None:
        """Gerekli tabloları oluşturur."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                price REAL NOT NULL,
                confidence REAL DEFAULT 0,
                message TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}',
                timestamp TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_signals_symbol
                ON signals(symbol);
            CREATE INDEX IF NOT EXISTS idx_signals_timestamp
                ON signals(timestamp);
            CREATE INDEX IF NOT EXISTS idx_signals_strategy
                ON signals(strategy_name);

            CREATE TABLE IF NOT EXISTS scan_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_time TEXT NOT NULL,
                total_scanned INTEGER DEFAULT 0,
                signal_count INTEGER DEFAULT 0,
                errors TEXT DEFAULT '[]',
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        self._conn.commit()

    def save_signal(self, signal: Signal) -> bool:
        """Tek bir sinyali kaydeder."""
        try:
            self._conn.execute(
                """
                INSERT INTO signals
                    (symbol, signal_type, strategy_name, price,
                     confidence, message, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal.symbol,
                    signal.signal_type.value,
                    signal.strategy_name,
                    signal.price,
                    signal.confidence,
                    signal.message,
                    json.dumps(signal.metadata),
                    signal.timestamp.isoformat(),
                ),
            )
            self._conn.commit()
            return True

        except sqlite3.Error as e:
            logger.error(f"Sinyal kaydetme hatası: {e}")
            return False

    def save_signals(self, signals: list[Signal]) -> int:
        """Birden fazla sinyali toplu kaydeder."""
        saved = 0
        try:
            for signal in signals:
                self._conn.execute(
                    """
                    INSERT INTO signals
                        (symbol, signal_type, strategy_name, price,
                         confidence, message, metadata, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        signal.symbol,
                        signal.signal_type.value,
                        signal.strategy_name,
                        signal.price,
                        signal.confidence,
                        signal.message,
                        json.dumps(signal.metadata),
                        signal.timestamp.isoformat(),
                    ),
                )
                saved += 1

            self._conn.commit()
            logger.info(f"💾 {saved} sinyal kaydedildi.")

        except sqlite3.Error as e:
            logger.error(f"Toplu kaydetme hatası: {e}")
            self._conn.rollback()

        return saved

    def get_signals(
        self,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[Signal]:
        """Filtrelere göre sinyalleri getirir."""
        query = "SELECT * FROM signals WHERE 1=1"
        params = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        if strategy:
            query += " AND strategy_name = ?"
            params.append(strategy)
        if since:
            query += " AND timestamp >= ?"
            params.append(since.isoformat())

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        try:
            cursor = self._conn.execute(query, params)
            rows = cursor.fetchall()

            signals = []
            for row in rows:
                signal = Signal(
                    symbol=row["symbol"],
                    signal_type=SignalType(row["signal_type"]),
                    strategy_name=row["strategy_name"],
                    price=row["price"],
                    confidence=row["confidence"],
                    message=row["message"],
                    metadata=json.loads(row["metadata"]),
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    id=row["id"],
                )
                signals.append(signal)

            return signals

        except sqlite3.Error as e:
            logger.error(f"Sinyal sorgulama hatası: {e}")
            return []

    def get_signal_count(
        self,
        symbol: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> int:
        """Sinyal sayısını döner."""
        query = "SELECT COUNT(*) FROM signals WHERE 1=1"
        params = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        if since:
            query += " AND timestamp >= ?"
            params.append(since.isoformat())

        try:
            cursor = self._conn.execute(query, params)
            return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"Sayım hatası: {e}")
            return 0

    def save_scan_log(
        self,
        scan_time: datetime,
        total_scanned: int,
        signal_count: int,
        errors: list[str],
    ) -> None:
        """Tarama logunu kaydeder."""
        try:
            self._conn.execute(
                """
                INSERT INTO scan_logs
                    (scan_time, total_scanned, signal_count, errors)
                VALUES (?, ?, ?, ?)
                """,
                (
                    scan_time.isoformat(),
                    total_scanned,
                    signal_count,
                    json.dumps(errors),
                ),
            )
            self._conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Scan log hatası: {e}")

    def close(self) -> None:
        """Veritabanı bağlantısını kapatır."""
        if self._conn:
            self._conn.close()
            logger.info("SQLite bağlantısı kapatıldı.")
