"""Containment guard: pydantic stays inside config/.

The containment rule recorded in the Sprint 1.1 typed-config PR, as CI
instead of prose: pydantic types appear in config/'s public API only;
connectors and all modules rightward take plain parameters. Any pydantic
import outside config/ fails this test and should fail review.
"""

import re
from pathlib import Path

import reade

_PYDANTIC_IMPORT = re.compile(r"^\s*(?:from|import)\s+pydantic", re.MULTILINE)


def test_pydantic_imports_contained_to_config() -> None:
    package_root = Path(reade.__file__).parent

    offenders = sorted(
        str(path.relative_to(package_root))
        for path in package_root.rglob("*.py")
        if path.relative_to(package_root).parts[0] != "config"
        and _PYDANTIC_IMPORT.search(path.read_text(encoding="utf-8"))
    )

    assert offenders == [], f"pydantic imported outside config/: {offenders}"
