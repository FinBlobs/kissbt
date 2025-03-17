from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from kissbt.entities import ClosedPosition, OpenPosition, Order, OrderType


class Broker:
    """
    Manages the portfolio's cash, open and closed positions, and pending orders.

    This broker class is responsible for tracking capital, applying trading fees, and
    handling order execution for both opening and closing positions. It maintains
    consistency between current and previous market data bars, ensuring correct updates
    for position values, cash, and any accrued expenses such as short fees.

    The broker interfaces with several other components:
        - Manages OpenPosition and ClosedPosition objects to track trade lifecycles
        - Processes Order objects from Strategy class based on market data
        - Records transaction history for analysis by Analyzer
        - Receives updates from Engine for each market data bar

    Typical usage:
        broker = Broker(start_capital=100000, fees=0.001)
        broker.place_order(Order("AAPL", 100, OrderType.OPEN))
        broker.update(next_bar, next_datetime)
    """

    def __init__(
        self,
        start_capital: float = 100000,
        fees: float = 0.001,
        long_only: bool = True,
        short_fee_rate: float = 0.0050,
        benchmark: Optional[str] = None,
    ):
        """
        Initialize the Broker.

        Sets up the initial capital, commission fees, and optional benchmark tracking.
        Configures whether broker operates in long-only mode or allows short selling.
        Initializes all internal data structures for managing positions, orders, and
        history.

        Args:
            start_capital: Initial amount of cash available for trading, defaults to
                100000.
            fees: Commission or transaction fee applied to each trade, defaults to
                0.0050.
            long_only: If True, restricts trading to long positions only.
                Defaults to True.
            short_fee_rate: Annual fee rate for maintaining short positions.
                Defaults to 0.0050. Daily rate derived automatically.
            benchmark: Symbol used for performance comparison.
                If provided, broker tracks performance against this symbol.
        """
        self._cash = start_capital
        self._start_capital = start_capital
        self._fees = fees

        self._open_positions: Dict[str, OpenPosition] = dict()
        self._closed_positions: List[ClosedPosition] = []
        self._open_orders: List[Order] = []

        self._current_bar: pd.DataFrame = pd.DataFrame()
        self._current_datetime = None
        self._previous_bar: pd.DataFrame = pd.DataFrame()
        self._previous_datetime = None

        self._long_only = long_only
        self._short_fee_rate = short_fee_rate
        self._daily_short_fee_rate = -1.0 + (1.0 + short_fee_rate) ** (1.0 / 252.0)

        self._benchmark = benchmark
        self._benchmark_size = 0.0

        self._history: Dict[str, List[float]] = {
            "date": [],
            "cash": [],
            "long_position_value": [],
            "short_position_value": [],
            "total_value": [],
            "positions": [],
        }
        if benchmark is not None:
            self._history["benchmark"] = []

    def _update_history(self):
        """
        Updates the history dictionary with the current portfolio state.
        """
        self._history["date"].append(self._current_datetime)
        self._history["cash"].append(self._cash)
        self._history["long_position_value"].append(self.long_position_value)
        self._history["short_position_value"].append(self.short_position_value)
        self._history["total_value"].append(
            self.long_position_value + self.short_position_value + self._cash
        )
        self._history["positions"].append(len(self._open_positions))
        if self._benchmark is not None:
            if len(self._history["benchmark"]) == 0:
                self.benchmark_size = (
                    self._start_capital
                    / self._current_bar.loc[self._benchmark, "close"]
                    * (1.0 + self._fees)
                )
            self._history["benchmark"].append(
                self._current_bar.loc[self._benchmark, "close"]
                * self.benchmark_size
                * (1.0 - self._fees)
            )

    def _get_price_for_order(self, order: Order, bar: pd.DataFrame) -> float | None:
        """
        Determines the execution price for a given order based on the current market
        data.

        Args:
            order (Order): The order to be executed, containing information about
                ticker, order type, size, and limit price if applicable.
            bar (pd.DataFrame): Current market data frame containing OHLC prices for the
                ticker.

        Returns:
            float | None: The execution price for the order. None is returned if:
                - For limit orders: the limit price condition is not met
                - For open/close orders with limits: the limit price condition is not
                  met

        Raises:
            ValueError: If the order type is not recognized (not OPEN, CLOSE, or LIMIT)

        Notes:
            Price determination rules:
                - For OPEN orders: Uses the opening price
                - For CLOSE orders: Uses the closing price
                - For LIMIT orders:
                    - Buy orders: Uses min(open price, limit price) if
                      low price <= limit
                    - Sell orders: Uses max(open price, limit price) if
                      high price >= limit
        """
        ticker = order.ticker
        if order.order_type == OrderType.OPEN or order.order_type == OrderType.CLOSE:
            col = "open" if order.order_type == OrderType.OPEN else "close"
            if order.limit is None:
                return bar.loc[ticker, col]
            else:
                if order.size > 0.0 and bar.loc[ticker, col] <= order.limit:
                    return bar.loc[ticker, col]
                elif order.size < 0.0 and bar.loc[ticker, col] >= order.limit:
                    return bar.loc[ticker, col]
                else:
                    return None
        elif order.order_type == OrderType.LIMIT:
            if order.size > 0.0 and bar.loc[ticker, "low"] <= order.limit:
                return min(bar.loc[ticker, "open"], order.limit)
            elif order.size < 0.0 and bar.loc[ticker, "high"] >= order.limit:
                return max(bar.loc[ticker, "open"], order.limit)
            else:
                return None
        else:
            raise ValueError(f"Unknown order type {order.order_type}")

    def _update_closed_positions(
        self, ticker: str, size: float, price: float, datetime: datetime
    ):
        """
        Updates the list of closed positions for a given trade.

        Updates closed positions tracking when a position is fully or partially closed.
        For long positions being closed, records the entry price from open position and
        exit at current price. For short positions being closed, records entry at
        current price and exit at open position price.

        Args:
            ticker (str): The ticker symbol of the position
            size (float): Position size (positive for long, negative for short)
            price (float): The current closing/reduction price
            datetime (datetime): Timestamp of the closing/reduction
        """
        if (
            ticker in self._open_positions
            and size * self._open_positions[ticker].size < 0.0
        ):
            # if long position is closed/reduced
            if self._open_positions[ticker].size > 0.0:
                self._closed_positions.append(
                    ClosedPosition(
                        self._open_positions[ticker].ticker,
                        min(self._open_positions[ticker].size, abs(size)),
                        self._open_positions[ticker].price,
                        self._open_positions[ticker].datetime,
                        price,
                        datetime,
                    ),
                )
            # if short position is closed/reduced
            else:
                self._closed_positions.append(
                    ClosedPosition(
                        self._open_positions[ticker].ticker,
                        max(self._open_positions[ticker].size, -size),
                        price,
                        datetime,
                        self._open_positions[ticker].price,
                        self._open_positions[ticker].datetime,
                    ),
                )

    def _update_open_positions(
        self, ticker: str, size: float, price: float, datetime: datetime
    ):
        """
        Updates the open positions for a given ticker.

        If the ticker already exists in the open positions, it updates the size, price,
        and datetime based on the new transaction. If the size of the position becomes
        zero, the position is removed. If the ticker does not exist, a new open position
        is created.

        Args:
            ticker (str): The ticker symbol of the asset.
            size (float): The size of the position.
            price (float): The price at which the position was opened or updated.
            datetime (datetime): The datetime when the position was opened or updated.
        """
        if ticker in self._open_positions:
            if size + self._open_positions[ticker].size == 0.0:
                self._open_positions.pop(ticker)
            else:
                open_position_size = self._open_positions[ticker].size + size
                open_position_price = price
                open_position_datetime = datetime

                if size * self._open_positions[ticker].size > 0.0:
                    open_position_price = (
                        self._open_positions[ticker].size
                        * self._open_positions[ticker].price
                        + size * price
                    ) / (self._open_positions[ticker].size + size)
                    open_position_datetime = self._open_positions[ticker].datetime
                elif abs(self._open_positions[ticker].size) > abs(size):
                    open_position_datetime = self._open_positions[ticker].datetime
                    open_position_price = self._open_positions[ticker].price
                self._open_positions[ticker] = OpenPosition(
                    ticker,
                    open_position_size,
                    open_position_price,
                    open_position_datetime,
                )
        else:
            self._open_positions[ticker] = OpenPosition(
                ticker,
                size,
                price,
                datetime,
            )

    def _update_cash(self, order: Order, price: float):
        """
        Updates the cash balance based on the given order and price, accounting for the
        order size, price, and fees.

        Args:
            order (Order): The order object containing the size of the order.
            price (float): The price at which the order is executed.
        """
        if order.size > 0.0:
            self._cash -= order.size * price * (1.0 + self._fees)
        else:
            self._cash -= order.size * price * (1.0 - self._fees)

    def _check_long_only_condition(self, order: Order, datetime: datetime):
        size = order.size
        if order.ticker in self._open_positions:
            size += self._open_positions[order.ticker].size

        if size < 0.0:
            raise ValueError(
                f"Short selling is not allowed for {order.ticker} on {datetime}."
            )

    def _execute_order(
        self,
        order: Order,
        bar: pd.DataFrame,
        datetime: datetime,
    ) -> bool:
        """
        Executes an order based on the provided bar data and datetime.

        Args:
            order (Order): The order to be executed.
            bar (pd.DataFrame): The bar data containing price information.
            datetime (datetime): The datetime at which the order is executed.

        Returns:
            bool: True if the order was successfully executed, False otherwise.

        Raises:
            ValueError: If the long-only condition is violated.
        """
        ticker = order.ticker

        if order.size == 0.0:
            return False

        if self._long_only:
            self._check_long_only_condition(order, datetime)

        price = self._get_price_for_order(order, bar)

        # if the order is a limit order and cannot be filled, return
        if price is None:
            return False

        # update cash for long and short positions
        self._update_cash(order, price)

        self._update_closed_positions(ticker, order.size, price, datetime)

        self._update_open_positions(ticker, order.size, price, datetime)

        return True

    def update(
        self,
        next_bar: pd.DataFrame,
        next_datetime: pd.Timestamp,
    ):
        """
        Updates the broker's state with the next trading bar and executes pending
        orders.

        This method performs several key operations:
            1. Updates current and previous bar/date references
            2. Applies short fees for short positions if not in long-only mode
            3. Sells assets that are no longer in the universe
            4. Processes pending buy/sell orders
            5. Updates trading history statistics

        Args:
            next_bar (pd.DataFrame): The next trading bar data containing at minimum
                'close' prices for assets
            next_datetime (pd.Timestamp): The timestamp for the next trading bar

        Notes:
            - Short fees are calculated using the current bar's closing price
            - Assets outside the universe are sold at the previous bar's closing price
            - Orders that cannot be executed due to missing data are skipped with a
              warning
            - Good-till-cancel orders that aren't filled are retained for the next bar
        """
        self._previous_bar = self._current_bar
        self._previous_datetime = self._current_datetime
        self._current_bar = next_bar
        self._current_datetime = next_datetime

        # consider short fees
        if not self._long_only:
            for ticker in self._open_positions.keys():
                if self._open_positions[ticker].size < 0.0:
                    price = (
                        self._current_bar.loc[ticker, "close"]
                        if ticker in self._current_bar.index
                        else self._previous_bar.loc[ticker, "close"]
                    )
                    self._cash += (
                        self._open_positions[ticker].size
                        * price
                        * self._daily_short_fee_rate
                    )

        # sell assets out of universe, we use close price of previous bar, since this is
        # the last price we know
        ticker_out_of_universe = set()
        if not self._previous_bar.empty:
            ticker_out_of_universe = set(self._open_positions.keys()) - set(
                self._current_bar.index
            )
            for ticker in ticker_out_of_universe:
                self._execute_order(
                    Order(ticker, -self._open_positions[ticker].size, OrderType.CLOSE),
                    self._previous_bar,
                    self._previous_datetime,
                )

        # buy and sell assets
        remaining_open_orders = []
        ticker_not_available = set(
            [open_order.ticker for open_order in self._open_orders]
        ) - set(self._current_bar.index)
        for open_order in self._open_orders:
            if open_order.ticker in ticker_not_available:
                if open_order.size > 0:
                    print(
                        f"{open_order.ticker} could not be bought on {self._current_datetime}."  # noqa: E501
                    )
                else:
                    print(
                        f"{open_order.ticker} could not be sold on {self._current_datetime}."  # noqa: E501
                    )
                continue
            if (
                not self._execute_order(
                    open_order, self._current_bar, self._current_datetime
                )
                and open_order.good_till_cancel
            ):
                remaining_open_orders.append(open_order)

        # Retain orders that are good till cancel and were not filled for the next bar
        self._open_orders = remaining_open_orders

        # update stats
        self._update_history()

    def liquidate_positions(self):
        """
        Close all open positions in the broker by executing CLOSE orders.

        The method iterates through all open positions and creates close orders with
        opposite size to the current position size, effectively liquidating all
        holdings.
        All orders are executed at the current bar's timestamp.

        No parameters are needed as it operates on the broker's internal state.

        Returns:
            None
        """
        for ticker in [
            ticker for ticker in self._open_positions.keys()
        ]:  # open_positions is modified during iteration
            self._execute_order(
                Order(ticker, -self._open_positions[ticker].size, OrderType.CLOSE),
                self._current_bar,
                self._current_datetime,
            )

    def place_order(self, order: Order):
        """
        Places a new order in the broker's open orders list.

        Args:
            order (Order): The order object to be placed in the open orders.

        Note:
            The order is appended to the internal _open_orders list and remains there
            until it is either executed or cancelled.
        """
        self._open_orders.append(order)

    @property
    def short_position_value(self) -> float:
        """
        Gets the total market value of all short positions including fees.

        Calculates the sum of (price * quantity) for all positions with negative size,
        using the most recent closing price available. Transaction fees are included
        in the final value.

        Returns:
            float: Total value of short positions (negative number), including fees.
        """
        value = 0.0
        for ticker in self._open_positions.keys():
            if self._open_positions[ticker].size < 0.0:
                price = (
                    self._current_bar.loc[ticker, "close"]
                    if ticker in self._current_bar.index
                    else self._previous_bar.loc[ticker, "close"]
                )
                value += price * self._open_positions[ticker].size * (1.0 + self._fees)
        return value

    @property
    def long_position_value(self) -> float:
        """
        Gets the total market value of all long positions after fees.

        Calculates the sum of (price * quantity) for all positions with positive size,
        using the most recent closing price available. Transaction fees are deducted
        from the final value to reflect net liquidation value.

        Returns:
            float: Total value of long positions (positive number), net of fees.
        """
        value = 0.0
        for ticker in self._open_positions.keys():
            if self._open_positions[ticker].size > 0.0:
                price = (
                    self._current_bar.loc[ticker, "close"]
                    if ticker in self._current_bar.index
                    else self._previous_bar.loc[ticker, "close"]
                )
                value += price * self._open_positions[ticker].size * (1.0 - self._fees)
        return value

    @property
    def portfolio_value(self) -> float:
        """
        Gets the total portfolio value including cash and all positions.

        Calculates net portfolio value by summing:
            - Available cash balance
            - Long positions market value (less fees)
            - Short positions market value (including fees)

        Returns:
            float: Total portfolio value in base currency.
        """
        return self._cash + self.long_position_value + self.short_position_value

    @property
    def open_positions(self) -> Dict[str, OpenPosition]:
        """Gets a dictionary of currently active trading positions.

        Maps ticker symbols to OpenPosition objects containing:
        - ticker: Financial instrument identifier
        - size: Position size (positive=long, negative=short)
        - price: Average entry price
        - datetime: Position opening timestamp

        Returns:
            Dict[str, OpenPosition]: Dictionary mapping ticker symbols to positions.
                Returns a defensive copy to prevent external modifications.
        """
        return self._open_positions.copy()

    @property
    def closed_positions(self) -> List[ClosedPosition]:
        """
        Gets a list of all completed trades.

        Each ClosedPosition contains the complete trade lifecycle:
        - Entry price and timestamp
        - Exit price and timestamp
        - Position size and direction
        - Ticker symbol

        Returns a defensive copy to prevent external modifications.

        Returns:
            List[ClosedPosition]: Chronological list of completed trades.
        """
        return self._closed_positions.copy()

    @property
    def history(self) -> Dict[str, List[float]]:
        """Gets the historical performance metrics dictionary.

        Contains time series data tracking portfolio metrics:
        - 'cash': Available cash balance
        - 'portfolio': Total portfolio value
        - 'short_value': Value of short positions
        - 'long_value': Value of long positions
        - 'benchmark': Benchmark performance if specified

        Returns:
            Dict[str, List[float]]: Dictionary mapping metric names to value histories.
                Returns a defensive copy to prevent external modifications.
        """
        return self._history.copy()

    @property
    def cash(self) -> float:
        """Gets the current available cash balance.

        Represents uninvested capital that can be used for new positions. Updated after
        each trade to reflect fees and position changes.

        Returns:
            float: Available cash balance in base currency.
        """
        return self._cash

    @property
    def benchmark(self) -> str:
        """Gets the benchmark symbol used for performance comparison.

        The benchmark tracks a reference asset (e.g., market index) to evaluate relative
        strategy performance. Returns None if no benchmark was specified.

        Returns:
            str: Ticker symbol of the benchmark instrument.
        """
        return self._benchmark
