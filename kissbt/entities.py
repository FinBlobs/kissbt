from dataclasses import dataclass
from enum import Enum

import pandas as pd


class OrderType(Enum):
    OPEN = "open"
    CLOSE = "close"
    LIMIT = "limit"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class OpenPosition:
    """
    Immutable representation of an open trading position.

    Args:
        ticker (str): Financial instrument identifier
        size (float): Position size (positive for long, negative for short)
        price (float): Opening price of the position
        datetime (datetime): Position opening timestamp
    """

    ticker: str
    size: float
    price: float
    datetime: pd.Timestamp


@dataclass(frozen=True)
class ClosedPosition:
    """
    Immutable representation of a completed trading transaction.

    Args:
        ticker (str): Financial instrument identifier
        size (float): Position size (positive for long, negative for short)
        purchase_price (float): Entry price of the position
        purchase_datetime (pd.Timestamp): Position entry timestamp
        selling_price (float): Exit price of the position
        selling_datetime (pd.Timestamp): Position exit timestamp
    """

    ticker: str
    size: float
    purchase_price: float
    purchase_datetime: pd.Timestamp
    selling_price: float
    selling_datetime: pd.Timestamp
