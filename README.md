# kissbt

`kissbt` (Keep It Simple Stupid Backtesting) is a Python library designed for backtesting trading strategies with simplicity and ease of use in mind. The library provides essential components for creating, running, and analyzing trading strategies.

## Features

- **Modular Design**: The library is composed of several modules, each handling a specific aspect of the backtesting process.
- **Strategy Implementation**: Easily implement custom trading strategies by extending the `Strategy` class.
- **Broker Simulation**: Simulate trading with the `Broker` class, which manages orders, positions, and cash.
- **Performance Analysis**: Analyze trading performance with the `Analyzer` class, which calculates key metrics like total return, Sharpe ratio, and drawdown.
- **Data Handling**: Efficiently handle and preprocess market data using `pandas`.
- **Visualization**: Plot equity curves and drawdowns to visualize strategy performance.

## Installation

To install `kissbt`, clone the repository and install the dependencies:

```bash
git clone https://github.com/FinBlobs/kissbt.git
cd kissbt
pip install -r requirements.txt
```

## Usage

### 1. Define a Strategy

Create a custom strategy by extending the `Strategy` class and implementing the `generate_orders` method:

```python
from kissbt.strategy import Strategy
from kissbt.entities import Order, OrderType

class MyStrategy(Strategy):
    def generate_orders(self, current_data, current_datetime, previous_data=None, previous_datetime=None):
        # Example: Buy if the close price is above the 128-day SMA
        for ticker in current_data.index.get_level_values('ticker').unique():
            close_price = current_data.loc[(current_datetime, ticker), 'close']
            sma_128 = current_data.loc[(current_datetime, ticker), 'sma_128']
            if close_price > sma_128:
                order = Order(ticker=ticker, size=10, order_type=OrderType.OPEN)
                self.broker.open_orders.append(order)
```

### 2. Set Up the Broker

Initialize the `Broker` with starting capital, fees, and other parameters:

```python
from kissbt.broker import Broker

broker = Broker(start_capital=100000, fees=0.001, tax_rate=0.2)
```

### 3. Run the Backtest

Use the `Engine` to run the backtest with your strategy and market data:

```python
from kissbt.engine import Engine
import pandas as pd

# Load market data
data = pd.read_csv('market_data.csv', parse_dates=['date'])

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

Contributions are welcome! Please feel free to submit a Pull Request.

## Contact

For any questions or inquiries, please contact Adrian Hasse at adrian.hasse@finblobs.com.
