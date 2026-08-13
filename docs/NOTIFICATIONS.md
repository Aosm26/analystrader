# 🔔 Notification System Setup

AnalyTrader supports multi-channel notification dispatches simultaneously.

---

## 1. Console Notifier
- **Output**: Directly prints to `stdout` with ANSI color formatting.
- **BUY Signals**: Highlighted in Green / Light Green.
- **SELL Signals**: Highlighted in Red / Light Red.
- **Configuration**:
  ```yaml
  notifications:
    console:
      enabled: true
      colored: true
  ```

---

## 2. Telegram Bot Integration

### Setup Steps:
1. Message `@BotFather` on Telegram to create a new bot and obtain your `BOT_TOKEN`.
2. Add the bot to your group/channel or send a message directly to it.
3. Retrieve your `CHAT_ID` using `@userinfobot` or `https://api.telegram.org/bot<TOKEN>/getUpdates`.
4. Update `.env`:
   ```ini
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   ```
5. Enable in `config.yaml`:
   ```yaml
   notifications:
     telegram:
       enabled: true
   ```

---

## 3. Webhook Integration (n8n, Discord, Slack)

AnalyTrader delivers JSON payloads over HTTP POST requests.

### Sample Webhook JSON Payload
```json
{
  "event": "signal",
  "data": {
    "symbol": "BTCUSDT",
    "signal_type": "BUY",
    "strategy_name": "rsi_strategy",
    "price": 63445.85,
    "confidence": 85.0,
    "message": "RSI oversold level: 25.4",
    "metadata": {
      "rsi": 25.4,
      "threshold": 30
    },
    "timestamp": "2026-08-14T00:15:00"
  }
}
```
