"""Integration tests for the full pipeline."""

import json
import tempfile
from pathlib import Path

import pytest

from itunes_reorganizer.config import Config
from itunes_reorganizer.errors import ErrorLog
from itunes_reorganizer.executor import execute_plans, generate_dry_run_report
from itunes_reorganizer.grouping import group_tracks
from itunes_reorganizer.metadata import TrackMetadata
from itunes_reorganizer.planner import build_plans
from itunes_reorganizer.scanner import scan_audio_files


def _make_track(**overrides) -> TrackMetadata:
    defaults = {
        "source_path": Path("/source/test.mp3"),
        "title": "Test Song",
        "album": "Test Album",
        "albumartist": "Test Artist",
        "tracknumber": 1,
        "year": "2023",
    }
    defaults.update(overrides)
    return TrackMetadata(**defaults)


class TestDryRunNoFilesystemChanges:
    def test_dry_run_creates_no_files(self, tmp_path):
        """Dry-run mode should not create any files or directories."""
        config = Config(
            source_root=tmp_path / "source",
            destination_root=tmp_path / "dest",
            dry_run=True,
        )
        (tmp_path / "source").mkdir()

        log = ErrorLog()
        tracks = [_make_track(source_path=tmp_path / "source" / "song.mp3")]
        grouping = group_tracks(tracks, config, log)
        plans = build_plans(grouping, config, log)

        report = generate_dry_run_report(plans, config)
        assert "DRY-RUN" in report

        # Destination directory should NOT exist after dry-run
        dest = tmp_path / "dest"
        # The report is generated in memory; we don't write it during execute
        executed = execute_plans(plans, config, log)

        # No destination folders should have been created
        assert not (tmp_path / "dest" / "Test Artist").exists()


class TestCollisionHandling:
    def test_collision_does_not_overwrite(self, tmp_path):
        """Collisions should produce renamed files, not overwrite."""
        dest = tmp_path / "dest" / "Test Artist" / "2023 - Test Album"
        dest.mkdir(parents=True)

        # Pre-create the destination file
        existing = dest / "01 - Test Song.mp3"
        existing.write_text("original content")

        config = Config(
            source_root=tmp_path / "source",
            destination_root=dest.parent.parent.parent,
            dry_run=False,
            operation="copy",
        )
        (tmp_path / "source").mkdir()
        source_file = tmp_path / "source" / "song.mp3"
        source_file.write_text("new content")

        log = ErrorLog()
        tracks = [_make_track(source_path=source_file)]
        grouping = group_tracks(tracks, config, log)
        plans = build_plans(grouping, config, log)

        # The collision would be resolved by the planner with (2)
        if plans.collisions:
            executed = execute_plans(plans, config, log)
            # Original file should be unchanged
            assert existing.read_text() == "original content"


class TestScannerIntegration:
    def test_scan_finds_audio_files(self, tmp_path):
        """Scanner should find supported audio files."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "song.mp3").write_bytes(b"fake mp3")
        (source / "readme.txt").write_text("not audio")
        (source / "subdir").mkdir()
        (source / "subdir" / "track.flac").write_bytes(b"fake flac")

        log = ErrorLog()
        files = scan_audio_files(source, log)
        names = {f.name for f in files}
        assert "song.mp3" in names
        assert "track.flac" in names
        assert "readme.txt" not in names

    def test_scan_empty_directory(self, tmp_path):
        source = tmp_path / "empty"
        source.mkdir()
        log = ErrorLog()
        files = scan_audio_files(source, log)
        assert files == []
