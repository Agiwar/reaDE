"""URI-style connection-string expansion for the typed config models.

A ``uri`` key in a model's input — from a config file, an env override,
or direct construction — expands before validation into the
who-and-where fields a URI encodes (host, port, user, password,
database) plus allowlisted option query parameters. The key is
consumed: models never retain the URI string, so the composite secret
cannot leak through reprs, dumps, or validation-error echoes, and
expansion errors name components and keys, never values.

Placement note (per the standing placement rule): the expansion speaks
only neutral vocabulary — stdlib plus core types — but config/ is its
sole consumer, so it lives here; core placement would be legal but
unnecessary.
"""

from typing import Any, Final
from urllib.parse import SplitResult, parse_qsl, unquote, urlsplit

from reade.core.enums.db_type import DbType
from reade.core.errors.config import ConfigError
from reade.core.models.db_metadata import DB_METADATA_REGISTRY

_WHO_WHERE: Final[dict[DbType, frozenset[str]]] = {
    DbType.SQLITE: frozenset({"database"}),
    DbType.POSTGRESQL: frozenset({"host", "port", "user", "password", "database"}),
    DbType.MYSQL: frozenset({"host", "port", "user", "password", "database"}),
}

_QUERY_ALLOWLIST: Final[dict[DbType, frozenset[str]]] = {
    DbType.SQLITE: frozenset(),
    DbType.POSTGRESQL: frozenset({"sslmode", "sslrootcert", "sslcert", "sslkey"}),
    DbType.MYSQL: frozenset(
        {
            "charset",
            "ssl_ca",
            "ssl_cert",
            "ssl_key",
            "ssl_verify_cert",
            "ssl_verify_identity",
        }
    ),
}


def expand_uri(data: dict[str, Any], *, db_type: DbType) -> dict[str, Any]:
    """Expand a ``uri`` key into the fields it encodes.

    Args:
        data: The model's raw input mapping, before validation.
        db_type: The backend whose URI dialect applies; its plain
            scheme comes from ``DB_METADATA_REGISTRY``.

    Returns:
        ``data`` unchanged when it carries no ``uri`` key; otherwise a
        new mapping with ``uri`` consumed and its components placed as
        plain fields. Query-parameter values stay raw strings —
        coercion belongs to model validation, as with env overrides.

    Raises:
        ConfigError: If the URI is malformed, its scheme is not this
            backend's plain scheme, a who-and-where key is also set
            explicitly, a required component is missing or empty, or a
            query parameter is unknown, duplicated, or also set
            explicitly. Messages name components and keys, never
            values.
    """
    if "uri" not in data:
        return data
    uri = data["uri"]
    if not isinstance(uri, str):
        raise ConfigError("'uri' must be a string")
    remaining = {key: value for key, value in data.items() if key != "uri"}
    overlap = sorted(_WHO_WHERE[db_type] & remaining.keys())
    if overlap:
        raise ConfigError(
            "'uri' encodes the connection's who and where; remove the "
            f"explicit key(s) {overlap} or drop 'uri'"
        )
    expected = DB_METADATA_REGISTRY[db_type].uri_scheme
    parsed = urlsplit(uri)
    if "+" in parsed.scheme:
        raise ConfigError(
            f"URI scheme {parsed.scheme!r} is driver-qualified; reaDE "
            f"connection URIs use the plain scheme {expected!r}"
        )
    if not parsed.scheme:
        raise ConfigError(f"not a valid connection URI; expected {expected}://…")
    if parsed.scheme != expected:
        raise ConfigError(
            f"URI scheme {parsed.scheme!r} does not match this backend; "
            f"expected {expected!r}"
        )
    if parsed.fragment:
        raise ConfigError("connection URIs take no fragment")
    if db_type is DbType.SQLITE:
        remaining.update(_sqlite_components(parsed))
    else:
        remaining.update(_server_components(parsed, remaining, db_type))
    return remaining


def _sqlite_components(parsed: SplitResult) -> dict[str, Any]:
    """Extract the database path from a ``sqlite:///path`` URI."""
    if parsed.netloc or not parsed.path.startswith("/"):
        raise ConfigError("sqlite URIs take no host; use the sqlite:///path form")
    if parsed.query:
        raise ConfigError("sqlite URIs take no query parameters")
    database = unquote(parsed.path[1:])
    if not database:
        raise ConfigError("URI is missing its database component")
    return {"database": database}


def _server_components(
    parsed: SplitResult, remaining: dict[str, Any], db_type: DbType
) -> dict[str, Any]:
    """Extract who-and-where plus allowlisted options from a server URI."""
    try:
        port = parsed.port
    except ValueError as e:
        raise ConfigError("invalid port in URI") from e
    user = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    host = parsed.hostname or ""
    database = unquote(parsed.path.removeprefix("/"))
    for name, value in (
        ("user", user),
        ("password", password),
        ("host", host),
        ("database", database),
    ):
        if not value:
            raise ConfigError(f"URI is missing its {name} component")
    if "/" in database:
        raise ConfigError("the URI database component must be a single path segment")
    expanded: dict[str, Any] = {
        "host": host,
        "user": user,
        "password": password,
        "database": database,
    }
    if port is not None:
        expanded["port"] = port
    expanded.update(_query_options(parsed.query, remaining, db_type))
    return expanded


def _query_options(
    query: str, remaining: dict[str, Any], db_type: DbType
) -> dict[str, Any]:
    """Map allowlisted query parameters onto option fields, raw strings."""
    allow = _QUERY_ALLOWLIST[db_type]
    options: dict[str, Any] = {}
    for key, value in parse_qsl(query, keep_blank_values=True):
        if key not in allow:
            raise ConfigError(
                f"unknown URI query parameter {key!r}; allowed for this "
                f"backend: {sorted(allow)}"
            )
        if key in options:
            raise ConfigError(f"duplicate URI query parameter {key!r}")
        if key in remaining:
            raise ConfigError(
                f"URI query parameter {key!r} conflicts with the explicit {key!r} key"
            )
        options[key] = value
    return options
