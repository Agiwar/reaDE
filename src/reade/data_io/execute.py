"""Query execution against a connected database."""

from typing import Any

from reade.core.base.connector import ConnectionBase


def execute_query(connector: ConnectionBase[Any], sql: str) -> list[tuple[Any, ...]]:
    """Execute a SQL statement and return all result rows, materialized.

    Thin facade over the connector's ``execute()``: driver specifics
    stay in the db layer; this seam deepens with readers, writers, and
    streaming results in later sprints.

    Statements without a result set (DDL, INSERT) return an empty list.

    Args:
        connector: A connected database connector.
        sql: The SQL statement to execute.

    Returns:
        All result rows as tuples.

    Raises:
        NotConnectedError: If the connector is not connected.
        DbError: If the driver fails to execute the statement or fetch
            its results. The driver exception is attached as the cause.
    """
    return connector.execute(sql)
