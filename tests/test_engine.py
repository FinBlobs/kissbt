import pandas as pd
import pytest

from kissbt.broker import Broker
from kissbt.engine import Engine
from kissbt.entities import Order
from kissbt.strategy import Strategy


class DummyStrategy(Strategy):
    def initialize(self) -> None:
        self.observed_indexes: list[list[str]] = []

    def generate_orders(
        self, current_data: pd.DataFrame, current_timestamp: pd.Timestamp
    ) -> None:
        self.observed_indexes.append(list(current_data.index))
        return None


class BuyFirstBarStrategy(Strategy):
    def initialize(self) -> None:
        self.did_buy = False

    def generate_orders(
        self, current_data: pd.DataFrame, current_timestamp: pd.Timestamp
    ) -> None:
        if not self.did_buy:
            self.broker.place_order(Order("AAPL", 1))
            self.did_buy = True


def test_engine_requires_matching_broker():
    broker_for_engine = Broker()
    different_broker = Broker()
    strategy = DummyStrategy(different_broker)

    with pytest.raises(ValueError):
        Engine(broker=broker_for_engine, strategy=strategy)


def test_engine_accepts_matching_broker():
    broker = Broker()
    strategy = DummyStrategy(broker)

    engine = Engine(broker=broker, strategy=strategy)

    assert engine.broker is broker
    assert engine.strategy is strategy


def test_engine_run_accepts_timestamp_and_ticker_columns():
    broker = Broker()
    strategy = DummyStrategy(broker)
    engine = Engine(broker=broker, strategy=strategy)

    data = pd.DataFrame(
        {
            "timestamp": [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02")],
            "ticker": ["AAPL", "AAPL"],
            "close": [100.0, 101.0],
        }
    )

    engine.run(data)

    assert strategy.observed_indexes == [["AAPL"], ["AAPL"]]


def test_engine_run_requires_timestamp_for_non_multiindex_data():
    broker = Broker()
    strategy = DummyStrategy(broker)
    engine = Engine(broker=broker, strategy=strategy)
    data = pd.DataFrame({"date": [pd.Timestamp("2024-01-01")], "ticker": ["AAPL"]})

    with pytest.raises(ValueError, match="Data must use MultiIndex"):
        engine.run(data)


def test_engine_run_requires_timestamp_level_for_multiindex_data():
    broker = Broker()
    strategy = DummyStrategy(broker)
    engine = Engine(broker=broker, strategy=strategy)
    data = pd.DataFrame(
        {"close": [100.0]},
        index=pd.MultiIndex.from_tuples(
            [(pd.Timestamp("2024-01-01"), "AAPL")],
            names=["date", "ticker"],
        ),
    )

    with pytest.raises(ValueError, match="must be named"):
        engine.run(data)


def test_engine_run_records_post_liquidation_history_snapshot():
    broker = Broker()
    strategy = BuyFirstBarStrategy(broker)
    engine = Engine(broker=broker, strategy=strategy)
    data = pd.DataFrame(
        {
            "timestamp": [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02")],
            "ticker": ["AAPL", "AAPL"],
            "open": [100.0, 110.0],
            "high": [101.0, 111.0],
            "low": [99.0, 109.0],
            "close": [105.0, 115.0],
        }
    )

    engine.run(data)

    assert broker.history["positions"][-1] == 0


def test_engine_run_requires_sorted_timestamps():
    broker = Broker()
    strategy = DummyStrategy(broker)
    engine = Engine(broker=broker, strategy=strategy)
    data = pd.DataFrame(
        {
            "timestamp": [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-01")],
            "ticker": ["AAPL", "AAPL"],
            "close": [101.0, 100.0],
        }
    )

    with pytest.raises(ValueError, match="sorted by 'timestamp'"):
        engine.run(data)
