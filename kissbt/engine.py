from dataclasses import dataclass

import pandas as pd

from kissbt._market_data_validation import (
    validate_benchmark_data,
    validate_market_data_frame,
)
from kissbt.broker import Broker
from kissbt.entities import ClosedPosition
from kissbt.strategy import Strategy


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Structured backtest output for programmatic consumption."""

    history: pd.DataFrame
    closed_positions: list[ClosedPosition]
    final_portfolio_value: float


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

    def _validate_data(self, data: pd.DataFrame) -> None:
        """Validate data shape early to provide actionable errors."""
        validate_market_data_frame(
            data,
            required_columns=("open", "close"),
            context="data",
        )
        validate_benchmark_data(data, self.broker.benchmark, context="data")

    def run(self, data: pd.DataFrame) -> BacktestResult:
        self._validate_data(data)

        for current_timestamp, current_data in data.groupby(level="timestamp"):
            current_data = current_data.copy()
            current_data.index = current_data.index.droplevel("timestamp")

            self.broker.update(current_data, current_timestamp)
            self.strategy.generate_orders(current_data, current_timestamp)

        self.broker.liquidate_positions()
        if self.broker.open_positions:
            raise RuntimeError(
                "failed to liquidate all positions at end of run: "
                + ", ".join(sorted(self.broker.open_positions.keys()))
            )

        return BacktestResult(
            history=pd.DataFrame(self.broker.history),
            closed_positions=self.broker.closed_positions,
            final_portfolio_value=self.broker.portfolio_value,
        )
