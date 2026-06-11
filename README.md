# reaDE

*Pronounced "ready" — the `DE` stands for **D**ata **E**ngineer.*

**Data Engineering SDK with built-in Data Quality — connect, query, validate.**

> Every DE, ready to ship — boilerplate handled, data quality built in.

## The Problem

**Every DE writes the same boilerplate. Every. Single. Time.**

```python
# Sound familiar?
def get_connection(db_type, host, port, ...):   # Written 100 times
def load_config(path):                          # Copy-pasted everywhere
def build_connection_string(...):               # Slightly different each time
```

Then, after shipping the pipeline, DQ never happens because:

- "I'll add validation later" → Never happens
- "Adopting a validation tool is its own project" → Skipped
- "No time, deadline tomorrow" → Technical debt

**The reality:**

| What DEs typically do | Problem |
|----------------------|---------|
| Ad-hoc `SELECT COUNT(*)` | No tracking, no alerting |
| Manual null checks | Inconsistent, forgotten |
| "I'll check it later" | Never happens |
| No freshness monitoring | Stale data goes unnoticed |
| Custom validation scripts | DRY violation, unmaintainable |

**Why DQ gets skipped:**

- **Adopting a separate validation tool** brings its own setup, config, and operational surface
- **Time pressure** — ship first, validate never
- **No integrated path** — DQ feels like "extra work" instead of a natural step in the pipeline

## What reaDE Does

reaDE is a Python SDK for the work data engineers already do — connect to a database, render a SQL template, execute it, and check the result — with data quality treated as part of the toolkit, not a separate platform you adopt.

- **Code-native** — pure Python with typed interfaces. Composable like any other library; mypy-strict at the source.
- **DQ designed in, not bolted on** — counts, freshness, nulls, schema, and custom rules share the same execution path as your queries, so writing a check has the same shape as writing a query.
- **Modular** — pick the parts you need (`config/`, `db/`, `sql/`, `data_io/`, `validation/`, `dq/`); each has a small, documented surface.
- **Stays out of your way** — runs wherever your Python runs. No hosted service, no metadata store, no UI server to operate.

Free, open-source, MIT-licensed.

## Installation

> **Not yet published to PyPI; install from source.**

```bash
# 1. Clone the repo
git clone https://github.com/Agiwar/reaDE.git
cd reaDE

# 2. Create the environment and install reaDE (resolves from uv.lock)
uv sync

# 3. Activate the environment
source .venv/bin/activate
```

## Status

reaDE is pre-alpha, being rebuilt as a [walking skeleton](DEVELOPMENT_PLAN.md):
the public API surface in `core/` lands first, then thin implementations of
the whole chain, then each module is hardened in release-gated sprints.

What exists today is the `core/` contract layer:

```python
from reade.core.enums import DbType, FileType
from reade.core.errors import ConfigError, DbError, ReadeError
from reade.core.interfaces import ConfigLoader, ConnectionInterface
from reade.core.models import DB_METADATA_REGISTRY, DbMetadata
```

### Module Status

| Module | Status | Notes |
|--------|--------|-------|
| `core/` | ✅ API surface | Protocols, enums, errors, models |
| `config/` | 📋 Sprint 0.2 | YAML first; JSON / CSV follow in Phase 1 |
| `db/` | 📋 Sprint 0.2 | SQLite first; PostgreSQL / MySQL in Phase 1 |
| `sql/` | 📋 Sprint 0.2 | Jinja2 template rendering |
| `data_io/` | 📋 Sprint 0.2 | SQL execution, readers/writers |
| `validation/` | 📋 Sprint 0.2 | Row-count rule first; more rules in Phase 3 |
| `dq/` | 📋 Sprint 0.2 | Volume dimension first; more dims in Phase 3 |

Earlier prototype implementations are parked on the
[`archive/pre-skeleton`](https://github.com/Agiwar/reaDE/tree/archive/pre-skeleton)
branch and will be re-landed sprint by sprint.

## MVP Scope

**Core (always installed):**
- PostgreSQL (psycopg2)
- MySQL (pymysql)
- SQLite (stdlib)

**Planned (not yet shipped):**
- Trino (analytics engine connector)

**Not in MVP:**
- Oracle, DB2, ClickHouse, Snowflake
- Spark, dbt integration
- Orchestration, CDC, streaming

## Architecture

![reaDE Overview](docs/reade_overview.png)

<sub>Diagram source: [`docs/reade_overview.puml`](docs/reade_overview.puml) — regenerate `reade_overview.png` after editing it.</sub>

**reaDE is a Data Engineering SDK that unifies:**

| Module | Responsibility |
|--------|---------------|
| `config/` | Parse YAML / JSON / CSV → typed objects |
| `db/` | Connection lifecycle, health check |
| `sql/` | Render Jinja2 templates → SQL strings |
| `data_io/` | Execute SQL, external I/O |
| `validation/` | Schema, type, and rule validation |
| `dq/` | Data quality dimension aggregation |

**Data Flow:**
```
config/ → db/ → sql/ → data_io/ → validation/ → dq/
  │        │      │        │           │          │
parse   connect  render  execute    validate   aggregate
```

**DQ is powered by the other layers — the synergy is the value.**

## Project Structure

```
src/reade/
└── core/           # Shared foundation (the frozen public API surface)
    ├── enums/      # DbType, FileType
    ├── errors/     # Exception hierarchy rooted at ReadeError
    ├── interfaces/ # Protocol definitions (contracts)
    └── models/     # Shared data models (DbMetadata)
```

Feature modules (`config/`, `db/`, `sql/`, `data_io/`, `validation/`, `dq/`)
are added sprint by sprint — see [ARCHITECTURE.md](ARCHITECTURE.md) for the
target layout and dependency chain.

## Development

```bash
# Setup (installs dev tools from locked versions)
uv sync --extra dev
source .venv/bin/activate

# Commands
make help          # Show all commands
make lint          # Run ruff linter
make type-check    # Run mypy
make test          # Run tests
make check-all     # Run all checks
```

## License

MIT License

## Author

**Jeffrey Li** - [@Agiwar](https://github.com/Agiwar)
