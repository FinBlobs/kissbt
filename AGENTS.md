# AGENTS.md

## Scope
- Applies to the whole repository.

## Project Goal
- Keep `kissbt` small, understandable, and reliable for real backtesting use.
- Optimize for long-term maintainability over short-term feature volume.

## Engineering Principles
- Prefer the simplest implementation that meets the requirement.
- Add complexity only for clear gains in correctness, maintainability, or major performance.
- Avoid adding dependencies unless there is a strong, explicit reason.
- Fail fast with clear errors when invariants are violated.

## Public API Discipline
- Treat Python package exports, documented behavior, and CLI JSON output as public surface.
- Keep public interfaces minimal and coherent; avoid adding convenience fields that blur semantics.
- When behavior changes, make it explicit in docs/tests/changelog.
- Preserve backward compatibility when practical; if not practical, document the break clearly.

## Core Invariants
- Preserve the current execution model unless a task explicitly requires changing it.
- `Strategy.generate_orders(...)` runs after the broker processes the current bar; orders placed there execute on the next bar.
- `OPEN` orders use the next bar `open`; `CLOSE` orders use the next bar `close`; `LIMIT` orders require `open`/`high`/`low`.
- `Engine.run(...)` liquidates remaining positions on the final bar and must fail clearly if liquidation leaves positions open.
- `ClosedPosition` uses `entry_*` / `exit_*` semantics as the canonical trade lifecycle model.
- If a benchmark is configured, input data must contain that ticker for every timestamp.
- CLI JSON is a public contract: keep field names, timestamp formatting, and null-normalization deterministic.

## Data & Behavior Contracts
- Validate external inputs at boundaries and raise actionable errors.
- Prefer explicit invariants over silent fallback behavior.
- Keep output schemas deterministic and machine-consumable.

## Refactor Threshold
- Only refactor when it removes duplicated business rules, improves correctness, or makes public behavior easier to understand.
- Do not split modules or introduce abstraction layers only to make the code look cleaner.
- Prefer consolidating validation and invariant enforcement over reorganizing already-small components.

## README & Documentation
- README is the GitHub landing page: prioritize human readability and quick comprehension.
- Keep examples runnable, concise, and aligned with current API behavior.
- Present CLI as a first-class user interface for shell/script workflows.
- Put deeper implementation details in dedicated docs/tests/changelog rather than in quickstart sections.
- Document execution semantics and output contracts before adding more feature examples.

## Runtime & Tooling
- Use `uv` for development commands.
- Development baseline: Python `3.13`.
- Supported runtime versions: Python `3.12` to `3.14`.
- Keep code compatible with Python `3.12` syntax.

## Test & CI Discipline
- Keep tests deterministic; avoid network calls in test execution paths.
- Add or update tests for all user-visible behavior changes.
- Prefer regression tests when fixing bugs.
- When changing validation, cover both success paths and actionable failure messages.
- When changing execution semantics or CLI JSON, add or update tests before changing docs.

## Final Gate (Before Commit/Push)
```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy kissbt tests
uv run pytest
```

## Release Notes
- For user-visible code, API, behavior, docs, or CI changes, add a short entry to
  `CHANGELOG.md` under `Unreleased` (`Added`, `Changed`, `Fixed`, `Removed`).
