"""
Paper Trader Engine — Simulated Live Trading & Portfolio Tracker

Executes virtual paper trades based on generated strategy signals, tracks active
open positions against real-time market data, and automatically triggers TP/SL closures.
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from models.signal import Signal, SignalType
from storage.sqlite_storage import SQLiteStorage

logger = logging.getLogger("crypto_bot.paper_trader")


class PaperTrader:
    """Paper Trading Engine & Portfolio Manager."""

    def __init__(self, storage: SQLiteStorage, config: Optional[dict] = None):
        self.storage = storage
        self.config = config or {}

        self.initial_balance = float(self.config.get("initial_balance", 10000.0))
        self.trade_amount_usd = float(self.config.get("trade_amount_usd", 100.0))
        self.max_open_positions = int(self.config.get("max_open_positions", 10))

    def update(self, df: pd.DataFrame, signals: list[Signal]) -> dict:
        """
        Main tick handler called after market scanning.
        1. Checks active open positions against updated market prices (TP/SL checks).
        2. Opens new paper positions for eligible BUY signals.
        3. Returns current account & trade statistics.
        """
        # Create price map from scanned market data
        price_map = {}
        name_col = self._find_col(df, ["name", "Name", "ticker", "Symbol"])
        price_col = self._find_col(df, ["close", "Close", "price", "Price"])

        if name_col and price_col:
            for _, row in df.iterrows():
                symbol = str(row.get(name_col))
                price = float(row.get(price_col, 0))
                if symbol and price > 0:
                    price_map[symbol] = price

        # 1. Update Open Positions (Check TP / SL)
        closed_tp_count = 0
        closed_sl_count = 0

        open_positions = self.storage.get_open_paper_positions()
        for pos in open_positions:
            symbol = pos["symbol"]
            current_price = price_map.get(symbol)

            if current_price is None or current_price <= 0:
                continue

            tp_price = pos["tp_price"]
            sl_price = pos["sl_price"]
            entry_price = pos["entry_price"]
            quantity = pos["quantity"]

            # Check TP Hit
            if current_price >= tp_price:
                pnl_usd = (current_price - entry_price) * quantity
                pnl_percent = ((current_price - entry_price) / entry_price) * 100.0
                self.storage.close_paper_position(
                    position_id=pos["id"],
                    exit_price=current_price,
                    status="CLOSED_TP",
                    pnl_usd=pnl_usd,
                    pnl_percent=pnl_percent,
                )
                closed_tp_count += 1
                logger.info(
                    f"🎯 PAPER TP HIT! [{symbol}] Closed at ${current_price:,.4f} "
                    f"(PnL: +${pnl_usd:.2f} / +{pnl_percent:.2f}%)"
                )

            # Check SL Hit
            elif current_price <= sl_price:
                pnl_usd = (current_price - entry_price) * quantity
                pnl_percent = ((current_price - entry_price) / entry_price) * 100.0
                self.storage.close_paper_position(
                    position_id=pos["id"],
                    exit_price=current_price,
                    status="CLOSED_SL",
                    pnl_usd=pnl_usd,
                    pnl_percent=pnl_percent,
                )
                closed_sl_count += 1
                logger.warning(
                    f"🛑 PAPER SL HIT! [{symbol}] Closed at ${current_price:,.4f} "
                    f"(PnL: ${pnl_usd:.2f} / {pnl_percent:.2f}%)"
                )

        # 2. Process New Signals (Open New Positions)
        open_positions_after = self.storage.get_open_paper_positions()
        open_symbols = {p["symbol"] for p in open_positions_after}

        opened_count = 0
        for sig in signals:
            if sig.signal_type not in (SignalType.BUY, SignalType.STRONG_BUY):
                continue

            if sig.symbol in open_symbols:
                continue  # Already in position

            if len(open_symbols) >= self.max_open_positions:
                logger.debug("Max paper open positions limit reached.")
                break

            entry_price = sig.price
            if entry_price <= 0:
                continue

            # Extract TP and SL from metadata or defaults (+2% / -1%)
            meta = sig.metadata or {}
            tp_price = meta.get("tp_price", entry_price * 1.02)
            sl_price = meta.get("sl_price", entry_price * 0.99)

            amount_usd = self.trade_amount_usd
            quantity = amount_usd / entry_price

            pos_id = self.storage.open_paper_position(
                symbol=sig.symbol,
                strategy_name=sig.strategy_name,
                side="BUY",
                entry_price=entry_price,
                quantity=quantity,
                amount_usd=amount_usd,
                tp_price=tp_price,
                sl_price=sl_price,
            )

            if pos_id:
                open_symbols.add(sig.symbol)
                opened_count += 1
                logger.info(
                    f"🚀 PAPER POSITION OPENED: [{sig.symbol}] Entry: ${entry_price:,.4f} | "
                    f"Size: ${amount_usd:.2f} | TP: ${tp_price:,.4f} | SL: ${sl_price:,.4f}"
                )

        # 3. Compute Performance Stats
        stats = self.storage.get_paper_stats()
        current_open = self.storage.get_open_paper_positions()
        total_pnl = stats.get("total_pnl_usd", 0.0)
        current_balance = self.initial_balance + total_pnl

        return {
            "initial_balance": self.initial_balance,
            "current_balance": current_balance,
            "realized_pnl_usd": total_pnl,
            "open_positions_count": len(current_open),
            "total_trades": stats.get("total_trades", 0),
            "win_rate": stats.get("win_rate", 0.0),
            "closed_tp_this_tick": closed_tp_count,
            "closed_sl_this_tick": closed_sl_count,
            "opened_this_tick": opened_count,
        }

    def _find_col(self, df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
        """Helper to resolve column name."""
        for c in candidates:
            if c in df.columns:
                return c
        return None
