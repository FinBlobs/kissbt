import numpy as np
import pandas as pd
import pytest

from kissbt.analyzer import Analyzer
from kissbt.broker import Broker


def _append_history_row(
    broker: Broker,
    *,
    timestamp: pd.Timestamp,
    total_value: float,
    cash: float = 0.0,
    long_position_value: float = 0.0,
    short_position_value: float = 0.0,
    positions: int = 0,
    benchmark: float | None = None,
) -> None:
    broker._history["timestamp"].append(timestamp)
    broker._history["total_value"].append(total_value)
    broker._history["cash"].append(cash)
    broker._history["long_position_value"].append(long_position_value)
    broker._history["short_position_value"].append(short_position_value)
    broker._history["positions"].append(positions)
    if benchmark is not None:
        broker._history["benchmark"].append(benchmark)


def test_constant_growth_benchmark_stats():
    daily_return = 0.0001
    num_days = 252
    start_value = 100000.0
    values = [start_value * (1 + daily_return) ** i for i in range(num_days)]

    broker = Broker(benchmark="constant_growth")
    for i, val in enumerate(values):
        ts = pd.Timestamp("2023-01-01") + pd.Timedelta(days=i)
        _append_history_row(
            broker, timestamp=ts, total_value=start_value, benchmark=val
        )

    analyzer = Analyzer(broker)
    metrics = analyzer.get_performance_metrics()

    assert abs(metrics["benchmark_slope"] - np.log(1 + daily_return)) < 1e-10
    assert metrics["benchmark_slope_se"] < 1e-10
    assert metrics["benchmark_slope_tstat"] > 1e5
    assert metrics["benchmark_r_squared"] > 0.9999


def test_portfolio_equity_curve_stats_with_volatility():
    np.random.seed(42)
    num_days = 256 * 3
    start_value = 100000.0

    # Generate portfolio values with some volatility
    daily_returns = np.random.normal(0.001, 0.02, num_days)
    portfolio_values = [start_value]
    for ret in daily_returns:
        portfolio_values.append(portfolio_values[-1] * (1 + ret))

    broker = Broker()
    for i, val in enumerate(portfolio_values):
        ts = pd.Timestamp("2023-01-01") + pd.Timedelta(days=i)
        _append_history_row(
            broker,
            timestamp=ts,
            total_value=val,
            long_position_value=val,
        )

    analyzer = Analyzer(broker)
    metrics = analyzer.get_performance_metrics()

    assert metrics["slope"] == pytest.approx(0.001, abs=0.0005)
    assert metrics["slope_se"] > 0
    assert metrics["slope_tstat"] > 1.96
    assert 0.5 < metrics["r_squared"] < 0.9


@pytest.mark.parametrize(
    ("kwargs", "error_match"),
    [
        (
            {"bar_size": "D"},
            "bar_size must be a positive integer followed by one of: S, T, H, D",
        ),
        (
            {"bar_size": "0D"},
            "bar_size must be a positive integer followed by one of: S, T, H, D",
        ),
        (
            {"trading_hours_per_day": 0.0},
            "trading_hours_per_day must be greater than 0",
        ),
        (
            {"trading_days_per_year": 0},
            "trading_days_per_year must be greater than 0",
        ),
    ],
)
def test_analyzer_rejects_invalid_configuration(kwargs, error_match):
    broker = Broker()
    _append_history_row(
        broker,
        timestamp=pd.Timestamp("2023-01-01"),
        total_value=100000.0,
        cash=100000.0,
    )

    with pytest.raises(ValueError, match=error_match):
        Analyzer(broker, **kwargs)


def test_analyzer_rejects_missing_history_columns():
    broker = Broker()
    broker._history.pop("cash")

    with pytest.raises(ValueError, match="broker history is missing required columns"):
        Analyzer(broker)


def test_analyzer_rejects_empty_history():
    broker = Broker()

    with pytest.raises(ValueError, match="broker history must not be empty"):
        Analyzer(broker)
