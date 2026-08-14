"""
Paper Trader Engine — Simulated Live Trading & Order Execution Motor

Processes signals through a risk & quality filter motor, dynamically calculates
position sizing based on equal balance division (Balance / max_open_positions),
tracks active open positions, and automatically triggers TP/SL closures.
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from models.signal import Signal, SignalType
from storage.sqlite_storage import SQLiteStorage

logger = logging.getLogger("crypto_bot.paper_trader")


class PaperTrader:
    """Paper Trading Engine & Order Execution Motor."""

    def __init__(self, storage: SQLiteStorage, config: Optional[dict] = None):
        self.storage = storage
        self.config = config or {}

        self.initial_balance = float(self.config.get("initial_balance", 10000.0))
        self.max_open_positions = int(self.config.get("max_open_positions", 5))
        self.min_confidence = float(self.config.get("min_confidence", 60.0))
        self.min_risk_reward = float(self.config.get("min_risk_reward", 1.5))

    def update(self, df: pd.DataFrame, signals: list[Signal]) -> dict:
        """
        Main tick handler called after market scanning.
        1. Checks active open positions against updated market prices (TP/SL checks).
        2. Filters and ranks raw strategy signals via the Execution Motor.
        3. Dynamically calculates position size (Balance / max_open_positions).
        4. Opens paper positions for top qualified signals up to max_open_positions.
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

        # Compute current account balance
        stats = self.storage.get_paper_stats()
        total_pnl = stats.get("total_pnl_usd", 0.0)
        current_balance = self.initial_balance + total_pnl

        # Calculate dynamic position size: Current Balance / max_open_positions
        position_size_usd = max(10.0, current_balance / max(1, self.max_open_positions))

        # 2. Execution Motor: Filter & Rank incoming signals
        qualified_signals = self._filter_and_rank_signals(signals)

        # 3. Open Paper Positions for top qualified signals
        open_positions_after = self.storage.get_open_paper_positions()
        open_symbols = {p["symbol"] for p in open_positions_after}

        opened_count = 0
        for sig in qualified_signals:
            if sig.symbol in open_symbols:
                continue  # Already in position

            if len(open_symbols) >= self.max_open_positions:
                logger.debug("Max paper open positions limit reached.")
                break

            entry_price = sig.price
            if entry_price <= 0:
                continue

            meta = sig.metadata or {}
            tp_price = meta.get("tp_price", entry_price * 1.02)
            sl_price = meta.get("sl_price", entry_price * 0.99)

            quantity = position_size_usd / entry_price

            pos_id = self.storage.open_paper_position(
                symbol=sig.symbol,
                strategy_name=sig.strategy_name,
                side="BUY",
                entry_price=entry_price,
                quantity=quantity,
                amount_usd=position_size_usd,
                tp_price=tp_price,
                sl_price=sl_price,
            )

            if pos_id:
                open_symbols.add(sig.symbol)
                opened_count += 1
                logger.info(
                    f"🚀 EXECUTION MOTOR: Opened [{sig.symbol}] ({sig.strategy_name}) | "
                    f"Entry: ${entry_price:,.4f} | Size: ${position_size_usd:,.2f} "
                    f"(1/{self.max_open_positions} of Balance) | "
                    f"TP: ${tp_price:,.4f} | SL: ${sl_price:,.4f} | Conf: {sig.confidence:.1f}%"
                )

        current_open = self.storage.get_open_paper_positions()
        return {
            "initial_balance": self.initial_balance,
            "current_balance": current_balance,
            "realized_pnl_usd": total_pnl,
            "position_size_usd": position_size_usd,
            "open_positions_count": len(current_open),
            "total_trades": stats.get("total_trades", 0),
            "win_rate": stats.get("win_rate", 0.0),
            "closed_tp_this_tick": closed_tp_count,
            "closed_sl_this_tick": closed_sl_count,
            "opened_this_tick": opened_count,
            "signals_filtered_count": len(signals) - len(qualified_signals),
        }

    def _filter_and_rank_signals(self, signals: list[Signal]) -> list[Signal]:
        """
        Signal Execution Motor:
        Filters raw signals by confidence threshold and risk/reward ratio,
        deduplicates by symbol, and ranks by highest confidence score.
        """
        filtered_by_symbol: dict[str, Signal] = {}

        for sig in signals:
            if sig.signal_type not in (SignalType.BUY, SignalType.STRONG_BUY):
                continue

            # 1. Filter by minimum confidence score
            if sig.confidence < self.min_confidence:
                continue

            # 2. Filter by minimum risk/reward ratio if metadata has RR info
            meta = sig.metadata or {}
            rr_ratio = meta.get("risk_reward_ratio")
            if rr_ratio is not None and rr_ratio < self.min_risk_reward:
                continue

            # 3. Deduplicate by symbol: Keep highest confidence signal for each coin
            if sig.symbol not in filtered_by_symbol or sig.confidence > filtered_by_symbol[sig.symbol].confidence:
                filtered_by_symbol[sig.symbol] = sig

        # 4. Rank signals by confidence score descending
        ranked_signals = sorted(filtered_by_symbol.values(), key=lambda s: s.confidence, reverse=True)

        logger.info(
            f"⚡ EXECUTION MOTOR: Filtered {len(signals)} raw signals down to "
            f"{len(ranked_signals)} top qualified signals (Min Conf: {self.min_confidence}%, "
            f"Min RR: {self.min_risk_reward})."
        )
        return ranked_signals

    def _find_col(self, df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
        """Helper to resolve column name."""
        for c in candidates:
            if c in df.columns:
                return c
        return None
