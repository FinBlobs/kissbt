from __future__ import annotations

from pathlib import Path

import pandas as pd

TECH_STOCK_TICKERS: tuple[str, ...] = (
    "AAPL",
    "GOOGL",
    "MSFT",
    "AMZN",
    "NVDA",
    "TSLA",
    "META",
    "SPY",
)
REQUIRED_COLUMNS: tuple[str, ...] = (
    "open",
    "high",
    "low",
    "close",
    "sma_128",
    "sma_256",
)
START_DATE = "2020-01-01"
END_DATE = "2024-12-31"
TRIM_START_DATE = "2022-01-01"
TRIM_END_DATE = "2024-12-31"


def normalize_market_data(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize index naming conventions across parquet/yfinance sources."""
    if isinstance(df.index, pd.MultiIndex):
        names = list(df.index.names)
        if len(names) >= 2 and names[0] == "date":
            names[0] = "timestamp"
            df.index = df.index.set_names(names)
    return df


def validate_market_data(df: pd.DataFrame) -> None:
    """Validate integration dataset shape and required content."""
    if not isinstance(df.index, pd.MultiIndex):
        raise ValueError("Dataset must use a MultiIndex with timestamp and ticker.")

    names = list(df.index.names)
    if len(names) < 2 or names[0] != "timestamp" or names[1] != "ticker":
        raise ValueError(
            "Dataset index must be a MultiIndex named ['timestamp', 'ticker']."
        )

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Dataset missing required columns: {missing_columns}")

    ticker_index = df.index.get_level_values("ticker")
    missing_tickers = sorted(set(TECH_STOCK_TICKERS).difference(set(ticker_index)))
    if missing_tickers:
        raise ValueError(f"Dataset missing required tickers: {missing_tickers}")


def _download_and_prepare_data(data_path: Path) -> pd.DataFrame:
    import yfinance as yf

    df = yf.download(
        list(TECH_STOCK_TICKERS),
        start=START_DATE,
        end=END_DATE,
        interval="1d",
    )
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

    df = df.loc[TRIM_START_DATE:TRIM_END_DATE]  # type: ignore[misc]
    data_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(data_path)
    return df


def load_tech_stock_data(data_path: str, allow_download: bool) -> pd.DataFrame:
    """
    Load and validate integration data.

    If `allow_download` is False and file is missing, raises FileNotFoundError.
    """
    path = Path(data_path)

    if path.exists():
        df = pd.read_parquet(path)
    elif allow_download:
        df = _download_and_prepare_data(path)
    else:
        raise FileNotFoundError(f"Expected integration dataset at {path}.")

    df = normalize_market_data(df)
    validate_market_data(df)
    return df
