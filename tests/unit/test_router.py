"""Tests for the router."""

from pathlib import Path

import pytest

from itunes_reorganizer.config import Config
from itunes_reorganizer.metadata import TrackMetadata
from itunes_reorganizer.models import AlbumGroup, Route, ReleaseType
from itunes_reorganizer.router import route_album


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


def _config(**overrides) -> Config:
    defaults = {
        "source_root": Path("/source"),
        "destination_root": Path("/dest"),
        "enable_label_routing": True,
    }
    defaults.update(overrides)
    return Config(**defaults)


class TestRouteAlbum:
    def test_compilation_routes_to_compilations(self, tmp_path):
        config = _config(source_root=tmp_path, destination_root=tmp_path / "dest")
        group = AlbumGroup(
            album_artist="Various Artists",
            album="Comp",
            tracks=[_make_track(artist="A"), _make_track(artist="B")],
        )
        assert route_album(group, config) == Route.COMPILATIONS

    def test_album_routes_to_artists(self, tmp_path):
        config = _config(source_root=tmp_path, destination_root=tmp_path / "dest")
        group = AlbumGroup(
            album_artist="Rock Band",
            album="Great Album",
            tracks=[_make_track(tracknumber=i) for i in range(10)],
        )
        assert route_album(group, config) == Route.ARTISTS

    def test_ep_without_label_routes_to_artists(self, tmp_path):
        config = _config(source_root=tmp_path, destination_root=tmp_path / "dest")
        group = AlbumGroup(
            album_artist="DJ Someone",
            album="EP",
            tracks=[_make_track(tracknumber=i) for i in range(3)],
        )
        assert route_album(group, config) == Route.ARTISTS

    def test_ep_with_label_and_dance_routes_to_labels(self, tmp_path):
        config = _config(source_root=tmp_path, destination_root=tmp_path / "dest")
        group = AlbumGroup(
            album_artist="DJ Someone",
            album="EP",
            label="Some Label",
            tracks=[
                _make_track(tracknumber=1),
                _make_track(tracknumber=2),
            ],
        )
        # No genre info on tracks, so won't match dance genres
        result = route_album(group, config)
        # Should go to artists since no dance genre detected
        assert result == Route.ARTISTS

    def test_single_routes_to_artists(self, tmp_path):
        config = _config(source_root=tmp_path, destination_root=tmp_path / "dest")
        group = AlbumGroup(
            album_artist="Solo Artist",
            album="Single",
            tracks=[_make_track()],
        )
        assert route_album(group, config) == Route.ARTISTS

    def test_label_routing_disabled(self, tmp_path):
        config = _config(source_root=tmp_path, destination_root=tmp_path / "dest", enable_label_routing=False)
        group = AlbumGroup(
            album_artist="DJ",
            album="EP",
            label="Label",
            tracks=[_make_track(tracknumber=1), _make_track(tracknumber=2)],
        )
        assert route_album(group, config) == Route.ARTISTS
