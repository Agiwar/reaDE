"""Connection ergonomics: TLS/charset options and URI-style config input.

Sprint 4.2 acceptance script. Demonstrates the additive connection
surface: per-driver TLS/charset options on the server connectors,
mirrored as config fields (with scoped env overrides), and one
``DATABASE_URL``-style string arriving through the typed config layer —
who-and-where from the URI, options composing beside it — for all three
backends.

Server-free by design: the config layer and constructor surface are what
this script demonstrates, and the SQLite leg runs a real query. The wire
behavior of the TLS options is asserted by the integration suite.

Run with: uv run python examples/connection_ergonomics.py
"""

import os
import tempfile
from pathlib import Path
from urllib.parse import unquote

from reade.config import MysqlConfig, PostgresConfig, SqliteConfig, load_config
from reade.core.errors import ConfigError
from reade.db import MysqlConnector, PostgresConnector, SqliteConnector


def _connection_options_leg(config_dir: Path) -> None:
    """TLS/charset options: per-driver names, config-mirrored."""
    # Option names are each driver's own vocabulary; an unset option is
    # omitted from the driver call, so driver defaults apply.
    (config_dir / "postgres.yaml").write_text(
        "host: db.internal\n"
        "database: app\n"
        "user: app\n"
        "password: your_password_here\n"  # pragma: allowlist secret
        'sslmode: "verify-full"\n'
        "sslrootcert: /etc/ssl/certs/company-ca.pem\n",
        encoding="utf-8",
    )
    pg_config = load_config(
        "postgres.yaml", model=PostgresConfig, search_paths=(config_dir,)
    )
    print(f"[options]  postgres file config: sslmode={pg_config.sslmode!r}")

    # Scoped env overrides reach the new fields like any other field.
    os.environ["READE__MYSQL__CHARSET"] = "utf8mb4"
    try:
        (config_dir / "mysql.yaml").write_text(
            "host: db.internal\n"
            "database: app\n"
            "user: app\n"
            "password: your_password_here\n"  # pragma: allowlist secret
            "ssl_ca: /etc/ssl/certs/company-ca.pem\n"
            "ssl_verify_cert: true\n",
            encoding="utf-8",
        )
        my_config = load_config(
            "mysql.yaml", model=MysqlConfig, search_paths=(config_dir,)
        )
    finally:
        del os.environ["READE__MYSQL__CHARSET"]
    print(
        f"[options]  mysql env override: charset={my_config.charset!r} "
        f"ssl_verify_cert={my_config.ssl_verify_cert}"
    )
    if pg_config.sslmode != "verify-full" or my_config.charset != "utf8mb4":
        raise SystemExit("connection options did not reach the config layer")

    # Past config/'s boundary the connectors take the same names.
    PostgresConnector(
        host=pg_config.host,
        database=pg_config.database,
        user=pg_config.user,
        password=pg_config.password,
        sslmode=pg_config.sslmode,
        sslrootcert=pg_config.sslrootcert,
    )
    MysqlConnector(
        host=my_config.host,
        database=my_config.database,
        user=my_config.user,
        password=my_config.password,
        charset=my_config.charset,
        ssl_ca=my_config.ssl_ca,
        ssl_verify_cert=my_config.ssl_verify_cert,
    )
    print("[options]  both connectors accept the mirrored option names")


def _uri_leg(config_dir: Path) -> None:
    """URI input: one ``DATABASE_URL``-style string, three backends."""
    # A URI encodes who and where; options compose beside it. The
    # password percent-decodes, and the allowlisted query parameter
    # lands in its option field.
    uri = (
        "postgresql://app:s%40fe@db.internal:6432"  # pragma: allowlist secret
        "/analytics?sslmode=require"
    )
    os.environ["READE__POSTGRES__URI"] = uri
    try:
        (config_dir / "empty.yaml").write_text("{}\n", encoding="utf-8")
        uri_config = load_config(
            "empty.yaml", model=PostgresConfig, search_paths=(config_dir,)
        )
    finally:
        del os.environ["READE__POSTGRES__URI"]
    print(
        f"[uri]      env DATABASE_URL expanded: host={uri_config.host!r} "
        f"port={uri_config.port} database={uri_config.database!r}"
    )
    if uri_config.password != unquote("s%40fe") or uri_config.sslmode != "require":
        raise SystemExit("URI expansion lost a component")
    # The parsed password never surfaces in the model's repr.
    if unquote("s%40fe") in repr(uri_config) or "s%40fe" in repr(uri_config):
        raise SystemExit("password leaked through the config repr")
    print(f"[uri]      masked repr: {uri_config!r}")

    # Conflict rule: a URI carries who-and-where, so a URI plus an
    # explicit who/where field is a contradiction and fails loud.
    # (Typed callers pass uri in the input mapping — the synthesized
    # constructor signature knows only real fields.)
    try:
        PostgresConfig.model_validate({"uri": uri, "host": "db.internal"})
    except ConfigError as e:
        print(f"[conflict] uri + host rejected: {type(e).__name__}: {e}")
    else:
        raise SystemExit("uri + URI-encoded field was silently accepted")

    # Driver-qualified schemes belong to ORM dialect strings, not
    # connection URIs; plain schemes only, rejected with guidance.
    try:
        SqliteConfig.model_validate({"uri": "sqlite+pysqlite:///local.db"})
    except ConfigError as e:
        print(f"[scheme]   +driver form rejected: {type(e).__name__}: {e}")
    else:
        raise SystemExit("driver-qualified scheme was silently accepted")

    # SQLite leg, live: URI → config → connector → real query.
    db_path = config_dir / "local.db"
    sqlite_config = SqliteConfig.model_validate({"uri": f"sqlite:///{db_path}"})
    with SqliteConnector(database=sqlite_config.database) as connector:
        rows = connector.execute("SELECT 1")
    print(f"[sqlite]   sqlite:///… executed: SELECT 1 -> {rows}")
    if rows != [(1,)]:
        raise SystemExit("sqlite URI leg failed")


def main() -> None:
    """Run the connection-ergonomics flow and exit non-zero on failure."""
    with tempfile.TemporaryDirectory() as tmp:
        config_dir = Path(tmp)
        _connection_options_leg(config_dir)
        _uri_leg(config_dir)

    print("connection ergonomics OK")


if __name__ == "__main__":
    main()
