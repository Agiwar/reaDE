"""Query execution against a connected database."""

from typing import Any

from reade.core.interfaces.connector import ConnectionInterface


def execute_query(
    connector: ConnectionInterface,
    sql: str,
    params: dict[str, Any] | None = None,
) -> list[tuple[Any, ...]]:
    """Execute a SQL statement and return all result rows, materialized.

    Thin facade over the connector's ``execute()``: driver specifics
    stay in the db layer; this seam deepens with readers and writers in
    later sprints. Any ``ConnectionInterface`` implementation is
    accepted — protocol-only connectors included, per the third-party
    plug-in contract.

    Statements without a result set (DDL, INSERT) return an empty list.
    ``params`` passes through unchanged: normalizing falsy params to
    no-parameters is the connector's contract, so
    ``execute_query(connector, rendered.sql, rendered.params)`` is safe
    even when a query binds nothing.

    Args:
        connector: A connected database connector.
        sql: The SQL statement to execute, in the connector dialect's
            placeholder style for any bound parameters.
        params: Values for the statement's placeholders, keyed by
            placeholder name (e.g. ``RenderedQuery.params``). ``None``
            or ``{}`` mean the statement binds nothing.

    Returns:
        All result rows as tuples.

    Raises:
        NotConnectedError: If the connector is not connected.
        DbError: If the driver fails to execute the statement or fetch
            its results. The driver exception is attached as the cause.

    Stability: stable.
    """
    return connector.execute(sql, params)
