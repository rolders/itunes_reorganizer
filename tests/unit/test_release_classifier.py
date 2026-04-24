"""Tests for the release classifier."""

from pathlib import Path

import pytest

from itunes_reorganizer.metadata import TrackMetadata
from itunes_reorganizer.models import AlbumGroup, ReleaseType
from itunes_reorganizer.release_classifier import classify_release


def _make_track(**overrides) -> TrackMetadata:
    defaults = {
        "source_path": Path("test.mp3"),
        "title": "Test Song",
        "album": "Test Album",
        "albumartist": "Test Artist",
        "tracknumber": 1,
    }
    defaults.update(overrides)
    return TrackMetadata(**defaults)


class TestClassifyRelease:
    def test_album(self):
        group = AlbumGroup(album_artist="A", album="B", tracks=[_make_track(tracknumber=i) for i in range(8)])
        assert classify_release(group) == ReleaseType.ALBUM

    def test_ep(self):
        group = AlbumGroup(album_artist="A", album="B", tracks=[_make_track(tracknumber=i) for i in range(3)])
        assert classify_release(group) == ReleaseType.EP

    def test_single(self):
        group = AlbumGroup(album_artist="A", album="B", tracks=[_make_track()])
        assert classify_release(group) == ReleaseType.SINGLE

    def test_compilation(self):
        group = AlbumGroup(
            album_artist="Various Artists",
            album="Comp",
            tracks=[_make_track(artist="A"), _make_track(artist="B")],
        )
        assert classify_release(group) == ReleaseType.COMPILATION
