# 🚀 AnalyTrader — TradingView Crypto Scanning & Quantitative Signal Bot

**AnalyTrader** is a modular, high-performance Python bot designed to scan cryptocurrency markets via the `tvscreener` library (TradingView API), compute technical indicators, generate trading signals, and notify users via multiple channels (Telegram, Console, Webhooks).

---

## ✨ Features

- 📡 **TradingView Scanner Integration**: Fetch live crypto market data, indicators (RSI, MACD, Moving Averages, Volume, Ratings).
- 🧠 **Modular Strategy Engine**: Built-in strategies (RSI, MACD, Volume Spike) and Meta-Composite (Confluence) strategy.
- 🔔 **Multi-Channel Notifications**: Real-time alerts via Console (colored), Telegram Bot, and Custom Webhooks.
- 💾 **SQLite Persistence**: Stores all signal history and scan logs with indexed queries for performance analysis.
- ⚡ **Extensible Architecture**: Easy to add custom technical strategies, exchanges, backtesting, or web dashboards.
- 🛡️ **Rate Limiting & Retries**: Built-in rate limiter and exponential backoff to handle network blips.

---

## 📚 Documentation Index

- [Architecture & System Design](docs/ARCHITECTURE.md)
- [Strategy Guide & Custom Strategy Creation](docs/STRATEGIES.md)
- [Configuration Guide (`config.yaml` & `.env`)](docs/CONFIGURATION.md)
- [Notification Channels Setup (Telegram, Webhook)](docs/NOTIFICATIONS.md)
- [Storage & Database Queries](docs/STORAGE.md)

---

## ⚡ Quick Start Guide

### 1. Requirements
- Python 3.8+
- Git

### 2. Installation

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/analytrader.git
cd analytrader

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration Setup

Copy environment template:
```bash
cp .env.example .env
```
*(Edit `.env` to add your Telegram bot token and chat ID if desired).*

### 4. Running the Bot

```bash
# Execute a single scan cycle and exit
python3 main.py --once

# Run periodic background scanning (every 5 minutes)
python3 main.py

# Discover available TradingView fields
python3 main.py --discover
python3 main.py --discover rsi
```

---

## 🛠️ Project Structure

```
analytrader/
├── config/             # Configuration parsing & Singleton settings
│   ├── settings.py
│   └── logging_config.py
├── core/               # Main application pipeline
│   ├── scanner.py      # TVScreener wrapper & field resolver
│   ├── analyzer.py     # Strategy aggregator & signal coordinator
│   └── scheduler.py    # Graceful interval scheduler
├── strategies/         # Technical analysis strategies
│   ├── base.py         # Abstract Strategy Base Class
│   ├── rsi_strategy.py
│   ├── macd_strategy.py
│   ├── volume_spike.py
│   └── composite.py    # Confluence strategy
├── notifications/      # Notification engines
│   ├── base.py
│   ├── console_notifier.py
│   ├── telegram_notifier.py
│   └── webhook_notifier.py
├── storage/            # Database layer
│   ├── base.py
│   └── sqlite_storage.py
├── models/             # Data models & Enums
│   ├── signal.py
│   └── scan_result.py
├── utils/              # Helper utilities & Rate limiter
│   ├── helpers.py
│   └── rate_limiter.py
├── docs/               # Detailed documentation
├── config.yaml         # Main configuration file
├── .env.example        # Environment variables template
├── main.py             # Application entry point
├── requirements.txt    # Python dependencies
└── README.md           # Main documentation
```

---

## 📄 License

This project is licensed under the MIT License.
