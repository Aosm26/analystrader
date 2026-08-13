# 💾 Storage & Data Management

AnalyTrader persists all detected market signals and scan cycle metadata in an indexed SQLite database located at `data/signals.db`.

---

## 🗄️ Database Schema

### Table: `signals`
Stores every individual trading signal emitted by active strategies.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique signal ID |
| `symbol` | TEXT | NOT NULL, INDEXED | Ticker symbol (e.g. BTCUSDT) |
| `signal_type` | TEXT | NOT NULL | `BUY`, `SELL`, `STRONG_BUY`, `STRONG_SELL` |
| `strategy_name` | TEXT | NOT NULL, INDEXED | Strategy that triggered the signal |
| `price` | REAL | NOT NULL | Coin price at signal generation |
| `confidence` | REAL | DEFAULT 0 | Signal confidence score (0-100%) |
| `message` | TEXT | DEFAULT '' | Human readable signal reasoning |
| `metadata` | TEXT | DEFAULT '{}' | JSON string of technical indicator snapshots |
| `timestamp` | TEXT | NOT NULL, INDEXED | ISO-8601 timestamp of signal generation |
| `created_at` | TEXT | DEFAULT (datetime('now')) | SQLite insertion time |

### Table: `scan_logs`
Stores execution statistics for each scanning cycle.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary Key |
| `scan_time` | TEXT | ISO-8601 timestamp of scan execution |
| `total_scanned` | INTEGER | Total coins processed |
| `signal_count` | INTEGER | Total signals generated in scan |
| `errors` | TEXT | JSON list of execution errors |

---

## 🔍 Useful SQL Queries

You can inspect your signal history using SQLite CLI or GUI tools (DBeaver, DB Browser for SQLite):

```sql
-- Top 10 highest confidence BUY signals
SELECT symbol, strategy_name, price, confidence, timestamp
FROM signals
WHERE signal_type IN ('BUY', 'STRONG_BUY')
ORDER BY confidence DESC
LIMIT 10;

-- Signal count grouped by strategy
SELECT strategy_name, COUNT(*) as signal_count
FROM signals
GROUP BY strategy_name;

-- Get recent signals for BTCUSDT
SELECT * FROM signals
WHERE symbol LIKE '%BTC%'
ORDER BY timestamp DESC;
```
