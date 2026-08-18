"""Sprint 4.3 acceptance: the stability table and docs containment config.

The stability table (``docs/stability.md``) is the user-facing
per-symbol view of the freeze record; its rows must mirror the
public-API snapshot mechanically — name-set equality in both
directions, count 44, every disposition ``stable`` — so a dropped,
invented, or destabilized row fails loud instead of drifting in.

The containment asserts pin the verified ``exclude_docs`` pattern in
``mkdocs.yml``: patterns are gitignore-format relative to ``docs_dir``,
so the anchored ``/internal/`` is the form that actually excludes the
internal tree (proven by the build-time leak control recorded in the
docs PR); the committed assert keeps it from regressing to a
plausible-but-inert literal. The MkDocs validation checks that default
to ``info`` are pinned at ``warn`` so the strict build fails on the
link/nav rot classes it exists to catch.

This module never builds the site: the strict build belongs to
``make docs`` and its CI step; ``make check-all``'s gates stay
build-free.
"""

import json
import re
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SNAPSHOT_PATH = _REPO_ROOT / "tests" / "snapshots" / "public_api.json"
_TABLE_PATH = _REPO_ROOT / "docs" / "stability.md"
_MKDOCS_CONFIG_PATH = _REPO_ROOT / "mkdocs.yml"

_PINNED_SYMBOL_COUNT = 44

_SYMBOL_CELL = re.compile(r"^`([\w.]+)`$")


def _table_rows() -> list[tuple[str, str]]:
    """Parse (symbol, disposition) pairs from the stability table.

    The parse contract is fixed: a pipe table, one row per symbol, the
    symbol backticked in column one, the disposition in column three.
    Header and separator rows carry no backticked first cell and are
    skipped by the same rule that admits symbol rows.
    """
    assert _TABLE_PATH.exists(), (
        f"{_TABLE_PATH} is missing — the stability table is the sprint's "
        "acceptance artifact"
    )
    rows: list[tuple[str, str]] = []
    for line in _TABLE_PATH.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        matched = _SYMBOL_CELL.match(cells[0])
        if matched is None:
            continue
        assert len(cells) >= 3, f"symbol row has fewer than 3 columns: {line!r}"
        rows.append((matched.group(1), cells[2]))
    return rows


def _snapshot_names() -> set[str]:
    return set(json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8")))


def test_stability_table_mirrors_snapshot() -> None:
    rows = _table_rows()
    table_names = {symbol for symbol, _ in rows}

    assert len(rows) == len(table_names), "duplicate symbol rows in the table"
    assert len(rows) == _PINNED_SYMBOL_COUNT

    snapshot_names = _snapshot_names()
    missing = snapshot_names - table_names
    invented = table_names - snapshot_names
    assert not missing, f"pinned symbols absent from the table: {sorted(missing)}"
    assert not invented, f"table rows not in the snapshot: {sorted(invented)}"


def test_stability_table_dispositions_all_stable() -> None:
    non_stable = [
        (symbol, disposition)
        for symbol, disposition in _table_rows()
        if disposition != "stable"
    ]
    assert not non_stable, (
        f"non-stable dispositions in the table: {non_stable} — a "
        "disposition change is an API event, not a docs edit"
    )


def _mkdocs_config() -> dict[str, object]:
    assert _MKDOCS_CONFIG_PATH.exists(), (
        f"{_MKDOCS_CONFIG_PATH} is missing — the docs build config carries "
        "the internal-containment control"
    )
    loaded = yaml.safe_load(_MKDOCS_CONFIG_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_mkdocs_excludes_internal_tree() -> None:
    exclude = _mkdocs_config().get("exclude_docs")
    assert isinstance(exclude, str), "mkdocs.yml carries no exclude_docs block"
    patterns = [line.strip() for line in exclude.splitlines() if line.strip()]
    assert "/internal/" in patterns, (
        f"exclude_docs patterns {patterns} lack the anchored '/internal/' — "
        "patterns are relative to docs_dir, so other spellings of the "
        "internal path exclude nothing"
    )


def test_mkdocs_validation_levels_are_warn() -> None:
    validation = _mkdocs_config().get("validation")
    assert isinstance(validation, dict), "mkdocs.yml carries no validation block"
    nav = validation.get("nav")
    links = validation.get("links")
    assert isinstance(nav, dict)
    assert isinstance(links, dict)
    expected_warn = {
        ("nav", "omitted_files"): nav.get("omitted_files"),
        ("nav", "absolute_links"): nav.get("absolute_links"),
        ("links", "anchors"): links.get("anchors"),
        ("links", "absolute_links"): links.get("absolute_links"),
        ("links", "unrecognized_links"): links.get("unrecognized_links"),
    }
    not_warn = {key: level for key, level in expected_warn.items() if level != "warn"}
    assert not not_warn, (
        f"validation checks not at warn: {not_warn} — these default to "
        "info, and --strict only fails on warnings"
    )
