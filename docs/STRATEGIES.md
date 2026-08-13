# 📊 Strategy Guide & Development

AnalyTrader's strategy system is designed for high modularity. Every strategy operates on Pandas DataFrames produced by the scanner.

---

## 💡 Active Built-in Strategies

### 1. RSI Strategy (`rsi_strategy`)
- **Logic**: Evaluates Relative Strength Index (RSI 14).
- **Parameters**:
  - `oversold_threshold` (default: `30`): Values $\le 30$ generate `BUY` / `STRONG_BUY` signals.
  - `overbought_threshold` (default: `70`): Values $\ge 70$ generate `SELL` / `STRONG_SELL` signals.
- **Confidence Formula**: Dynamic scaling based on distance from thresholds.

### 2. MACD Strategy (`macd_strategy`)
- **Logic**: Evaluates MACD Level vs Signal Line and Histogram.
- **Parameters**:
  - `signal_type`: `"bullish"`, `"bearish"`, or `"both"`.
- **Confidence Formula**: Scaled according to the magnitude of the histogram difference.

### 3. Volume Spike Strategy (`volume_spike`)
- **Logic**: Identifies volume explosions relative to the median market volume.
- **Parameters**:
  - `multiplier` (default: `3.0`): Triggers when current volume $\ge 3.0 \times \text{median\_volume}$.
- **Direction**: Determined by 24h price change percentage (positive = BUY, negative = SELL).

### 4. Volume Spike + RSI Breakout Strategy (`volume_rsi_breakout`)
- **Logic**: Catches institutional algorithms / whale order flow by detecting simultaneous volume surges ($\ge 2.5\times \text{SMA}_{20}(V)$) and healthy RSI momentum breakouts ($50 < \text{RSI} \le 65$).
- **Parameters**:
  - `volume_multiplier` (default: `2.5`): Minimum volume surge relative to median market volume.
  - `rsi_min` (default: `50`): Minimum RSI threshold.
  - `rsi_max` (default: `65`): Maximum RSI threshold (prevents buying overbought tops).
  - `tp_percent` (default: `1.50%`): Take profit target percentage above entry price.
  - `sl_percent` (default: `0.75%`): Stop loss percentage below entry price (or candle low).
- **Risk / Reward Ratio**: 2.0 (TP: 1.50% / SL: 0.75%).

### 5. Bollinger Bands Squeeze & Breakout Strategy (`bollinger_squeeze`)
- **Logic**: Identifies tight consolidation (Bandwidth $\le 10\%$) followed by a sharp breakout above the Upper Bollinger Band ($P_{close} > \text{Upper Band}$).
- **Parameters**:
  - `bandwidth_threshold` (default: `0.10`): Maximum relative bandwidth threshold ($\frac{\text{Upper} - \text{Lower}}{\text{Middle}}$).
  - `tp_percent` (default: `2.00%`): Take profit target percentage above entry price.
  - `sl_price`: Middle Band (20 SMA). Setup invalidation if price drops back below middle band.

### 6. Composite Strategy (`composite`)
- **Logic**: Meta-strategy requiring $N$ sub-strategies to agree on the same coin (Confluence).
- **Boosted Confidence**: Emits `STRONG_BUY` or `STRONG_SELL` with confidence multiplier when agreement criteria is met.

---

## 🛠️ How to Create a Custom Strategy

Creating a new strategy requires only 3 simple steps:

### Step 1: Create a python file in `strategies/`

```python
from __future__ import annotations
import pandas as pd
from models.signal import Signal, SignalType
from strategies.base import BaseStrategy

class GoldenCrossStrategy(BaseStrategy):
    @property
    def name(self) -> str:
        return "golden_cross"

    def analyze(self, df: pd.DataFrame) -> list[Signal]:
        signals = []
        ema20_col = self._find_column(df, ["EMA20", "exponential_moving_average_20"])
        sma200_col = self._find_column(df, ["SMA200", "simple_moving_average_200"])
        price_col = self._find_column(df, ["close", "price"])
        name_col = self._find_column(df, ["name", "symbol"])

        if not ema20_col or not sma200_col:
            return signals

        for idx, row in df.iterrows():
            ema20 = float(row.get(ema20_col, 0))
            sma200 = float(row.get(sma200_col, 0))
            symbol = str(row.get(name_col, idx))
            price = float(row.get(price_col, 0))

            if ema20 > sma200:  # Bullish trend
                signals.append(Signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    strategy_name=self.name,
                    price=price,
                    confidence=75.0,
                    message=f"EMA20 ({ema20:.2f}) > SMA200 ({sma200:.2f})"
                ))
        return signals
```

### Step 2: Register strategy in `main.py`

In `_init_strategies()` method of `main.py`, add your strategy class mapping.

### Step 3: Enable in `config.yaml`

```yaml
strategies:
  enabled:
    - golden_cross

  golden_cross:
    custom_param: 100
```
