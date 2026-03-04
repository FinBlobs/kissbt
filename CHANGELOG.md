# Changelog

All notable changes to this project are documented in this file.
This changelog follows the Keep a Changelog style.

## [Unreleased]
### Added
- Regression tests for full and partial short position closes.
- Explicit CI assertion that each matrix job runs with the expected Python
  interpreter.
- Integration dataset validation for required schema and required tickers.
- `entry_value` and `exit_value` properties on `ClosedPosition`.

### Changed
- `ClosedPosition` now uses `entry_price`, `entry_timestamp`, `exit_price`,
  `exit_timestamp` as canonical trade lifecycle fields.
- Analyzer win-rate and profit-factor calculations now use
  `ClosedPosition.pnl`.
- CI integration dataset preparation now uses shared test utility code.
- `CHANGELOG.md` and AGENTS release-note process were introduced.

### Fixed
- Correct short-position closed-trade accounting so entry/exit semantics are
  consistent and profitable short closes are treated correctly.
- CI matrix now pins `uv` to the configured matrix Python version.
- CI integration dataset artifact is downloaded to
  `tests/data/tech_stocks.parquet` as expected by integration tests.
- Ruff import-ordering behavior is now deterministic across local and CI
  environments.

### Removed
- Removed legacy `purchase_*` and `selling_*` `ClosedPosition` fields/aliases.
  Use `entry_*` and `exit_*` fields instead.

## [0.1.6] - 2025-07-18
### Added
- Analyzer enhancements:
  - Boxplot support.
  - Linear regression statistics on the log-equity curve.

### Changed
- Release preparation updates for `v0.1.6`.

## [0.1.5] - 2025-03-17
### Fixed
- Ticker out-of-universe handling and related patch release updates.

## [0.1.4] - 2025-03-17
### Changed
- Patch release updates.

## [0.1.3] - 2025-02-15
### Fixed
- Publishing script and release workflow fixes.

## [0.1.2] - 2025-02-15
### Changed
- Release updates for `v0.1.2`.

## [0.1.1] - 2025-02-15
### Fixed
- Package publishing workflow fixes.

## [0.1.0] - 2025-02-15
### Added
- Initial public release of `kissbt`.

[Unreleased]: https://github.com/FinBlobs/kissbt/compare/v0.1.6...HEAD
[0.1.6]: https://github.com/FinBlobs/kissbt/releases/tag/v0.1.6
[0.1.5]: https://github.com/FinBlobs/kissbt/releases/tag/v0.1.5
[0.1.4]: https://github.com/FinBlobs/kissbt/releases/tag/v0.1.4
[0.1.3]: https://github.com/FinBlobs/kissbt/releases/tag/v0.1.3
[0.1.2]: https://github.com/FinBlobs/kissbt/releases/tag/v0.1.2
[0.1.1]: https://github.com/FinBlobs/kissbt/releases/tag/v0.1.1
[0.1.0]: https://github.com/FinBlobs/kissbt/releases/tag/v0.1.0
