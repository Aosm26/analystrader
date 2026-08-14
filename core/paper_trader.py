"""
Paper Trader Engine & Decision Motor

Implements weighted signal strength (WSS), base asset normalization (grouping SUNUSDT,
SUNUSDT.P, SUNTRY as SUN), risk-reward filtering (R:R >= 1.5), and confluence multiplier
equations (1 + (N * 0.15)).

Calculates dynamic position sizing (Balance / max_open_positions), tracks open positions,
and automatically triggers TP/SL closures.
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from models.signal import Signal, SignalType
from storage.sqlite_storage import SQLiteStorage
from utils.helpers import extract_base_asset

logger = logging.getLogger("crypto_bot.paper_trader")

# Strategy Weights Map
STRATEGY_WEIGHTS = {
    "volume_rsi_breakout": 1.2,  # High weight (Whale Momentum)
    "bollinger_squeeze": 1.1,    # High weight (Volatility Breakout)
    "macd_strategy": 1.0,        # Standard weight
    "ema_pullback": 0.8,         # Standard/Low weight (Dip Re-entry)
}


class PaperTrader:
    """Paper Trading Engine & Decision Motor with Asset Normalization."""

    def __init__(self, storage: SQLiteStorage, config: Optional[dict] = None):
        self.storage = storage
        self.config = config or {}

        self.initial_balance = float(self.config.get("initial_balance", 10000.0))
        self.max_open_positions = int(self.config.get("max_open_positions", 5))
        self.min_risk_reward = float(self.config.get("min_risk_reward", 1.5))
        self.min_final_score = float(self.config.get("min_confidence", 50.0))

    def update(self, df: pd.DataFrame, signals: list[Signal]) -> dict:
        """
        Main tick handler called after market scanning.
        1. Checks active open positions against updated market prices (TP/SL checks).
        2. Executes Decision Motor logic with Asset Normalization.
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

        # 2. Decision Motor: Group by Base Asset -> R:R Filter -> WSS -> Confluence Multiplier -> Rank
        qualified_signals = self.process_decision_motor(signals)

        # 3. Open Paper Positions for top qualified signals (Deduplicated by Base Asset)
        open_positions_after = self.storage.get_open_paper_positions()
        open_base_assets = {extract_base_asset(p["symbol"]) for p in open_positions_after}

        opened_count = 0
        for sig in qualified_signals:
            base_asset = extract_base_asset(sig.symbol)

            if base_asset in open_base_assets:
                continue  # Already in position for this base asset (e.g., SUN, PEOPLE, G)

            if len(open_base_assets) >= self.max_open_positions:
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
                open_base_assets.add(base_asset)
                opened_count += 1
                logger.info(
                    f"🚀 DECISION MOTOR ORDER: [{sig.symbol}] (Base Asset: {base_asset}) | "
                    f"Strategies: ({meta.get('strategies')}) | "
                    f"Entry: ${entry_price:,.4f} | Size: ${position_size_usd:,.2f} "
                    f"(1/{self.max_open_positions} Balance) | "
                    f"TP: ${tp_price:,.4f} | SL: ${sl_price:,.4f} | "
                    f"Final Score: {sig.confidence:.2f} | R:R: {meta.get('risk_reward_ratio', 0):.2f}"
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
            "processed_signals": [s.metadata for s in qualified_signals],
        }

    def process_decision_motor(self, signals: list[Signal]) -> list[Signal]:
        """
        Decision Motor Algorithm with Base Asset Normalization:
        1. Normalizes symbol tickers (SUNUSDT, SUNUSDT.P, SUNTRY -> Base: SUN).
        2. Groups all signals under the same Base Asset.
        3. Finds best trading pair signal by R:R ratio.
        4. Applies Risk Filter (R:R >= 1.5).
        5. Computes Weighted Signal Strength (WSS) per unique strategy for this asset.
        6. Applies Confluence Multiplier = 1 + (N * 0.15) if N > 1 else 1.0 based on distinct strategies.
        7. Sorts qualified assets descending by Final Score.
        """
        # Step 1: Group Signals by Base Asset (e.g., SUN, PEOPLE, G, BTC)
        grouped_by_asset: dict[str, list[Signal]] = {}
        for sig in signals:
            if sig.signal_type not in (SignalType.BUY, SignalType.STRONG_BUY):
                continue
            base = extract_base_asset(sig.symbol)
            if base:
                grouped_by_asset.setdefault(base, []).append(sig)

        qualified_signals: list[Signal] = []

        for base_asset, group in grouped_by_asset.items():
            # Find best trade signal based on Risk/Reward ratio and preferred USDT/USDT.P symbol
            def _signal_score_key(s: Signal) -> tuple[float, float]:
                rr = (s.metadata or {}).get("risk_reward_ratio", 1.5)
                pref = 2.0 if s.symbol.endswith(".P") else (1.5 if s.symbol.endswith("USDT") else 1.0)
                return (rr, pref)

            best_signal = max(group, key=_signal_score_key)
            meta = best_signal.metadata or {}
            rr_ratio = float(meta.get("risk_reward_ratio", 1.5))

            # --- 1. RISK FILTER ---
            if rr_ratio < self.min_risk_reward:
                logger.debug(f"Risk Filter Skipped Base [{base_asset}]: R:R {rr_ratio:.2f} < {self.min_risk_reward}")
                continue

            # --- 2. SIGNAL STRENGTH & UNIQUE STRATEGY DEDUPLICATION ---
            # Group strategy signals by strategy_name (keep highest confidence per strategy for this coin)
            strat_map: dict[str, Signal] = {}
            for sig in group:
                if sig.strategy_name not in strat_map or sig.confidence > strat_map[sig.strategy_name].confidence:
                    strat_map[sig.strategy_name] = sig

            total_score = 0.0
            strategies_used = []

            for strat_name, sig in strat_map.items():
                weight = STRATEGY_WEIGHTS.get(strat_name, 1.0)
                total_score += (sig.confidence * weight)
                strategies_used.append(strat_name)

            # --- 3. CONFLUENCE MULTIPLIER ---
            # Distinct strategy count for this underlying asset (e.g. SUN)
            confluence_count = len(strat_map)
            multiplier = (1.0 + (confluence_count * 0.15)) if confluence_count > 1 else 1.0
            final_score = round(total_score * multiplier, 2)

            if final_score < self.min_final_score:
                continue

            entry_price = float(meta.get("entry_price", best_signal.price))
            tp_price = float(meta.get("tp_price", entry_price * 1.02))
            sl_price = float(meta.get("sl_price", entry_price * 0.99))

            strategies_str = ", ".join(strategies_used)

            # Enriched Signal metadata matching n8n format
            enriched_meta = {
                "symbol": best_signal.symbol,
                "base_asset": base_asset,
                "action": best_signal.signal_type.value,
                "final_score": final_score,
                "confluence_count": confluence_count,
                "strategies": strategies_str,
                "entry_price": entry_price,
                "tp_price": tp_price,
                "sl_price": sl_price,
                "risk_reward_ratio": rr_ratio,
            }

            processed_signal = Signal(
                symbol=best_signal.symbol,
                signal_type=best_signal.signal_type,
                strategy_name=f"Motor({strategies_str})",
                price=entry_price,
                confidence=final_score,
                message=best_signal.message,
                metadata=enriched_meta,
                timestamp=best_signal.timestamp,
            )
            qualified_signals.append(processed_signal)

            if confluence_count > 1:
                logger.info(
                    f"🔥 ASSET CONFLUENCE DETECTED on Base [{base_asset}] ({best_signal.symbol})! "
                    f"Strategies: {strategies_used} | Confluence Score: {final_score:.2f}"
                )

        # Step 5: Sort by Final Score descending
        ranked_signals = sorted(
            qualified_signals,
            key=lambda s: (s.metadata or {}).get("final_score", 0.0),
            reverse=True
        )

        logger.info(
            f"⚡ DECISION MOTOR: Evaluated {len(signals)} raw signals across "
            f"{len(grouped_by_asset)} base assets ➔ {len(ranked_signals)} top qualified orders."
        )
        return ranked_signals

    def _find_col(self, df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
        """Helper to resolve column name."""
        for c in candidates:
            if c in df.columns:
                return c
        return None
