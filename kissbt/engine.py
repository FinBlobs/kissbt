from dataclasses import dataclass

import pandas as pd

from kissbt.broker import Broker
from kissbt.entities import ClosedPosition, OpenPosition
from kissbt.strategy import Strategy


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Structured backtest output for programmatic consumption."""

    history: pd.DataFrame
    closed_positions: list[ClosedPosition]
    open_positions: dict[str, OpenPosition]
    final_cash: float
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
        if not isinstance(data, pd.DataFrame):
            raise TypeError("data must be a pandas DataFrame")

        if data.empty:
            raise ValueError("data must not be empty")

        if not isinstance(data.index, pd.MultiIndex):
            raise ValueError(
                "data index must be a MultiIndex named ['timestamp', 'ticker']"
            )

        names = list(data.index.names)
        if len(names) < 2 or names[0] != "timestamp" or names[1] != "ticker":
            raise ValueError(
                "data index must be a MultiIndex named ['timestamp', 'ticker']"
            )

        required_columns = {"open", "close"}
        missing_columns = sorted(required_columns.difference(data.columns))
        if missing_columns:
            raise ValueError(
                "data is missing required columns: "
                + ", ".join(f"'{column}'" for column in missing_columns)
            )

    def run(self, data: pd.DataFrame) -> BacktestResult:
        self._validate_data(data)

        for current_timestamp, current_data in data.groupby(level="timestamp"):
            current_data = current_data.copy()
            current_data.index = current_data.index.droplevel("timestamp")

            self.broker.update(current_data, current_timestamp)
            self.strategy.generate_orders(current_data, current_timestamp)

        self.broker.liquidate_positions()
        return BacktestResult(
            history=pd.DataFrame(self.broker.history),
            closed_positions=self.broker.closed_positions,
            open_positions=self.broker.open_positions,
            final_cash=self.broker.cash,
            final_portfolio_value=self.broker.portfolio_value,
        )
