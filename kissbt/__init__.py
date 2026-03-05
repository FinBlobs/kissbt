from importlib.metadata import version

from kissbt.analyzer import Analyzer
from kissbt.broker import Broker
from kissbt.engine import BacktestResult, Engine
from kissbt.entities import ClosedPosition, OpenPosition, Order, OrderType
from kissbt.strategy import Strategy

__version__ = version("kissbt")

__all__ = [
    "Analyzer",
    "BacktestResult",
    "Broker",
    "ClosedPosition",
    "Engine",
    "OpenPosition",
    "Order",
    "OrderType",
    "Strategy",
    "__version__",
]
