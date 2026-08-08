"""Unit tests for URI-style config input (the 4.2 ``uri`` key).

The ``uri`` key expands before validation into who-and-where fields
(host, port, user, password, database) plus allowlisted option query
parameters. It is consumed by the expansion — never a model field — so
the field↔parameter mirror and ``model_dump()`` unpacking stay intact.
Typed callers pass ``uri`` in the input mapping (``model_validate``, a
config file, or an env override): the synthesized constructor signature
knows only real fields, so keyword construction is runtime-only.
Containment: the URI (and the password inside it) is never retained on
the model, and expansion errors name components and keys, never values.
"""

from typing import TYPE_CHECKING, Any
from urllib.parse import unquote

import pytest

from reade.config import MysqlConfig, PostgresConfig, SqliteConfig, load_config
from reade.core.errors import ConfigError

if TYPE_CHECKING:
    from pathlib import Path

PG_URI = (
    "postgresql://app:s%40fe@db.internal:6432/analytics"  # pragma: allowlist secret
)
MY_URI = "mysql://app:s%40fe@db.internal:3307/analytics"  # pragma: allowlist secret


def _pg(**data: Any) -> PostgresConfig:
    return PostgresConfig.model_validate(data)


def _my(**data: Any) -> MysqlConfig:
    return MysqlConfig.model_validate(data)


def _sq(**data: Any) -> SqliteConfig:
    return SqliteConfig.model_validate(data)


class TestServerExpansion:
    def test_uri_expands_who_and_where(self) -> None:
        config = _pg(uri=PG_URI)

        assert config.host == "db.internal"
        assert config.port == 6432
        assert config.user == "app"
        assert config.password == unquote("s%40fe")
        assert config.database == "analytics"

    def test_mysql_uri_expands(self) -> None:
        config = _my(uri=MY_URI)

        assert config.host == "db.internal"
        assert config.port == 3307
        assert config.database == "analytics"

    def test_credentials_percent_decode(self) -> None:
        config = _pg(uri=PG_URI)

        assert config.password == unquote("s%40fe")

    def test_missing_port_uses_model_default(self) -> None:
        pg = _pg(uri="postgresql://u:p@h/db")
        my = _my(uri="mysql://u:p@h/db")

        assert pg.port == 5432
        assert my.port == 3306

    def test_ipv6_bracket_host(self) -> None:
        config = _pg(uri="postgresql://u:p@[::1]:5433/db")

        assert config.host == "::1"
        assert config.port == 5433

    def test_option_fields_compose_beside_uri(self) -> None:
        # The scoped conflict rule: who/where conflicts, options compose.
        config = _pg(uri=PG_URI, sslmode="require", connect_attempts=3)

        assert config.sslmode == "require"
        assert config.connect_attempts == 3

    def test_uri_is_not_retained_on_the_model(self) -> None:
        config = _pg(uri=PG_URI)

        assert "uri" not in config.model_dump()
        assert not hasattr(config, "uri")

    def test_repr_masks_password_through_the_uri_path(self) -> None:
        config = _pg(uri=PG_URI)

        assert "s@fe" not in repr(config)
        assert "s%40fe" not in repr(config)

    def test_keyword_construction_works_at_runtime(self) -> None:
        # The synthesized constructor signature knows only real fields,
        # so static checkers reject uri= as a keyword — mapping input is
        # the typed call form. The runtime keyword path stays supported
        # for untyped callers; pinned here.
        config = PostgresConfig(uri=PG_URI)  # type: ignore[call-arg]

        assert config.host == "db.internal"


class TestConflictRule:
    def test_uri_plus_host_raises(self) -> None:
        with pytest.raises(ConfigError, match="who and where"):
            _pg(uri=PG_URI, host="db.internal")

    def test_uri_plus_password_raises(self) -> None:
        with pytest.raises(ConfigError, match="who and where"):
            _pg(uri=PG_URI, password="other")  # pragma: allowlist secret

    def test_uri_plus_port_raises_even_when_uri_lacks_a_port(self) -> None:
        # The conflict is on the field class a URI encodes, not on the
        # components this particular URI happens to carry.
        with pytest.raises(ConfigError, match="who and where"):
            _pg(uri="postgresql://u:p@h/db", port=6543)

    def test_conflict_message_names_keys_never_values(self) -> None:
        with pytest.raises(ConfigError) as exc_info:
            _pg(uri=PG_URI, host="db.internal")

        message = str(exc_info.value)
        assert "host" in message
        assert "db.internal" not in message
        assert "s@fe" not in message
        assert "s%40fe" not in message


class TestScheme:
    def test_driver_qualified_scheme_rejected_with_guidance(self) -> None:
        with pytest.raises(ConfigError, match="driver-qualified"):
            _pg(uri="postgresql+psycopg://u:p@h/db")

    def test_wrong_backend_scheme_rejected(self) -> None:
        with pytest.raises(ConfigError, match="does not match this backend"):
            _pg(uri=MY_URI)

    def test_garbage_uri_rejected(self) -> None:
        with pytest.raises(ConfigError, match="not a valid connection URI"):
            _pg(uri="not a uri")

    def test_non_string_uri_rejected(self) -> None:
        with pytest.raises(ConfigError, match="must be a string"):
            _pg(uri=5)


class TestComponents:
    @pytest.mark.parametrize(
        ("uri", "component"),
        [
            ("postgresql://:pw@h/db", "user"),
            ("postgresql://app@h/db", "password"),
            ("postgresql://u:p@/db", "host"),
            ("postgresql://u:p@h", "database"),
            ("postgresql://u:p@h/", "database"),
        ],
    )
    def test_missing_components_fail_loud(self, uri: str, component: str) -> None:
        with pytest.raises(ConfigError, match=f"missing its {component} component"):
            _pg(uri=uri)

    def test_component_error_never_echoes_the_password(self) -> None:
        # The URI carries a password but lacks a database: the loud
        # failure must not leak the secret it is refusing to place.
        with pytest.raises(ConfigError) as exc_info:
            _pg(uri="postgresql://app:s%40fe@h")  # pragma: allowlist secret

        message = str(exc_info.value)
        assert "s@fe" not in message
        assert "s%40fe" not in message

    def test_invalid_port_fails_loud(self) -> None:
        with pytest.raises(ConfigError, match="invalid port"):
            _pg(uri="postgresql://u:p@h:notaport/db")

    def test_multi_segment_database_rejected(self) -> None:
        with pytest.raises(ConfigError, match="single path segment"):
            _pg(uri="postgresql://u:p@h/a/b")

    def test_fragment_rejected(self) -> None:
        with pytest.raises(ConfigError, match="no fragment"):
            _pg(uri="postgresql://u:p@h/db#frag")


class TestQueryParams:
    def test_allowlisted_param_lands_in_its_option_field(self) -> None:
        config = _pg(uri=f"{PG_URI}?sslmode=require")

        assert config.sslmode == "require"

    def test_bool_option_coerces_from_query_string(self) -> None:
        # Raw strings in, model coercion during validation — the same
        # contract env overrides follow.
        config = _my(uri=f"{MY_URI}?ssl_verify_cert=true")

        assert config.ssl_verify_cert is True

    def test_unknown_param_rejected_naming_the_key_only(self) -> None:
        with pytest.raises(ConfigError, match="unknown URI query parameter") as exc:
            _pg(uri=f"{PG_URI}?foo=topsecret")

        message = str(exc.value)
        assert "'foo'" in message
        assert "topsecret" not in message

    def test_retry_knobs_are_not_uri_content(self) -> None:
        # Deploy knobs stay out of the allowlist by ruling.
        with pytest.raises(ConfigError, match="unknown URI query parameter"):
            _pg(uri=f"{PG_URI}?connect_attempts=3")

    def test_duplicate_param_rejected(self) -> None:
        with pytest.raises(ConfigError, match="duplicate URI query parameter"):
            _pg(uri=f"{PG_URI}?sslmode=require&sslmode=disable")

    def test_query_param_conflicts_with_the_explicit_field(self) -> None:
        with pytest.raises(ConfigError, match="conflicts with the explicit"):
            _pg(uri=f"{PG_URI}?sslmode=require", sslmode="disable")


class TestSqlite:
    def test_relative_path(self) -> None:
        config = _sq(uri="sqlite:///local.db")

        assert config.database == "local.db"

    def test_absolute_path(self) -> None:
        config = _sq(uri="sqlite:////var/data/prod.db")

        assert config.database == "/var/data/prod.db"

    def test_memory_form(self) -> None:
        config = _sq(uri="sqlite:///:memory:")

        assert config.database == ":memory:"

    def test_netloc_rejected_with_form_guidance(self) -> None:
        with pytest.raises(ConfigError, match="sqlite:///path"):
            _sq(uri="sqlite://local.db")

    def test_empty_path_fails_loud(self) -> None:
        with pytest.raises(ConfigError, match="missing its database component"):
            _sq(uri="sqlite:///")

    def test_query_params_rejected(self) -> None:
        with pytest.raises(ConfigError, match="no query parameters"):
            _sq(uri="sqlite:///x.db?mode=ro")

    def test_uri_plus_database_raises(self) -> None:
        with pytest.raises(ConfigError, match="who and where"):
            _sq(uri="sqlite:///x.db", database="y.db")


class TestLoadConfigPath:
    def test_uri_from_file(self, tmp_path: "Path") -> None:
        file_path = tmp_path / "db.yaml"
        file_path.write_text(f'uri: "{PG_URI}"\n', encoding="utf-8")

        config = load_config(file_path, model=PostgresConfig)

        assert config.host == "db.internal"
        assert config.database == "analytics"

    def test_uri_from_env_override(self, tmp_path: "Path") -> None:
        file_path = tmp_path / "empty.yaml"
        file_path.write_text("{}\n", encoding="utf-8")

        config = load_config(
            file_path,
            model=PostgresConfig,
            environ={"READE__POSTGRES__URI": PG_URI},
        )

        assert config.host == "db.internal"
        assert config.password == unquote("s%40fe")

    def test_env_uri_conflicts_with_file_host(self, tmp_path: "Path") -> None:
        file_path = tmp_path / "db.yaml"
        file_path.write_text(
            "host: h\ndatabase: d\nuser: u\npassword: p\n", encoding="utf-8"
        )

        with pytest.raises(ConfigError, match="who and where"):
            load_config(
                file_path,
                model=PostgresConfig,
                environ={"READE__POSTGRES__URI": PG_URI},
            )
