"""Contract tests for the ConfigLoader protocol.

Every loader implementation must satisfy these guarantees, in particular
the two-tier error contract: OSError from the filesystem passes through
unchanged (tier 1); every failure the loader owns — unhandled format,
unparseable content — surfaces as ConfigError, with the original parser
exception attached as the cause (tier 2).
"""

from pathlib import Path

import pytest
import yaml

from reade.config import YamlLoader
from reade.core.errors import ConfigError
from reade.core.interfaces import ConfigLoader

# Static conformance proof: mypy verifies on this assignment that the
# implementation satisfies the protocol.
_conformance: ConfigLoader = YamlLoader()


class TestConfigLoaderContract:
    def test_load_returns_parsed_dict(self, valid_yaml_file: Path) -> None:
        loader: ConfigLoader = YamlLoader()

        result = loader.load(valid_yaml_file)

        assert result == {"database": {"host": "localhost", "port": 5432}}

    def test_tier1_missing_file_passes_oserror_through(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            YamlLoader().load(tmp_path / "missing.yaml")

    def test_tier2_unhandled_format_raises_config_error(self, tmp_path: Path) -> None:
        json_file = tmp_path / "config.json"
        json_file.write_text('{"a": 1}')

        with pytest.raises(ConfigError, match="does not handle"):
            YamlLoader().load(json_file)

    def test_tier2_parse_failure_raises_config_error_with_cause(
        self, invalid_yaml_file: Path
    ) -> None:
        with pytest.raises(ConfigError) as exc_info:
            YamlLoader().load(invalid_yaml_file)

        assert isinstance(exc_info.value.__cause__, yaml.YAMLError)
