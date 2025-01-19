from datetime import datetime
from typing import List, Dict
import pandas as pd
from kissbt.entities import OpenPosition, ClosedPosition, Order, OrderType


class Broker:
    def __init__(
        self,
        start_capital: float,
        fees: float,
        tax_rate: float,
        long_only: bool = True,
        short_fee_rate: float = 0.0050,
        benchmark: str | None = None,
    ):
        self.last_tax_year = 0
        self.tax_balance = 0.0
        self.tax_rate = tax_rate

        self.cash = start_capital
        self.start_capital = start_capital
        self.fees = fees

        self.open_positions: Dict[str, OpenPosition] = dict()
        self.closed_positions: List[ClosedPosition] = []
        self.open_orders: List[Order] = []

        self.long_only = long_only
        self.short_fee_rate = short_fee_rate
        self.daily_short_fee_rate = -1.0 + (1.0 + short_fee_rate) ** (1.0 / 252.0)

        self.benchmark = benchmark
        self.benchmark_size = 0.0

        self.history: Dict[str, List[float]] = {
            "date": [],
            "cash": [],
            "long_position_value": [],
            "short_position_value": [],
            "total_value": [],
            "positions": [],
        }
        if benchmark is not None:
            self.history["benchmark"] = []

    def _update_history(
        self, date: pd.Timestamp, next_bar: pd.DataFrame, previous_bar: pd.DataFrame
    ):
        long_position_value = self.get_long_position_value(next_bar, previous_bar)
        short_position_value = self.get_short_position_value(next_bar, previous_bar)
        self.history["date"].append(date)
        self.history["cash"].append(self.cash)
        self.history["long_position_value"].append(long_position_value)
        self.history["short_position_value"].append(short_position_value)
        self.history["total_value"].append(
            long_position_value + short_position_value + self.cash
        )
        self.history["positions"].append(len(self.open_positions))
        if self.benchmark is not None:
            if len(self.history["benchmark"]) == 0:
                self.benchmark_size = (
                    self.start_capital
                    / next_bar.loc[self.benchmark, "close"]
                    * (1.0 + self.fees)
                )
            self.history["benchmark"].append(
                next_bar.loc[self.benchmark, "close"]
                * self.benchmark_size
                * (1.0 - self.fees)
            )

    def _update_tax_balance(self):
        selling_price = self.closed_positions[-1].selling_price
        purchase_price = self.closed_positions[-1].purchase_price
        size = self.closed_positions[-1].size

        total_gain = selling_price * size * (
            1.0 - self.fees
        ) - purchase_price * size * (1.0 + self.fees)

        self.tax_balance += total_gain

    def _get_price(self, order: Order, bar: pd.DataFrame) -> float | None:
        """Determines the price for an order. If the order is a limit order and cannot
        be filled, None is returned. The price also depends on the order size
        distinguishing between buying and selling."""

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
        # update closed positions if an open position exists and the order goes in the
        # opposite direction
        if (
            ticker in self.open_positions
            and size * self.open_positions[ticker].size < 0.0
        ):
            # if long position is closed/reduced
            if self.open_positions[ticker].size > 0.0:
                self.closed_positions.append(
                    ClosedPosition(
                        self.open_positions[ticker].ticker,
                        min(self.open_positions[ticker].size, abs(size)),
                        self.open_positions[ticker].price,
                        self.open_positions[ticker].datetime,
                        price,
                        datetime,
                    ),
                )
            # if short position is closed/reduced
            else:
                self.closed_positions.append(
                    ClosedPosition(
                        self.open_positions[ticker].ticker,
                        max(self.open_positions[ticker].size, -size),
                        price,
                        datetime,
                        self.open_positions[ticker].price,
                        self.open_positions[ticker].datetime,
                    ),
                )

            self._update_tax_balance()

    def _update_open_positions(
        self, ticker: str, size: float, price: float, datetime: datetime
    ):
        # update open positions
        if ticker in self.open_positions:
            if size + self.open_positions[ticker].size == 0.0:
                self.open_positions.pop(ticker)
            else:
                open_position_size = self.open_positions[ticker].size + size
                open_position_price = price
                open_position_datetime = datetime

                if size * self.open_positions[ticker].size > 0.0:
                    open_position_price = (
                        self.open_positions[ticker].size
                        * self.open_positions[ticker].price
                        + size * price
                    ) / (self.open_positions[ticker].size + size)
                    open_position_datetime = self.open_positions[ticker].datetime
                elif abs(self.open_positions[ticker].size) > abs(size):
                    open_position_datetime = self.open_positions[ticker].datetime
                    open_position_price = self.open_positions[ticker].price
                self.open_positions[ticker] = OpenPosition(
                    ticker,
                    open_position_size,
                    open_position_price,
                    open_position_datetime,
                )
        else:
            self.open_positions[ticker] = OpenPosition(
                ticker,
                size,
                price,
                datetime,
            )

    def _update_cash(self, order: Order, price: float):
        if order.size > 0.0:
            self.cash -= order.size * price * (1.0 + self.fees)
        else:
            self.cash -= order.size * price * (1.0 - self.fees)

    def _check_long_only_condition(self, order: Order, datetime: datetime):
        size = order.size
        if order.ticker in self.open_positions:
            size += self.open_positions[order.ticker].size

        if size < 0.0:
            raise ValueError(
                f"Short selling is not allowed for {order.ticker} on {datetime}."
            )

    def _execute_order(
        self,
        order: Order,
        bar: pd.DataFrame,
        datetime: datetime,
    ):
        """
        This function sells a position. It is called by the update function.
        """
        ticker = order.ticker

        if order.size == 0.0:
            return

        if self.long_only:
            self._check_long_only_condition(order, datetime)

        price = self._get_price(order, bar)

        # if the order is a limit order and cannot be filled, return
        if price is None:
            return

        # update cash for long and short positions
        self._update_cash(order, price)

        self._update_closed_positions(ticker, order.size, price, datetime)

        self._update_open_positions(ticker, order.size, price, datetime)

        order.was_filled = True

    def update(
        self,
        next_bar: pd.DataFrame,
        next_date: pd.Timestamp,
        previous_bar: pd.DataFrame | None,
        previous_date: pd.Timestamp | None,
    ):
        # consider short fees
        if not self.long_only:
            for ticker in self.open_positions.keys():
                if self.open_positions[ticker].size < 0.0:
                    price = (
                        next_bar.loc[ticker, "close"]
                        if ticker in next_bar.index
                        else previous_bar.loc[ticker, "close"]
                    )
                    self.cash += (
                        self.open_positions[ticker].size
                        * price
                        * self.daily_short_fee_rate
                    )

        # consider taxes
        tax_year, _, _ = next_date.isocalendar()
        if tax_year != self.last_tax_year:
            self.last_tax_year = tax_year
            if self.tax_balance > 0.0:
                self.cash -= self.tax_balance * self.tax_rate
                self.tax_balance = 0.0

        # sell assets out of universe, we use close price of previous bar, since this is
        # the last price we know
        ticker_out_of_universe = set()
        if previous_bar is not None:
            ticker_out_of_universe = set(self.open_positions.keys()) - set(
                next_bar.index
            )
            for ticker in ticker_out_of_universe:
                self._execute_order(
                    Order(ticker, -self.open_positions[ticker].size, OrderType.CLOSE),
                    previous_bar,
                    previous_date,
                )

        # buy and sell assets
        ticker_not_available = set(
            [open_order.ticker for open_order in self.open_orders]
        ) - set(next_bar.index)
        for open_order in self.open_orders:
            if open_order.ticker in ticker_not_available:
                if open_order.size > 0:
                    print(f"{open_order.ticker} could not be bought on {next_date}.")
                else:
                    print(f"{open_order.ticker} could not be sold on {next_date}.")
                continue
            self._execute_order(
                open_order,
                next_bar,
                next_date,
            )

        # Retain orders that are good till cancel and were not filled for the next bar
        self.open_orders = [
            open_order
            for open_order in self.open_orders
            if open_order.good_till_cancel and not open_order.was_filled
        ]

        # update stats
        self._update_history(next_date, next_bar, previous_bar)

    def liquidate_positions(self, bar: pd.DataFrame, datetime: pd.Timestamp):
        for ticker in [
            ticker for ticker in self.open_positions.keys()
        ]:  # open_positions is modified during iteration
            self._execute_order(
                Order(ticker, -self.open_positions[ticker].size, OrderType.CLOSE),
                bar,
                datetime,
            )
            if self.tax_balance > 0.0:
                self.cash -= self.tax_balance * self.tax_rate
                self.tax_balance = 0.0

    def get_short_position_value(
        self, bar: pd.DataFrame, previous_bar: pd.DataFrame
    ) -> float:
        value = 0.0
        for ticker in self.open_positions.keys():
            if self.open_positions[ticker].size < 0.0:
                price = (
                    bar.loc[ticker, "close"]
                    if ticker in bar.index
                    else previous_bar.loc[ticker, "close"]
                )
                value += price * self.open_positions[ticker].size * (1.0 + self.fees)
        return value

    def get_long_position_value(
        self, bar: pd.DataFrame, previous_bar: pd.DataFrame
    ) -> float:
        value = 0.0
        for ticker in self.open_positions.keys():
            if self.open_positions[ticker].size > 0.0:
                price = (
                    bar.loc[ticker, "close"]
                    if ticker in bar.index
                    else previous_bar.loc[ticker, "close"]
                )
                value += price * self.open_positions[ticker].size * (1.0 - self.fees)
        return value

    def get_value(self, bar: pd.DataFrame, previous_bar: pd.DataFrame) -> float:
        value = self.cash
        value += self.get_long_position_value(bar, previous_bar)
        value += self.get_short_position_value(bar, previous_bar)
        return value

    def get_positions(self, excluded_tickers: list[str] = []) -> list[(str, float)]:
        positions = []
        for ticker in self.open_positions.keys():
            if ticker not in excluded_tickers:
                positions.append((ticker, self.open_positions[ticker].size))
        return positions
