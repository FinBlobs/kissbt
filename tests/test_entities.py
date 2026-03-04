import pandas as pd

import kissbt
from kissbt.entities import ClosedPosition, OpenPosition, Order, OrderType


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
    entry_time = pd.Timestamp(2024, 1, 1, 10, 30, 0)
    position = OpenPosition(ticker="MSFT", size=50, price=250.0, timestamp=entry_time)

    assert position.ticker == "MSFT"
    assert position.size == 50
    assert position.price == 250.0
    assert position.timestamp == entry_time


def test_closed_position_uses_entry_exit_semantics():
    position = ClosedPosition(
        ticker="AAPL",
        size=-10,
        entry_price=100.0,
        entry_timestamp=pd.Timestamp(2024, 1, 1),
        exit_price=90.0,
        exit_timestamp=pd.Timestamp(2024, 1, 2),
    )

    assert position.entry_price == 100.0
    assert position.entry_timestamp == pd.Timestamp(2024, 1, 1)
    assert position.exit_price == 90.0
    assert position.exit_timestamp == pd.Timestamp(2024, 1, 2)
    assert position.entry_value == -1000.0
    assert position.exit_value == -900.0
    assert position.pnl == 100.0


def test_closed_position_requires_entry_exit_fields():
    position = ClosedPosition(
        ticker="AAPL",
        size=10,
        entry_price=100.0,
        entry_timestamp=pd.Timestamp(2024, 1, 1),
        exit_price=105.0,
        exit_timestamp=pd.Timestamp(2024, 1, 2),
    )

    assert position.entry_price == 100.0
    assert position.exit_price == 105.0


def test_package_root_exports_core_api():
    assert kissbt.Broker.__name__ == "Broker"
    assert kissbt.Engine.__name__ == "Engine"
    assert kissbt.Analyzer.__name__ == "Analyzer"
    assert kissbt.Strategy.__name__ == "Strategy"
