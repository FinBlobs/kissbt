# kissbt

**kissbt**, the `keep it simple` backtesting framework, is a lightweight and user-friendly Python framework for backtesting trading strategies. It focuses on simplicity, performance, and ease of extensibility while providing essential tools for effective backtesting.

## Why kissbt?

- **🚀 Lightweight** – Minimal dependencies ensure fast installation and execution.
- **📖 Simple API** – Lowers the barrier for traders new to backtesting.
- **🔌 Extensible** – Modular architecture enables easy customization.
- **📊 Essential Features** – Includes tools for data handling, strategy implementation, and performance evaluation.

## Features

✔️ Object-oriented design for intuitive strategy development
✔️ Fast execution, even for large universes
✔️ Supports long and short positions
✔️ Built-in trade execution, position tracking, and P&L calculation
✔️ Performance analysis with key trading metrics
✔️ Backtesting with historical market data
✔️ Modular components (Strategy, Broker, Engine, Analyzer)

## Installation

You can install `kissbt` using either `pip` or `conda`.

### Using pip

To install `kissbt` via `pip`, run the following command:

```sh
pip install kissbt
```

### Using conda

To install `kissbt` via `conda`, run the following command:

```sh
conda install -c conda-forge kissbt
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

## Usage

### Data contract

`Engine.run(data)` expects a pandas `DataFrame` with:

- MultiIndex index named `["timestamp", "ticker"]`
- Required columns for all strategies: `open`, `close`
- Additional required columns if you place `LIMIT` orders: `high`, `low`

### Minimal in-memory example

This example is fully local (no file I/O, no downloads) and uses the top-level API:

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
data = pd.DataFrame(
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
result = engine.run(data)

print(result.final_portfolio_value)
print(Analyzer(broker).get_performance_metrics())
```

### BacktestResult fields

`Engine.run(...)` returns a `BacktestResult` object with:

- `history`: Portfolio history as a DataFrame
- `closed_positions`: Closed trades as `ClosedPosition` objects
- `open_positions`: Remaining open positions by ticker
- `final_cash`: Ending cash balance
- `final_portfolio_value`: Ending total portfolio value

```python
result = engine.run(data)
print(result.final_cash)
print(result.final_portfolio_value)
print(result.history.tail(1))
print(len(result.closed_positions), len(result.open_positions))
```

### 1. Define a Strategy

Create a custom strategy by extending the `Strategy` class and implementing the `generate_orders` method:

```python
from kissbt import Order, OrderType, Strategy

class MyStrategy(Strategy):
    def generate_orders(self, current_data, current_datetime):
        # Example: Buy if the close price is above the 128-day SMA
        for ticker in current_data.index:
            close_price = current_data.loc[ticker, "close"]
            sma_128 = current_data.loc[ticker, "sma_128"]
            if close_price > sma_128:
                order = Order(ticker=ticker, size=10, order_type=OrderType.OPEN)
                self.broker.place_order(order)
```

### 2. Set Up the Broker

Initialize the `Broker` with starting capital, fees, and other parameters:

```python
from kissbt.broker import Broker

broker = Broker(start_capital=100000, fees=0.001)
```

### 3. Run the Backtest

Use the `Engine` to run the backtest with your strategy and market data.
`Engine.run(...)` returns a structured `BacktestResult`:

```python
from kissbt import Engine
import pandas as pd

# Load market data
data = pd.read_parquet("market_data.parquet")
# Required format:
# - index: MultiIndex["timestamp", "ticker"]
# - required columns: open, close
# - additional columns for LIMIT orders: high, low

# Initialize strategy and engine
strategy = MyStrategy(broker)
engine = Engine(broker, strategy)

# Run the backtest
result = engine.run(data)
print(result.final_cash, result.final_portfolio_value)
```

### 4. Analyze Performance

Use the `Analyzer` to calculate and display performance metrics:

```python
from kissbt import Analyzer

analyzer = Analyzer(broker)
metrics = analyzer.get_performance_metrics()
print(metrics)
```

### 5. Run via CLI

`kissbt` includes a CLI entrypoint for agent workflows.

Minimal strategy module example (`my_strategies/golden_cross.py`):

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

Run:

```sh
kissbt backtest \
  --input tests/data/tech_stocks.parquet \
  --strategy my_strategies.golden_cross:GoldenCrossStrategy \
  --output backtest_result.json
```

### Agent usage notes

- Prefer top-level imports, e.g. `from kissbt import Broker, Engine, Strategy`.
- Use `BacktestResult` fields instead of reading broker internals directly.
- Structured order-processing events are available via `broker.events`.
- CLI output is strict JSON; non-finite numeric metrics are normalized to `null`.

## Examples

Check out the `examples` directory for more detailed examples and use cases.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

## Contributing

We welcome contributions! If you have ideas, bug fixes, or feature requests, feel free to open an issue or submit a pull request.

## Contact

For any questions or inquiries, please contact Adrian Hasse at adrian.hasse@finblobs.com.
