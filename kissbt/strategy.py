from abc import ABC, abstractmethod
import pandas as pd
from kissbt.broker import Broker


class Strategy(ABC):
    def __init__(self, broker: Broker):
        self.broker = broker
        self.initialize()

    def initialize(self) -> None:
        """Set up any strategy-specific parameters or state"""
        pass

    @abstractmethod
    def generate_orders(
        self,
        current_data: pd.DataFrame,
        current_datetime: pd.Timestamp,
        previous_data: pd.DataFrame | None = None,
        previous_datetime: pd.Timestamp | None = None,
    ) -> None:
        """Generate trading orders based on current market data"""
        pass

    def __call__(self, *args, **kwargs) -> None:
        """Wrapper that calls generate_orders"""
        self.generate_orders(*args, **kwargs)
