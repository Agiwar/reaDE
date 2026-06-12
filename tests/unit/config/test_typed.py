"""Unit tests for the typed loading layer (``load_config`` + models).

The typed layer is additive: it composes the frozen dict contract
(``ConfigLoader.load``) with pydantic validation on top, and maps
``ValidationError`` into ``ConfigError`` so pydantic's exception type
never escapes config/.
"""

from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from reade.config import SqliteConfig, load_config
from reade.core.errors import ConfigError


class _PortModel(BaseModel):
    """Test-only model with a non-string field to observe coercion."""

    model_config = ConfigDict(extra="forbid")

    port: int


@pytest.fixture
def sqlite_yaml(tmp_path: Path) -> Path:
    file_path = tmp_path / "db.yaml"
    file_path.write_text('database: "local.db"\n', encoding="utf-8")
    return file_path


class TestLoadConfig:
    def test_returns_validated_model_instance(self, sqlite_yaml: Path) -> None:
        config = load_config(sqlite_yaml, model=SqliteConfig)

        assert isinstance(config, SqliteConfig)
        assert config.database == "local.db"

    def test_accepts_path_as_str(self, sqlite_yaml: Path) -> None:
        config = load_config(str(sqlite_yaml), model=SqliteConfig)

        assert config.database == "local.db"

    def test_string_values_coerce_to_typed_fields(self, tmp_path: Path) -> None:
        file_path = tmp_path / "server.yaml"
        file_path.write_text('port: "5432"\n', encoding="utf-8")

        config = load_config(file_path, model=_PortModel)

        assert config.port == 5432

    def test_validation_failure_raises_config_error_with_field_path(
        self, tmp_path: Path
    ) -> None:
        file_path = tmp_path / "server.yaml"
        file_path.write_text("port: not-a-number\n", encoding="utf-8")

        with pytest.raises(ConfigError, match="port"):
            load_config(file_path, model=_PortModel)

    def test_validation_failure_chains_validation_error_as_cause(
        self, tmp_path: Path
    ) -> None:
        file_path = tmp_path / "server.yaml"
        file_path.write_text("port: not-a-number\n", encoding="utf-8")

        with pytest.raises(ConfigError) as exc_info:
            load_config(file_path, model=_PortModel)

        assert isinstance(exc_info.value.__cause__, ValidationError)

    def test_unknown_field_rejected_with_field_path(self, tmp_path: Path) -> None:
        file_path = tmp_path / "db.yaml"
        content = 'database: "local.db"\ndatabse: "typo"\n'
        file_path.write_text(content, encoding="utf-8")

        with pytest.raises(ConfigError, match="databse"):
            load_config(file_path, model=SqliteConfig)

    def test_unknown_suffix_raises_config_error(self, tmp_path: Path) -> None:
        file_path = tmp_path / "config.toml"
        file_path.write_text('database = "local.db"\n', encoding="utf-8")

        with pytest.raises(ConfigError, match="suffix"):
            load_config(file_path, model=SqliteConfig)

    def test_missing_file_passes_oserror_through(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "missing.yaml", model=SqliteConfig)

    def test_parse_failure_raises_config_error(self, invalid_yaml_file: Path) -> None:
        with pytest.raises(ConfigError):
            load_config(invalid_yaml_file, model=SqliteConfig)


class TestSqliteConfig:
    def test_fields_unpack_as_plain_parameters(self) -> None:
        config = SqliteConfig(database=":memory:")

        assert config.database == ":memory:"
        assert isinstance(config.database, str)
