# Changelog

All notable changes to reaDE are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/) with a `0.x` API that may
change between minor versions until 1.0.0.

reaDE is not yet published to PyPI — install from a git tag:
`uv add "git+https://github.com/Agiwar/reaDE@v0.2.0"`.

## [0.2.0] — 2026-08-02

Phase 2 — sql and data_io.

### Added

- `sql`: `render_template` renders to `RenderedQuery(sql, params)` — the
  `bind` filter registers values as bound parameters and emits the
  dialect's PEP 249 placeholder (`:name` for SQLite, `%(name)s` for
  PostgreSQL/MySQL); the `ident` filter quotes identifiers per dialect.
  Templates render with `StrictUndefined` and load only from the packaged
  directory plus caller-supplied `search_paths`; missing search-path
  entries fail loud.
- `data_io`: `execute_query(connector, sql, params=None)` executes bound
  parameters through the SDK; `read_csv` / `write_csv` stream dict rows
  keyed by header — values stay raw strings, ragged rows raise, CSV
  parse/shape failures map to `DataIoError`, `OSError` passes through.
- Machine-checked development gates: public-API snapshot test,
  import-linter layered-dependency contract, 90% coverage floor.

### Changed

- Breaking (pre-registered bundle; design-review note in PR #31):
  `execute()` gains `params: dict[str, Any] | None = None` on
  `ConnectionInterface`, `ConnectionBase`, and all three connectors —
  falsy `params` normalize to `None` at the connector; `db_type` joins
  `ConnectionInterface` as a read-only property; `execute_query`,
  `RowCountRule.evaluate`, and `VolumeDimension.assess` accept any
  `ConnectionInterface` implementation (was `ConnectionBase[Any]`);
  `merge_env_overrides`'s `environ` becomes keyword-only with a
  call-time default.
- Breaking: `render_template(template_name, dialect, context=None, /, *,
  search_paths=None) -> RenderedQuery` replaces the Phase-0 signature.
- Database query results stay materialized (`list[tuple]`); the CSV
  reader streams (files are unbounded, query results are not).

### Security

- Identifiers are allowlisted (`[A-Za-z_][A-Za-z0-9_]*`, optional schema
  part) and dialect-quoted; hostile identifiers raise `SqlError`. Bound
  values never appear in SQL text — asserted end-to-end on all three
  dialects, including the built-in `row_count` template.

## [0.1.0] — 2026-07-06

Phase 1 — config and db hardening.

### Added

- `config`: JSON and YAML loaders; `load_config` auto-locate with
  `search_paths`; `READE__<PREFIX>__FIELD` env-var overrides; typed
  pydantic models (`SqliteConfig`, `PostgresConfig`, `MysqlConfig`).
- `db`: PostgreSQL connector on psycopg v3 (`reade[postgres]`) and MySQL
  connector on pymysql (`reade[mysql]`); `reade[all]` installs both.
- `db`: connect-scoped retry — bounded attempts, doubling backoff capped
  at 30s, per-attempt timeout. Statement execution is never retried.
- Integration test suite against dockerized PostgreSQL and MySQL.

### Changed

- Connection pooling deferred by plan amendment: `ping()` plus connect
  retry cover the idle-timeout failure mode; revisit at Phase 4.

### Fixed

- `SqliteConnector.execute()` is durable on file-backed databases: rows
  now survive `close()` (autocommit connection).

## [0.1.0a1] — 2026-06-12

Phase 0 — walking skeleton.

### Added

- Frozen public API surface in `core`: interfaces (Protocols), enums,
  errors, models.
- Thin happy-path implementations across the whole chain
  (`config → db → sql → data_io → validation → dq`) with SQLite as the
  zero-setup backend.
- `examples/end_to_end.py` running the full chain against SQLite.

[0.2.0]: https://github.com/Agiwar/reaDE/releases/tag/v0.2.0
[0.1.0]: https://github.com/Agiwar/reaDE/releases/tag/v0.1.0
[0.1.0a1]: https://github.com/Agiwar/reaDE/releases/tag/v0.1.0a1
