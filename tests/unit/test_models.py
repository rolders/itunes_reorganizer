"""Tests for the V2 models."""

from pathlib import Path

import pytest

from itunes_reorganizer.metadata import TrackMetadata
from itunes_reorganizer.models import AlbumGroup, ReleaseType, Route


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


class TestReleaseType:
    def test_album_6_tracks(self):
        group = AlbumGroup(album_artist="A", album="B", tracks=[_make_track(tracknumber=i) for i in range(6)])
        assert group.release_type == ReleaseType.ALBUM

    def test_album_10_tracks(self):
        group = AlbumGroup(album_artist="A", album="B", tracks=[_make_track(tracknumber=i) for i in range(10)])
        assert group.release_type == ReleaseType.ALBUM

    def test_ep_2_tracks(self):
        group = AlbumGroup(album_artist="A", album="B", tracks=[_make_track(tracknumber=i) for i in range(2)])
        assert group.release_type == ReleaseType.EP

    def test_ep_5_tracks(self):
        group = AlbumGroup(album_artist="A", album="B", tracks=[_make_track(tracknumber=i) for i in range(5)])
        assert group.release_type == ReleaseType.EP

    def test_single_1_track(self):
        group = AlbumGroup(album_artist="A", album="B", tracks=[_make_track()])
        assert group.release_type == ReleaseType.SINGLE


class TestIsCompilation:
    def test_va_album_artist(self):
        group = AlbumGroup(album_artist="Various Artists", album="Comp", tracks=[
            _make_track(artist="A"), _make_track(artist="B"),
        ])
        assert group.is_compilation is True

    def test_multiple_artists(self):
        group = AlbumGroup(album_artist="Some Label", album="Comp", tracks=[
            _make_track(artist="Artist A"), _make_track(artist="Artist B"),
        ])
        assert group.is_compilation is True

    def test_single_artist(self):
        group = AlbumGroup(album_artist="Solo Artist", album="Album", tracks=[
            _make_track(artist="Solo Artist"), _make_track(artist="Solo Artist"),
        ])
        assert group.is_compilation is False

    def test_compilation_overrides_track_count(self):
        """Even with 1 track, if it's VA it's a compilation."""
        group = AlbumGroup(album_artist="Various Artists", album="Comp", tracks=[
            _make_track(artist="A"),
        ])
        assert group.release_type == ReleaseType.COMPILATION
