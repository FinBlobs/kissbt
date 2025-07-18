import numpy as np
import pandas as pd
import pytest
from kissbt.analyzer import Analyzer
from kissbt.broker import Broker


def test_constant_growth_benchmark_stats():
    daily_return = 0.0001
    num_days = 252
    start_value = 100000.0
    values = [start_value * (1 + daily_return) ** i for i in range(num_days)]

    broker = Broker(benchmark="constant_growth")
    for i, val in enumerate(values):
        ts = pd.Timestamp("2023-01-01") + pd.Timedelta(days=i)
        broker.history["timestamp"].append(ts)
        broker.history["total_value"].append(start_value)
        broker.history["benchmark"].append(val)
        broker.history["cash"].append(0)
        broker.history["long_position_value"].append(0)
        broker.history["short_position_value"].append(0)
        broker.history["positions"].append({})

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
        broker.history["timestamp"].append(ts)
        broker.history["total_value"].append(val)
        broker.history["cash"].append(0)
        broker.history["long_position_value"].append(val)
        broker.history["short_position_value"].append(0)
        broker.history["positions"].append({})

    analyzer = Analyzer(broker)
    metrics = analyzer.get_performance_metrics()

    assert metrics["slope"] == pytest.approx(0.001, abs=0.0005)
    assert metrics["slope_se"] > 0
    assert metrics["slope_tstat"] > 1.96
    assert 0.5 < metrics["r_squared"] < 0.9
