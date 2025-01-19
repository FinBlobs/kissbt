from kissbt.broker import Broker
from kissbt.strategy import Strategy
import pandas as pd


class Engine:

    def __init__(self, broker: Broker, strategy: Strategy) -> None:
        self.broker = broker
        self.strategy = strategy

    def run(self, data: pd.DataFrame) -> None:
        previous_data = None
        previous_date = None
        for current_date, current_data in data.groupby("date"):
            current_data.index = current_data.index.droplevel("date")

            self.broker.update(current_data, current_date, previous_data, previous_date)
            self.strategy(current_data, current_date, previous_data, previous_date)

            previous_data = current_data
            previous_date = current_date

        self.broker.liquidate_positions(current_data, current_date)
