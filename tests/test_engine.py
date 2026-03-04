import pandas as pd
import pytest

from kissbt.broker import Broker
from kissbt.engine import Engine
from kissbt.strategy import Strategy


class DummyStrategy(Strategy):
    def generate_orders(
        self, current_data: pd.DataFrame, current_timestamp: pd.Timestamp
    ) -> None:
        return None


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
