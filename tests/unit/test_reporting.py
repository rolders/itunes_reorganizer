"""Tests for the reporting module."""

import json
from pathlib import Path

import pytest

from itunes_reorganizer.errors import ErrorLog, OrganizerError, Severity
from itunes_reorganizer.planner import FilePlan
from itunes_reorganizer.reporting import (
    RunStats,
    write_collisions_csv,
    write_dry_run_report,
    write_moved_csv,
    write_run_summary,
    write_skipped_csv,
)


class TestRunStats:
    def test_to_dict(self):
        stats = RunStats(
            total_files_scanned=100,
            files_with_metadata=90,
            files_planned=90,
            files_executed=90,
        )
        d = stats.to_dict()
        assert d["total_files_scanned"] == 100
        assert d["files_with_metadata"] == 90
        assert "timestamp" in d


class TestWriteRunSummary:
    def test_writes_json(self, tmp_path):
        stats = RunStats(total_files_scanned=10)
        path = write_run_summary(stats, tmp_path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["total_files_scanned"] == 10


class TestWriteMovedCsv:
    def test_writes_csv(self, tmp_path):
        plans = [
            FilePlan(
                source=Path("/src/a.mp3"),
                destination=Path("/dest/Artist/Album/01 - Song.mp3"),
                album_artist="Artist",
                album="Album",
                year="2023",
                title="Song",
                tracknumber=1,
                extension=".mp3",
            ),
        ]
        path = write_moved_csv(plans, tmp_path)
        assert path.exists()
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2  # header + 1 row
        assert "Artist" in lines[1]


class TestWriteSkippedCsv:
    def test_writes_csv(self, tmp_path):
        log = ErrorLog()
        log.add_skip("Missing album", Path("/src/a.mp3"), "validate")
        path = write_skipped_csv(log, tmp_path)
        assert path.exists()
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2
        assert "Missing album" in lines[1]


class TestWriteCollisionsCsv:
    def test_writes_csv(self, tmp_path):
        collisions = [
            FilePlan(
                source=Path("/src/a.mp3"),
                destination=Path("/dest/Artist/Album/01 - Song (2).mp3"),
                album_artist="Artist",
                album="Album",
                year="2023",
                title="Song",
                tracknumber=1,
                extension=".mp3",
                collision_suffix=1,
            ),
        ]
        path = write_collisions_csv(collisions, tmp_path)
        assert path.exists()
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2


class TestWriteDryRunReport:
    def test_writes_report(self, tmp_path):
        report = "DRY-RUN REORGANIZATION PLAN\nNo files to process."
        path = write_dry_run_report(report, tmp_path)
        assert path.exists()
        assert "DRY-RUN" in path.read_text()
