from pathlib import Path

import pandas as pd
import pytest

from tests.conftest import tech_stock_data as _fixture_tech_stock_data
from tests.data_utils import (
    TECH_STOCK_TICKERS,
    load_tech_stock_data,
    normalize_market_data,
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
    fixture_fn = getattr(
        _fixture_tech_stock_data, "__wrapped__", _fixture_tech_stock_data
    )

    with pytest.raises(FileNotFoundError, match="Expected integration dataset"):
        fixture_fn()


def test_validate_market_data_requires_all_columns():
    df = _sample_market_data().drop(columns=["sma_256"])
    with pytest.raises(ValueError, match="missing required columns"):
        validate_market_data(df)


def test_validate_market_data_requires_all_tickers():
    df = _sample_market_data().drop(index=("2024-01-01", "SPY"))
    with pytest.raises(ValueError, match="missing required tickers"):
        validate_market_data(df)


def test_normalize_market_data_renames_date_index_level():
    df = _sample_market_data().copy()
    df.index = df.index.set_names(["date", "ticker"])

    normalized = normalize_market_data(df)
    assert list(normalized.index.names) == ["timestamp", "ticker"]
