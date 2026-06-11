# reaDE — Architecture

> Data Engineering SDK with built-in Data Quality.
> This document is the textual source of truth for the architecture diagram
> (`reade_overview.png`). If they disagree, this file wins.

---

## 1. Layers

```
Use Cases
  ├── Data Quality Apps
  ├── Simple Apps
  └── Future
        │
        ▼
Python Foundation          ← reusable, maintainable, scalable, testable
  ├── Features:  config · db · sql · data_io · validation · dq · utils
  ├── core:      interfaces · enums · errors · models
  └── Standards: pyproject.toml · uv · ruff · mypy · PEP8 · pytest
```

The Foundation exists to serve the use cases above it. Features depend on
`core/`; nothing in `core/` depends on a feature module.

---

## 2. Modules and roles

| Module | Role |
|---|---|
| `core` | Interfaces (Protocols), enums, errors, models — shared contracts for all features |
| `config` | Read JSON / YAML / CSV; auto-locate; return typed config objects |
| `db` | Connection lifecycle, health check, pooling, retries |
| `sql` | Jinja2 template → SQL, with parameter safety |
| `data_io` | Execute query, read / write results |
| `validation` | Rules: count, delay, schema, custom plug-ins |
| `dq` | Data-quality dimensions (volume, freshness, completeness) composed from validation rules |
| `utils` | Generic helpers; no business logic |

---

## 3. Dependency chain

```
config → db → sql → data_io → validation → dq
            (core/ underpins everything)
```

Rules:
- A module may depend only on `core/` and modules to its **left** in the chain.
- `dq` is the highest-level feature: it composes `validation`, which uses
  `data_io`, which executes via `db` + `sql`, configured by `config`.
- `utils` may be used anywhere but depends on nothing except the stdlib.
- No circular imports — CI should fail on them.

---

## 4. Design pattern per feature module

```
Interface (Protocol)  →  Base (ABC, only where shared behavior earns it)
                      →  Implementation  →  Factory
```

- Extension points (DB connectors, config loaders, validation rules) are
  Protocols, so third parties can plug in without inheriting from us.
- Factories are the only place that maps enums/strings to implementations.
- Raw driver exceptions never cross a module boundary — they are mapped into
  `core.errors` at the implementation layer.

---

## 5. Standards (enforced by CI)

| Tool | Purpose |
|---|---|
| `pyproject.toml` + `uv` | Packaging and dependency management (not pip) |
| `ruff` 0.6+ | Lint + format (replaces black, isort, flake8) |
| `mypy` (strict) | Type checking; type hints required on all public functions |
| `pytest` + coverage | Unit, contract, and integration tests |
| PEP8 / Google-style docstrings | Style; docstring-first development |

Python 3.12+.

---

## 6. Foundation qualities (the bar for every PR)

- **Reusable** — no project-specific or employer-specific logic
- **Maintainable** — small public API, single-responsibility functions
- **Scalable** — new connectors/loaders/rules plug in without API changes
- **Testable** — SQLite as the zero-setup test backend; contract tests per interface
