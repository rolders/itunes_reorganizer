"""Tests for the grouping module."""

from pathlib import Path

import pytest

from itunes_reorganizer.config import Config
from itunes_reorganizer.errors import ErrorLog
from itunes_reorganizer.album_grouper import group_tracks, validate_track
from itunes_reorganizer.metadata import TrackMetadata


def _make_track(**overrides) -> TrackMetadata:
    defaults = {
        "source_path": Path("test.mp3"),
        "title": "Test Song",
        "album": "Test Album",
        "albumartist": "Test Artist",
        "tracknumber": 1,
        "year": "2023",
    }
    defaults.update(overrides)
    return TrackMetadata(**defaults)


class TestValidateTrack:
    def test_valid_track(self, tmp_path):
        config = Config(source_root=tmp_path, destination_root=tmp_path / "dest")
        log = ErrorLog()
        track = _make_track()
        assert validate_track(track, config, log) is True

    def test_missing_album(self, tmp_path):
        config = Config(source_root=tmp_path, destination_root=tmp_path / "dest")
        log = ErrorLog()
        track = _make_track(album=None)
        assert validate_track(track, config, log) is False

    def test_missing_title(self, tmp_path):
        config = Config(source_root=tmp_path, destination_root=tmp_path / "dest")
        log = ErrorLog()
        track = _make_track(title=None)
        assert validate_track(track, config, log) is False

    def test_missing_tracknumber(self, tmp_path):
        config = Config(source_root=tmp_path, destination_root=tmp_path / "dest")
        log = ErrorLog()
        track = _make_track(tracknumber=None)
        assert validate_track(track, config, log) is False

    def test_missing_albumartist_no_fallback(self, tmp_path):
        config = Config(source_root=tmp_path, destination_root=tmp_path / "dest", fallback_to_artist=False)
        log = ErrorLog()
        track = _make_track(albumartist=None)
        assert validate_track(track, config, log) is False

    def test_missing_albumartist_with_fallback_and_artist(self, tmp_path):
        config = Config(source_root=tmp_path, destination_root=tmp_path / "dest", fallback_to_artist=True)
        log = ErrorLog()
        track = _make_track(albumartist=None, artist="Fallback Artist")
        assert validate_track(track, config, log) is True

    def test_missing_albumartist_with_fallback_no_artist(self, tmp_path):
        config = Config(source_root=tmp_path, destination_root=tmp_path / "dest", fallback_to_artist=True)
        log = ErrorLog()
        track = _make_track(albumartist=None, artist=None)
        assert validate_track(track, config, log) is False


class TestGroupTracks:
    def test_single_album(self, tmp_path):
        config = Config(source_root=tmp_path, destination_root=tmp_path / "dest")
        log = ErrorLog()
        tracks = [
            _make_track(title="Song 1", tracknumber=1),
            _make_track(title="Song 2", tracknumber=2),
        ]
        result = group_tracks(tracks, config, log)
        assert len(result.groups) == 1
        assert len(list(result.groups.values())[0].tracks) == 2

    def test_multiple_albums(self, tmp_path):
        config = Config(source_root=tmp_path, destination_root=tmp_path / "dest")
        log = ErrorLog()
        tracks = [
            _make_track(album="Album A", tracknumber=1),
            _make_track(album="Album B", tracknumber=1),
        ]
        result = group_tracks(tracks, config, log)
        assert len(result.groups) == 2

    def test_compilation_grouped_together(self, tmp_path):
        config = Config(source_root=tmp_path, destination_root=tmp_path / "dest")
        log = ErrorLog()
        tracks = [
            _make_track(album="Now That's Music", artist="Artist A", albumartist="Various Artists", tracknumber=1),
            _make_track(album="Now That's Music", artist="Artist B", albumartist="Various Artists", tracknumber=2),
        ]
        result = group_tracks(tracks, config, log)
        assert len(result.groups) == 1
        group = list(result.groups.values())[0]
        assert group.album_artist == "Various Artists"

    def test_compilation_flag(self, tmp_path):
        config = Config(source_root=tmp_path, destination_root=tmp_path / "dest")
        log = ErrorLog()
        tracks = [
            _make_track(album="Best Of", artist="Artist A", compilation=True, tracknumber=1),
            _make_track(album="Best Of", artist="Artist B", compilation=True, tracknumber=2),
        ]
        result = group_tracks(tracks, config, log)
        assert len(result.groups) == 1
        group = list(result.groups.values())[0]
        assert group.album_artist == "Various Artists"

    def test_skipped_tracks(self, tmp_path):
        config = Config(source_root=tmp_path, destination_root=tmp_path / "dest")
        log = ErrorLog()
        tracks = [
            _make_track(title="Good Song", tracknumber=1),
            _make_track(title=None, tracknumber=2),  # missing title
        ]
        result = group_tracks(tracks, config, log)
        assert len(result.skipped) == 1
        assert len(result.groups) == 1

    def test_fallback_to_artist(self, tmp_path):
        config = Config(source_root=tmp_path, destination_root=tmp_path / "dest", fallback_to_artist=True)
        log = ErrorLog()
        tracks = [
            _make_track(albumartist=None, artist="Solo Artist", tracknumber=1),
        ]
        result = group_tracks(tracks, config, log)
        assert len(result.groups) == 1
        group = list(result.groups.values())[0]
        assert group.album_artist == "Solo Artist"
