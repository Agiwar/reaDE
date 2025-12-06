# reaDE

A Python SDK providing unified interfaces for database connections, config loading, and validation - eliminating boilerplate that every data engineer rewrites.

## Why reaDE?

Every data engineer writes the same boilerplate:
- Database connection setup with different drivers
- Config file loading (YAML, JSON, env)
- Connection string building
- Basic validation logic

**reaDE** provides clean, unified interfaces so you can focus on your actual data work.

## Features

- **Unified DB Interface**: One consistent API for PostgreSQL, MySQL, SQLite (MVP)
- **Config Loading**: YAML, JSON, and environment variable support
- **Type-Safe**: Full type hints with strict mypy checking
- **Modern Python**: Supports Python 3.10+

## Installation

```bash
# Using uv (recommended)
uv pip install reade

# With Trino support
uv pip install reade[trino]

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

## Design Pattern

**Protocol → Implementation → Factory**

```python
# Protocol (interface)
class DbConnector(Protocol):
    def connect(self) -> None: ...
    def execute(self, query: str) -> list[dict]: ...

# Implementation
class PostgresConnector:
    def connect(self) -> None: ...
    def execute(self, query: str) -> list[dict]: ...

# Factory
def connect(url: str) -> DbConnector:
    ...
```

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

**Data Flow:**
```
config/ → db/ → sql/ → data_io/ → validation/ → dq/
  │        │      │        │           │          │
parse   connect  render  execute    validate   aggregate
```

## License

MIT License

## Author

**Jeffrey Li** - [@Agiwar](https://github.com/Agiwar)
