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
- Execute query / read / write; streaming vs. materialized results
- Breaking changes (pre-registered at the 2.1 spec and its kickoff
  consults; post-Phase-0 contract changes — one design-review note
  covers the bundle, itemizing each break, due in the implementing PR):
  - `execute()` on `ConnectionInterface`/`ConnectionBase` gains a
    `params` argument so `RenderedQuery` executes through the SDK
  - `db_type` joins `ConnectionInterface`, riding the same break — the
    ABC `ClassVar` shipped in Sprint 2.1; this formalizes it for
    protocol-only connectors
  - `execute_query` / `RowCountRule.evaluate` / `VolumeDimension.assess`
    retype from `ConnectionBase[Any]` to the `ConnectionInterface`
    protocol — today a protocol-only connector cannot be passed at
    these seams, contradicting the third-party plug-in promise
- Consistent error mapping into `core.errors`
- CSV reader (relocated from config — CSV is data, not config; see PR #7's
  design notes)

**Gate → tag `v0.2.0`.**

---

### Phase 3 — validation + dq → `v0.3.0`

**Sprint 3.1 — validation**
- Rules: count, delay, schema, custom-rule plug-in point
- Note: the parked rule set (`agg`, `null`) diverges from this list
  (`schema`); reconcile at the re-land design review

**Sprint 3.2 — dq**
- Dimensions: volume, freshness, completeness (composed from validation rules)
- One opinionated golden path: `reade.dq.check(table, dims=[...])`

**Gate → tag `v0.3.0`.**

---

### Phase 4 — Release readiness → `v1.0.0rc1` → `v1.0.0`

- API freeze review: walk every public symbol, mark experimental ones
- Optional-scope decision point: add Trino connector here if still wanted
- Docs: full README, API reference, 3+ examples
- Performance benchmark on hot paths (config load, query execute)
- `v1.0.0rc1` on PyPI → soak period → `v1.0.0`

---

## 4. Scope guard (non-goals)

- Not an orchestrator (Prefect/Airflow/Dagster exist).
- Not a heavyweight DQ framework (Great Expectations exists).
- Small, sharp, opinionated helpers for the 95% boring work:
  config, connections, sanity checks.
