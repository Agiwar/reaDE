"""Containment guards: pydantic stays inside config/, sql stays off db.

The containment rule recorded in the Sprint 1.1 typed-config PR, as CI
instead of prose: pydantic types appear in config/'s public API only;
connectors and all modules rightward take plain parameters. Two guards
cover the direct and indirect leaks: importing pydantic itself, and
importing config's pydantic model classes (which would put a pydantic
type in a signature without ever importing pydantic).

A third guard pins the Sprint 2.1 dependency edge: sql imports nothing
from db (dialect arrives as ``core.enums.DbType``) nor from any module
to its right in the chain.
"""

import re
from pathlib import Path

from pydantic import BaseModel

import reade
from reade.config import models as config_models

_PYDANTIC_IMPORT = re.compile(r"^\s*(?:from|import)\s+pydantic", re.MULTILINE)

_MODEL_NAMES = sorted(
    name
    for name, obj in vars(config_models).items()
    if isinstance(obj, type) and issubclass(obj, BaseModel) and obj is not BaseModel
)


def _offenders(pattern: re.Pattern[str]) -> list[str]:
    package_root = Path(reade.__file__).parent
    return sorted(
        str(path.relative_to(package_root))
        for path in package_root.rglob("*.py")
        if path.relative_to(package_root).parts[0] != "config"
        and pattern.search(path.read_text(encoding="utf-8"))
    )


def test_pydantic_imports_contained_to_config() -> None:
    offenders = _offenders(_PYDANTIC_IMPORT)

    assert offenders == [], f"pydantic imported outside config/: {offenders}"


_SQL_FORBIDDEN_IMPORT = re.compile(
    r"^\s*(?:from|import)\s+reade\.(?:db|data_io|validation|dq)\b", re.MULTILINE
)


def test_sql_imports_nothing_from_db_or_rightward_modules() -> None:
    package_root = Path(reade.__file__).parent
    offenders = sorted(
        str(path.relative_to(package_root))
        for path in (package_root / "sql").rglob("*.py")
        if _SQL_FORBIDDEN_IMPORT.search(path.read_text(encoding="utf-8"))
    )

    assert offenders == [], f"sql/ imports db or rightward modules: {offenders}"


def test_config_model_types_not_imported_outside_config() -> None:
    assert _MODEL_NAMES, "no config models found — guard would be vacuous"
    names = "|".join(_MODEL_NAMES)
    pattern = re.compile(
        rf"^\s*from\s+reade\.config[.\w]*\s+import\s+[^\n]*\b(?:{names})\b"
        rf"|^\s*import\s+reade\.config\.models\b",
        re.MULTILINE,
    )

    offenders = _offenders(pattern)

    assert offenders == [], f"config models imported outside config/: {offenders}"
