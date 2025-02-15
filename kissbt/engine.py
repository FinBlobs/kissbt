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
        self.broker = broker
        self.strategy = strategy

    def run(self, data: pd.DataFrame) -> None:
        for current_date, current_data in data.groupby("date"):
            current_data.index = current_data.index.droplevel("date")

            self.broker.update(current_data, current_date)
            self.strategy(current_data, current_date)

        self.broker.liquidate_positions()
