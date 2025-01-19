from datetime import datetime
from enum import Enum


class OrderType(Enum):
    OPEN = "open"
    CLOSE = "close"
    LIMIT = "limit"


class Order:
    """
    A class to represent an open trading order.

    Attributes:
    ----------
    ticker : str
        The ticker symbol of the traded asset.
    size : float
        The size of the order.
    order_type : OrderType
        The type of the order, currently supported are open, close, and limit and the
        default is set to open.
    limit : float, optional
        The limit price for the order, if applicable.
    good_till_cancel : bool
        Whether the order is valid until canceled. The default is set to False, meaning
        the order is only valid for the next bar.
    was_filled : bool
        Whether the order has been filled. This is initially set to False and updated
        when the order is executed.
    """

    def __init__(
        self,
        ticker: str,
        size: float,
        order_type: OrderType = OrderType.OPEN,
        limit: float | None = None,
        good_till_cancel: bool = False,
    ) -> None:
        self.ticker: str = ticker
        self.size: float = size
        self.order_type: str = order_type
        self.limit: float = limit
        self.good_till_cancel: bool = good_till_cancel
        self.was_filled: bool = False

    def __str__(self):
        return f"""
            ----------
            ticker {self.ticker}
            size {self.size}
            type {self.order_type}
            limit {self.limit}
            good_till_cancel {self.good_till_cancel}
            was_filled {self.was_filled}
            ----------
        """


class OpenPosition:
    """
    Represents an open position in a financial instrument.

    Attributes:
        ticker (str): The ticker symbol of the financial instrument.
        size (float): The size of the position.
        price (float): The price at which the position was opened.
        datetime (datetime): The date and time when the position was opened.
    """

    def __init__(
        self,
        ticker: str,
        size: float,
        price: float,
        datetime: datetime,
    ) -> None:
        self.price = price
        self.datetime = datetime
        self.size = size
        self.ticker = ticker

    def __str__(self):
        return f"""
            ----------
            ticker {self.ticker}
            size {self.size}
            price {self.price}
            datetime {self.datetime}
            ----------
        """


class ClosedPosition:
    """
    A class to represent a closed trading position.

    Attributes:
    ----------
    ticker : str
        The ticker symbol of the traded asset.
    size : float
        The size of the position.
    purchase_price : float
        The price at which the asset was purchased.
    purchase_datetime : datetime
        The datetime when the asset was purchased.
    selling_price : float
        The price at which the asset was sold.
    selling_datetime : datetime
        The datetime when the asset was sold.
    """

    def __init__(
        self,
        ticker: str,
        size: float,
        purchase_price: float,
        purchase_datetime: datetime,
        selling_price: float,
        selling_datetime: datetime,
    ) -> None:
        self.ticker: str = ticker
        self.size: float = size
        self.purchase_price: float = purchase_price
        self.purchase_datetime: datetime = purchase_datetime
        self.selling_price: float = selling_price
        self.selling_datetime: datetime = selling_datetime

    def __str__(self):
        return f"""
            ----------
            ticker {self.ticker}
            size {self.size}
            purchase_price {self.purchase_price}
            purchase_datetime {self.purchase_datetime}
            selling_price {self.selling_price}
            selling_datetime {self.selling_datetime}
            ----------
        """
