# Changelog

All notable changes to this project are documented in this file.

## Format
- The project uses a lightweight release-notes format with sections:
  `Added`, `Changed`, `Fixed`, `Removed`, and `Breaking`.
- New pull requests should update `Unreleased`.
- On release, move `Unreleased` entries to a versioned section
  (`## [x.y.z] - YYYY-MM-DD`) and reset `Unreleased`.

## [Unreleased]
### Changed
- `ClosedPosition` now uses `entry_price`, `entry_timestamp`, `exit_price`,
  `exit_timestamp` as canonical trade lifecycle fields.
- Analyzer win-rate and profit-factor calculations now use
  `ClosedPosition.pnl`.

### Fixed
- Correct short-position closed-trade accounting so entry/exit semantics are
  consistent and profitable short closes are treated correctly.
- CI matrix now pins `uv` to the configured matrix Python version.
- CI integration dataset artifact is downloaded directly to
  `tests/data/tech_stocks.parquet`.

### Added
- Regression tests for full and partial short position closes.
- Explicit CI assertion that each matrix job runs with the expected Python
  interpreter.
- Integration dataset validation for required schema and required tickers.

### Breaking
- Removed legacy `purchase_*` and `selling_*` `ClosedPosition` fields/aliases.
  Use `entry_*` and `exit_*` fields instead.
