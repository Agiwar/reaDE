"""Query execution against a connected database."""

from typing import Any

from reade.core.base.connector import ConnectionBase
from reade.core.errors.base import ReadeError
from reade.core.errors.data_io import DataIoError


def execute_query(connector: ConnectionBase[Any], sql: str) -> list[tuple[Any, ...]]:
    """Execute a SQL statement and return all result rows, materialized.

    Statements without a result set (DDL, INSERT) return an empty list.

    Args:
        connector: A connected database connector.
        sql: The SQL statement to execute.

    Returns:
        All result rows as tuples.

    Raises:
        NotConnectedError: If the connector is not connected; passed
            through unchanged, like any ``ReadeError`` raised below
            this layer.
        DataIoError: If the driver fails to execute the statement or
            fetch its results. The driver exception is attached as the
            cause.
    """
    try:
        cursor = connector.connection.execute(sql)
        rows = cursor.fetchall()
    except ReadeError:
        raise
    except Exception as e:
        raise DataIoError("Query execution failed") from e
    return [tuple(row) for row in rows]
