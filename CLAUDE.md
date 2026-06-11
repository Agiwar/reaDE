# CLAUDE.md

reaDE — Data Engineering SDK with built-in Data Quality. Small, sharp,
opinionated helpers that eliminate the boilerplate every data engineer
rewrites: config loading, DB connections, SQL templating, sanity checks,
data-quality dimensions. An SDK, not a platform.

## Before touching code

Read `ARCHITECTURE.md` (module layout, dependency chain) and
`DEVELOPMENT_PLAN.md` (phases, sprints, definitions of done). A change is in
scope only if the current sprint's DoD covers it.

## Commands

- Install: `uv sync` (with dev tools: `uv sync --extra dev`)
- Test: `uv run pytest`
- Lint + types: `uv run ruff check src tests && uv run mypy src tests`
- All gates: `make check-all` (lint, type-check, bandit, tests)
- Hooks: `uv run pre-commit install`

## Architecture rules

- Dependency chain: `config → db → sql → data_io → validation → dq`.
  `core/` underpins everything and imports from no feature module; a feature
  module may depend only on `core/` and modules to its left.
- Pattern per feature: Interface (Protocol) → Base (ABC, only where shared
  behavior earns it) → Implementation → Factory. Factories are the only
  place that maps enums to implementations.
- Errors map into `core.errors` at the implementation layer; raw driver
  exceptions never cross a module boundary.
- The public API freezes after Phase 0: changing a public symbol requires a
  design-review note in the PR description.

## Code standards

- Python 3.12+; mypy strict; type hints required on all public functions.
- Google-style docstrings, docstring-first: behavior documented in a
  docstring is contract, including which exceptions a method raises.
- Ruff handles lint and formatting. No speculative abstraction; clarity
  over premature optimization.

## Git

- Conventional Commits (`type: description`); feature branches squash-merged
  to `main`; trunk-based, no develop branch.
- Branch prefixes: `feat/`, `fix/`, `chore/`, `docs/`, `refactor/`, `test/`,
  `ci/`.
- Commit messages: high-level what/why, no file listings, no generated-by
  footers.
