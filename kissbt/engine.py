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

    def _iter_bars(
        self, data: pd.DataFrame
    ) -> Iterator[tuple[pd.Timestamp, pd.DataFrame]]:
        if isinstance(data.index, pd.MultiIndex):
            if "timestamp" not in data.index.names:
                raise ValueError(
                    "MultiIndex data must include a 'timestamp' index level."
                )
            for current_timestamp, current_data in data.groupby(
                level="timestamp", sort=False
            ):
                yield (
                    pd.Timestamp(current_timestamp),
                    current_data.droplevel("timestamp"),
                )
            return

        if "timestamp" not in data.columns:
            raise ValueError(
                "Data must use a MultiIndex with 'timestamp' level or contain a "
                "'timestamp' column."
            )
        if "ticker" not in data.columns:
            raise ValueError(
                "Data with a 'timestamp' column must also contain a 'ticker' column."
            )

        for current_timestamp, current_data in data.groupby("timestamp", sort=False):
            normalized_bar = current_data.copy().set_index("ticker")
            normalized_bar = normalized_bar.drop(columns=["timestamp"])
            yield pd.Timestamp(current_timestamp), normalized_bar

    def run(self, data: pd.DataFrame) -> None:
        for current_timestamp, current_data in self._iter_bars(data):
            self.broker.update(current_data, current_timestamp)
            self.strategy.generate_orders(current_data, current_timestamp)

        self.broker.liquidate_positions()
