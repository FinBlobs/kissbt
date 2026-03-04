"""
Run with:
    uv run python -m tests.scripts.prepare_integration_data
"""

from tests.data_utils import load_tech_stock_data


def main() -> None:
    data_path = "tests/data/tech_stocks.parquet"
    df = load_tech_stock_data(data_path=data_path, allow_download=True)
    print(f"Saved {len(df)} rows to {data_path}")


if __name__ == "__main__":
    main()
