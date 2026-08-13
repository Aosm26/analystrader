"""Strategies Package — Quantitative trading strategies."""

from strategies.base import BaseStrategy
from strategies.rsi_strategy import RSIStrategy
from strategies.macd_strategy import MACDStrategy
from strategies.volume_spike import VolumeSpikeStrategy
from strategies.volume_rsi_breakout import VolumeRSIBreakoutStrategy
from strategies.bollinger_squeeze import BollingerSqueezeStrategy
from strategies.composite import CompositeStrategy

__all__ = [
    "BaseStrategy",
    "RSIStrategy",
    "MACDStrategy",
    "VolumeSpikeStrategy",
    "VolumeRSIBreakoutStrategy",
    "BollingerSqueezeStrategy",
    "CompositeStrategy",
]
