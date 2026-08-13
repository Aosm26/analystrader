# ⚙️ Configuration Guide

AnalyTrader uses a combination of `config.yaml` for application settings and `.env` for secrets.

---

## 📄 `config.yaml` Reference

```yaml
bot:
  name: "AnalyTraderBot"     # Bot display name
  scan_interval: 300         # Scan cycle interval in seconds (300s = 5m)
  timezone: "Europe/Istanbul"

scanner:
  screener_type: "crypto"    # TradingView screener type ("crypto" or "coin")
  default_limit: 100         # Maximum top market cap coins to scan
  min_volume: 500000         # Minimum 24h USD volume filter
  fields:                    # TradingView fields to retrieve
    - name
    - close
    - change_percent
    - volume
    - relative_strength_index_14
    - macd_level_12_26
    - macd_signal_12_26
    - exponential_moving_average_20
    - exponential_moving_average_50
    - simple_moving_average_200
    - recommendation_mark

strategies:
  enabled:
    - rsi_strategy
    - macd_strategy
    - volume_spike

  rsi_strategy:
    oversold_threshold: 30
    overbought_threshold: 70

  macd_strategy:
    signal_type: "both"      # Options: bullish, bearish, both

  volume_spike:
    multiplier: 3.0

notifications:
  telegram:
    enabled: false           # Set true after configuring .env
    bot_token: "${TELEGRAM_BOT_TOKEN}"
    chat_id: "${TELEGRAM_CHAT_ID}"

  console:
    enabled: true
    colored: true

  webhook:
    enabled: false
    url: "${WEBHOOK_URL}"

storage:
  type: "sqlite"
  path: "data/signals.db"

logging:
  level: "INFO"              # Options: DEBUG, INFO, WARNING, ERROR
  file: "data/logs/bot.log"
  max_size_mb: 10
  backup_count: 5
```

---

## 🔐 Environment Variables (`.env`)

Copy `.env.example` to `.env` and fill in your keys:

```ini
# Telegram Integration
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
TELEGRAM_CHAT_ID=-100123456789

# Webhook Integration (Discord, Slack, n8n)
WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL
```
