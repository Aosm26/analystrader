"""
Paper Trader Engine — Simulated Live Trading & Order Execution Motor

Processes signals through a specialized Strategy Alignment Motor tailored for:
1. Volume Spike + RSI Breakout (volume_rsi_breakout)
2. Bollinger Bands Squeeze & Breakout (bollinger_squeeze)
3. Dual EMA Trend Pullback (ema_pullback)

Calculates dynamic position sizing (Balance / max_open_positions), detects multi-strategy
confluence boosts, tracks active positions, and executes automatic TP/SL closures.
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from models.signal import Signal, SignalType
from storage.sqlite_storage import SQLiteStorage

logger = logging.getLogger("crypto_bot.paper_trader")

# Target Core Strategies
CORE_STRATEGIES = {
    "bollinger_squeeze": {"weight": 1.10, "label": "Bollinger Breakout"},
    "volume_rsi_breakout": {"weight": 1.08, "label": "Whale RSI Momentum"},
    "ema_pullback": {"weight": 1.05, "label": "Dual EMA Pullback"},
}


class PaperTrader:
    """Paper Trading Engine & Strategy Execution Motor."""

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
        2. Filters & ranks raw strategy signals via the Strategy-Aligned Execution Motor.
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

        # 2. Execution Motor: Filter, Confluence-Boost & Rank incoming signals
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
                    f"🚀 EXECUTION MOTOR ORDER: [{sig.symbol}] ({sig.strategy_name}) | "
                    f"Entry: ${entry_price:,.4f} | Size: ${position_size_usd:,.2f} "
                    f"(1/{self.max_open_positions} Balance) | "
                    f"TP: ${tp_price:,.4f} | SL: ${sl_price:,.4f} | Final Score: {sig.confidence:.1f}%"
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
        Strategy-Aligned Execution Motor:
        1. Filters signals produced by bollinger_squeeze, volume_rsi_breakout, and ema_pullback.
        2. Detects multi-strategy confluence (if a coin hits multiple core strategies).
        3. Applies strategy weighting & risk/reward filters.
        4. Ranks signals by final weighted score descending.
        """
        # Group signals by symbol
        symbol_signals: dict[str, list[Signal]] = {}
        for sig in signals:
            if sig.signal_type not in (SignalType.BUY, SignalType.STRONG_BUY):
                continue
            symbol_signals.setdefault(sig.symbol, []).append(sig)

        qualified_signals: list[Signal] = []

        for symbol, sig_list in symbol_signals.items():
            # Check strategy alignment
            core_sigs = [s for s in sig_list if s.strategy_name in CORE_STRATEGIES]

            if not core_sigs:
                # If no core strategy generated signal for this symbol, fall back to best signal if confidence is high
                best_sig = max(sig_list, key=lambda s: s.confidence)
                if best_sig.confidence >= self.min_confidence + 10.0:  # Higher bar for non-core
                    qualified_signals.append(best_sig)
                continue

            # Pick primary core signal with highest base confidence
            primary_sig = max(core_sigs, key=lambda s: s.confidence)
            strat_info = CORE_STRATEGIES[primary_sig.strategy_name]
            weight = strat_info["weight"]

            # Calculate weighted score
            weighted_score = primary_sig.confidence * weight

            # Confluence Boost: Check if multiple core strategies fired for the same coin!
            strategies_fired = {s.strategy_name for s in core_sigs}
            if len(strategies_fired) >= 2:
                weighted_score += 15.0  # +15% Confluence Bonus!
                logger.info(
                    f"🔥 MULTI-STRATEGY CONFLUENCE DETECTED on [{symbol}]! "
                    f"Strategies: {list(strategies_fired)} | Score Boosted: {weighted_score:.1f}%"
                )

            # Risk/Reward Check
            meta = primary_sig.metadata or {}
            rr_ratio = meta.get("risk_reward_ratio")
            if rr_ratio is not None and rr_ratio < self.min_risk_reward:
                continue

            # Minimum confidence check against weighted score
            if weighted_score < self.min_confidence:
                continue

            # Clone signal with final weighted score for ranking
            final_signal = Signal(
                symbol=primary_sig.symbol,
                signal_type=SignalType.BUY,
                strategy_name=f"{primary_sig.strategy_name}" + (f"+Confluence({len(strategies_fired)})" if len(strategies_fired) > 1 else ""),
                price=primary_sig.price,
                confidence=min(100.0, weighted_score),
                message=primary_sig.message,
                metadata=primary_sig.metadata,
                timestamp=primary_sig.timestamp,
            )
            qualified_signals.append(final_signal)

        # Rank by final score descending
        ranked_signals = sorted(qualified_signals, key=lambda s: s.confidence, reverse=True)

        logger.info(
            f"⚡ STRATEGY MOTOR: Evaluated {len(signals)} raw signals ➔ "
            f"{len(ranked_signals)} qualified orders (Min Conf: {self.min_confidence}%, Min RR: {self.min_risk_reward})."
        )
        return ranked_signals

    def _find_col(self, df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
        """Helper to resolve column name."""
        for c in candidates:
            if c in df.columns:
                return c
        return None
