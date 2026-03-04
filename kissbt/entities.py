from dataclasses import dataclass
from enum import Enum

import pandas as pd


class OrderType(Enum):
    OPEN = "open"
    CLOSE = "close"
    LIMIT = "limit"


@dataclass(frozen=True, slots=True)
class Order:
    """
    Trading order representation. Immutable to ensure data integrity and thread safety.

    Args:
        ticker (str): Ticker symbol of the traded asset
        size (float): Order size (positive for buy, negative for sell)
        order_type (OrderType, optional): Order type, defaults to OPEN
        limit (float | None, optional): Limit price if applicable, defaults to None
        good_till_cancel (bool, optional): Order validity flag, defaults to False
    """

    ticker: str
    size: float
    order_type: OrderType = OrderType.OPEN
    limit: float | None = None
    good_till_cancel: bool = False


@dataclass(frozen=True, slots=True)
class OpenPosition:
    """
    Immutable representation of an open trading position.

    Args:
        ticker (str): Financial instrument identifier
        size (float): Position size (positive for long, negative for short)
        price (float): Opening price of the position
        timestamp (pd.Timestamp): Position opening timestamp
    """

    ticker: str
    size: float
    price: float
    timestamp: pd.Timestamp


@dataclass(frozen=True, slots=True)
class ClosedPosition:
    """
    Immutable representation of a completed trading transaction.

    Args:
        ticker (str): Financial instrument identifier
        size (float): Position size (positive for long, negative for short)
        entry_price (float): Position entry price
        entry_timestamp (pd.Timestamp): Position entry timestamp
        exit_price (float): Position exit price
        exit_timestamp (pd.Timestamp): Position exit timestamp
    """

    ticker: str
    size: float
    entry_price: float
    entry_timestamp: pd.Timestamp
    exit_price: float
    exit_timestamp: pd.Timestamp

    @property
    def entry_value(self) -> float:
        """Signed entry notional value (`entry_price * size`)."""
        return self.entry_price * self.size

    @property
    def exit_value(self) -> float:
        """Signed exit notional value (`exit_price * size`)."""
        return self.exit_price * self.size

    @property
    def pnl(self) -> float:
        """Signed profit and loss (PnL) from entry/exit prices and signed size."""
        return self.exit_value - self.entry_value
