# 🏗️ AnalyTrader — System Architecture

AnalyTrader is a modular, extensible cryptocurrency scanning and quantitative signal generation platform built on top of Python and the `tvscreener` library.

---

## 📐 High-Level Architecture

The system follows a reactive pipeline pattern:

```
[Scheduler] ──► [CryptoScanner] ──► [Analyzer] ──► [Strategies]
                                       │
                                       ▼
                             [Signal Aggregator]
                                 │         │
                                 ▼         ▼
                           [Storage]   [Notifications]
```

### Data Pipeline Sequence
1. **Trigger**: `BotScheduler` fires a scan event based on configured interval (default: 300s).
2. **Data Fetching**: `CryptoScanner` queries TradingView Screener API for live market metrics (OHLCV, RSI, MACD, Moving Averages, Technical Ratings).
3. **Analysis & Strategy Execution**: `Analyzer` passes the fetched `DataFrame` through all enabled strategies (RSI, MACD, Volume Spike, Composite).
4. **Signal Generation**: Each strategy evaluates rows against criteria and emits standardized `Signal` dataclass objects with confidence scores (0-100%).
5. **Persistence**: `SQLiteStorage` records all generated signals and scan metadata to `data/signals.db`.
6. **Notification Dispatch**: `ConsoleNotifier`, `TelegramNotifier`, and `WebhookNotifier` format and dispatch alerts to designated channels.

---

## 📂 Core Modules Breakdown

### 1. `config/`
- `settings.py`: Singleton pattern configuration parser loading `config.yaml` and expanding `${ENV_VAR}` variables from `.env`.
- `logging_config.py`: Centralized logging setup supporting console & size-rotated file logs (`data/logs/bot.log`).

### 2. `core/`
- `scanner.py`: Wrapper around `tvscreener.CryptoScreener`. Features field resolution, custom filters, and built-in rate-limiting logic (`utils/rate_limiter.py`).
- `analyzer.py`: Strategy execution engine. Runs data against active strategy instances, handles errors gracefully, and sorts signals by confidence.
- `scheduler.py`: Thread-safe loop manager using `schedule` with SIGINT/SIGTERM graceful shutdown handlers.

### 3. `strategies/`
- `base.py`: Abstract base class (`BaseStrategy`) enforcing `analyze(df: pd.DataFrame) -> list[Signal]` and column-matching helper utilities.
- `rsi_strategy.py`: Evaluates overbought/oversold levels.
- `macd_strategy.py`: Evaluates MACD line crossovers & histogram direction.
- `volume_spike.py`: Detects volume anomalies relative to rolling averages.
- `composite.py`: Confluence strategy that requires multiple sub-strategies to agree before emitting a high-confidence signal.

### 4. `storage/`
- `base.py`: Storage interface definition.
- `sqlite_storage.py`: SQLite implementation managing indexed tables for `signals` and `scan_logs`.

### 5. `notifications/`
- `base.py`: Notifier interface.
- `console_notifier.py`: Terminal output formatted with ANSI color codes.
- `telegram_notifier.py`: Async-ready Telegram bot notifier sending HTML formatted alerts.
- `webhook_notifier.py`: Generic HTTP POST notifier compatible with Discord, Slack, n8n, and Webhooks.

---

## 🔒 Security & Data Privacy

- Secrets (API Tokens, Webhook URLs) are kept in `.env` and excluded via `.gitignore`.
- Database files (`data/*.db`) and log files (`data/logs/*`) are local-only and git-ignored.
