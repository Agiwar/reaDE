# Changelog

All notable changes to reaDE are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/) with a `0.x` API that may
change between minor versions until 1.0.0.

reaDE is not yet published to PyPI — install from a git tag:
`uv add "git+https://github.com/Agiwar/reaDE@v0.1.0"`.

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

[0.1.0]: https://github.com/Agiwar/reaDE/releases/tag/v0.1.0
[0.1.0a1]: https://github.com/Agiwar/reaDE/releases/tag/v0.1.0a1
