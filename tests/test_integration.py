import pandas as pd
import pytest

from kissbt.analyzer import Analyzer
from kissbt.broker import Broker
from kissbt.engine import Engine
from kissbt.entities import Order
from kissbt.strategy import Strategy


class GoldenCrossStrategy(Strategy):
    def __init__(self, broker):
        super().__init__(broker)

    def generate_orders(
        self,
        current_data: pd.DataFrame,
        current_date: pd.Timestamp,
    ) -> None:
        for ticker in self._broker.open_positions:
            if (
                current_data.loc[ticker, "sma_128"]
                < current_data.loc[ticker, "sma_256"]
            ):
                self._broker.place_order(
                    Order(ticker, -self._broker.open_positions[ticker].size)
                )

        for ticker in current_data.index:
            if (
                ticker == self._broker.benchmark
                or ticker in self._broker.open_positions
            ):
                continue
            if (
                current_data.loc[ticker, "sma_128"]
                >= current_data.loc[ticker, "sma_256"]
            ):
                size = round(
                    self._broker.portfolio_value / 7 / current_data.loc[ticker, "close"]
                )
                self._broker.place_order(Order(ticker, size))


def test_analyzer_with_golden_cross(tech_stock_data):
    """
    Integration test to verify that the Analyzer computes correct metrics
    using the Golden Cross Strategy over real stock market data.
    """

    # Initialize Broker
    broker = Broker(
        start_capital=100000,
        fees=0.001,
        benchmark="SPY",
    )

    # Instantiate strategy
    strategy = GoldenCrossStrategy(broker)

    # Create and run backtesting engine
    engine = Engine(broker=broker, strategy=strategy)
    engine.run(tech_stock_data)

    # Additional portfolio growth and trade execution verification
    assert len(broker.open_positions) == 0, "All positions should be closed"
    assert pytest.approx(broker.cash, 0.01) == 167534.46, "Final cash manually verified"
    assert pytest.approx(broker.portfolio_value, 0.01) == 167534.46
    assert (
        len(broker.closed_positions) == 15
    ), "15 trades should have been executed, manually verified"

    # Create the Analyzer
    analyzer = Analyzer(broker, bar_size="1D")

    # Get performance metrics
    metrics = analyzer.get_performance_metrics()

    # Validate that expected keys exist
    expected_keys = [
        "total_return",
        "annual_return",
        "sharpe_ratio",
        "max_drawdown",
        "volatility",
        "win_rate",
        "profit_factor",
    ]

    for key in expected_keys:
        assert key in metrics, f"Missing metric: {key}"
        assert isinstance(metrics[key], float), f"Metric {key} should be a float"

    # Manually verified metrics
    assert pytest.approx(metrics["total_return"], abs=0.01) == 0.68
    assert pytest.approx(metrics["annual_return"], abs=0.01) == 0.19
    assert pytest.approx(metrics["sharpe_ratio"], abs=0.01) == 0.85
    assert pytest.approx(metrics["max_drawdown"], abs=0.01) == 0.32
    assert pytest.approx(metrics["volatility"], abs=0.01) == 0.24
    assert pytest.approx(metrics["win_rate"], abs=0.01) == 0.47
    assert pytest.approx(metrics["profit_factor"], abs=0.01) == 3.17
    assert pytest.approx(metrics["total_benchmark_return"], abs=0.01) == 0.29
    assert pytest.approx(metrics["annual_benchmark_return"], abs=0.01) == 0.09

    # Ensure running the plot functions does not raise an exception
    analyzer.plot_equity_curve()
    analyzer.plot_drawdowns()
