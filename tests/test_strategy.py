import pandas as pd
import pytest

from kissbt.broker import Broker
from kissbt.entities import Order
from kissbt.strategy import Strategy


class DummyStrategy(Strategy):
    def generate_orders(
        self, current_data: pd.DataFrame, current_datetime: pd.Timestamp
    ) -> None:
        for ticker in current_data.index:
            if current_data.loc[ticker, "close"] > 100:
                self._broker.place_order(Order(ticker, 1))


def test_strategy_broker_type_error():
    with pytest.raises(TypeError):
        DummyStrategy(broker=None)


def test_strategy_execution():
    broker = Broker()
    strategy = DummyStrategy(broker)
    test_data = pd.DataFrame({"close": [101, 99]}, index=["TICKER_A", "TICKER_B"])

    strategy(test_data, pd.Timestamp("2023-01-01"))

    assert len(broker._open_orders) == 1
    assert broker._open_orders[0].ticker == "TICKER_A"
    assert broker._open_orders[0].size == 1
