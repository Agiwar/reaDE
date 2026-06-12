"""Server-backed db chain: scoped config → validated object → PostgreSQL.

Sprint 1.2 acceptance script. Loads a PostgreSQL config through the typed
layer, demonstrates the per-model override namespace (``READE__POSTGRES__*``
applies, out-of-prefix variables are ignored, in-prefix typos fail loudly),
and runs the full connector lifecycle — connect, ping, execute, close —
against a real server, including the empty-list contract for statements
without result sets.

Requires a reachable PostgreSQL matching ``examples/config/postgres.yaml``
(CI provides a service container; locally: the compose file under
``tests/integration/``).

Run with: uv run python examples/db_typed.py
"""

import os
from pathlib import Path

from reade.config import PostgresConfig, load_config
from reade.core.errors import ConfigError
from reade.db import PostgresConnector


def main() -> None:
    """Run the typed db flow and exit non-zero on failure."""
    config_dir = Path(__file__).parent / "config"

    # File values only: everything comes from postgres.yaml.
    config = load_config(
        "postgres.yaml", model=PostgresConfig, search_paths=(config_dir,)
    )
    print(f"[typed]     file values: host={config.host!r} port={config.port}")

    # Scoped override: READE__POSTGRES__PORT targets PostgresConfig only.
    # A bare READE__DATABASE (no namespace) is out of every prefix and
    # ignored — the namespace collision 1.1 deferred, solved by construction.
    os.environ["READE__POSTGRES__PORT"] = "5432"
    os.environ["READE__DATABASE"] = "stray-from-another-model"
    try:
        config = load_config(
            "postgres.yaml", model=PostgresConfig, search_paths=(config_dir,)
        )
    finally:
        del os.environ["READE__POSTGRES__PORT"]
        del os.environ["READE__DATABASE"]
    print(f"[override]  scoped env applied: port={config.port}")

    # Typo-loudness survives inside the namespace: an unknown field within
    # READE__POSTGRES__* is rejected with a field path, never ignored.
    os.environ["READE__POSTGRES__HOSTT"] = "oops"
    try:
        load_config("postgres.yaml", model=PostgresConfig, search_paths=(config_dir,))
    except ConfigError as e:
        print(f"[validate]  in-prefix typo rejected: {type(e).__name__}: {e}")
    else:
        raise SystemExit("typo'd scoped override was silently accepted")
    finally:
        del os.environ["READE__POSTGRES__HOSTT"]

    # Past config/'s boundary the connector takes plain parameters.
    with PostgresConnector(
        host=config.host,
        port=config.port,
        database=config.database,
        user=config.user,
        password=config.password,
    ) as connector:
        print(f"[db]        connected={connector.is_connected()}", end=" ")
        print(f"ping={connector.ping()}")

        # The frozen execute contract, against a real server: result rows
        # materialize as tuples; statements without a result set return [].
        rows = connector.execute("SELECT 1")
        print(f"[execute]   SELECT 1 -> {rows}")
        ddl = connector.execute("CREATE TEMP TABLE reade_accept (id integer)")
        print(f"[execute]   DDL (no result set) -> {ddl!r}")
        if rows != [(1,)] or ddl != []:
            raise SystemExit("execute() contract violated")

    print("typed db chain OK")


if __name__ == "__main__":
    main()
