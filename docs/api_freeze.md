# reaDE public API freeze record — Phase 4, Sprint 4.1

Recorded at the Sprint 4.1 API freeze walk (2026-08-07), against the
public-API snapshot (`tests/snapshots/public_api.json`) as it stands
after the freeze-contract changes of PR #48. The pinned surface is
**44 symbols across 11 packages** — counted mechanically from the
snapshot's keys, which this record mirrors one-to-one. Each symbol
also carries a `Stability:` marker — a docstring line for 43 of the
44; `DB_METADATA_REGISTRY`'s is a source comment, carried user-facing
by its row in the [stability table](stability.md).

## Classification rubric

A symbol is **stable** if and only if all four hold:

1. It shipped through its module's hardening sprint, with contract or
   unit tests exercising its documented behavior.
2. Its documented contract (docstring and README) claims only shipped,
   test-backed behavior.
3. No open design question or recorded condition targets its shape.
4. Its pin is machine-enforced by the public-API snapshot test.

A symbol failing any leg is **experimental** — shipped ahead of its
hardening sprint, carrying an unresolved design condition, or
documented beyond its tests — and is marked as such in its docstring.

**Outcome under this rubric: 44 stable, 0 experimental.** Every module
completed its hardening sprint (Phases 1–3), and the five standing
design questions that targeted symbol shapes were all ruled at the 4.1
kickoff (see `DEVELOPMENT_PLAN.md`, Phase 4), so no condition remains
open against any pinned symbol. A zero-experimental outcome is the
expected result of freezing *after* every surface has been hardened
and every dangling question ruled — the rubric exists so the next
surface (Sprint 4.2's additive work) is classified by the same rule,
not by mood.

## Rulings at the walk that shaped the surface

| Question | Ruling | Surface effect |
|---|---|---|
| Positional-only protocol members | Flip | 15 signature pins changed (5 `execute`, 4 `evaluate`, 4 `assess`, 2 `load`); keyword calls at the seams are `TypeError`s; implementation parameter renames are legal |
| ABC extender hooks vs the snapshot | Pin | Abstract members of public ABCs join the snapshot; `FileLoaderBase._parse_content` pinned |
| Named errored entries on `DqReport` | Closed | No change — errored entries stay positionally identified (entries follow `dims` order; a `RuleError` message names its table/column). Revives on real consumer demand |
| Schema rule | Closed | No new validation symbol. Revives with a real consumer, as additive work |
| Pooling and retry jitter | Closed | Connector surface unchanged; `ping()` plus connect-scoped retry remain the operational answer to idle timeouts. Revives with a real concurrent consumer |

## The walk — 44 symbols

### reade.config (8)

| Symbol | Disposition | Note |
|---|---|---|
| `reade.config.ConfigLoaderFactory` | stable | The only place a `FileType` maps to a loader; mapping derives from each loader's own `file_types` declaration |
| `reade.config.JsonLoader` | stable | Format parsing only; suffix guard and error mapping inherited from `FileLoaderBase` |
| `reade.config.YamlLoader` | stable | As `JsonLoader`; owns `.yaml` and `.yml` |
| `reade.config.SqliteConfig` | stable | Flat model mirroring connector parameters; scoped `READE__SQLITE__*` overrides |
| `reade.config.PostgresConfig` | stable | Scoped `READE__POSTGRES__*` overrides |
| `reade.config.MysqlConfig` | stable | Scoped `READE__MYSQL__*` overrides |
| `reade.config.load_config` | stable | Resolve → parse → env overrides → validate; pydantic types stop at this boundary |
| `reade.config.merge_env_overrides` | stable | Raw-string merge; coercion belongs to model validation |

### reade.core.base (2)

| Symbol | Disposition | Note |
|---|---|---|
| `reade.core.base.ConnectionBase` | stable | Lifecycle template; all abstract members pinned, `connection` escape hatch for transactions |
| `reade.core.base.FileLoaderBase` | stable | Template method; the `_parse_content` extender hook is snapshot-pinned as of this walk |

### reade.core.enums (2)

| Symbol | Disposition | Note |
|---|---|---|
| `reade.core.enums.DbType` | stable | Exactly the MVP dialects |
| `reade.core.enums.FileType` | stable | `CSV` retained by design: CSV is data (read via `data_io`), never registered for config |

### reade.core.errors (8)

| Symbol | Disposition | Note |
|---|---|---|
| `reade.core.errors.ReadeError` | stable | Hierarchy root; raw driver exceptions never cross a module boundary |
| `reade.core.errors.ConfigError` | stable | |
| `reade.core.errors.DataIoError` | stable | |
| `reade.core.errors.DbError` | stable | |
| `reade.core.errors.NotConnectedError` | stable | Subclass of `DbError` |
| `reade.core.errors.DqError` | stable | |
| `reade.core.errors.SqlError` | stable | |
| `reade.core.errors.RuleError` | stable | Evaluation failure, never a failed check; the split semantic hinges on this type |

### reade.core.interfaces (2)

| Symbol | Disposition | Note |
|---|---|---|
| `reade.core.interfaces.ConfigLoader` | stable | `load(path, /)` |
| `reade.core.interfaces.ConnectionInterface` | stable | `execute(sql, params=None, /)`; falsy-params normalization is interface contract, binding every implementer |

### reade.core.models (2)

| Symbol | Disposition | Note |
|---|---|---|
| `reade.core.models.DbMetadata` | stable | Field values are data defaults, not API shape |
| `reade.core.models.DB_METADATA_REGISTRY` | stable | Read-only mapping covering every `DbType` |

### reade.data_io (3)

| Symbol | Disposition | Note |
|---|---|---|
| `reade.data_io.execute_query` | stable | Facade over `ConnectionInterface.execute`; accepts protocol-only connectors |
| `reade.data_io.read_csv` | stable | Streams dict rows; ragged rows raise — a DQ toolkit that pads misreports the data it later checks |
| `reade.data_io.write_csv` | stable | Mirrors the reader's strictness |

### reade.db (3)

| Symbol | Disposition | Note |
|---|---|---|
| `reade.db.SqliteConnector` | stable | Autocommit execute; zero-setup backend |
| `reade.db.PostgresConnector` | stable | Autocommit; connect-scoped retry only — statement execution is never retried |
| `reade.db.MysqlConnector` | stable | As Postgres; TLS parameters are Sprint 4.2's additive scope |

### reade.dq (7)

| Symbol | Disposition | Note |
|---|---|---|
| `reade.dq.Dimension` | stable | Assess-only protocol, positional-only; minimal membership keeps later additions additive |
| `reade.dq.DqResult` | stable | |
| `reade.dq.DqReport` | stable | Union entries — errored vs failed is a type distinction, unreadable as each other |
| `reade.dq.VolumeDimension` | stable | |
| `reade.dq.FreshnessDimension` | stable | Propagates `RuleError` on unanswerable measurement; no `now` keyword by design (a later one is additive) |
| `reade.dq.CompletenessDimension` | stable | Plural columns, uniform threshold; degenerate columns raise at construction |
| `reade.dq.check` | stable | Catches `RuleError` only; `SqlError`/`DbError` propagate — caller bugs and dead connections are not data conditions |

### reade.sql (2)

| Symbol | Disposition | Note |
|---|---|---|
| `reade.sql.RenderedQuery` | stable | Bound values never appear in SQL text |
| `reade.sql.render_template` | stable | Data parameters positional-only since Sprint 2.1 — the precedent the protocol flip followed |

### reade.validation (5)

| Symbol | Disposition | Note |
|---|---|---|
| `reade.validation.Rule` | stable | Evaluate-only protocol, positional-only |
| `reade.validation.RuleResult` | stable | `float` fields cover counts and durations (PEP 484 numeric tower); count rules still report exact ints |
| `reade.validation.RowCountRule` | stable | Empty table is `observed=0`, a result |
| `reade.validation.DelayRule` | stable | Client-side UTC measurement; empty table raises — `MAX` over zero rows has no value |
| `reade.validation.NullCountRule` | stable | Empty table is `observed=0`; emptiness is the volume dimension's finding |

## What stable means going forward

- Changing any pinned symbol requires a design-review note in the PR
  and rides with the snapshot regeneration — the freeze is
  machine-enforced, not convention-enforced.
- Additive evolution (new symbols, new keyword-only options) remains
  open and freezes through its own design-review notes; Sprint 4.2's
  additive surface will be recorded that way, and any future release
  gate re-walks only that delta.
- The closed questions above each carry a revival condition; if one
  fires, the work re-files as new, additive scope — nothing reopens
  silently.

## Sprint 4.2 delta — connection ergonomics (2026-08-08)

Recorded per the freeze disposition ruled at the 4.1 kickoff: 4.2's
additive surface freezes through its itemized design-review notes; a
future release gate re-walks only this delta. No symbol joined or left
the pinned surface — the count stays **44**.

| Change | Kind | Freeze record |
|---|---|---|
| `PostgresConnector.__init__` + `PostgresConfig`: keyword-only TLS options `sslmode` / `sslrootcert` / `sslcert` / `sslkey` (libpq vocabulary; unset means omitted from the driver call) | Additive parameters/fields on pinned symbols | PR #51 design-review note |
| `MysqlConnector.__init__` + `MysqlConfig`: keyword-only options `charset` / `ssl_ca` / `ssl_cert` / `ssl_key` / `ssl_verify_cert` / `ssl_verify_identity` (pymysql vocabulary; `ssl_verify_identity` is effective only together with `ssl_ca`) | Additive parameters/fields on pinned symbols | PR #51 design-review note |
| `uri` config-input key on all three models — consumed by pre-validation expansion, never a field; plain schemes only; who/where-vs-options conflict rule; allowlisted query parameters | Additive input contract (no signature change — docstrings, README, and tests carry it, as with env-variable names) | PR #52 design-review note |
| `DB_METADATA_REGISTRY` `uri_scheme` values → plain schemes (`postgresql`, `mysql`, `sqlite`) — the scheme→backend anchor | Data-default change (values, not shape; behavioral for consumers deriving URLs from the registry) | PR #52 design-review note |
| `load_config` validation errors carry field paths and messages only — input values never echoed; the chained `ValidationError` retains them | Behavior fix, message tier | PR #53 design-review note |
| PostgreSQL wire posture → **acceptance-proven, negotiation declared**: conninfo acceptance (all four TLS options parsed by libpq on a green connect) and a required-TLS control proven against the dockerized server; negotiation stays declared on the libpq-environment precedent | Posture amendment (probe-gated ruling; probe held) | PR #53 design-review note |

Option types stay wide by ruling: `sslmode` is `str`, not a `Literal`
(libpq's value set has grown before), and cert paths are `str`, not
`Path` — driver honesty first (the drivers take strings; existence is
a connect-time fact on the connecting host), freeze asymmetry second.
