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

The entire chain now runs end-to-end against SQLite — see
[`examples/end_to_end.py`](examples/end_to_end.py):

```python
from reade.config import ConfigLoaderFactory, YamlLoader
from reade.db import SqliteConnector
from reade.sql import render_template
from reade.data_io import execute_query, read_csv, write_csv
from reade.validation import RowCountRule
from reade.dq import VolumeDimension
```

### Module Status

| Module | Status | Notes |
|--------|--------|-------|
| `core/` | ✅ API surface | Protocols, enums, errors, models, base ABCs |
| `config/` | ✅ Hardened (1.1) | YAML / JSON → typed objects; search paths; env overrides |
| `db/` | ✅ Hardened (1.2) | SQLite / PostgreSQL / MySQL; lifecycle, health check, connect retry; dockerized integration tests |
| `sql/` | ✅ Hardened (2.1) | `RenderedQuery` render contract; `bind`/`ident` filters; discovery convention; injection tests |
| `data_io/` | ✅ Hardened (2.2) | Bound-param execution through `execute_query`; streaming CSV reader/writer |
| `validation/` | ✅ Hardened (3.1) | Count / delay / null-count rules; `Rule` plug-in protocol |
| `dq/` | ✅ Thin slice | Volume dimension; more dims in Phase 3 |

Earlier prototype implementations are being re-landed sprint by sprint.

## Configuration

Config files validate into typed objects at the `config/` boundary;
everything past it takes plain parameters.

```yaml
# db.yaml
database: "local.db"
```

```bash
# Deploy-time override — no file edit, no code change.
export READE__SQLITE__DATABASE="/var/data/prod.db"
```

```python
from reade.config import SqliteConfig, load_config
from reade.db import SqliteConnector

# resolve → parse → env overrides → validate
config = load_config("db.yaml", model=SqliteConfig)

with SqliteConnector(database=config.database) as connector:
    print(connector.ping())  # True
```

- **Formats:** YAML (`.yaml` / `.yml`) and JSON (`.json`). CSV is data,
  not config — it ships as `data_io`'s `read_csv` (see Data I/O below).
- **Resolution:** a relative name is tried against `search_paths` in
  order (default: the current working directory only); absolute paths
  bypass the search; a miss raises `FileNotFoundError` listing every
  directory searched. The SDK reads no environment variables for file
  location — applications wanting an env-var convention pass
  `os.environ[...]` into `search_paths` themselves.
- **Env overrides:** every model reads its own namespace —
  `READE__<PREFIX>__KEY` (`SqliteConfig` → `READE__SQLITE__DATABASE`,
  `PostgresConfig` → `READE__POSTGRES__HOST`) — and ignores variables
  outside it, so several configs share one process environment without
  collisions. An environment value overrides the file value (the only
  precedence rule); values arrive as raw strings and the model coerces
  and validates them. A typo'd variable inside the namespace fails
  loudly with a field path — unknown fields are rejected. Pass
  `environ={}` to disable overrides for a call, or a filtered mapping
  to substitute the process environment.
- **Validation failures** raise reaDE's own `ConfigError` carrying the
  field-path report; `ConfigLoader.load(path)` remains the untyped
  dict layer underneath.

See [`examples/config_typed.py`](examples/config_typed.py) for the full
flow, including a rejected typo'd override.

## Database Connections

Three connectors share one contract — connect, ping, execute, close —
behind `ConnectionInterface`; server drivers install as extras
(`reade[postgres]`, `reade[mysql]`, `reade[all]`).

```python
from reade.config import PostgresConfig, load_config
from reade.db import PostgresConnector

config = load_config("postgres.yaml", model=PostgresConfig)

with PostgresConnector(
    host=config.host,
    database=config.database,
    user=config.user,
    password=config.password,
    port=config.port,
    connect_attempts=config.connect_attempts,  # retry is deploy-tunable
) as connector:
    connector.ping()                      # round-trip health check
    rows = connector.execute("SELECT 1")  # [(1,)]
```

- **Every `execute()` is atomic and immediately durable, on every
  backend.** Connections run in autocommit mode: no commit calls, a
  failed statement cannot wedge the connection (health checks keep
  working), and writes survive `close()`. Callers needing transactions
  manage them through the `connection` property.
- **Retry is connect-scoped only** — bounded attempts, doubling backoff
  capped at 30s, optional per-attempt `connect_timeout` (set it on
  PostgreSQL: libpq otherwise waits indefinitely). Statement execution
  and `ping()` are never retried: retrying writes repeats non-idempotent
  work, and a health check that retries stops being a measurement.
- **Known limitations (v0.1.x):** no TLS or charset parameters yet — a
  scheduled follow-up. Interim, PostgreSQL honors libpq's standard
  [environment variables](https://www.postgresql.org/docs/current/libpq-envars.html)
  (`PGSSLMODE`, `PGSSLROOTCERT`, …) for any parameter the connector does
  not set explicitly; MySQL over TLS is not yet reachable.
- The `postgres` extra pins `psycopg[binary]` (bundled libpq) so the
  install works without system PostgreSQL libraries; the trade-off is
  that libpq security updates arrive with psycopg releases rather than
  through your OS package manager.

See [`examples/db_typed.py`](examples/db_typed.py) for the full chain —
scoped config, override namespacing, and the connector lifecycle against
a real server (CI runs it against a dockerized PostgreSQL; locally, start
`tests/integration/compose.yaml`).

## SQL Templating

Templates render into a `RenderedQuery(sql, params)` — values passed
through the `bind` filter never appear in the SQL text, and identifiers
pass the `ident` allowlist before per-dialect quoting. One template
serves every backend: the dialect decides placeholder style and quote
character at render time.

```python
from pathlib import Path

from reade.core.enums import DbType
from reade.sql import render_template

rendered = render_template(
    "daily_events",                     # <name>.sql.j2, looked up by name
    DbType.POSTGRESQL,                  # or connector.db_type
    {"table": "events", "since": "2026-01-01"},
    search_paths=[Path("my/templates")],
)
rendered.sql     # ... FROM "events" WHERE created_at >= %(since)s ...
rendered.params  # {"since": "2026-01-01"}
```

- **Trust model: templates are code, context is data.** Render only
  templates from directories you control; pass untrusted values through
  `bind` and untrusted identifiers through `ident`. There is no API to
  render ad-hoc template strings.
- **`bind`** registers a value in `params` and emits the dialect's
  PEP 249 placeholder — pyformat `%(key)s` for PostgreSQL/MySQL, named
  `:key` for SQLite. Keys are deterministic (`p0, p1, …`, or an explicit
  `bind("since")` for readable params). In pyformat dialects, write a
  literal `%` as `%%` whenever the statement binds parameters.
- **`ident`** allows `[A-Za-z_][A-Za-z0-9_]*` per dot-part (at most one
  schema qualifier) and quotes per dialect (`"events"`, `` `events` ``).
  Quoted identifiers are case-exact — on PostgreSQL pass names in stored
  case. Exotic-but-legal names (spaces, quotes, non-ASCII) are rejected
  by design.
- **Discovery:** the packaged templates plus your `search_paths`,
  nothing else. Packaged names always win; a missing `search_paths`
  directory fails loud; lookup uses the fixed `<name>.sql.j2` form.
- **Bound params execute through the SDK:**
  `execute_query(connector, rendered.sql, rendered.params)` — safe even
  when a query binds nothing, because connectors normalize empty params
  to none (part of the `ConnectionInterface` contract). Only when
  bypassing the SDK via the `connection` escape hatch must you pass
  `None`, not `{}`, for empty params.

See [`examples/sql_render.py`](examples/sql_render.py) — one template
rendered for all three dialects, then executed with bound parameters on
SQLite.

## Data I/O

Query execution and file I/O share one module: `execute_query` runs SQL
(with bound parameters) through any connector, and `read_csv` /
`write_csv` move tabular files with the same strictness the rest of the
SDK applies to data.

```python
from reade.data_io import execute_query, read_csv, write_csv

rows = execute_query(connector, rendered.sql, rendered.params)

write_csv("daily_events.csv", [{"event_name": "signup", "event_count": 2}])
for row in read_csv("daily_events.csv"):  # streams; list(...) materializes
    print(row)                            # {'event_name': 'signup', ...}
```

- **`execute_query` takes any `ConnectionInterface` implementation** —
  including third-party, protocol-only connectors; nothing needs to
  inherit from reaDE. Empty `params` are safe through the SDK path
  (connectors normalize them), so `rendered.params` passes straight
  through whether or not the query binds values.
- **`read_csv` streams dict rows keyed by the header.** Values arrive
  as raw strings — type coercion belongs to the validation layer. The
  header is validated at the call (missing file, missing header, and
  duplicate names fail immediately); a row with the wrong number of
  fields raises at that row rather than being silently padded — a DQ
  toolkit that pads is misreporting the data it will later check.
- **`write_csv` mirrors the reader:** header from the first row's keys,
  rows consumed lazily, a row with mismatched keys raises.
- **Errors:** parse and shape failures raise `DataIoError` (the parser
  error attached as cause); `OSError` — including `FileNotFoundError` —
  passes through unchanged, as in the config layer.

See [`examples/end_to_end.py`](examples/end_to_end.py) — bound-param
execution and a CSV round trip inside the full chain.

## Validation

Rules check data against expectations through any connector, and a
failed check is a result, never a raise: every rule returns
`RuleResult(rule, passed, observed, threshold)`, so the pipeline
decides what failure means. Raising is reserved for evaluation
failures — the rule could not measure at all (`RuleError`).

```python
from reade.validation import DelayRule, NullCountRule, RowCountRule

RowCountRule(table="events", min_rows=1).evaluate(connector)
DelayRule(
    table="events", column="created_at", max_delay_seconds=3600
).evaluate(connector)
NullCountRule(table="events", column="event_name").evaluate(connector)
```

- **`RowCountRule`** — the table holds at least `min_rows` rows. An
  empty table reports `observed=0` (and fails the default threshold).
- **`DelayRule`** — the newest value in a timestamp column is at most
  `max_delay_seconds` old. Measurement is client-side against the
  client clock in UTC: naive timestamps are assumed UTC, aware values
  are normalized, `date` values measure from midnight UTC (erring
  toward staleness), and future timestamps pass. An empty table
  raises `RuleError` — a freshness check with nothing to measure is
  unanswerable, not stale. `now=` takes a fixed instant for
  deterministic tests. MySQL `TIMESTAMP` columns convert through the
  session time zone on read, shifting the measured delay by the
  session's offset — run UTC sessions, or use `DATETIME`, which is
  returned as stored.
- **`NullCountRule`** — a column holds at most `max_nulls` NULLs
  (default 0: fully populated). Only the named column counts, and an
  empty table reports `observed=0` — zero rows contain zero NULLs;
  volume is `RowCountRule`'s job.
- **Custom rules** — anything with an
  `evaluate(connector) -> RuleResult` method satisfies the `Rule`
  protocol structurally; nothing inherits from reaDE, and one seam
  runs built-in and custom rules alike. Keep the parameter name
  `connector` — keyword calls are legal for every conforming rule.
  Rule table and column names pass the `ident` allowlist before
  reaching SQL: hostile identifiers raise and never reach the
  database.

See [`examples/validation_rules.py`](examples/validation_rules.py) —
the three shipped rules plus a custom protocol-only rule evaluated
through one seam, and a failing check reporting instead of raising.

## MVP Scope

**Core database support** — the base install stays light; server drivers
are opt-in extras:
- SQLite — stdlib, no extra needed
- PostgreSQL — `pip install 'reade[postgres]'` (psycopg 3)
- MySQL — `pip install 'reade[mysql]'` (PyMySQL)
- Both servers — `pip install 'reade[all]'`

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
| `config/` | Parse YAML / JSON → typed objects |
| `db/` | Connection lifecycle, health check |
| `sql/` | Render Jinja2 templates → `RenderedQuery` (SQL + bound params) |
| `data_io/` | Execute SQL, external I/O (incl. CSV readers) |
| `validation/` | Row-count, delay, and null-count rules; custom-rule plug-in point |
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
├── core/           # Shared foundation (the frozen public API surface)
│   ├── base/       # ABCs with shared behavior (ConnectionBase, FileLoaderBase)
│   ├── enums/      # DbType, FileType
│   ├── errors/     # Exception hierarchy rooted at ReadeError
│   ├── interfaces/ # Protocol definitions (contracts)
│   └── models/     # Shared data models (DbMetadata)
├── config/         # YAML loader + loader factory
├── db/             # SQLite connector
├── sql/            # Jinja2 template rendering + packaged templates
├── data_io/        # Query execution
├── validation/     # Row-count rule
└── dq/             # Volume dimension
```

Each feature module is a thin slice that deepens in its hardening sprint —
see [ARCHITECTURE.md](ARCHITECTURE.md) for the target layout and dependency
chain.

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
