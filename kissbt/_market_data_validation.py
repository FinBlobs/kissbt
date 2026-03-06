from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


def validate_market_data_frame(
    data: pd.DataFrame,
    *,
    required_columns: Iterable[str],
    context: str = "data",
) -> None:
    """Validate the shape and minimum schema required for backtest input."""
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"{context} must be a pandas DataFrame")

    if data.empty:
        raise ValueError(f"{context} must not be empty")

    if not isinstance(data.index, pd.MultiIndex):
        raise ValueError(
            f"{context} index must be a MultiIndex named ['timestamp', 'ticker']"
        )

    names = list(data.index.names)
    if len(names) < 2 or names[0] != "timestamp" or names[1] != "ticker":
        raise ValueError(
            f"{context} index must be a MultiIndex named ['timestamp', 'ticker']"
        )

    if not data.index.is_unique:
        raise ValueError(
            f"{context} index must contain unique ('timestamp', 'ticker') rows"
        )

    missing_columns = sorted(set(required_columns).difference(data.columns))
    if missing_columns:
        raise ValueError(
            f"{context} is missing required columns: "
            + ", ".join(f"'{column}'" for column in missing_columns)
        )


def validate_benchmark_data(
    data: pd.DataFrame,
    benchmark: str | None,
    *,
    context: str = "data",
) -> None:
    """Ensure the configured benchmark is present for every timestamp."""
    if benchmark is None:
        return

    if not benchmark.strip():
        raise ValueError("benchmark must not be empty")

    ticker_index = pd.Index(data.index.get_level_values("ticker").unique())
    if benchmark not in ticker_index:
        raise ValueError(f"{context} does not contain benchmark ticker '{benchmark}'")

    all_timestamps = pd.Index(data.index.get_level_values("timestamp").unique())
    benchmark_timestamps = pd.Index(data.xs(benchmark, level="ticker").index.unique())
    missing_timestamps = all_timestamps.difference(benchmark_timestamps)
    if not missing_timestamps.empty:
        raise ValueError(
            f"{context} is missing benchmark ticker '{benchmark}' for timestamp "
            f"{missing_timestamps[0]}"
        )
