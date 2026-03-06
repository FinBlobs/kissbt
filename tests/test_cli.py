import json

import pandas as pd
import pytest

from kissbt.cli import main


def _write_strategy_module(tmp_path) -> None:
    strategy_module = tmp_path / "test_strategy_module.py"
    strategy_module.write_text(
        "\n".join(
            [
                "from kissbt import Order, Strategy",
                "",
                "class CliTestStrategy(Strategy):",
                "    def initialize(self) -> None:",
                "        self.has_order = False",
                "",
                "    def generate_orders(",
                "        self, current_data, current_timestamp",
                "    ) -> None:",
                "        if self.has_order:",
                "            return",
                "        self.broker.place_order(Order('AAPL', 1))",
                "        self.has_order = True",
            ]
        ),
        encoding="utf-8",
    )


def _write_market_data_csv(tmp_path, *, integer_values: bool = False):
    csv_path = tmp_path / "market_data.csv"
    price_values: list[int | float] = (
        [100, 101] if integer_values else [100.0, 101.0]
    )
    pd.DataFrame(
        {
            "timestamp": ["2024-01-01", "2024-01-02"],
            "ticker": ["AAPL", "AAPL"],
            "open": price_values,
            "high": [value + 2 for value in price_values],
            "low": [value - 1 for value in price_values],
            "close": [value + 1 for value in price_values],
        }
    ).to_csv(csv_path, index=False)
    return csv_path


def test_cli_backtest_writes_result_json(tmp_path, monkeypatch):
    _write_strategy_module(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    csv_path = _write_market_data_csv(tmp_path)
    output_path = tmp_path / "result.json"

    exit_code = main(
        [
            "backtest",
            "--input",
            str(csv_path),
            "--strategy",
            "test_strategy_module:CliTestStrategy",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    raw_output = output_path.read_text(encoding="utf-8")
    assert "Infinity" not in raw_output
    payload = json.loads(raw_output)
    assert payload["summary"]["bars"] == 2
    assert payload["summary"]["closed_positions"] == 1
    assert "final_cash" not in payload["summary"]
    assert "open_positions" not in payload["summary"]
    assert "metrics" in payload
    assert payload["metrics"]["profit_factor"] is None


def test_cli_backtest_serializes_numpy_scalars_from_integer_csv(tmp_path, monkeypatch):
    _write_strategy_module(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    csv_path = _write_market_data_csv(tmp_path, integer_values=True)
    output_path = tmp_path / "integer_result.json"

    exit_code = main(
        [
            "backtest",
            "--input",
            str(csv_path),
            "--strategy",
            "test_strategy_module:CliTestStrategy",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["closed_positions"][0]["entry_price"] == 101
    assert payload["closed_positions"][0]["exit_price"] == 102
    assert payload["events"][0]["price"] == 101


def test_cli_backtest_creates_parent_output_directory(tmp_path, monkeypatch):
    _write_strategy_module(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    csv_path = _write_market_data_csv(tmp_path)
    output_path = tmp_path / "nested" / "reports" / "result.json"

    exit_code = main(
        [
            "backtest",
            "--input",
            str(csv_path),
            "--strategy",
            "test_strategy_module:CliTestStrategy",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()


def test_cli_backtest_prints_clean_error_for_missing_input(tmp_path, capsys):
    missing_path = tmp_path / "missing.csv"

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "backtest",
                "--input",
                str(missing_path),
                "--strategy",
                "unused:Strategy",
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert "Error: input file does not exist:" in captured.err
    assert "Traceback" not in captured.err


def test_cli_backtest_prints_clean_error_for_invalid_csv(tmp_path, capsys):
    invalid_csv = tmp_path / "invalid.csv"
    invalid_csv.write_text('timestamp,ticker\n"2024-01-01,AAPL\n', encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "backtest",
                "--input",
                str(invalid_csv),
                "--strategy",
                "unused:Strategy",
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert "Error: failed to parse CSV input data from" in captured.err
    assert "Traceback" not in captured.err
