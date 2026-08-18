# Examples

Seven runnable scripts, one per surface the SDK grew — each the
acceptance script of its sprint, each exiting non-zero on failure, and
each running as its own CI step on every push (that is the freshness
proof: if an example rots, CI goes red).

Run any of them from the repo root:

```bash
uv run python examples/<name>.py
```

| Example | Demonstrates | Needs a server? |
|---|---|---|
| [`end_to_end.py`](end_to_end.py) | The full chain — config → db → sql → data_io → validation → dq — against SQLite, public API only | No |
| [`config_typed.py`](config_typed.py) | Typed config: file value + scoped env override → validated object → plain connector parameters | No |
| [`db_typed.py`](db_typed.py) | The typed db chain against a real PostgreSQL: scoped override namespaces and the full connector lifecycle | **Yes** — PostgreSQL matching [`config/postgres.yaml`](config/postgres.yaml); CI provides a service container, locally use the compose file under `tests/integration/` |
| [`sql_render.py`](sql_render.py) | One template rendered for all three dialects, then bound execution through render → `RenderedQuery` → `execute_query` | No |
| [`validation_rules.py`](validation_rules.py) | The built-in rules (row-count, delay, null-count) plus a custom `Rule`-protocol plug-in; failed checks are results, not raises | No |
| [`dq_dimensions.py`](dq_dimensions.py) | Shipped dimensions plus a custom `Dimension`-protocol plug-in, assessed directly and through `check`; errored vs failed shown at both layers | No |
| [`connection_ergonomics.py`](connection_ergonomics.py) | TLS/charset options (per-driver names, config-mirrored) and `DATABASE_URL`-style URI input; server-free by design, with a live SQLite leg | No |

Each module docstring carries the full walkthrough and its exact
`Run with:` line — the docstrings are the detail; this index only
routes.

Support files:

- [`config/`](config/) — the YAML configs the scripts load (`db.yaml`,
  `sqlite.yaml`, `postgres.yaml`).
- [`templates/`](templates/) — the Jinja2 SQL template
  (`daily_events.sql.j2`) rendered per dialect by `sql_render.py` and
  `end_to_end.py`.

More context: the [README](../README.md) walks the same surfaces
narratively, and the per-symbol API reference builds locally with
`make docs` (see [docs/](../docs/index.md)).
