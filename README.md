# reaDE

*Pronounced "ready" — the `DE` stands for **D**ata **E**ngineer.*

**Data Engineering SDK with built-in Data Quality — connect, query, validate.**

> Add data quality checks alongside the Python you already use to connect and query.

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

# 2. Create and activate a virtual environment (Python 3.12+)
uv venv --python 3.12 .venv
source .venv/bin/activate

# 3. Install in editable mode with dev extras
uv pip install -e ".[dev]"
```

## Quick Start

Load a config file with a single call — extension auto-detected (YAML / JSON / CSV):

```python
from pathlib import Path

from reade.config.utils import get_config_content

base = Path("examples/sample_configs")

db_config = get_config_content("db.yaml", base_path=base)
app_config = get_config_content("app.json", base_path=base)
settings = get_config_content("settings.csv", base_path=base)

print(db_config["database"]["host"])  # e.g. "localhost"
print(app_config["service"])          # e.g. "reade-demo"
print(settings["log_level"])          # e.g. "INFO"
```

Runnable demo — see [`examples/`](examples/):

```bash
python examples/basic_config_loading.py
```

### Module Status

| Module | Status | Notes |
|--------|--------|-------|
| `config/` | ✅ Functional | YAML / JSON / CSV loaders + factory + `get_config_content()` |
| `db/` (SQLite) | ✅ Functional | `SqliteConnector` with tests |
| `db/` (PostgreSQL, MySQL, Trino) | 🚧 In progress | Connector scaffolding in place |
| `sql/` | 🚧 In progress | Jinja2 template rendering |
| `data_io/` | 🚧 In progress | SQL execution, readers/writers/serializers |
| `validation/` | 🚧 In progress | Schema, type, and rule validation |
| `dq/` | 🚧 In progress | DQ dimension aggregation |

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

![reaDE Overview](http://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/Agiwar/reaDE/main/docs/reade_overview.puml)

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
├── core/           # Shared foundation
│   ├── base/       # ABCs with shared implementation
│   ├── enums/      # DbType, DqDimension, etc.
│   ├── errors/     # Exception hierarchy
│   ├── interfaces/ # Protocol definitions (contracts)
│   └── models/     # Shared data models
├── config/         # Config parsing (YAML/JSON/CSV)
├── db/             # Connection lifecycle, health check
├── sql/            # Jinja2 SQL template rendering
├── data_io/        # SQL execution, external I/O
├── validation/     # Schema, type, and rule validation
│   └── rules/      # Generic rules (count, agg, null, delay)
└── dq/             # DQ dimension aggregation
    └── dimensions/ # Volume, timeliness, completeness, accuracy
```

## Development

```bash
# Setup
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -e ".[dev]"

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
