# reaDE

**Data Engineering SDK with built-in Data Quality — connect, query, validate.**

> The easiest way to add real data quality checks without adopting a platform.

## The Problem

**Every DE writes the same boilerplate. Every. Single. Time.**

```python
# Sound familiar?
def get_connection(db_type, host, port, ...):  # Written 100 times
def load_config(path):                          # Copy-pasted everywhere
def build_connection_string(...):               # Slightly different each time
```

Then, after shipping the pipeline, DQ never happens because:

- "I'll add validation later" → Never happens
- "Great Expectations is too complex" → Skipped
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

- **Great Expectations / Soda** = overkill for simple checks (YAML hell, learning curve, setup overhead)
- **dbt tests** = only works in dbt context
- **Time pressure** = ship first, validate never
- **No integrated solution** = DQ feels like "extra work"

## The Solution

```
┌─────────────────────────────────────────────────────────┐
│  "I just need to connect, query, and validate"          │
│                                                         │
│   Too heavy ←────────────────────────→ Too manual       │
│   Great Expectations                   Raw SQL scripts  │
│   Soda                                 Ad-hoc checks    │
│                                                         │
│                    reaDE sits here                      │
│              ↓                                          │
│         Lightweight, built-in, just works               │
└─────────────────────────────────────────────────────────┘
```

**reaDE gives DEs tools they already understand:**

- Connect to databases
- Render SQL from templates
- Execute queries
- Validate with rules
- Return structured results

No DSL. No YAML factories. No checkpoint configs. No metadata store. No hosted agent. No UI server.

Just high-value primitives.

## Why reaDE?

| Other Tools | reaDE |
|-------------|-------|
| Platform-heavy | SDK-first |
| Config ceremony | Code-native |
| Framework ideology | Boring and reliable |
| DQ bolted on | DQ built in |
| Learn new paradigm | Use what you know |

**reaDE is the DE swiss-army knife with DQ built in.**

**Free, open-source, built by a DE for DEs.**

## Installation

```bash
# Using uv (recommended)
uv pip install reade

# Development install
uv pip install -e ".[dev]"
```

## Quick Start

```python
from reade.core.enums import DbType

# Database types available
print(DbType.POSTGRESQL)  # postgresql
print(DbType.MYSQL)       # mysql
print(DbType.SQLITE)      # sqlite
```

> **Note**: Connection and query APIs are under development. See [Project Structure](#project-structure) for current modules.

## MVP Scope

**Core (always installed):**
- PostgreSQL (psycopg2)
- MySQL (pymysql)
- SQLite (stdlib)

**Optional:**
- Trino (`pip install reade[trino]`)

**Not in MVP:**
- Oracle, DB2, ClickHouse, Snowflake
- Spark, dbt integration
- Orchestration, CDC, streaming

## Architecture

**reaDE is a Data Engineering SDK that unifies:**

| Module | Responsibility |
|--------|---------------|
| `config/` | Parse YAML/JSON/TOML → typed objects |
| `db/` | Connection lifecycle, health check |
| `sql/` | Render Jinja2 templates → SQL strings |
| `data_io/` | Execute SQL, Kafka, external I/O |
| `validation/` | Schema, type, and rule validation |
| `dq/` | DQ dimension aggregation |

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
├── config/         # Config parsing (YAML/JSON/TOML)
├── db/             # Connection lifecycle, health check
├── sql/            # Jinja2 SQL template rendering
├── data_io/        # SQL execution, Kafka, external I/O
├── validation/     # Schema, type, and rule validation
│   └── rules/      # Generic rules (count, agg, null, delay)
└── dq/             # DQ dimension aggregation
    └── dimensions/ # Volume, timeliness, completeness, accuracy
```

## Development

```bash
# Setup
uv venv --python 3.10 .pyvenv3.10
source .pyvenv3.10/bin/activate
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
