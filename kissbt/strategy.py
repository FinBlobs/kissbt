from abc import ABC, abstractmethod

import pandas as pd

from kissbt.broker import Broker


class Strategy(ABC):
    """
    Abstract base class for trading strategies in the kissbt backtesting framework.

    This class serves as a template for implementing trading strategies. Subclasses must
    implement the generate_orders() method to define the trading logic. The strategy
    interacts with a broker instance to place orders and manage positions.

    Attributes:
        _broker (Broker): Trading broker instance for order execution and position
            management
    """

    def __init__(self, broker: Broker) -> None:
        """
        Initialize the strategy with a broker instance.

        Args:
            broker: Broker instance for order execution

        Raises:
            TypeError: If broker is not an instance of Broker class
        """
        if not isinstance(broker, Broker):
            raise TypeError("broker must be an instance of Broker")
        self._broker = broker  # Make broker protected
        self.initialize()

    def initialize(self) -> None:
        """
        Hook method for strategy initialization and parameter setup.

        Override this method to set up strategy-specific parameters, indicators,
        or other initialization logic. Called automatically after strategy creation.

        Returns:
            None
        """
        pass

    @abstractmethod
    def generate_orders(
        self,
        current_data: pd.DataFrame,
        current_datetime: pd.Timestamp,
    ) -> None:
        """
        Generate trading orders based on current market data and indicators.

        This is the main method where trading logic should be implemented. It is called
        for each bar in the backtest data sequence.

        Args:
            current_data: DataFrame containing market data and indicators for the
                current bar. Index consists of ticker symbols. For single-asset
                strategies, the DataFrame will have one row. For multi-asset strategies,
                it contains data for all assets in the current universe.

                Common columns include:
                - open: Opening price
                - high: High price
                - low: Low price
                - close: Closing price
                - volume: Trading volume
                - [custom]: Any additional indicators added during data preparation

            current_datetime: Timestamp of the current bar, e.g. used for order timing

        Returns:
            None

        Note:
            - Orders are placed through the _broker instance using methods like:
              create_market_order(), create_limit_order()
            - Position and portfolio information can be accessed through the _broker
            - Avoid look-ahead bias by only using data available at current_datetime
            - All orders are processed at the next bar's prices (which price depends on
              the order type)

        Raises:
            NotImplementedError: If the method is not implemented by subclass
        """
        raise NotImplementedError("Subclass must implement generate_orders()")

    def __call__(self, *args, **kwargs) -> None:
        """
        Make strategy callable to generate orders.

        Delegates to generate_orders() method.
        """
        self.generate_orders(*args, **kwargs)
