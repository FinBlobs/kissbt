import os

import pandas as pd
import pytest
import yfinance as yf

from kissbt.analyzer import Analyzer
from kissbt.broker import Broker


@pytest.fixture(scope="session")
def tech_stock_data():
    """
    Fixture that loads tech stock price data (magnificent 7 + SPY as benachmark),
    downloading it if necessary.
    """
    TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "NVDA", "TSLA", "META", "SPY"]
    START_DATE = "2020-01-01"
    END_DATE = "2024-12-31"
    DATA_PATH = "tests/data/tech_stocks.parquet"

    # Check if data already exists
    if not os.path.exists(DATA_PATH):
        print("Downloading tech stock data from Yahoo Finance...")

        df = yf.download(TICKERS, start=START_DATE, end=END_DATE, interval="1d")
        os.makedirs(
            os.path.dirname(DATA_PATH), exist_ok=True
        )  # Ensure directory exists

        # Stack and reset index
        df = df.stack(level=1, future_stack=True).reset_index()

        # Clean up column names
        df.columns = df.columns.str.lower()
        df.columns.name = None

        # Sort and set multi-index
        df = df.sort_values(by=["date", "ticker"]).set_index(["date", "ticker"])

        # Compute rolling means
        df["sma_128"] = df.groupby("ticker")["close"].transform(
            lambda x: x.rolling(window=128).mean()
        )
        df["sma_256"] = df.groupby("ticker")["close"].transform(
            lambda x: x.rolling(window=256).mean()
        )

        # Subset date range
        df = df.loc["2022-01-01":"2024-12-31"]
        df.to_parquet(DATA_PATH)

    return pd.read_parquet(DATA_PATH)


# Mock Broker class
def create_mock_broker(mocker, history_data, closed_positions=None):
    broker = mocker.MagicMock(spec=Broker)
    broker.history = history_data
    broker.closed_positions = closed_positions or []
    return broker


@pytest.fixture(scope="function")
def sample_broker():
    history = pd.DataFrame(
        {
            "date": pd.date_range(start="2023-01-01", periods=5, freq="D"),
            "total_value": [10000, 10500, 10200, 10700, 11000],
            "cash": [5000, 5500, 5200, 5700, 6000],
        }
    )
    return create_mock_broker(history)


@pytest.fixture(scope="function")
def analyzer(sample_broker) -> Analyzer:
    return Analyzer(sample_broker, bar_size="1D")


@pytest.fixture(scope="function")
def broker():
    """Creates a broker instance for testing."""
    return Broker(start_capital=100000, fees=0.001, long_only=True, short_fee_rate=0.02)
