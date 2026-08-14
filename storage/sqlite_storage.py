"""
SQLite Storage Implementation

Persists signals and scan logs in an indexed SQLite database file.
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
    """SQLite signal and scan log database."""

    def __init__(self, db_path: str = "data/signals.db"):
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()
        logger.info(f"SQLite database opened: {db_path}")

    def _create_tables(self) -> None:
        """Initializes database schema and indices."""
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

            CREATE TABLE IF NOT EXISTS paper_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                quantity REAL NOT NULL,
                amount_usd REAL NOT NULL,
                tp_price REAL NOT NULL,
                sl_price REAL NOT NULL,
                status TEXT DEFAULT 'OPEN',
                exit_price REAL DEFAULT 0,
                pnl_usd REAL DEFAULT 0,
                pnl_percent REAL DEFAULT 0,
                opened_at TEXT NOT NULL,
                closed_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_paper_positions_status
                ON paper_positions(status);
            CREATE INDEX IF NOT EXISTS idx_paper_positions_symbol
                ON paper_positions(symbol);
        """)
        self._conn.commit()

    def save_signal(self, signal: Signal) -> bool:
        """Saves a single signal."""
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
            logger.error(f"Save signal error: {e}")
            return False

    def save_signals(self, signals: list[Signal]) -> int:
        """Batch saves multiple signals."""
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
            logger.info(f"💾 {saved} signals saved to SQLite.")

        except sqlite3.Error as e:
            logger.error(f"Batch save error: {e}")
            self._conn.rollback()

        return saved

    def get_signals(
        self,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[Signal]:
        """Queries stored signals matching filters."""
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
            logger.error(f"Signal query error: {e}")
            return []

    def get_signal_count(
        self,
        symbol: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> int:
        """Returns signal count matching filters."""
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
            logger.error(f"Count query error: {e}")
            return 0

    def save_scan_log(
        self,
        scan_time: datetime,
        total_scanned: int,
        signal_count: int,
        errors: list[str],
    ) -> None:
        """Saves scan cycle log metrics."""
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
            logger.error(f"Scan log error: {e}")

    def open_paper_position(
        self,
        symbol: str,
        strategy_name: str,
        side: str,
        entry_price: float,
        quantity: float,
        amount_usd: float,
        tp_price: float,
        sl_price: float,
    ) -> Optional[int]:
        """Opens a new paper trading position."""
        try:
            now = datetime.utcnow().isoformat()
            cursor = self._conn.execute(
                """
                INSERT INTO paper_positions
                    (symbol, strategy_name, side, entry_price, quantity,
                     amount_usd, tp_price, sl_price, status, opened_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)
                """,
                (
                    symbol,
                    strategy_name,
                    side,
                    entry_price,
                    quantity,
                    amount_usd,
                    tp_price,
                    sl_price,
                    now,
                ),
            )
            self._conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Error opening paper position: {e}")
            return None

    def close_paper_position(
        self,
        position_id: int,
        exit_price: float,
        status: str,
        pnl_usd: float,
        pnl_percent: float,
    ) -> bool:
        """Closes an open paper trading position with TP or SL."""
        try:
            now = datetime.utcnow().isoformat()
            self._conn.execute(
                """
                UPDATE paper_positions
                SET status = ?, exit_price = ?, pnl_usd = ?, pnl_percent = ?, closed_at = ?
                WHERE id = ?
                """,
                (status, exit_price, pnl_usd, pnl_percent, now, position_id),
            )
            self._conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error closing paper position {position_id}: {e}")
            return False

    def get_open_paper_positions(self) -> list[dict]:
        """Retrieves all currently open paper trading positions."""
        try:
            cursor = self._conn.execute(
                "SELECT * FROM paper_positions WHERE status = 'OPEN'"
            )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error fetching open paper positions: {e}")
            return []

    def get_paper_stats(self) -> dict:
        """Calculates paper trading performance stats."""
        try:
            cursor = self._conn.execute("""
                SELECT
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) as win_trades,
                    SUM(CASE WHEN pnl_usd < 0 THEN 1 ELSE 0 END) as loss_trades,
                    COALESCE(SUM(pnl_usd), 0.0) as total_pnl_usd
                FROM paper_positions
                WHERE status IN ('CLOSED_TP', 'CLOSED_SL')
            """)
            row = dict(cursor.fetchone())
            total = row["total_trades"] or 0
            wins = row["win_trades"] or 0
            row["win_rate"] = round((wins / total) * 100.0, 1) if total > 0 else 0.0
            return row
        except sqlite3.Error as e:
            logger.error(f"Error fetching paper stats: {e}")
            return {"total_trades": 0, "win_trades": 0, "loss_trades": 0, "total_pnl_usd": 0.0, "win_rate": 0.0}

    def close(self) -> None:
        """Closes SQLite database connection."""
        if self._conn:
            self._conn.close()
            logger.info("SQLite connection closed.")
