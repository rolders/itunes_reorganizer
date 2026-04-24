"""Tests for the planner module."""

from pathlib import Path

import pytest

from itunes_reorganizer.config import Config
from itunes_reorganizer.errors import ErrorLog
from itunes_reorganizer.album_grouper import group_tracks
from itunes_reorganizer.metadata import TrackMetadata
from itunes_reorganizer.planner import build_plans
from itunes_reorganizer.naming import sanitize_name


def _make_track(**overrides) -> TrackMetadata:
    defaults = {
        "source_path": Path("/source/Artist/Album/01 - Test.mp3"),
        "title": "Test Song",
        "album": "Test Album",
        "albumartist": "Test Artist",
        "tracknumber": 1,
        "year": "2023",
    }
    defaults.update(overrides)
    return TrackMetadata(**defaults)


class TestSanitizeName:
    def test_normal(self):
        assert sanitize_name("Hello World") == "Hello World"

    def test_invalid_chars(self):
        assert sanitize_name('Hello: World/ <test>') == "Hello World test"

    def test_multiple_spaces(self):
        assert sanitize_name("Hello   World") == "Hello World"

    def test_leading_dots(self):
        assert sanitize_name("..hidden") == "hidden"

    def test_empty(self):
        assert sanitize_name("") == "Unknown"

    def test_only_invalid(self):
        assert sanitize_name(":::") == "Unknown"


class TestBuildPlans:
    def test_single_track(self, tmp_path):
        config = Config(source_root=tmp_path, destination_root=tmp_path / "dest")
        log = ErrorLog()
        track = _make_track()
        grouping = group_tracks([track], config, log)
        result = build_plans(grouping, config, log)

        assert len(result.plans) == 1
        plan = result.plans[0]
        assert plan.album_artist == "Test Artist"
        assert "Test Album [2023]" in str(plan.destination)
        assert plan.destination.name.startswith("01")

    def test_album_folder_with_year(self, tmp_path):
        config = Config(source_root=tmp_path, destination_root=tmp_path / "dest")
        log = ErrorLog()
        track = _make_track(year="1999")
        grouping = group_tracks([track], config, log)
        result = build_plans(grouping, config, log)

        dest = result.plans[0].destination
        assert "Test Album [1999]" in str(dest)

    def test_album_folder_without_year(self, tmp_path):
        config = Config(source_root=tmp_path, destination_root=tmp_path / "dest")
        log = ErrorLog()
        track = _make_track(year=None)
        grouping = group_tracks([track], config, log)
        result = build_plans(grouping, config, log)

        dest = result.plans[0].destination
        # Should not have " - " separator for year
        parent_name = dest.parent.name
        assert parent_name == "Test Album"

    def test_track_number_padded(self, tmp_path):
        config = Config(source_root=tmp_path, destination_root=tmp_path / "dest")
        log = ErrorLog()
        track = _make_track(tracknumber=5)
        grouping = group_tracks([track], config, log)
        result = build_plans(grouping, config, log)

        dest = result.plans[0].destination
        assert dest.name.startswith("05 - ")

    def test_collision_detected(self, tmp_path):
        config = Config(source_root=tmp_path, destination_root=tmp_path / "dest")
        log = ErrorLog()
        # Two tracks with same artist/album/title/tracknumber
        tracks = [
            _make_track(
                source_path=Path("/source/a.mp3"),
                title="Same Song",
                tracknumber=1,
            ),
            _make_track(
                source_path=Path("/source/b.mp3"),
                title="Same Song",
                tracknumber=1,
            ),
        ]
        grouping = group_tracks(tracks, config, log)
        result = build_plans(grouping, config, log)

        assert len(result.plans) == 2
        assert len(result.collisions) == 1
        # Collision should have (2) in name
        collision_dest = result.plans[1].destination
        assert "(2)" in collision_dest.name

    def test_compilation_artist_folder(self, tmp_path):
        config = Config(source_root=tmp_path, destination_root=tmp_path / "dest")
        log = ErrorLog()
        track = _make_track(compilation=True)
        grouping = group_tracks([track], config, log)
        result = build_plans(grouping, config, log)

        dest = result.plans[0].destination
        assert "Various Artists" in str(dest)

    def test_plans_sorted_by_tracknumber(self, tmp_path):
        config = Config(source_root=tmp_path, destination_root=tmp_path / "dest")
        log = ErrorLog()
        tracks = [
            _make_track(source_path=Path("/s/3.mp3"), title="Third", tracknumber=3),
            _make_track(source_path=Path("/s/1.mp3"), title="First", tracknumber=1),
            _make_track(source_path=Path("/s/2.mp3"), title="Second", tracknumber=2),
        ]
        grouping = group_tracks(tracks, config, log)
        result = build_plans(grouping, config, log)

        names = [p.destination.name for p in result.plans]
        assert names[0].startswith("01")
        assert names[1].startswith("02")
        assert names[2].startswith("03")
