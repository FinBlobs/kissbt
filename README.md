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

### 1. Define a Strategy

Create a custom strategy by extending the `Strategy` class and implementing the `generate_orders` method:

```python
from kissbt.strategy import Strategy
from kissbt.entities import Order, OrderType

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

Use the `Engine` to run the backtest with your strategy and market data:

```python
from kissbt.engine import Engine
import pandas as pd

# Load market data and normalize it for Engine.run(...)
data = pd.read_csv("market_data.csv", parse_dates=["date"])
data = data.rename(columns={"date": "timestamp"})
data = data.sort_values(["timestamp", "ticker"]).set_index(["timestamp", "ticker"])

# Initialize strategy and engine
strategy = MyStrategy(broker)
engine = Engine(broker, strategy)

# Run the backtest
engine.run(data)
```

### 4. Analyze Performance

Use the `Analyzer` to calculate and display performance metrics:

```python
from kissbt.analyzer import Analyzer

analyzer = Analyzer(broker)
metrics = analyzer.get_performance_metrics()
print(metrics)
```

## Examples

Check out the `examples` directory for more detailed examples and use cases.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

## Contributing

We welcome contributions! If you have ideas, bug fixes, or feature requests, feel free to open an issue or submit a pull request.

## Contact

For any questions or inquiries, please contact Adrian Hasse at adrian.hasse@finblobs.com.
