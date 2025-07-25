from typing import Any, Dict

import numpy as np
import pandas as pd
from scipy.stats import linregress

from kissbt.broker import Broker


class Analyzer:
    """
    A class for analyzing trading performance and calculating various performance
    metrics.

    This class provides comprehensive analysis of trading performance by calculating
    key metrics used in financial analysis and portfolio management.
    """

    def __init__(
        self,
        broker: Broker,
        bar_size: str = "1D",
        trading_hours_per_day: float = 6.5,
        trading_days_per_year: int = 252,
    ) -> None:
        """
        Initialize the Analyzer with a Broker instance and the bar size, which is the
        time interval of each bar in the data.

        Parameters:
            broker (Broker): The broker instance containing the trading history.
            bar_size (str): The time interval of each bar in the data, supported units
                are 'S' for seconds, 'T' for minutes, 'H' for hours and 'D' for days
                (default is "1D").
            trading_hours_per_day (float): Number of trading hours per day (default is
                6.5, which assumes US equities market hours; adjust as needed for other
                markets).
            trading_days_per_year (int): Number of trading days per year (default is
                252, which assumes US equities; adjust as needed for other markets).
        """

        value = int(bar_size[:-1])
        bar_unit = bar_size[-1]
        seconds_multiplier = {
            "S": 1,
            "T": 60,
            "H": 3600,
            "D": 3600 * trading_hours_per_day,
        }
        if bar_unit not in seconds_multiplier:
            raise ValueError(f"Unsupported bar size unit: {bar_unit}")
        self.seconds_per_bar = value * seconds_multiplier[bar_unit]
        self.trading_seconds_per_year = (
            trading_days_per_year * trading_hours_per_day * 3600
        )

        self.broker = broker
        self.analysis_df = pd.DataFrame(self.broker.history)
        self.analysis_df["returns"] = self.analysis_df["total_value"].pct_change()
        self.analysis_df["drawdown"] = (
            self.analysis_df["total_value"].cummax() - self.analysis_df["total_value"]
        ) / self.analysis_df["total_value"].cummax()

        if "benchmark" in self.analysis_df.columns:
            self.analysis_df["benchmark_returns"] = self.analysis_df[
                "benchmark"
            ].pct_change()
            self.analysis_df["benchmark_drawdown"] = (
                self.analysis_df["benchmark"].cummax() - self.analysis_df["benchmark"]
            ) / self.analysis_df["benchmark"].cummax()

    def _equity_curve_stats(
        self,
        value_series: pd.Series,
        *,
        prefix: str = "",
    ) -> Dict[str, float]:
        """
        Calculate statistics of the equity curve based on the log-equity curve.
        This method performs a linear regression on the log-equity curve to estimate
        the slope, standard error, t-statistic, and R² value.

        - slope: The slope of the log-equity curve, indicating the average return per
            bar.
        - slope_se: The standard error of the slope, indicating the variability of the
            average return.
        - slope_tstat: The t-statistic of the slope, indicating how strongly the data
            supports the presence of a non-zero trend in the log-equity curve.
        - r_squared: The R² value of the regression, indicating the proportion of
            variance explained.

        Parameters:
            value_series (pd.Series): The series of values to analyze, typically the
                total value of the portfolio or benchmark.
            prefix (str): A prefix to add to the keys in the returned dictionary, useful
                for distinguishing between portfolio and benchmark statistics.
        """

        if (value_series <= 0).any():
            raise ValueError(
                "Value series contains non-positive values, cannot compute log-based statistics"  # noqa: E501
            )
        y = np.log(value_series.to_numpy())
        x = np.arange(y.size, dtype=float)

        res = linregress(x, y)
        slope, slope_se, r_squared = res.slope, res.stderr, res.rvalue**2

        slope_tstat = slope / slope_se

        return {
            f"{prefix}slope": slope,
            f"{prefix}slope_se": slope_se,
            f"{prefix}slope_tstat": slope_tstat,
            f"{prefix}r_squared": r_squared,
        }

    def get_performance_metrics(self) -> Dict[str, float]:
        """
        Calculate and return key performance metrics of the trading strategy.

        This method computes various performance metrics used in financial analysis
        and portfolio management. The returned dictionary includes the following keys:

        - total_return: The total return of the portfolio as a decimal.
        - annual_return: The annualized return of the portfolio as a decimal.
        - sharpe_ratio: The Sharpe ratio of the trading strategy, a measure of
            risk-adjusted return.
        - max_drawdown: The maximum drawdown of the portfolio as a decimal.
        - volatility: The annualized volatility of the portfolio returns.
        - win_rate: The win rate of the trading strategy as a decimal.
        - profit_factor: The profit factor of the trading strategy, a ratio of gross
            profits to gross losses.

        Additionally we compute the equity curve statistics for the portfolio's
        total value, including:
        - slope: The slope of the log-equity curve, indicating the average return per
            bar.
        - slope_se: The standard error of the slope, indicating the variability of the
            average return.
        - slope_tstat: The t-statistic of the slope (slope / slope_se), indicating how
            strongly the data supports the presence of a non-zero trend in the
            log-equity curve. A larger absolute value (positive or negative) provides
            stronger evidence against H_0 (β = 0), suggesting that the observed trend is
            unlikely to be due to random fluctuations. For typical backtests the
            t-statistic approximately follows a standard normal distribution. Values
            above +1.96 or below -1.96 are considered statistically significant at the
            95% confidence level.
        - r_squared: The R² value of the regression, indicating the proportion of
            variance explained by the model.

        If a benchmark is available in the data, the dictionary also includes the
        total_return, annual_return, slope, slope_se, slope_tstat and r_squared for the
        benchmark, prefixed with "benchmark_".

        Returns:
            Dict[str, float]: A dictionary containing the calculated performance
                metrics.
        """

        metrics = {
            "total_return": self._calculate_total_return("total_value"),
            "annual_return": self._calculate_annual_return("total_value"),
            "sharpe_ratio": self._calculate_sharpe_ratio(),
            "max_drawdown": self._calculate_max_drawdown(),
            "volatility": self._calculate_annualized_volatility(),
            "win_rate": self._calculate_win_rate(),
            "profit_factor": self._calculate_profit_factor(),
        }
        metrics.update(self._equity_curve_stats(self.analysis_df["total_value"]))

        if "benchmark" in self.analysis_df.columns:
            metrics["benchmark_total_return"] = self._calculate_total_return(
                "benchmark"
            )
            metrics["benchmark_annual_return"] = self._calculate_annual_return(
                "benchmark"
            )
            metrics.update(
                self._equity_curve_stats(
                    self.analysis_df["benchmark"],
                    prefix="benchmark_",
                )
            )

        return metrics

    def _calculate_total_return(self, column: str) -> float:
        """
        Calculate the total return of either the portfolio or a benchmark.

        Parameters:
            column (str): The column name to calculate the total return for.

        Returns:
            float: The total return as a decimal (e.g., 0.10 for 10% total return).
        """
        return (
            float(self.analysis_df[column].iloc[-1] / self.analysis_df[column].iloc[0])
            - 1
        )

    def _calculate_annual_return(self, column: str) -> float:
        """
        Calculate the annualized return of the portfolio.

        This method computes the annual rate of return by taking into account the total
        return over the analysis period and normalizing it to a yearly basis. The
        annualized return is a key performance metric that allows comparing investments
        over different time periods by expressing returns as if they were earned at a
        compound annual rate.

        For example, if a portfolio earned 21% over 2 years, the annualized return would
        be approximately 10% per year. This metric is particularly useful for:
        - Comparing performance across different time periods
        - Evaluating investment strategies against benchmarks

        Note, that we assume that one year has 252 trading days.

        Parameters:
            column (str): The column name to calculate the total return for.

        Returns:
            float: The annualized return as a decimal (e.g., 0.10 for 10% annual return)
        """
        number_of_bars = len(self.analysis_df)
        years = number_of_bars * self.seconds_per_bar / self.trading_seconds_per_year

        total_return = (
            self.analysis_df[column].iloc[-1] / self.analysis_df[column].iloc[0]
        )
        annualized_return = float((total_return ** (1 / years)) - 1)
        return annualized_return

    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.0) -> float:
        """
        Calculate the Sharpe ratio of the trading strategy.

        The Sharpe ratio is a widely used metric in finance to evaluate the performance
        of investment strategies and portfolios. It provides a way to compare the return
        of an investment to its risk, with higher values indicating better risk-adjusted
        returns.

        The Sharpe ratio is calculated as the annualized return of the strategy minus
        the risk-free rate, divided by the standard deviation of the strategy's returns.
        The risk-free rate is typically the return on a risk-free investment, such as a
        US Treasury bond.

        Parameters:
            risk_free_rate (float): The annual risk-free rate (default is 0.0).
        """
        bars_per_year = self.trading_seconds_per_year / self.seconds_per_bar
        rf_rate_per_bar = (1 + risk_free_rate) ** (1 / bars_per_year) - 1
        excess_returns = self.analysis_df["returns"] - rf_rate_per_bar

        if np.isclose(excess_returns.std(), 0):
            return 0
        return float(
            np.sqrt(bars_per_year) * excess_returns.mean() / excess_returns.std()
        )

    def _calculate_max_drawdown(self) -> float:
        """
        Calculate the maximum drawdown of the trading strategy.

        The maximum drawdown is a risk metric that measures the largest peak-to-trough
        decline in the value of a portfolio over a specified period. It represents the
        worst loss an investor could have experienced if they had bought at the highest
        point and sold at the lowest point during the period.

        This metric is important because it provides insight into the potential downside
        risk of an investment strategy. A lower maximum drawdown indicates a more stable
        and less volatile strategy, while a higher maximum drawdown suggests greater
        risk and potential for significant losses.

        Returns:
            float: The maximum drawdown as a decimal (e.g., 0.20 for a 20% drawdown).
        """
        max_value = self.analysis_df["total_value"].expanding().max()
        drawdowns = (max_value - self.analysis_df["total_value"]) / max_value
        return float(drawdowns.max())

    def _calculate_annualized_volatility(self) -> float:
        """
        Calculate the annualized volatility of the portfolio returns.

        The calculation takes into account the bar size by using the number of bars
        per year based on the trading seconds per year and seconds per bar.

        Returns:
            float: The annualized volatility of the portfolio returns
        """
        bars_per_year = self.trading_seconds_per_year / self.seconds_per_bar
        return float(self.analysis_df["returns"].std() * np.sqrt(bars_per_year))

    def _calculate_win_rate(self) -> float:
        """
        Calculate the win rate of the trading strategy.

        The win rate is a performance metric that measures the proportion of profitable
        trades out of the total number of trades. It is calculated as the number of
        profitable trades divided by the total number of closed trades.

        This metric is important because it provides insight into the effectiveness of
        the trading strategy. A higher win rate indicates a greater proportion of
        successful trades, while a lower win rate suggests a higher proportion of losing
        trades.

        Note that this calculation does not consider trading costs such as commissions
        and fees, which can impact the overall profitability of the strategy.

        Returns:
            float: The win rate as a decimal (e.g., 0.60 for a 60% win rate).
        """
        if not self.broker.closed_positions:
            return 0
        profitable_trades = sum(
            1
            for pos in self.broker.closed_positions
            if (pos.selling_price - pos.purchase_price) * pos.size > 0
        )
        return float(profitable_trades / len(self.broker.closed_positions))

    def _calculate_profit_factor(self) -> float:
        """
        Calculate the profit factor of the trading strategy.

        The profit factor is a performance metric that measures the ratio of gross
        profits to gross losses for a trading strategy. It is calculated as the total
        gross profits divided by the total gross losses. This metric provides insight
        into the overall profitability of the strategy.

        A profit factor greater than 1 indicates that the strategy is profitable, as the
        gross profits exceed the gross losses. Conversely, a profit factor less than 1
        indicates that the strategy is unprofitable. A higher profit factor suggests a
        more robust and potentially more profitable strategy.

        This metric is important because it helps in assessing the risk-reward profile
        of the trading strategy, complementing other metrics such as the Sharpe ratio
        and win rate.

        Returns:
            float: The profit factor as a ratio (e.g., 1.5 for a strategy that gains
                $1.50 for every $1.00 lost).
        """
        profits = sum(
            (pos.selling_price - pos.purchase_price) * pos.size
            for pos in self.broker.closed_positions
            if (pos.selling_price - pos.purchase_price) * pos.size > 0
        )
        losses = abs(
            sum(
                (pos.selling_price - pos.purchase_price) * pos.size
                for pos in self.broker.closed_positions
                if (pos.selling_price - pos.purchase_price) * pos.size < 0
            )
        )
        return float(profits / losses) if losses != 0 else float("inf")

    def plot_drawdowns(self, **kwargs: Dict[str, Any]) -> None:
        """
        Plot the drawdown over time for both the portfolio and benchmark (if available).

        This method creates a line plot showing the drawdown percentage over time. If a
        benchmark is present in the data, it will show both the portfolio and benchmark
        drawdowns for comparison.

        Parameters:
            **kwargs(Dict[str, Any]): Additional keyword arguments to pass to the plot
                function of pandas.
        """
        columns_to_plot = ["timestamp", "drawdown"]
        if "benchmark_drawdown" in self.analysis_df.columns:
            columns_to_plot.append("benchmark_drawdown")

        self.analysis_df.loc[:, columns_to_plot].plot(
            x="timestamp",
            title="Portfolio Drawdown Over Time",
            xlabel="Timestamp",
            ylabel="Drawdown %",
            **kwargs,
        )

    def plot_equity_curve(self, logy: bool = False, **kwargs: Dict[str, Any]) -> None:
        """
        Plot the portfolio's cash, total value, and benchmark (if available) over time.

        This method creates a line plot showing the portfolio's cash, total value, and
        benchmark over time for comparison. If the benchmark is not available, it will
        plot only the available columns. If logy is True, the cash column will be
        excluded, to focus on the total value and benchmark on logarithmic scale.

        Parameters:
            logy (bool): If True, use a logarithmic scale for the y-axis and exclude the
                cash column.
            **kwargs(Dict[str, Any]): Additional keyword arguments to pass to the plot
                function of pandas.
        """
        columns_to_plot = ["timestamp", "total_value"]
        if "benchmark" in self.analysis_df.columns:
            columns_to_plot.append("benchmark")
        if not logy:
            columns_to_plot.append("cash")

        self.analysis_df.loc[:, columns_to_plot].plot(
            x="timestamp",
            title="Portfolio Equity Curve Over Time",
            xlabel="Timestamp",
            ylabel="Value",
            logy=logy,
            **kwargs,
        )

    def plot_rolling_returns_distribution(
        self, window_bars: int, include_benchmark: bool = True, **kwargs: Dict[str, Any]
    ) -> None:
        """
        Plot box plots of rolling returns for the portfolio and optionally benchmark.

        Parameters:
            window_bars (int): Window size as number of bars.
            include_benchmark (bool): Whether to include benchmark if available
                (default True).
            **kwargs (dict): Additional keyword arguments to pass to the pandas
                DataFrame.boxplot function for customizing the appearance and behavior
                of the box plot.
        """
        if window_bars >= len(self.analysis_df):
            raise ValueError(
                f"Window size {window_bars} is too large for the available data {len(self.analysis_df)}."  # noqa: E501
            )

        result = {
            "Portfolio": self.analysis_df["total_value"]
            .pct_change(periods=window_bars)
            .dropna()
            .reset_index(drop=True)
        }
        if include_benchmark and "benchmark" in self.analysis_df.columns:
            result["Benchmark"] = (
                self.analysis_df["benchmark"]
                .pct_change(periods=window_bars)
                .dropna()
                .reset_index(drop=True)
            )

        pd.DataFrame(result).boxplot(**kwargs)
