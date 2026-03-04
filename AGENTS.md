# AGENTS.md

## Scope
- Applies to the whole repository.

## KISS
- `kissbt` means keep it simple.
- Prefer the simplest solution that works.
- Add complexity only for clear high-impact benefit (correctness,
  maintainability, major performance).
- Do not add abstractions, patterns, or dependencies without a short
  justification in the PR/commit message.

## Runtime & Tooling
- Use `uv` for development commands.
- Development baseline: Python `3.13`.
- Supported runtime versions: Python `3.12` to `3.14`.
- Keep code compatible with Python `3.12` syntax.

## Test & CI Discipline
- Keep tests deterministic; avoid network calls in test execution paths.
- If behavior changes, update or add tests.

## Final Gate (Before Commit/Push)
```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy kissbt tests
uv run pytest
```

## Release Notes
- For user-visible code, API, behavior, or CI changes, add one short entry to
  `CHANGELOG.md` under `Unreleased` (`Added`, `Changed`, `Fixed`, `Removed`).
