"""Typed configuration: file + env override → validated object → connector.

Sprint 1.1 acceptance script. Loads a YAML config through the typed layer
(``load_config``), demonstrates a deploy-time env-var override
(``READE__DATABASE``), shows that a typo'd override fails loudly, and hands
plain parameters to the connector — pydantic stops at config/'s boundary.

Run with: uv run python examples/config_typed.py
"""

import os
from pathlib import Path

from reade.config import SqliteConfig, load_config
from reade.core.errors import ConfigError
from reade.db import SqliteConnector


def main() -> None:
    """Run the typed-config flow and exit non-zero on failure."""
    config_dir = Path(__file__).parent / "config"

    # File value only: database comes from sqlite.yaml.
    config = load_config("sqlite.yaml", model=SqliteConfig, search_paths=(config_dir,))
    print(f"[typed]    file value: database={config.database!r}")

    # Deploy-time override: READE__DATABASE replaces the file value.
    # (Set here so the demo is self-contained; normally exported in the shell.)
    os.environ["READE__DATABASE"] = ":memory:"
    try:
        config = load_config(
            "sqlite.yaml", model=SqliteConfig, search_paths=(config_dir,)
        )
    finally:
        del os.environ["READE__DATABASE"]
    print(f"[override] env value:  database={config.database!r}")

    # A typo'd override is an unknown field: rejected with a field path,
    # never silently ignored.
    os.environ["READE__DATABSE"] = "oops"
    try:
        load_config("sqlite.yaml", model=SqliteConfig, search_paths=(config_dir,))
    except ConfigError as e:
        print(f"[validate] typo'd override rejected: {type(e).__name__}: {e}")
    else:
        raise SystemExit("typo'd env override was silently accepted")
    finally:
        del os.environ["READE__DATABSE"]

    # Past config/'s boundary the connector takes plain parameters.
    with SqliteConnector(database=config.database) as connector:
        print(f"[db]       connected={connector.is_connected()}", end=" ")
        print(f"ping={connector.ping()}")

    print("typed config chain OK")


if __name__ == "__main__":
    main()
