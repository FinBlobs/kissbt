# AGENTS.md

## Scope
- These instructions apply to the whole repository.

## KISS Rule
- `kissbt` means keep it simple.
- Prefer the simplest solution that works.
- Add complexity only with clear, high impact benefit (correctness, maintainability, or major performance).
- Do not add new abstractions, patterns, or dependencies without a short justification in the PR/commit message.

## Python and Tooling
- Use `uv` for development commands.
- Development baseline: Python `3.13`.
- Supported runtime versions: Python `3.10` to `3.14`.
- Keep code compatible with Python `3.10` syntax.

## Setup
```bash
uv python install 3.13
uv venv --python 3.13
uv sync --extra dev
```

## Commands
```bash
uv run ruff format .
uv run ruff check .
uv run mypy kissbt tests
uv run pytest
```

## Definition of Done
- Tests updated when behavior changes.
- `uv run ruff format --check .` passes.
- `uv run ruff check .` passes.
- `uv run mypy kissbt tests` passes.
- `uv run pytest` passes.
