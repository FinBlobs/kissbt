from collections.abc import Iterator

import pandas as pd

from kissbt.broker import Broker
from kissbt.strategy import Strategy


class Engine:
    """Coordinates execution of a trading strategy using broker actions.

    This class drives the main loop that processes market data, updates the
    broker's state, and calls the strategy logic for each segment of data.

    Args:
        broker (Broker): The Broker instance for managing trades and positions.
        strategy (Strategy): The trading strategy to be applied to the data.
    """

    def __init__(self, broker: Broker, strategy: Strategy) -> None:
        if strategy.broker is not broker:
            raise ValueError(
                "strategy must be initialized with the same broker passed to Engine"
            )
        self.broker = broker
        self.strategy = strategy

    def _normalize_data_index(self, data: pd.DataFrame) -> pd.DataFrame:
        normalized: pd.DataFrame
        if isinstance(data.index, pd.MultiIndex):
            if list(data.index.names) != ["timestamp", "ticker"]:
                raise ValueError(
                    "MultiIndex data must be named ['timestamp', 'ticker']."
                )
            normalized = data
        elif "timestamp" in data.columns and "ticker" in data.columns:
            normalized = data.set_index(["timestamp", "ticker"])
        else:
            raise ValueError(
                "Data must use MultiIndex ['timestamp', 'ticker'] or contain "
                "'timestamp' and 'ticker' columns."
            )

        timestamp_values = normalized.index.get_level_values("timestamp")
        if not timestamp_values.is_monotonic_increasing:
            raise ValueError("Data must be sorted by 'timestamp' in ascending order.")
        return normalized

    def _iter_bars(
        self, data: pd.DataFrame
    ) -> Iterator[tuple[pd.Timestamp, pd.DataFrame]]:
        normalized = self._normalize_data_index(data)
        for current_timestamp, current_data in normalized.groupby(
            level="timestamp", sort=False
        ):
            yield pd.Timestamp(current_timestamp), current_data.droplevel("timestamp")

    def run(self, data: pd.DataFrame) -> None:
        for current_timestamp, current_data in self._iter_bars(data):
            self.broker.update(current_data, current_timestamp)
            self.strategy(current_data, current_timestamp)

        self.broker.liquidate_positions()
