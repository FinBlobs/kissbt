from datetime import datetime

import pandas as pd

from kissbt.entities import OpenPosition, Order, OrderType


def test_order_creation():
    order = Order(
        ticker="AAPL",
        size=10,
        order_type=OrderType.LIMIT,
        limit=150.0,
        good_till_cancel=True,
    )

    assert order.ticker == "AAPL"
    assert order.size == 10
    assert order.order_type == OrderType.LIMIT
    assert order.limit == 150.0
    assert order.good_till_cancel is True


def test_order_defaults():
    order = Order(ticker="GOOGL", size=5)

    assert order.order_type == OrderType.OPEN  # Default value
    assert order.limit is None
    assert order.good_till_cancel is False


def test_open_position_creation():
    entry_time = pd.Timestamp(datetime(2024, 1, 1, 10, 30, 0))
    position = OpenPosition(ticker="MSFT", size=50, price=250.0, datetime=entry_time)

    assert position.ticker == "MSFT"
    assert position.size == 50
    assert position.price == 250.0
    assert position.datetime == entry_time
