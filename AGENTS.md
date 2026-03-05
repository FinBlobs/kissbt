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

## Data & Behavior Contracts
- Validate external inputs at boundaries and raise actionable errors.
- Prefer explicit invariants over silent fallback behavior.
- Keep output schemas deterministic and machine-consumable.

## README & Documentation
- README is the GitHub landing page: prioritize human readability and quick comprehension.
- Keep examples runnable, concise, and aligned with current API behavior.
- Present CLI as a first-class user interface for shell/script workflows.
- Put deeper implementation details in dedicated docs/tests/changelog rather than in quickstart sections.

## Runtime & Tooling
- Use `uv` for development commands.
- Development baseline: Python `3.13`.
- Supported runtime versions: Python `3.12` to `3.14`.
- Keep code compatible with Python `3.12` syntax.

## Test & CI Discipline
- Keep tests deterministic; avoid network calls in test execution paths.
- Add or update tests for all user-visible behavior changes.
- Prefer regression tests when fixing bugs.

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
