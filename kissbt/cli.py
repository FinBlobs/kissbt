import argparse
import importlib
import json
import math
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from kissbt._market_data_validation import validate_market_data_frame
from kissbt.analyzer import Analyzer
from kissbt.broker import Broker
from kissbt.engine import Engine
from kissbt.entities import ClosedPosition
from kissbt.strategy import Strategy


def _sanitize_for_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize_for_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_json(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_for_json(item) for item in value]
    if isinstance(value, np.generic):
        return _sanitize_for_json(value.item())
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _load_market_data(input_path: Path, input_format: str) -> pd.DataFrame:
    detected_format = input_format
    if detected_format == "auto":
        if input_path.suffix.lower() == ".parquet":
            detected_format = "parquet"
        else:
            detected_format = "csv"

    try:
        if detected_format == "parquet":
            data = pd.read_parquet(input_path)
        elif detected_format == "csv":
            data = pd.read_csv(input_path)
        else:
            raise ValueError(f"Unsupported input format: {detected_format}")
    except FileNotFoundError as exc:
        raise ValueError(f"input file does not exist: {input_path}") from exc
    except pd.errors.ParserError as exc:
        raise ValueError(
            f"failed to parse CSV input data from '{input_path}': {exc}"
        ) from exc
    except OSError as exc:
        raise ValueError(
            f"failed to read input data from '{input_path}': {exc}"
        ) from exc

    if not isinstance(data.index, pd.MultiIndex):
        required_columns = {"timestamp", "ticker"}
        missing_columns = sorted(required_columns.difference(data.columns))
        if missing_columns:
            raise ValueError(
                "input data must either have a MultiIndex or contain "
                + ", ".join(f"'{column}'" for column in missing_columns)
                + " columns"
            )
        data["timestamp"] = pd.to_datetime(data["timestamp"])
        data = data.set_index(["timestamp", "ticker"]).sort_index()

    validate_market_data_frame(
        data,
        required_columns=("open", "close"),
        context="input data",
    )
    return data


def _load_strategy_class(strategy_spec: str) -> type[Strategy]:
    if ":" not in strategy_spec:
        raise ValueError("strategy must be in format 'module:ClassName'")
    module_name, class_name = strategy_spec.split(":", maxsplit=1)

    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise ValueError(
            f"could not import strategy module '{module_name}': {exc}"
        ) from exc
    strategy_class = getattr(module, class_name, None)
    if strategy_class is None:
        raise ValueError(
            f"Could not find strategy class '{class_name}' in {module_name}"
        )
    if not isinstance(strategy_class, type) or not issubclass(strategy_class, Strategy):
        raise ValueError(f"{strategy_spec} must resolve to a Strategy subclass")
    return strategy_class


def _serialize_closed_position(position: ClosedPosition) -> dict[str, Any]:
    item = asdict(position)
    item["entry_timestamp"] = position.entry_timestamp.isoformat()
    item["exit_timestamp"] = position.exit_timestamp.isoformat()
    item["pnl"] = position.pnl
    return item


def _run_backtest(args: argparse.Namespace) -> dict[str, Any]:
    data = _load_market_data(Path(args.input), args.input_format)
    strategy_class = _load_strategy_class(args.strategy)

    broker = Broker(
        start_capital=args.start_capital,
        fees=args.fees,
        long_only=not args.allow_short,
        short_fee_rate=args.short_fee_rate,
        benchmark=args.benchmark,
    )
    strategy = strategy_class(broker)
    engine = Engine(broker=broker, strategy=strategy)
    result = engine.run(data)
    metrics = Analyzer(
        broker=broker,
        bar_size=args.bar_size,
        trading_hours_per_day=args.trading_hours_per_day,
        trading_days_per_year=args.trading_days_per_year,
    ).get_performance_metrics()

    return {
        "summary": {
            "bars": len(result.history),
            "final_portfolio_value": result.final_portfolio_value,
            "closed_positions": len(result.closed_positions),
            "events": len(broker.events),
        },
        "metrics": metrics,
        "closed_positions": [
            _serialize_closed_position(position) for position in result.closed_positions
        ],
        "events": broker.events,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="kissbt command line interface")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backtest_parser = subparsers.add_parser(
        "backtest",
        help="Run a backtest with a strategy class and market data",
    )
    backtest_parser.add_argument(
        "--input", required=True, help="Path to CSV/Parquet data"
    )
    backtest_parser.add_argument(
        "--strategy",
        required=True,
        help="Strategy class spec in format 'module:ClassName'",
    )
    backtest_parser.add_argument(
        "--input-format",
        default="auto",
        choices=["auto", "csv", "parquet"],
        help="Input format, defaults to auto detection by file extension",
    )
    backtest_parser.add_argument(
        "--output",
        default=None,
        help="Optional output JSON path. Defaults to stdout.",
    )
    backtest_parser.add_argument("--start-capital", type=float, default=100000.0)
    backtest_parser.add_argument("--fees", type=float, default=0.001)
    backtest_parser.add_argument("--allow-short", action="store_true")
    backtest_parser.add_argument("--short-fee-rate", type=float, default=0.0050)
    backtest_parser.add_argument("--benchmark", default=None)
    backtest_parser.add_argument("--bar-size", default="1D")
    backtest_parser.add_argument("--trading-hours-per-day", type=float, default=6.5)
    backtest_parser.add_argument("--trading-days-per-year", type=int, default=252)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "backtest":
        try:
            payload = _sanitize_for_json(_run_backtest(args))
            json_output = json.dumps(payload, indent=2, allow_nan=False)
            if args.output:
                output_path = Path(args.output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(json_output + "\n", encoding="utf-8")
            else:
                print(json_output)
            return 0
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            parser.exit(1, f"Error: {exc}\n")

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
