"""Tests for configuration data models."""

import pytest
from pydantic import SecretStr, ValidationError

from reade.config.models import DbCredentials, SqliteCredentials


class TestDbCredentials:
    """Tests for DbCredentials model validation."""

    def test_valid_credentials(self) -> None:
        """Valid credentials create model successfully."""
        creds = DbCredentials(
            host="localhost",
            port=5432,
            database="mydb",
            username="user",
            password="secret",  # type: ignore[arg-type]
        )

        assert creds.host == "localhost"
        assert creds.port == 5432
        assert creds.database == "mydb"
        assert creds.username == "user"
        assert isinstance(creds.password, SecretStr)

    def test_password_is_masked(self) -> None:
        """Password is masked in string representation."""
        creds = DbCredentials(
            host="localhost",
            port=5432,
            database="mydb",
            username="user",
            password="secret123",  # type: ignore[arg-type]
        )

        assert "secret123" not in str(creds)
        assert "**********" in str(creds)

    def test_password_get_secret_value(self) -> None:
        """Password can be retrieved with get_secret_value()."""
        creds = DbCredentials(
            host="localhost",
            port=5432,
            database="mydb",
            username="user",
            password="secret123",  # type: ignore[arg-type]
        )

        assert creds.password.get_secret_value() == "secret123"

    def test_port_minimum_valid(self) -> None:
        """Port at minimum (1) is valid."""
        creds = DbCredentials(
            host="localhost",
            port=1,
            database="mydb",
            username="user",
            password="secret",  # type: ignore[arg-type]
        )

        assert creds.port == 1

    def test_port_maximum_valid(self) -> None:
        """Port at maximum (65535) is valid."""
        creds = DbCredentials(
            host="localhost",
            port=65535,
            database="mydb",
            username="user",
            password="secret",  # type: ignore[arg-type]
        )

        assert creds.port == 65535

    def test_port_below_minimum_raises(self) -> None:
        """Port below 1 raises ValidationError."""
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            DbCredentials(
                host="localhost",
                port=0,
                database="mydb",
                username="user",
                password="secret",  # type: ignore[arg-type]
            )

    def test_port_above_maximum_raises(self) -> None:
        """Port above 65535 raises ValidationError."""
        with pytest.raises(ValidationError, match="less than or equal to 65535"):
            DbCredentials(
                host="localhost",
                port=65536,
                database="mydb",
                username="user",
                password="secret",  # type: ignore[arg-type]
            )

    def test_missing_required_field_raises(self) -> None:
        """Missing required field raises ValidationError."""
        with pytest.raises(ValidationError, match="host"):
            DbCredentials(  # type: ignore[call-arg]
                port=5432,
                database="mydb",
                username="user",
                password="secret",  # type: ignore[arg-type]
            )

    def test_extra_field_raises(self) -> None:
        """Extra unknown field raises ValidationError."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            DbCredentials(  # type: ignore[call-arg]
                host="localhost",
                port=5432,
                database="mydb",
                username="user",
                password="secret",  # type: ignore[arg-type]
                ssl_mode="require",  # Extra field not in model
            )

    def test_from_dict(self) -> None:
        """Model can be created from dict (simulating YAML load)."""
        config = {
            "host": "db.example.com",
            "port": 3306,
            "database": "analytics",
            "username": "admin",
            "password": "supersecret",  # pragma: allowlist secret
        }

        creds = DbCredentials(**config)  # type: ignore[arg-type]

        assert creds.host == "db.example.com"
        assert creds.port == 3306


class TestSqliteCredentials:
    """Tests for SqliteCredentials model validation."""

    def test_valid_credentials(self) -> None:
        """Valid SQLite credentials create model successfully."""
        creds = SqliteCredentials(database="/path/to/data.db")

        assert creds.database == "/path/to/data.db"

    def test_missing_database_raises(self) -> None:
        """Missing database field raises ValidationError."""
        with pytest.raises(ValidationError, match="database"):
            SqliteCredentials()  # type: ignore[call-arg]

    def test_extra_field_raises(self) -> None:
        """Extra unknown field raises ValidationError."""
        with pytest.raises(ValidationError, match="extra_forbidden"):
            SqliteCredentials(  # type: ignore[call-arg]
                database="/path/to/data.db",
                host="localhost",  # SQLite doesn't use host
            )

    def test_from_dict(self) -> None:
        """Model can be created from dict (simulating YAML load)."""
        config = {"database": "/var/lib/app/data.db"}

        creds = SqliteCredentials(**config)

        assert creds.database == "/var/lib/app/data.db"
