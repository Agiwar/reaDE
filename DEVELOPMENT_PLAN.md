# reaDE — Development Plan

> Data Engineering SDK with built-in Data Quality.
> Strategy: **walking skeleton** — scaffold the entire dependency chain with minimal
> implementations first, then deepen each module in release-gated sprints.

---

## 1. Three loops

| Loop | When it runs | Steps |
|---|---|---|
| **Design loop** | Once, at the start (Phase 0) | Purpose & scope → API contract → architecture spike → design review |
| **Sprint loop** | Every sprint | Implement → test → code review → optimize |
| **Release loop** | End of every phase | Docs → version bump → tag → collect feedback; publishing starts at Phase 4 (Phase 1 gate amendment) |

Rule: a sprint is **done** only when its definition of done (DoD) passes.
A phase is **done** only when its release tag exists.

---

## 2. Dependency chain

```
config → db → sql → data_io → validation → dq
            (core/ underpins everything)
```

---

## 3. Phases and sprints

### Phase 0 — Skeleton (the "working pool")

Goal: entire chain importable and runnable end-to-end with minimal happy-path code.
Public API surface is drafted here and treated as frozen afterward
(changes after this require a design-review note in the PR).

**Sprint 0.1 — Core & tooling**
- `core/`: interfaces (Protocols), enums, errors, models
- Tooling: `pyproject.toml`, `uv`, `ruff`, `mypy` (strict), `pytest`,
  `bandit`, `pre-commit`, GitHub Actions CI
- `ARCHITECTURE.md` and the public plan committed; internal process notes
  stay untracked
- DoD: CI green; `import reade` works; every public interface has a
  Google-style docstring

**Sprint 0.2 — Thin implementations across the whole chain**

Re-lands parked code from the `archive/pre-skeleton` branch. The `core/base`
ABCs return only after design review; `ConnectionBase.connection` swaps
`ValueError` for `NotConnectedError` at re-land.

- `config`: YAML only, returns parsed `dict` (typed config objects are
  Sprint 1.1)
- `db`: SQLite connector only (zero-setup): connect, close, ping — ping is
  accepted scope creep; rationale recorded in PR #3's design notes
- `sql`: render one Jinja2 template
- `data_io`: execute one query, return rows
- `validation`: one rule (row count)
- `dq`: one dimension (volume), built on validation
- `examples/end_to_end.py` runs the full chain against SQLite
- DoD: example runs clean; contract tests pass for every interface and
  assert `close()` idempotency and the two-tier `ConfigLoader` error
  contract

**Gate → tag `v0.1.0a1` (alpha).** From this point, every phase ends in a
usable release — this closes the "everything 30%, nothing shippable" risk.

---

### Phase 1 — config + db hardening → `v0.1.0`

**Sprint 1.1 — config**
- JSON / YAML loaders, auto-locate, env-var overrides
- Typed config objects (decide: pydantic vs. stdlib dataclasses — record the
  decision and rationale in the PR)
- DoD: ≥90% coverage on module; README section; example

**Sprint 1.2 — db**
- Connection lifecycle, health check, retry policy (connect-scoped:
  bounded attempts, doubling backoff, per-attempt timeout; statement
  execution is never retried — auto-retrying writes is a correctness
  hazard)
- Pooling: deferred by amendment. Nothing in the golden path holds
  concurrent connections (batch DQ jobs use one), and the idle-timeout
  failure mode that pools-with-pre-ping address is covered by `ping()`
  plus connect retry. Revisit at the Phase 4 API-freeze walk if a
  concurrent consumer appears.
- Second and third connectors prove the plug-in interface: **PostgreSQL and
  MySQL** (core MVP DBs; ClickHouse/Snowflake/Oracle are out of MVP scope;
  Trino is optional and may be deferred to Phase 4)
- DoD: same as 1.1 + integration tests against dockerized PostgreSQL and MySQL

**Gate → tag `v0.1.0` (cut at PR #21, 2026-07-06).** TestPyPI/PyPI publish deferred by amendment to
Phase 4: publishing pre-freeze burns immutable version numbers for no
consumer benefit, and the tag keeps the phase installable via
`git+https://…@v0.1.0`. First publish is `v1.0.0rc1`. Accepted risk: the
`reade` name on PyPI stays unclaimed until then.

---

### Phase 2 — sql + data_io → `v0.2.0`

**Sprint 2.1 — sql**
- Render contract: `render_template` is rebuilt around
  `RenderedQuery(sql, params)` — values never appear in SQL text. A
  `bind` filter registers each value in `params` and emits the dialect's
  PEP 249 placeholder at render time (pyformat `%(name)s` for
  PostgreSQL/MySQL, named `:name` for SQLite). No post-render placeholder
  translation — naive `:name` rewriting breaks on PostgreSQL `::type`
  casts.
- Identifier safety: `ident` filter — allowlist
  `^[A-Za-z_][A-Za-z0-9_]*$` (optional schema part) plus per-dialect
  quoting (PostgreSQL/SQLite `"..."`, MySQL backticks). Dialect is the
  existing `DbType` enum from `core.enums`; `sql` imports nothing from
  `db`.
- Jinja2 environment: `StrictUndefined`; templates load from the packaged
  directory plus caller-configured directories, nothing else — this is
  the discovery convention. Documented trust model: templates are code,
  context is data.
- `RenderedQuery` is a frozen stdlib dataclass (pydantic stays contained
  to `config`).
- Scope fence: executing bound params through the SDK is 2.2 scope — the
  `execute` params seam is designed with `data_io`, its consumer. The one
  shipped template consumer (validation's count rule) needs identifier
  safety only. Also out: sandboxed/untrusted templates, dynamic ORDER BY
  helpers, dialects beyond the MVP three.
- Breaking change: `render_template`'s Phase-0 signature and return type
  change — design-review note required in the PR.
- DoD: 1.1 baseline (≥90% coverage gate on the module in CI, README
  section, example) + injection tests: hostile value
  `1; DROP TABLE fact_orders;--` appears only in `params`, never in SQL
  text; hostile identifiers `fact_orders; DROP TABLE fact_orders` and
  `fact_orders"--` raise; the README "unsanitized `{{ table }}`" alpha
  caveat is removed by the PR that ships `ident` (the general pre-alpha
  and not-yet-published notes stay until their own milestones).

**Sprint T1 — verification-loop tooling (chore)**

Lands before Sprint 2.2 so data_io is built inside the loop.
Adds no v0.2.0 feature scope.

- CLAUDE.md hardening: replace the discretionary check-running line with a
  completion contract; add TDD and hook-safety clauses (see PR diff)
- Public-API snapshot test (pays down the `inspect.signature` IOU):
  `tests/unit/test_public_api.py` pins the public surface — the
  `__all__` names of every feature package and core subpackage
  (structurally discovered; a public package missing `__all__` fails
  the test; the root namespaces are asserted publicly empty) — and
  compares against `tests/snapshots/public_api.json`. Functions pin as
  signature strings; classes pin as their body-defined members plus
  annotations, so a member joining a Protocol or ABC trips the pin,
  not only a top-level signature change. Failure message must state:
  an API contract change requires a design-review note in the PR.
  - Known interaction: Sprint 2.2's pre-registered contract breaks
    (`params` on `execute()`, `db_type` joining `ConnectionInterface`,
    the protocol retype of the consumer seams) will turn this test red
    on purpose. Updating the snapshot inside that PR, with the
    design-review note, is the mechanism working — not a defect.
    [2026-07-19, 2.2 kickoff amendment: the bundle is now FOUR
    breaks — Sprint 2.2's entry is the authoritative list.]
- Layered-import contract: import-linter as a dev dependency; `layers`
  contract encoding `dq → validation → data_io → sql → db → config → core`;
  wired into pre-commit and `make check-all`
- Coverage gate: `--cov-fail-under=90` on the coverage target;
  `check-all` runs the gated target (plain `pytest` stays fast)
- Claude Code mechanisms: `.claude/settings.json` PostToolUse hook
  (ruff + mypy after Edit|Write); `.claude/commands/sprint-start.md`
  and `sprint-close.md`
- Out of scope → IOU: Stop-hook enforcement (revisit after two sprints of
  stable signals); per-module coverage gating (global 90 floor for now)
- DoD:
  - `make check-all` green, including `lint-imports` and the coverage gate
  - Red-light proofs captured in the execution report, each then reverted:
    (1) two captures — a scratch edit to one top-level public signature,
        and a scratch member added to a protocol — snapshot test fails
        with the intended message in both
    (2) scratch wrong-direction import (e.g., `config` imports `db`) →
        `lint-imports` fails
    (3) a coverage floor above the measured total → coverage gate fails
        (pytest-cov rejects floors over 100 as a usage error, so the
        proof uses e.g. `--cov-fail-under=99` against 98% coverage)
  - Human-verified in a fresh session: PostToolUse hook fires on an edit;
    `/sprint-start` reproduces the session-start ritual
  - Single PR (`chore:` prefix), squash merge; no new runtime dependencies

**Sprint 2.2 — data_io**
- Execute query / read / write. Results decision (2.2 kickoff):
  database results stay materialized (`list[tuple]`) — the DQ golden
  path returns counts and aggregates, and query results are bounded by
  query semantics; files are not, so the CSV reader streams (it yields
  rows; `list()` materializes).
- Breaking changes (pre-registered at the 2.1 spec and its kickoff
  consults, completed to four at the 2.2 kickoff; post-Phase-0 contract
  changes — one design-review note covers the bundle, itemizing each
  break, due in the implementing PR):
  - `ConnectionInterface` gains `execute` — full signature
    `execute(self, sql: str, params: dict[str, Any] | None = None) ->
    list[tuple[Any, ...]]` — and `ConnectionBase` plus the three
    connectors adopt the identical signature, so `RenderedQuery`
    executes through the SDK. Falsy `params` normalize to `None` at
    the connector before reaching the driver (pyformat drivers
    %-format the statement whenever parameters are present, which
    would corrupt a literal `%`); the interface docstring states that
    promise, so it binds every implementer, not just the shipped
    connectors.
  - `db_type` joins `ConnectionInterface` as a read-only property
    member — the bundle's second break. The ABC `ClassVar` shipped in
    Sprint 2.1; this formalizes it for protocol-only connectors.
  - `execute_query` / `RowCountRule.evaluate` / `VolumeDimension.assess`
    retype from `ConnectionBase[Any]` to the `ConnectionInterface`
    protocol — today a protocol-only connector cannot be passed at
    these seams, contradicting the third-party plug-in promise.
    `execute_query` becomes `(connector, sql, params=None)`; rendered
    queries execute as `execute_query(connector, rendered.sql,
    rendered.params)`.
  - Fourth break (added by this kickoff amendment):
    `merge_env_overrides` drops its import-time `environ=os.environ`
    default for a call-time `None` sentinel, and `environ` becomes
    keyword-only — restoring consistency with `load_config`, which has
    resolved the environment at call time since Sprint 1.1.
  - Declared docstring-only rider (docstrings are not pinned):
    `RenderedQuery`'s "pass `None`, not `{}`" caller guidance is
    superseded by the connector-level normalization above; the bundle
    PR updates that docstring.
- Consistent error mapping into `core.errors`
- CSV reader and writer (relocated from config — CSV is data, not
  config; see PR #7's design notes): `read_csv` / `write_csv`. Rows
  are dicts keyed by header; values stay raw strings (coercion is the
  validation layer's job); ragged rows raise. Parse and shape failures
  map to `DataIoError`; `OSError` passes through unchanged (the
  config-layer precedent).
- DoD: 1.1 baseline (≥90% coverage gate on the module in CI, README
  section, example) + `make check-all` green at every completion claim
  (the standing completion contract) + the bundle's single itemized
  design-review note with the public-API snapshot updated in the same
  PR + injection test through the full path (a hostile value bound via
  `bind` executes via `execute_query` and lands in the data, never in
  the SQL text — asserted on all three dialects: SQLite locally, both
  servers dockerized) + a
  literal-`%` regression with empty params asserted on both dockerized
  pyformat backends (SQLite is exempt: its named placeholder style
  never %-formats) + bound-param INSERT durability cross-backend
  (insert → close → reopen → count) + CSV error-contract tests
  including `FileNotFoundError` passthrough + the README "arrives with
  the 2.2 seam" caveats removed by the PRs that ship the seam.

**Gate → tag `v0.2.0`.**

---

### Phase 3 — validation + dq → `v0.3.0`

**Sprint 3.1 — validation**
- Rule set (reconciled at the 3.1 kickoff, resolving the drafted
  list's own divergence note): the shipped count rule is joined by
  `DelayRule` and `NullCountRule`, plus the custom-rule plug-in
  point. The schema rule is deferred — no Sprint 3.2 dimension
  consumes it (volume/freshness/completeness compose the
  count/delay/null-count rules), and its per-dialect introspection is
  the sprint's heaviest surface; it returns with a consumer (3.2 or
  the Phase 4 walk). [2026-08-03, 3.2 kickoff: weighed per the
  condition — no 3.2 dimension consumes it; consumer still absent,
  so it stays deferred to the Phase 4 walk.] Of the parked taxonomy,
  `null` is adopted;
  `agg` stays out (no plan line, no dimension consumer).
- Plug-in point: a `Rule` protocol exported from `reade.validation` —
  not `core.interfaces`: its return type `RuleResult` is validation
  vocabulary, and core imports from no feature module — with exactly
  one member, `evaluate(self, connector: ConnectionInterface) ->
  RuleResult`. Minimal membership is the reversible choice: protocol
  members are snapshot-pinned, so a member added later is additive
  while one removed is a break.
- `DelayRule` (data-freshness delay, named for what it measures):
  client-side measurement — one dialect-neutral max-timestamp
  template; the delay is computed in Python against the client clock
  in UTC. Naive database timestamps are assumed UTC; aware values are
  normalized to UTC — the docstring states the stance as contract. An
  empty table raises `RuleError` (unanswerable is not stale). "Now"
  is injectable as a constructor keyword for testability.
- `NullCountRule`: null count in a column against a threshold — named
  for what it measures, mirroring `RowCountRule`.
- Breaking change (pre-registered in PR #5's design notes; the
  itemized design-review note and snapshot regen ride the
  implementing PR): `RuleResult.observed` and `RuleResult.threshold`
  retype from `int` to `float`. Per PEP 484's numeric tower, `int`
  stays valid at every call site and runtime values pass through
  untouched — count rules keep reporting exact ints; the annotation
  now covers durations honestly.
- DoD: 1.1 baseline (≥90% coverage gate on the module in CI, README
  section, example) + `make check-all` green at every completion
  claim (the standing completion contract) + the RuleResult break's
  itemized design-review note with the public-API snapshot updated in
  the same PR + contract tests proving the plug-in point (a static
  conformance proof per shipped rule and a protocol-only custom rule
  evaluated through the public seam) + results-not-raises asserted
  per rule (a failed check is `passed=False`, never a raise;
  evaluation failures raise `RuleError`; `DelayRule` on an empty
  table raises, asserted) + `DelayRule` asserted cross-backend
  (SQLite locally, both servers dockerized — where timestamp values
  arrive as `datetime`, not `str`) + hostile identifiers raise
  through both new packaged templates, asserted per dialect + the
  acceptance example runs red before the contract branch and green
  at close.

**Sprint 3.2 — dq**
- Dimensions (composed from the three rules shipped in 3.1 — no new
  validation rules): volume (shipped thin in Phase 0; its composition
  retypes to the `Rule` protocol internally, no public change),
  freshness over the delay rule, completeness over the null-count
  rule. `CompletenessDimension` takes `columns: Sequence[str]` — one
  null-count rule per column under a uniform threshold — because
  completeness is a plural question: one dimension answers it and
  `DqResult.rule_results` aggregates a genuinely multi-rule outcome;
  per-column tuning is another instance. Choosing the plural
  constructor now avoids a breaking change later.
- Plug-in point one layer up (added at the 3.2 kickoff, closing a
  gap the kickoff review caught): a `Dimension` protocol exported
  from `reade.dq` — `assess(self, connector: ConnectionInterface) ->
  DqResult`, assess-only membership, the validation `Rule` protocol's
  design applied at the dq seam (dq-local because `DqResult` is dq
  vocabulary; minimal membership is the reversible choice). Shipped
  dimensions compose their rules internally — the opinionated pairing
  is the value, so there is no rule-injection constructor; extension
  happens by writing a custom dimension, and `check` types its
  dimensions against the protocol.
- One opinionated golden path (signature amended at the 3.2 kickoff):
  `reade.dq.check(connector, dims=[...]) -> DqReport` — constructed
  dimension instances through the seam, consistent with every shipped
  seam. The drafted `table` parameter is dropped as redundant: each
  dimension carries its own table, and instance lists give
  cross-table reports for free.
- `RuleError` semantics (resolving the note reserved at the 3.1
  kickoff): SPLIT across the layers. Dimensions propagate
  `RuleError` — an unanswerable measurement is not a failed check;
  reporting it as `passed=False` would lie at the layer consumers
  filter on. `check` catches `RuleError` per dimension and reports
  errored vs failed distinctly in a new `DqReport` type: overall
  `passed` only if every dimension measured and passed; an errored
  dimension carries its error. Lower-layer errors (`DbError`,
  `NotConnectedError`) propagate out of `check` — a dead connection
  aborts the report rather than becoming a per-dimension verdict.
- Additive only: `Dimension`, `DqReport`, `FreshnessDimension`,
  `CompletenessDimension`, and `check` join `reade.dq`; the
  `DqResult` and `VolumeDimension` surfaces are unchanged.
- DoD: 1.1 baseline (≥90% coverage gate on the module in CI, README
  section, example) + `make check-all` green at every completion
  claim (the standing completion contract) + each additive symbol
  carries an itemized design-review note with the public-API
  snapshot updated in the same PR, and the `DqResult` /
  `VolumeDimension` pins stay byte-identical + contract tests prove
  the plug-in point (a static conformance proof per shipped
  dimension and a protocol-only custom dimension evaluated through
  `check`), with each shipped dimension's rule composition proven in
  its own branch's tests + the split semantic asserted per layer
  (freshness over an empty table propagates `RuleError`; volume and
  completeness report results there; `check` distinguishes errored
  from failed in one report, with overall `passed` asserted in both
  directions) + declared wire posture: dimensions add composition,
  not SQL — no new driver divergence to assert, declared in the PRs
  rather than silently absent + the acceptance example runs red
  before the contract branch and green at close.

**Gate → tag `v0.3.0`.**

---

### Phase 4 — Release readiness → `v1.0.0rc1` → `v1.0.0`

- API freeze review: walk every public symbol, mark experimental ones
- Optional-scope decision point: add Trino connector here if still wanted
- Connection ergonomics review (moved here at the 2.2 kickoff; the
  Phase 1 publish deferral moved broad adoption to Phase 4): URI-style
  connection strings as a config input, TLS/charset connection
  options, password-in-URI documentation — designed together, additive
- Docs: full README, API reference, 3+ examples
- Performance benchmark on hot paths (config load, query execute)
- `v1.0.0rc1` on PyPI → soak period → `v1.0.0`

---

## 4. Scope guard (non-goals)

- Not an orchestrator (Prefect/Airflow/Dagster exist).
- Not a heavyweight DQ framework (Great Expectations exists).
- Small, sharp, opinionated helpers for the 95% boring work:
  config, connections, sanity checks.
