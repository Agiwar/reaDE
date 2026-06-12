"""Contract tests for the ConfigLoader protocol.

Every loader implementation must satisfy these guarantees, in particular
the two-tier error contract: OSError from the filesystem passes through
unchanged (tier 1); every failure the loader owns — unhandled format,
unparseable content, a non-mapping document — surfaces as ConfigError,
with the original exception attached as the cause (tier 2).
"""

import json
from pathlib import Path
from typing import NamedTuple

import pytest
import yaml

from reade.config import JsonLoader, YamlLoader
from reade.core.base.file_loader import FileLoaderBase
from reade.core.errors import ConfigError
from reade.core.interfaces import ConfigLoader

# Static conformance proofs: mypy verifies on these assignments that each
# implementation satisfies the protocol.
_yaml_conformance: ConfigLoader = YamlLoader()
_json_conformance: ConfigLoader = JsonLoader()


class LoaderCase(NamedTuple):
    """One loader's inputs for the shared contract suite."""

    loader_cls: type[FileLoaderBase]
    file_name: str
    valid_content: str
    invalid_content: str
    non_mapping_content: str
    foreign_file_name: str
    parser_error: type[Exception]


CASES = [
    pytest.param(
        LoaderCase(
            loader_cls=YamlLoader,
            file_name="config.yaml",
            valid_content="database:\n  host: localhost\n  port: 5432\n",
            invalid_content="invalid: yaml: content:\n  - broken",
            non_mapping_content="- a\n- b\n",
            foreign_file_name="config.json",
            parser_error=yaml.YAMLError,
        ),
        id="yaml",
    ),
    pytest.param(
        LoaderCase(
            loader_cls=JsonLoader,
            file_name="config.json",
            valid_content='{"database": {"host": "localhost", "port": 5432}}',
            invalid_content='{"database": ',
            non_mapping_content="[1, 2]",
            foreign_file_name="config.yaml",
            parser_error=json.JSONDecodeError,
        ),
        id="json",
    ),
]


@pytest.mark.parametrize("case", CASES)
class TestConfigLoaderContract:
    def test_load_returns_parsed_dict(self, case: LoaderCase, tmp_path: Path) -> None:
        file_path = tmp_path / case.file_name
        file_path.write_text(case.valid_content, encoding="utf-8")
        loader: ConfigLoader = case.loader_cls()

        result = loader.load(file_path)

        assert result == {"database": {"host": "localhost", "port": 5432}}

    def test_tier1_missing_file_passes_oserror_through(
        self, case: LoaderCase, tmp_path: Path
    ) -> None:
        with pytest.raises(FileNotFoundError):
            case.loader_cls().load(tmp_path / case.file_name)

    def test_tier2_unhandled_format_raises_config_error(
        self, case: LoaderCase, tmp_path: Path
    ) -> None:
        foreign_file = tmp_path / case.foreign_file_name
        foreign_file.write_text(case.valid_content, encoding="utf-8")

        with pytest.raises(ConfigError, match="does not handle"):
            case.loader_cls().load(foreign_file)

    def test_tier2_parse_failure_raises_config_error_with_cause(
        self, case: LoaderCase, tmp_path: Path
    ) -> None:
        file_path = tmp_path / case.file_name
        file_path.write_text(case.invalid_content, encoding="utf-8")

        with pytest.raises(ConfigError) as exc_info:
            case.loader_cls().load(file_path)

        assert isinstance(exc_info.value.__cause__, case.parser_error)

    def test_tier2_non_mapping_document_raises_config_error_with_cause(
        self, case: LoaderCase, tmp_path: Path
    ) -> None:
        file_path = tmp_path / case.file_name
        file_path.write_text(case.non_mapping_content, encoding="utf-8")

        with pytest.raises(ConfigError) as exc_info:
            case.loader_cls().load(file_path)

        assert isinstance(exc_info.value.__cause__, TypeError)
