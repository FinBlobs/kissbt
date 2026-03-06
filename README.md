# kissbt

**kissbt** ("keep it simple backtesting") is a small Python backtesting framework for
people who want clear execution semantics, a compact API, and deterministic CLI output.
It is built for pandas-based strategy research, scripted backtest runs, and machine-friendly
result handling without the weight of a large framework. It stays comfortable for simple
single-asset ideas, but is also flexible enough for multi-asset and whole-universe workflows.

## Why kissbt?

- Small public API: `Strategy`, `Broker`, `Engine`, `Analyzer`
- Clear next-bar execution model with explicit `OPEN`, `CLOSE`, and `LIMIT` behavior
- Works directly with pandas `DataFrame` input using `("timestamp", "ticker")` MultiIndex data
- Flexible enough for single-asset, multi-asset, and whole-universe strategies
- Supports long-only and long/short workflows
- Structured backtest results for Python code and deterministic JSON output for shell/CI/agents
- Fails fast on invalid inputs instead of silently guessing

## Installation

Install with `pip`:

```sh
pip install kissbt
```

Install with `uv`:

```sh
uv add kissbt
```

Or with `conda`:

```sh
conda install -c conda-forge kissbt
```

Supported Python versions: `3.12` to `3.14`.

## Quickstart

This example is intentionally small enough to verify by inspection.

```python
import pandas as pd

from kissbt import Broker, Engine, Order, Strategy


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

trade = result.closed_positions[0]
print(trade.entry_price)
print(trade.exit_price)
print(round(result.final_portfolio_value, 2))
```

Expected output:

```text
101.0
102.0
10007.97
```

Why those numbers:

- The order is placed on `2024-01-01`
- It executes on the next bar at the `2024-01-02` `open` price of `101.0`
- `Engine.run(...)` liquidates the remaining position on the final bar at the same day's `close` price of `102.0`
- With the default `0.1%` fee on entry and exit, final portfolio value becomes `10007.97`

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

## Input Data Requirements

`Engine.run(data)` expects a pandas `DataFrame` with:

- MultiIndex named `("timestamp", "ticker")`
- Unique `("timestamp", "ticker")` rows
- Required columns: `open`, `close`
- Additional columns for `LIMIT` orders: `high`, `low`
- If `Broker(benchmark=...)` is configured, the benchmark ticker must be present for every timestamp

If your input is not already indexed, the CLI also accepts CSV or Parquet files with
`timestamp` and `ticker` columns and converts them into the required MultiIndex shape.

## Flexible Strategy Workflows

Each call to `Strategy.generate_orders(...)` receives the full bar for the current
timestamp as a `DataFrame` indexed by ticker. That makes it natural to:

- Run a single instrument strategy
- Scan a watchlist of symbols
- Rank, filter, or rebalance across a whole universe on each bar

You can keep the strategy logic small, or prepare richer indicator columns in pandas
before calling `Engine.run(...)`.

## Python API

Define a strategy:

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

`current_data` is the full cross-section for the current timestamp, so the same strategy
shape works for one ticker, a small basket, or a full universe.

Create a broker and engine, then run the backtest:

```python
from kissbt import Broker, Engine

broker = Broker(start_capital=100000, fees=0.001)
strategy = MyStrategy(broker)
engine = Engine(broker, strategy)
result = engine.run(market_data)
```

`result` is a `BacktestResult` with:

- `history`
- `closed_positions`
- `final_portfolio_value`

Analyze performance after the broker has processed at least one bar:

```python
from kissbt import Analyzer

metrics = Analyzer(broker).get_performance_metrics()
print(metrics["total_return"])
```

## CLI And Automation

The CLI is designed for shell scripts, CI jobs, and agent workflows that need strict,
machine-consumable output.

### Run a backtest

Create a strategy module, for example `my_strategies/golden_cross.py`:

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

Write JSON to a file:

```sh
kissbt backtest \
  --input tests/data/tech_stocks.parquet \
  --strategy my_strategies.golden_cross:GoldenCrossStrategy \
  --benchmark SPY \
  --output backtest_result.json
```

Or write JSON to stdout:

```sh
kissbt backtest \
  --input tests/data/tech_stocks.parquet \
  --strategy my_strategies.golden_cross:GoldenCrossStrategy
```

Useful flags:

- `--input-format auto|csv|parquet`
- `--start-capital 100000`
- `--fees 0.001`
- `--allow-short`
- `--short-fee-rate 0.005`
- `--benchmark SPY`
- `--bar-size 1D`

Failure behavior:

- Invalid inputs exit with a non-zero status
- Errors are printed as concise user-facing messages
- Non-finite numeric values in JSON are normalized to `null`

### JSON output contract

The command writes a JSON report with:

- `summary`
- `metrics`
- `closed_positions`
- `events`

`summary` contains:

- `bars`
- `final_portfolio_value`
- `closed_positions`
- `events`

Timestamps are emitted in ISO 8601 format. Field names are deterministic so the output
is stable for downstream scripts and automation.

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

## When kissbt is a good fit

`kissbt` is a good fit if you want:

- A Python backtesting engine that stays easy to read end-to-end
- pandas-first research workflows over OHLC or indicator-enriched data
- Flexible strategies that scale from one instrument to a whole universe
- Reproducible batch backtests from the command line
- Deterministic JSON output for automation, reporting, or agent orchestration

It is probably not the right tool if you want a large built-in ecosystem, live trading
connectors, or a framework that hides the execution model behind many abstractions.

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
