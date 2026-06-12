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
from reade.db import SqliteConnector


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

    def test_valid_suffix_without_registered_loader_raises_config_error(
        self, tmp_path: Path
    ) -> None:
        # .csv maps to a valid FileType but deliberately has no loader:
        # exercises the factory's ConfigError branch through load_config.
        file_path = tmp_path / "rules.csv"
        file_path.write_text("a,b\n1,2\n", encoding="utf-8")

        with pytest.raises(ConfigError, match="file type"):
            load_config(file_path, model=SqliteConfig)

    def test_missing_file_passes_oserror_through(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "missing.yaml", model=SqliteConfig)

    def test_parse_failure_raises_config_error(self, invalid_yaml_file: Path) -> None:
        with pytest.raises(ConfigError):
            load_config(invalid_yaml_file, model=SqliteConfig)

    def test_env_override_beats_file_value(self, sqlite_yaml: Path) -> None:
        config = load_config(
            sqlite_yaml,
            model=SqliteConfig,
            environ={"READE__DATABASE": "from-env.db"},
        )

        assert config.database == "from-env.db"

    def test_default_environ_is_process_environment(
        self, sqlite_yaml: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("READE__DATABASE", "from-env.db")

        config = load_config(sqlite_yaml, model=SqliteConfig)

        assert config.database == "from-env.db"

    def test_empty_environ_disables_overrides(
        self, sqlite_yaml: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("READE__DATABASE", "ignored.db")

        config = load_config(sqlite_yaml, model=SqliteConfig, environ={})

        assert config.database == "local.db"

    def test_env_override_string_coerces_during_validation(
        self, tmp_path: Path
    ) -> None:
        file_path = tmp_path / "server.yaml"
        file_path.write_text("port: 5432\n", encoding="utf-8")

        config = load_config(
            file_path, model=_PortModel, environ={"READE__PORT": "6543"}
        )

        assert config.port == 6543

    def test_typo_in_env_override_fails_loudly_with_field_path(
        self, sqlite_yaml: Path
    ) -> None:
        with pytest.raises(ConfigError, match="databse"):
            load_config(
                sqlite_yaml, model=SqliteConfig, environ={"READE__DATABSE": "oops"}
            )


class TestSearchPaths:
    def test_first_hit_wins_in_tuple_order(self, tmp_path: Path) -> None:
        first = tmp_path / "first"
        second = tmp_path / "second"
        for directory, value in ((first, "first.db"), (second, "second.db")):
            directory.mkdir()
            (directory / "db.yaml").write_text(
                f'database: "{value}"\n', encoding="utf-8"
            )

        config = load_config(
            "db.yaml", model=SqliteConfig, search_paths=(first, second)
        )

        assert config.database == "first.db"

    def test_later_directory_used_when_earlier_misses(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        hit = tmp_path / "hit"
        hit.mkdir()
        (hit / "db.yaml").write_text('database: "hit.db"\n', encoding="utf-8")

        config = load_config("db.yaml", model=SqliteConfig, search_paths=(empty, hit))

        assert config.database == "hit.db"

    def test_absolute_path_bypasses_search(
        self, sqlite_yaml: Path, tmp_path: Path
    ) -> None:
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()

        config = load_config(sqlite_yaml, model=SqliteConfig, search_paths=(elsewhere,))

        assert config.database == "local.db"

    def test_miss_raises_file_not_found_listing_every_directory(
        self, tmp_path: Path
    ) -> None:
        one = tmp_path / "one"
        two = tmp_path / "two"
        one.mkdir()
        two.mkdir()

        with pytest.raises(FileNotFoundError) as exc_info:
            load_config("db.yaml", model=SqliteConfig, search_paths=(one, two))

        message = str(exc_info.value)
        assert str(one) in message
        assert str(two) in message

    def test_default_resolves_against_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "db.yaml").write_text('database: "cwd.db"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        config = load_config("db.yaml", model=SqliteConfig)

        assert config.database == "cwd.db"

    def test_accepts_list_of_strings(self, tmp_path: Path) -> None:
        directory = tmp_path / "configs"
        directory.mkdir()
        (directory / "db.yaml").write_text(
            'database: "fromlist.db"\n', encoding="utf-8"
        )

        config = load_config(
            "db.yaml", model=SqliteConfig, search_paths=[str(directory)]
        )

        assert config.database == "fromlist.db"

    def test_relative_subpath_resolves_under_search_directory(
        self, tmp_path: Path
    ) -> None:
        nested = tmp_path / "configs" / "prod"
        nested.mkdir(parents=True)
        (nested / "db.yaml").write_text('database: "nested.db"\n', encoding="utf-8")

        config = load_config(
            Path("prod") / "db.yaml",
            model=SqliteConfig,
            search_paths=(tmp_path / "configs",),
        )

        assert config.database == "nested.db"


class TestSqliteConfig:
    def test_fields_unpack_as_plain_parameters(self, tmp_path: Path) -> None:
        file_path = tmp_path / "db.yaml"
        file_path.write_text('database: ":memory:"\n', encoding="utf-8")

        config = load_config(file_path, model=SqliteConfig)

        # The connector takes the plain str — pydantic stops at config/.
        with SqliteConnector(database=config.database) as connector:
            assert connector.ping() is True
