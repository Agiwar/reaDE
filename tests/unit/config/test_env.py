"""Unit tests for merge_env_overrides.

Every test injects a plain dict as the environment — the function is
pure and injectable by design, so no monkeypatching is needed.
"""

from typing import Any

from reade.config import merge_env_overrides


class TestMergeEnvOverrides:
    def test_env_overrides_file_value(self) -> None:
        data: dict[str, Any] = {"database": "local.db"}

        result = merge_env_overrides(data, {"READE__DATABASE": "prod.db"})

        assert result == {"database": "prod.db"}

    def test_nested_sections_via_double_underscore(self) -> None:
        data: dict[str, Any] = {"db": {"host": "localhost", "port": 5432}}

        result = merge_env_overrides(data, {"READE__DB__HOST": "db.internal"})

        assert result == {"db": {"host": "db.internal", "port": 5432}}

    def test_single_underscores_stay_inside_key_names(self) -> None:
        data: dict[str, Any] = {"db": {"max_retries": 3}}

        result = merge_env_overrides(data, {"READE__DB__MAX_RETRIES": "5"})

        assert result == {"db": {"max_retries": "5"}}

    def test_existing_keys_match_case_insensitively(self) -> None:
        data: dict[str, Any] = {"Database": "local.db"}

        result = merge_env_overrides(data, {"READE__DATABASE": "prod.db"})

        assert result == {"Database": "prod.db"}

    def test_values_inserted_as_raw_strings_without_coercion(self) -> None:
        data: dict[str, Any] = {"port": 5432}

        result = merge_env_overrides(data, {"READE__PORT": "8080"})

        assert result["port"] == "8080"

    def test_unmatched_key_inserted_lowercased(self) -> None:
        data: dict[str, Any] = {"database": "local.db"}

        result = merge_env_overrides(data, {"READE__TIMEOUT": "30"})

        assert result == {"database": "local.db", "timeout": "30"}

    def test_non_prefixed_variables_ignored(self) -> None:
        data: dict[str, Any] = {"database": "local.db"}
        environ = {"DATABASE": "a", "READE_DATABASE": "b", "XREADE__DATABASE": "c"}

        result = merge_env_overrides(data, environ)

        assert result == {"database": "local.db"}

    def test_input_data_not_mutated(self) -> None:
        data: dict[str, Any] = {"db": {"host": "localhost"}}

        result = merge_env_overrides(data, {"READE__DB__HOST": "other"})

        assert data == {"db": {"host": "localhost"}}
        assert result is not data

    def test_empty_environ_returns_equal_copy(self) -> None:
        data: dict[str, Any] = {"database": "local.db"}

        result = merge_env_overrides(data, {})

        assert result == data
        assert result is not data

    def test_non_mapping_intermediate_replaced_by_override(self) -> None:
        data: dict[str, Any] = {"db": "sqlite"}

        result = merge_env_overrides(data, {"READE__DB__HOST": "db.internal"})

        assert result == {"db": {"host": "db.internal"}}
