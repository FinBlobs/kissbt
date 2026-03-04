import os

import pandas as pd
import pytest
from kissbt.analyzer import Analyzer
from kissbt.broker import Broker


@pytest.fixture(scope="session")
def tech_stock_data():
    """
    Load tech stock data (magnificent 7 + SPY benchmark) from parquet when
    available, otherwise fetch once from Yahoo Finance and cache to parquet.
    """
    tickers = ["AAPL", "GOOGL", "MSFT", "AMZN", "NVDA", "TSLA", "META", "SPY"]
    start_date = "2020-01-01"
    end_date = "2024-12-31"
    data_path = os.getenv("TECH_STOCK_DATA_PATH", "tests/data/tech_stocks.parquet")

    if os.path.exists(data_path):
        df = pd.read_parquet(data_path)
        if isinstance(df.index, pd.MultiIndex):
            names = list(df.index.names)
            if len(names) >= 2 and names[0] == "date":
                names[0] = "timestamp"
                df.index = df.index.set_names(names)
        return df

    if "TECH_STOCK_DATA_PATH" in os.environ:
        raise FileNotFoundError(
            f"Expected integration dataset at {data_path}, but it does not exist."
        )

    os.makedirs(os.path.dirname(data_path), exist_ok=True)
    import yfinance as yf

    df = yf.download(tickers, start=start_date, end=end_date, interval="1d")
    df = df.stack(level=1, future_stack=True).reset_index()
    df.columns = df.columns.str.lower()
    df.columns.name = None
    df = df.rename(columns={"date": "timestamp"})
    df = df.sort_values(by=["timestamp", "ticker"]).set_index(["timestamp", "ticker"])

    df["sma_128"] = df.groupby("ticker")["close"].transform(
        lambda x: x.rolling(window=128).mean()
    )
    df["sma_256"] = df.groupby("ticker")["close"].transform(
        lambda x: x.rolling(window=256).mean()
    )

    df = df.loc["2022-01-01":"2024-12-31"]
    df.to_parquet(data_path)
    return df


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
