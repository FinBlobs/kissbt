import pandas as pd
import pytest

from kissbt.broker import Broker
from kissbt.engine import BacktestResult, Engine
from kissbt.entities import Order
from kissbt.strategy import Strategy


class DummyStrategy(Strategy):
    def generate_orders(
        self, current_data: pd.DataFrame, current_timestamp: pd.Timestamp
    ) -> None:
        return None


class BuyOnceStrategy(Strategy):
    def initialize(self) -> None:
        self._has_order = False

    def generate_orders(
        self, current_data: pd.DataFrame, current_timestamp: pd.Timestamp
    ) -> None:
        if self._has_order:
            return
        self.broker.place_order(Order("AAPL", 1))
        self._has_order = True


def _build_valid_data() -> pd.DataFrame:
    index = pd.MultiIndex.from_tuples(
        [
            (pd.Timestamp("2024-01-01"), "AAPL"),
            (pd.Timestamp("2024-01-02"), "AAPL"),
        ],
        names=["timestamp", "ticker"],
    )
    return pd.DataFrame(
        {
            "open": [100.0, 101.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.0],
            "close": [101.0, 102.0],
        },
        index=index,
    )


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


def test_run_returns_structured_backtest_result():
    broker = Broker()
    strategy = BuyOnceStrategy(broker)
    engine = Engine(broker=broker, strategy=strategy)

    result = engine.run(_build_valid_data())

    assert isinstance(result, BacktestResult)
    assert result.final_portfolio_value == broker.portfolio_value
    assert len(result.history) == 2
    assert len(result.closed_positions) == 1
    assert broker.open_positions == {}
    assert result.final_portfolio_value == broker.cash


def test_run_accepts_open_close_only_data_for_non_limit_strategies():
    broker = Broker()
    strategy = BuyOnceStrategy(broker)
    engine = Engine(broker=broker, strategy=strategy)
    data = _build_valid_data().drop(columns=["high", "low"])

    result = engine.run(data)

    assert isinstance(result, BacktestResult)
    assert len(result.history) == 2


def test_run_requires_dataframe_input():
    broker = Broker()
    strategy = DummyStrategy(broker)
    engine = Engine(broker=broker, strategy=strategy)

    with pytest.raises(TypeError, match="data must be a pandas DataFrame"):
        engine.run(data={})  # type: ignore[arg-type]


def test_run_rejects_empty_data():
    broker = Broker()
    strategy = DummyStrategy(broker)
    engine = Engine(broker=broker, strategy=strategy)
    empty = _build_valid_data().iloc[0:0]

    with pytest.raises(ValueError, match="data must not be empty"):
        engine.run(empty)


def test_run_rejects_non_multiindex_data():
    broker = Broker()
    strategy = DummyStrategy(broker)
    engine = Engine(broker=broker, strategy=strategy)
    data = pd.DataFrame({"open": [1], "high": [1], "low": [1], "close": [1]})

    with pytest.raises(ValueError, match="data index must be a MultiIndex"):
        engine.run(data)


def test_run_rejects_wrong_multiindex_names():
    broker = Broker()
    strategy = DummyStrategy(broker)
    engine = Engine(broker=broker, strategy=strategy)
    data = _build_valid_data().copy()
    data.index = data.index.set_names(["date", "symbol"])

    with pytest.raises(ValueError, match="data index must be a MultiIndex"):
        engine.run(data)


def test_run_rejects_missing_required_columns():
    broker = Broker()
    strategy = DummyStrategy(broker)
    engine = Engine(broker=broker, strategy=strategy)
    data = _build_valid_data().drop(columns=["close"])

    with pytest.raises(ValueError, match="data is missing required columns"):
        engine.run(data)


def test_run_raises_if_liquidation_does_not_close_positions():
    class BrokenLiquidationBroker(Broker):
        def liquidate_positions(self):  # type: ignore[override]
            return None

    broker = BrokenLiquidationBroker()
    strategy = BuyOnceStrategy(broker)
    engine = Engine(broker=broker, strategy=strategy)

    with pytest.raises(RuntimeError, match="failed to liquidate all positions"):
        engine.run(_build_valid_data())
