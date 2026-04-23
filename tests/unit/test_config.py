"""Tests for the config module."""

import json
import tempfile
from pathlib import Path

import pytest

from itunes_reorganizer.config import Config
from itunes_reorganizer.errors import ErrorLog


class TestConfigFromDict:
    def test_minimal_config(self, tmp_path):
        src = tmp_path / "source"
        src.mkdir()
        data = {"source_root": str(src), "destination_root": str(tmp_path / "dest")}
        config = Config.from_dict(data)
        assert config.source_root == src
        assert config.destination_root == tmp_path / "dest"
        assert config.dry_run is True
        assert config.operation == "copy"
        assert config.fallback_to_artist is False

    def test_full_config(self, tmp_path):
        src = tmp_path / "source"
        src.mkdir()
        data = {
            "source_root": str(src),
            "destination_root": str(tmp_path / "dest"),
            "dry_run": False,
            "operation": "move",
            "fallback_to_artist": True,
        }
        config = Config.from_dict(data)
        assert config.dry_run is False
        assert config.operation == "move"
        assert config.fallback_to_artist is True


class TestConfigFromFile:
    def test_load_valid_file(self, tmp_path):
        src = tmp_path / "source"
        src.mkdir()
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "source_root": str(src),
            "destination_root": str(tmp_path / "dest"),
        }))
        config = Config.from_file(config_path)
        assert config.source_root == src

    def test_missing_file(self):
        with pytest.raises(FileNotFoundError):
            Config.from_file("/nonexistent/config.json")


class TestConfigValidation:
    def test_valid_config(self, tmp_path):
        src = tmp_path / "source"
        src.mkdir()
        config = Config(source_root=src, destination_root=tmp_path / "dest")
        log = ErrorLog()
        assert config.validate(log) is True
        assert not log.has_fatal

    def test_missing_source(self, tmp_path):
        config = Config(source_root=tmp_path / "nonexistent", destination_root=tmp_path / "dest")
        log = ErrorLog()
        assert config.validate(log) is False
        assert log.has_fatal

    def test_invalid_operation(self, tmp_path):
        src = tmp_path / "source"
        src.mkdir()
        config = Config(source_root=src, destination_root=tmp_path / "dest", operation="delete", dry_run=False)
        log = ErrorLog()
        assert config.validate(log) is False

    def test_dry_run_no_dest_needed(self, tmp_path):
        src = tmp_path / "source"
        src.mkdir()
        config = Config(source_root=src, destination_root=tmp_path / "nonexistent_dest", dry_run=True)
        log = ErrorLog()
        assert config.validate(log) is True


class TestConfigSave:
    def test_roundtrip(self, tmp_path):
        src = tmp_path / "source"
        src.mkdir()
        original = Config(source_root=src, destination_root=tmp_path / "dest", dry_run=False, operation="move")
        path = tmp_path / "config.json"
        original.save(path)

        loaded = Config.from_file(path)
        assert loaded.source_root == original.source_root
        assert loaded.destination_root == original.destination_root
        assert loaded.dry_run == original.dry_run
        assert loaded.operation == original.operation
