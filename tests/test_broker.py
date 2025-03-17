from datetime import datetime

import pandas as pd
import pytest

from kissbt.broker import Broker
from kissbt.entities import OpenPosition, Order, OrderType


def test_initial_broker_state(broker):
    assert broker.cash == 100000
    assert broker.portfolio_value == 100000
    assert broker.open_positions == {}
    assert broker.closed_positions == []
    assert broker.history == {
        "cash": [],
        "date": [],
        "long_position_value": [],
        "positions": [],
        "short_position_value": [],
        "total_value": [],
    }


def test_place_order(broker):
    order = Order("AAPL", 10, OrderType.OPEN)
    broker.place_order(order)
    assert len(broker._open_orders) == 1
    assert broker._open_orders[0] == order


def test_execute_order(broker, mocker):
    order = Order("AAPL", 10, OrderType.OPEN)
    mocker.patch.object(broker, "_get_price_for_order", return_value=150.0)
    broker._execute_order(
        order,
        bar=pd.DataFrame({"open": [150.0], "close": [152.0]}, index=["AAPL"]),
        datetime=datetime.now(),
    )
    assert broker.cash == 100000 - (10 * 150 * 1.001)
    assert len(broker.open_positions) == 1


def test_get_price_for_order(broker, mocker):
    mocker.patch.object(broker, "_get_price_for_order", return_value=150.0)
    order = Order("AAPL", 5, OrderType.LIMIT, 145.0)
    price = broker._get_price_for_order(order)
    assert price == 150.0


def test_update_open_positions(broker):
    order = Order("AAPL", 10, OrderType.OPEN)
    assert broker._execute_order(
        order,
        bar=pd.DataFrame({"open": [150.0], "close": [152.0]}, index=["AAPL"]),
        datetime=datetime.now(),
    )
    assert len(broker.open_positions) == 1
    assert "AAPL" in broker.open_positions


def test_update_closed_positions(broker):
    position = OpenPosition("AAPL", 10, 150.0, datetime.now())
    broker._open_positions["AAPL"] = position
    broker._update_closed_positions(
        position.ticker, -position.size, position.price, position.datetime
    )
    assert len(broker.closed_positions) == 1
    assert broker.closed_positions[0].ticker == "AAPL"


def test_liquidate_positions(broker):
    order = Order("AAPL", 10, OrderType.OPEN)
    bar = pd.DataFrame({"open": [150.0], "close": [152.0]}, index=["AAPL"])
    time = datetime.now()
    broker._execute_order(
        order,
        bar=bar,
        datetime=time,
    )
    broker._current_bar = bar
    broker._current_datetime = time
    broker.liquidate_positions()

    assert broker.open_positions == {}
    assert len(broker.closed_positions) == 1
    assert broker.closed_positions[0].ticker == "AAPL"
    assert broker.closed_positions[0].size == 10
    assert broker.closed_positions[0].purchase_price == 150.0
    assert broker.closed_positions[0].purchase_datetime == time
    assert broker.closed_positions[0].selling_price == 152.0
    assert broker.closed_positions[0].selling_datetime == time


# --- Testing Portfolio Metrics ---
def test_long_position_value(broker):
    broker._open_positions = {"AAPL": OpenPosition("AAPL", 10, 150.0, datetime.now())}
    broker._current_bar = pd.DataFrame(
        {"open": [150.0], "close": [152.0]}, index=["AAPL"]
    )
    assert (
        float(broker.long_position_value) == 1520.0 * 0.999
    )  # Adjusted for trading fees


def test_short_position_value(broker):
    broker._open_positions = {"AAPL": OpenPosition("AAPL", -10, 150.0, datetime.now())}
    broker._current_bar = pd.DataFrame(
        {"open": [150.0], "close": [152.0]}, index=["AAPL"]
    )
    assert float(broker.short_position_value) == -1520.0 * (1 + 0.001)


# --- Testing Order Execution ---
def test_execute_order_open(broker, mocker):
    order = Order("AAPL", 10, OrderType.OPEN)
    mocker.patch.object(broker, "_get_price_for_order", return_value=150.0)
    executed = broker._execute_order(
        order,
        bar=pd.DataFrame({"open": [150.0], "close": [152.0]}, index=["AAPL"]),
        datetime=datetime.now(),
    )
    assert executed
    assert broker.cash == 98498.5
    assert len(broker.open_positions) == 1
    assert broker.open_positions["AAPL"].size == 10


def test_execute_order_close(broker):
    order = Order("AAPL", -10, OrderType.CLOSE)
    bar = pd.DataFrame({"open": [150.0], "close": [152.0]}, index=["AAPL"])
    broker._open_positions["AAPL"] = OpenPosition("AAPL", 10, 150.0, datetime.now())
    broker._current_bar = bar
    executed = broker._execute_order(
        order,
        bar=bar,
        datetime=datetime.now(),
    )
    assert executed
    assert float(broker.cash) == 100000 + 10 * 152 * 0.999
    assert len(broker.open_positions) == 0
    assert len(broker.closed_positions) == 1


def test_place_multiple_orders(broker):
    order1 = Order("AAPL", 10, OrderType.OPEN)
    order2 = Order("GOOG", 5, OrderType.OPEN)
    broker.place_order(order1)
    broker.place_order(order2)
    assert len(broker._open_orders) == 2
    assert broker._open_orders[0] == order1
    assert broker._open_orders[1] == order2


def test_portfolio_value_with_positions(broker):
    broker._open_positions = {
        "AAPL": OpenPosition("AAPL", 10, 150.0, datetime.now()),
        "GOOG": OpenPosition("GOOG", -5, 1000.0, datetime.now()),
    }
    broker._current_bar = pd.DataFrame(
        {"close": [152.0, 995.0]}, index=["AAPL", "GOOG"]
    )
    assert broker.portfolio_value == 100000 + (1520.0 * 0.999) - (4975.0 * 1.001)


def test_update_history(broker):
    broker._current_datetime = datetime.now()
    broker._cash = 100000
    broker._open_positions = {
        "AAPL": OpenPosition("AAPL", 10, 150.0, datetime.now()),
        "GOOG": OpenPosition("GOOG", -5, 1000.0, datetime.now()),
    }
    broker._current_bar = pd.DataFrame(
        {"close": [152.0, 995.0]}, index=["AAPL", "GOOG"]
    )
    broker._update_history()
    history = broker.history
    assert len(history["date"]) == 1
    assert len(history["cash"]) == 1
    assert len(history["long_position_value"]) == 1
    assert len(history["short_position_value"]) == 1
    assert len(history["total_value"]) == 1
    assert len(history["positions"]) == 1
    assert history["cash"][0] == 100000
    assert history["long_position_value"][0] == 1520.0 * 0.999
    assert history["short_position_value"][0] == -4975.0 * 1.001
    assert float(history["total_value"][0]) == pytest.approx(
        100000 + (1520.0 * 0.999) - (4975.0 * 1.001), abs=1e-5
    )
    assert history["positions"][0] == 2


def test_benchmark(broker):
    assert (
        "benchmark" not in broker.history
        or broker.history.get("benchmark") == []
        or broker.benchmark is None
    )


def test_benchmark_history_update(broker, mocker):
    broker._benchmark = "AAPL"
    bar = pd.DataFrame({"close": [150]}, index=["AAPL"])
    mocker.patch.object(broker, "_current_bar", bar)
    broker._history["benchmark"] = []
    broker._update_history()
    assert len(broker.history["benchmark"]) == 1


def test_limit_order_execution(broker):
    bar = pd.DataFrame({"open": [100], "low": [98], "high": [102]}, index=["AAPL"])
    order = Order("AAPL", 10, OrderType.LIMIT, limit=99)
    price = broker._get_price_for_order(order, bar)
    assert price == 99

    order = Order("AAPL", -10, OrderType.LIMIT, limit=101)
    price = broker._get_price_for_order(order, bar)
    assert price == 101


def test_invalid_order_type(broker):
    order = Order("AAPL", 10, "INVALID")
    bar = pd.DataFrame({"open": [100], "low": [98], "high": [102]}, index=["AAPL"])
    with pytest.raises(ValueError, match="Unknown order type"):
        broker._get_price_for_order(order, bar)


def test_position_update(broker):
    broker._open_positions["AAPL"] = OpenPosition(
        ticker="AAPL", size=5, price=100, datetime=datetime(2024, 1, 1)
    )
    broker._update_open_positions("AAPL", 10, 110, datetime(2024, 1, 2))
    assert broker._open_positions["AAPL"].size == 15
    assert broker._open_positions["AAPL"].price == pytest.approx(
        (5 * 100 + 10 * 110) / 15
    )


def test_short_position_fees(broker, mocker):
    broker._long_only = False
    broker._current_bar = pd.DataFrame({"close": [100]}, index=["AAPL"])
    broker._open_positions["AAPL"] = OpenPosition(
        ticker="AAPL", size=-10, price=105, datetime=datetime(2024, 1, 1)
    )
    next_bar = pd.DataFrame({"close": [100]}, index=["AAPL"])
    next_datetime = pd.Timestamp("2024-01-02")
    broker.update(next_bar, next_datetime)
    assert broker.cash < 100000  # Short fee applied


def test_benchmark_initialization():
    broker_with_benchmark = Broker(
        start_capital=100000,
        fees=0.001,
        long_only=True,
        short_fee_rate=0.02,
        benchmark="AAPL",
    )
    assert "benchmark" in broker_with_benchmark.history
    assert broker_with_benchmark.history["benchmark"] == []


def test_get_price_for_order_with_limit(broker):
    bar = pd.DataFrame({"open": [100], "low": [98], "high": [102]}, index=["AAPL"])
    order = Order("AAPL", 10, OrderType.OPEN)
    price = broker._get_price_for_order(order, bar)
    assert price == 100


def test_update_history_with_benchmark(broker, mocker):
    broker._benchmark = "AAPL"
    bar = pd.DataFrame({"close": [150]}, index=["AAPL"])
    mocker.patch.object(broker, "_current_bar", bar)
    broker._history["benchmark"] = []
    broker._update_history()
    assert len(broker.history["benchmark"]) == 1


def test_broker_initializes_with_benchmark():
    broker_with_benchmark = Broker(
        start_capital=100000,
        fees=0.001,
        long_only=True,
        short_fee_rate=0.02,
        benchmark="AAPL",
    )
    assert broker_with_benchmark.benchmark == "AAPL"


def test_check_long_only_blocks_short_orders(broker):
    broker._long_only = True
    order = Order("AAPL", -10, OrderType.OPEN)
    with pytest.raises(ValueError):
        broker._check_long_only_condition(order, datetime.now())


def test_check_long_only_condition(broker):
    time = datetime.now()
    broker._current_bar = pd.DataFrame(
        {"open": [150.0], "close": [152.0]}, index=["AAPL"]
    )
    broker._current_datetime = time
    order = Order("AAPL", -10, order_type=OrderType.OPEN)
    with pytest.raises(ValueError):
        broker._check_long_only_condition(order, time)


def test_update_with_short_fees(broker):
    broker._long_only = False
    broker._open_positions["AAPL"] = OpenPosition(
        "AAPL", -10, 100, datetime(2024, 1, 1)
    )
    next_bar = pd.DataFrame({"close": [100]}, index=["AAPL"])
    next_datetime = pd.Timestamp("2024-01-02")
    broker.update(next_bar, next_datetime)
    assert broker.cash < 100000  # Short fee applied


def test_history_copy(broker):
    history_copy = broker.history
    assert history_copy == broker._history
    assert history_copy is not broker._history  # Ensure it's a copy


def test_update_cash(broker):
    order = Order("AAPL", 10, OrderType.OPEN)
    broker._update_cash(order, price=150.0)
    assert broker.cash == 100000 - (10 * 150 * 1.001)

    order = Order("AAPL", -10, OrderType.CLOSE)
    broker._update_cash(order, price=150.0)
    assert broker.cash == 98498.5 + 10 * 150 * 0.999


@pytest.mark.parametrize(
    "size_change, expected_size, expected_price",
    [
        (-10, None, None),
        (5, 15, (10 * 100 + 5 * 110) / 15),
        (-5, 5, 100),
    ],
)
def test_update_open_positions_cases(
    broker, size_change, expected_size, expected_price
):
    broker._open_positions["AAPL"] = OpenPosition("AAPL", 10, 100, datetime(2024, 1, 1))
    broker._update_open_positions("AAPL", size_change, 110, datetime(2024, 1, 2))

    if expected_size is None:
        assert "AAPL" not in broker._open_positions
    else:
        assert broker._open_positions["AAPL"].size == expected_size
        assert broker._open_positions["AAPL"].price == pytest.approx(expected_price)


def test_update_ticker_out_of_universe(broker):
    broker._open_positions["AAPL"] = OpenPosition("AAPL", 10, 100, datetime(2024, 1, 1))

    broker.update(
        pd.DataFrame({"close": [100, 500]}, index=["GOOG", "AAPL"]),
        datetime(2024, 1, 2),
    )

    broker.update(pd.DataFrame({"close": [110]}, index=["GOOG"]), datetime(2024, 1, 3))

    assert len(broker._closed_positions) == 1
    closed_pos = broker._closed_positions[0]
    assert closed_pos.ticker == "AAPL"
    assert closed_pos.size == 10
    assert closed_pos.purchase_price == 100
    assert closed_pos.selling_price == 500
    assert closed_pos.purchase_datetime == datetime(2024, 1, 1)
    assert closed_pos.selling_datetime == datetime(2024, 1, 2)
