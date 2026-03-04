import os

import pandas as pd
import pytest
from kissbt.analyzer import Analyzer
from kissbt.broker import Broker
from tests.data_utils import load_tech_stock_data


@pytest.fixture(scope="session")
def tech_stock_data():
    """
    Load tech stock data for integration tests.
    """
    data_path = os.getenv("TECH_STOCK_DATA_PATH", "tests/data/tech_stocks.parquet")
    allow_download = "TECH_STOCK_DATA_PATH" not in os.environ
    return load_tech_stock_data(data_path=data_path, allow_download=allow_download)


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
