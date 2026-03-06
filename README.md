# kissbt

**kissbt** (keep it simple backtesting) is a lightweight Python framework for strategy backtesting.
It focuses on a clear API, fast iteration, and practical defaults.

## Why kissbt?

- Lightweight dependency footprint
- Simple object model (`Strategy`, `Broker`, `Engine`, `Analyzer`)
- Supports long-only and long/short workflows
- Built-in position tracking, P&L accounting, and performance metrics
- Easy to extend without large framework overhead

## Installation

Install with `pip`:

```sh
pip install kissbt
```

Or with `conda`:

```sh
conda install -c conda-forge kissbt
```

## Quickstart

```python
import pandas as pd

from kissbt import Analyzer, Broker, Engine, Order, Strategy


class BuyAndHoldOnce(Strategy):
    def initialize(self) -> None:
        self.has_bought = False

    def generate_orders(self, current_data, current_timestamp) -> None:
        if not self.has_bought:
            self.broker.place_order(Order(ticker="AAPL", size=10))
            self.has_bought = True


index = pd.MultiIndex.from_tuples(
    [
        (pd.Timestamp("2024-01-01"), "AAPL"),
        (pd.Timestamp("2024-01-02"), "AAPL"),
    ],
    names=["timestamp", "ticker"],
)

market_data = pd.DataFrame(
    {
        "open": [100.0, 101.0],
        "high": [102.0, 103.0],
        "low": [99.0, 100.0],
        "close": [101.0, 102.0],
    },
    index=index,
)

broker = Broker(start_capital=10_000)
strategy = BuyAndHoldOnce(broker)
engine = Engine(broker, strategy)
result = engine.run(market_data)

metrics = Analyzer(broker).get_performance_metrics()

print(result.final_portfolio_value)
print(metrics["total_return"])
```

## Input Data Requirements

`Engine.run(data)` expects a pandas `DataFrame` with:

- MultiIndex named `("timestamp", "ticker")`
- Unique `("timestamp", "ticker")` rows
- Required columns: `open`, `close`
- Additional columns for `LIMIT` orders: `high`, `low`
- If `Broker(benchmark=...)` is configured, the benchmark ticker must be present for every timestamp

## Execution Model

`kissbt` uses a simple next-bar execution model:

- `Strategy.generate_orders(...)` runs after the broker has processed the current bar
- Orders placed during bar `t` are evaluated on bar `t + 1`
- `OPEN` orders use the next bar `open`
- `CLOSE` orders use the next bar `close`
- `LIMIT` orders use the next bar `open`/`high`/`low` according to the limit-fill rules
- `Engine.run(...)` liquidates any remaining positions on the final bar after strategy execution

Two additional behaviors matter in practice:

- If a held ticker disappears from the current universe, `Broker.update(...)` closes it at the previous bar `close`
- Good-till-cancel orders remain pending until they fill or the run ends

## Python API

### 1. Define a strategy

```python
from kissbt import Order, OrderType, Strategy


class MyStrategy(Strategy):
    def generate_orders(self, current_data, current_timestamp) -> None:
        for ticker in current_data.index:
            close_price = current_data.loc[ticker, "close"]
            sma_128 = current_data.loc[ticker, "sma_128"]
            if close_price > sma_128:
                self.broker.place_order(
                    Order(ticker=ticker, size=10, order_type=OrderType.OPEN)
                )
```

### 2. Create broker and engine

```python
from kissbt import Broker, Engine

broker = Broker(start_capital=100000, fees=0.001)
strategy = MyStrategy(broker)
engine = Engine(broker, strategy)
```

### 3. Run backtest

```python
result = engine.run(market_data)
```

`result` is a `BacktestResult` with:

- `history`
- `closed_positions`
- `final_portfolio_value`

`Engine.run(...)` liquidates all positions at the end of the run. If liquidation
does not fully close positions, it raises an error.

### 4. Analyze performance

```python
from kissbt import Analyzer

metrics = Analyzer(broker).get_performance_metrics()
print(metrics)
```

`Analyzer(...)` expects non-empty broker history, so construct it after the
broker has processed at least one bar.

## Command Line Usage

The CLI is useful when you want reproducible runs from scripts, CI, or shell workflows.

### Strategy module example

Create a Python module, for example `my_strategies/golden_cross.py`:

```python
from kissbt import Order, Strategy


class GoldenCrossStrategy(Strategy):
    def generate_orders(self, current_data, current_timestamp) -> None:
        for ticker in current_data.index:
            if (
                current_data.loc[ticker, "sma_128"]
                >= current_data.loc[ticker, "sma_256"]
                and ticker not in self.broker.open_positions
            ):
                self.broker.place_order(Order(ticker=ticker, size=1))
```

### Run a backtest from shell

```sh
kissbt backtest \
  --input tests/data/tech_stocks.parquet \
  --strategy my_strategies.golden_cross:GoldenCrossStrategy \
  --output backtest_result.json
```

### Output

The command writes a JSON report with:

- `summary`
- `metrics`
- `closed_positions`
- `events`

Non-finite numeric values are normalized to `null` to keep output strict JSON.

`summary` currently contains:

- `bars`
- `final_portfolio_value`
- `closed_positions`
- `events`

Example shape:

```json
{
  "summary": {
    "bars": 252,
    "final_portfolio_value": 108734.12,
    "closed_positions": 14,
    "events": 28
  },
  "metrics": {
    "total_return": 0.0873412,
    "profit_factor": 1.91
  },
  "closed_positions": [
    {
      "ticker": "AAPL",
      "size": 10.0,
      "entry_price": 100.0,
      "entry_timestamp": "2024-01-02T00:00:00",
      "exit_price": 108.5,
      "exit_timestamp": "2024-01-15T00:00:00",
      "pnl": 85.0
    }
  ],
  "events": [
    {
      "type": "order_executed",
      "timestamp": "2024-01-02T00:00:00",
      "ticker": "AAPL",
      "size": 10.0,
      "order_type": "open",
      "price": 100.0
    }
  ]
}
```

## Development

For development, this repository uses `uv`.

- Development baseline: Python `3.13`
- Supported Python versions: `3.12` to `3.14`

```sh
uv python install 3.13
uv venv --python 3.13
uv sync --extra dev
uv run ruff format .
uv run ruff check .
uv run mypy kissbt tests
uv run pytest
```

## Examples

See the `examples` directory for more complete workflows.

## License

This project is licensed under Apache License 2.0. See [LICENSE](LICENSE).

## Contributing

Contributions are welcome via issues and pull requests.

## Contact

Adrian Hasse: adrian.hasse@finblobs.com
