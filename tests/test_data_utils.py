from pathlib import Path

import pandas as pd
import pytest

from tests.conftest import (
    TEST_DATA_DOWNLOAD_ENV_VAR,
)
from tests.conftest import (
    tech_stock_data as _fixture_tech_stock_data,
)
from tests.data_utils import (
    TECH_STOCK_TICKERS,
    load_tech_stock_data,
    validate_market_data,
)


def _sample_market_data() -> pd.DataFrame:
    timestamps = pd.to_datetime(["2024-01-01"] * len(TECH_STOCK_TICKERS))
    index = pd.MultiIndex.from_arrays(
        [timestamps, list(TECH_STOCK_TICKERS)],
        names=["timestamp", "ticker"],
    )
    return pd.DataFrame(
        {
            "open": [100.0] * len(index),
            "high": [101.0] * len(index),
            "low": [99.0] * len(index),
            "close": [100.0] * len(index),
            "sma_128": [100.0] * len(index),
            "sma_256": [100.0] * len(index),
        },
        index=index,
    )


def test_load_tech_stock_data_raises_if_missing_and_download_disallowed(tmp_path: Path):
    missing_path = tmp_path / "missing.parquet"
    with pytest.raises(FileNotFoundError, match="Expected integration dataset"):
        load_tech_stock_data(str(missing_path), allow_download=False)


def test_tech_stock_data_fixture_fails_fast_when_explicit_path_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    missing_path = tmp_path / "missing.parquet"
    monkeypatch.setenv("TECH_STOCK_DATA_PATH", str(missing_path))
    monkeypatch.delenv(TEST_DATA_DOWNLOAD_ENV_VAR, raising=False)
    fixture_fn = getattr(
        _fixture_tech_stock_data, "__wrapped__", _fixture_tech_stock_data
    )

    with pytest.raises(FileNotFoundError, match="Expected integration dataset"):
        fixture_fn()


def test_tech_stock_data_fixture_disables_download_by_default(
    monkeypatch: pytest.MonkeyPatch, mocker
):
    monkeypatch.delenv("TECH_STOCK_DATA_PATH", raising=False)
    monkeypatch.delenv(TEST_DATA_DOWNLOAD_ENV_VAR, raising=False)
    load_data = mocker.patch("tests.conftest.load_tech_stock_data", return_value="ok")
    fixture_fn = getattr(
        _fixture_tech_stock_data, "__wrapped__", _fixture_tech_stock_data
    )

    assert fixture_fn() == "ok"
    load_data.assert_called_once_with(
        data_path="tests/data/tech_stocks.parquet",
        allow_download=False,
    )


def test_tech_stock_data_fixture_allows_explicit_download_opt_in(
    monkeypatch: pytest.MonkeyPatch, mocker
):
    monkeypatch.delenv("TECH_STOCK_DATA_PATH", raising=False)
    monkeypatch.setenv(TEST_DATA_DOWNLOAD_ENV_VAR, "1")
    load_data = mocker.patch("tests.conftest.load_tech_stock_data", return_value="ok")
    fixture_fn = getattr(
        _fixture_tech_stock_data, "__wrapped__", _fixture_tech_stock_data
    )

    assert fixture_fn() == "ok"
    load_data.assert_called_once_with(
        data_path="tests/data/tech_stocks.parquet",
        allow_download=True,
    )


def test_validate_market_data_requires_all_columns():
    df = _sample_market_data().drop(columns=["sma_256"])
    with pytest.raises(ValueError, match="missing required columns"):
        validate_market_data(df)


def test_validate_market_data_requires_all_tickers():
    df = _sample_market_data().drop(index=("2024-01-01", "SPY"))
    with pytest.raises(ValueError, match="missing required tickers"):
        validate_market_data(df)


def test_validate_market_data_requires_timestamp_ticker_index_names():
    df = _sample_market_data().copy()
    df.index = df.index.set_names(["date", "ticker"])

    with pytest.raises(
        ValueError,
        match="MultiIndex named \\['timestamp', 'ticker'\\]",
    ):
        validate_market_data(df)


@pytest.mark.parametrize("ticker", TECH_STOCK_TICKERS)
def test_validate_market_data_rejects_ticker_with_all_nan_close(ticker: str):
    df = _sample_market_data()
    df.loc[(slice(None), ticker), "close"] = pd.NA

    with pytest.raises(ValueError, match=f"no valid close prices for ticker: {ticker}"):
        validate_market_data(df)
