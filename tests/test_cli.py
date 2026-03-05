import json

import pandas as pd

from kissbt.cli import main


def test_cli_backtest_writes_result_json(tmp_path, monkeypatch):
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
    monkeypatch.syspath_prepend(str(tmp_path))

    csv_path = tmp_path / "market_data.csv"
    pd.DataFrame(
        {
            "timestamp": ["2024-01-01", "2024-01-02"],
            "ticker": ["AAPL", "AAPL"],
            "open": [100.0, 101.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.0],
            "close": [101.0, 102.0],
        }
    ).to_csv(csv_path, index=False)

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
    assert "metrics" in payload
    assert payload["metrics"]["profit_factor"] is None
