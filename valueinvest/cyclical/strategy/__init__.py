"""
Cyclical Stock Investment Strategies

Different strategies for A-share (trading) and US (dividend defensive) markets.
"""

from .base import BaseCyclicalStrategy
from .ashare_strategy import AShareCyclicalStrategy
from .us_strategy import USCyclicalStrategy

__all__ = [
    "BaseCyclicalStrategy",
    "AShareCyclicalStrategy",
    "USCyclicalStrategy",
]
