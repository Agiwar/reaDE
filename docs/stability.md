# Stability table

The user-facing per-symbol view of the API freeze: all 44 pinned
public symbols and their dispositions from the Sprint 4.1 walk,
unchanged through the Sprint 4.2 delta (additive parameters, fields,
and input contracts on already-pinned symbols — the count stays 44).
The classification rubric, the per-symbol walk notes, and the delta
live in the [freeze record](api_freeze.md); this table mirrors the
public-API snapshot mechanically and is cross-checked against it by a
committed test.

| Symbol | Package | Disposition |
|---|---|---|
| `reade.config.ConfigLoaderFactory` | `reade.config` | stable |
| `reade.config.JsonLoader` | `reade.config` | stable |
| `reade.config.YamlLoader` | `reade.config` | stable |
| `reade.config.SqliteConfig` | `reade.config` | stable |
| `reade.config.PostgresConfig` | `reade.config` | stable |
| `reade.config.MysqlConfig` | `reade.config` | stable |
| `reade.config.load_config` | `reade.config` | stable |
| `reade.config.merge_env_overrides` | `reade.config` | stable |
| `reade.core.base.ConnectionBase` | `reade.core.base` | stable |
| `reade.core.base.FileLoaderBase` | `reade.core.base` | stable |
| `reade.core.enums.DbType` | `reade.core.enums` | stable |
| `reade.core.enums.FileType` | `reade.core.enums` | stable |
| `reade.core.errors.ReadeError` | `reade.core.errors` | stable |
| `reade.core.errors.ConfigError` | `reade.core.errors` | stable |
| `reade.core.errors.DataIoError` | `reade.core.errors` | stable |
| `reade.core.errors.DbError` | `reade.core.errors` | stable |
| `reade.core.errors.NotConnectedError` | `reade.core.errors` | stable |
| `reade.core.errors.DqError` | `reade.core.errors` | stable |
| `reade.core.errors.SqlError` | `reade.core.errors` | stable |
| `reade.core.errors.RuleError` | `reade.core.errors` | stable |
| `reade.core.interfaces.ConfigLoader` | `reade.core.interfaces` | stable |
| `reade.core.interfaces.ConnectionInterface` | `reade.core.interfaces` | stable |
| `reade.core.models.DbMetadata` | `reade.core.models` | stable |
| `reade.core.models.DB_METADATA_REGISTRY` | `reade.core.models` | stable |
| `reade.data_io.execute_query` | `reade.data_io` | stable |
| `reade.data_io.read_csv` | `reade.data_io` | stable |
| `reade.data_io.write_csv` | `reade.data_io` | stable |
| `reade.db.SqliteConnector` | `reade.db` | stable |
| `reade.db.PostgresConnector` | `reade.db` | stable |
| `reade.db.MysqlConnector` | `reade.db` | stable |
| `reade.dq.Dimension` | `reade.dq` | stable |
| `reade.dq.DqResult` | `reade.dq` | stable |
| `reade.dq.DqReport` | `reade.dq` | stable |
| `reade.dq.VolumeDimension` | `reade.dq` | stable |
| `reade.dq.FreshnessDimension` | `reade.dq` | stable |
| `reade.dq.CompletenessDimension` | `reade.dq` | stable |
| `reade.dq.check` | `reade.dq` | stable |
| `reade.sql.RenderedQuery` | `reade.sql` | stable |
| `reade.sql.render_template` | `reade.sql` | stable |
| `reade.validation.Rule` | `reade.validation` | stable |
| `reade.validation.RuleResult` | `reade.validation` | stable |
| `reade.validation.RowCountRule` | `reade.validation` | stable |
| `reade.validation.DelayRule` | `reade.validation` | stable |
| `reade.validation.NullCountRule` | `reade.validation` | stable |

A disposition here can only change through the freeze machinery —
a design-review note in the PR plus a snapshot regeneration — never
through a docs edit; the cross-check test fails loud on any row that
drifts from the snapshot.
