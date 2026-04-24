"""Tests for the naming module."""

from pathlib import Path

import pytest

from itunes_reorganizer.metadata import TrackMetadata
from itunes_reorganizer.models import AlbumGroup, AlbumPlan, Route, ReleaseType
from itunes_reorganizer.naming import (
    build_album_folder,
    build_artist_track_filename,
    build_compilation_track_filename,
    build_label_folder,
    build_destination_dir,
    sanitize_name,
)


class TestBuildAlbumFolder:
    def test_with_year(self):
        group = AlbumGroup(album_artist="A", album="Great Album", year="2023")
        assert build_album_folder(group) == "Great Album [2023]"

    def test_without_year(self):
        group = AlbumGroup(album_artist="A", album="Great Album")
        assert build_album_folder(group) == "Great Album"


class TestBuildArtistTrackFilename:
    def test_normal(self):
        assert build_artist_track_filename(1, "Song Title", ".mp3") == "01 - Song Title.mp3"

    def test_zero_tracknumber(self):
        assert build_artist_track_filename(0, "Song", ".flac") == "00 - Song.flac"

    def test_double_digit(self):
        assert build_artist_track_filename(12, "Song", ".mp3") == "12 - Song.mp3"


class TestBuildCompilationTrackFilename:
    def test_normal(self):
        result = build_compilation_track_filename(1, "Artist A", "Song Title", ".mp3")
        assert result == "01 - Artist A - Song Title.mp3"


class TestBuildLabelFolder:
    def test_with_year(self):
        group = AlbumGroup(
            album_artist="DJ X",
            album="Banger EP",
            year="2023",
            label="Tech Records",
            catalog_number="TECH001",
        )
        assert build_label_folder(group) == "TECH001 - DJ X - Banger EP [2023]"

    def test_without_year(self):
        group = AlbumGroup(
            album_artist="DJ X",
            album="Banger EP",
            label="Tech Records",
            catalog_number="TECH001",
        )
        assert build_label_folder(group) == "TECH001 - DJ X - Banger EP"


class TestBuildDestinationDir:
    def test_artists_route(self, tmp_path):
        group = AlbumGroup(album_artist="Rock Band", album="Album", year="2020")
        plan = AlbumPlan(group=group, route=Route.ARTISTS, release_type=ReleaseType.ALBUM)
        dest = build_destination_dir(plan, tmp_path)
        assert dest == tmp_path / "Artists" / "Rock Band" / "Album [2020]"

    def test_compilations_route(self, tmp_path):
        group = AlbumGroup(album_artist="Various Artists", album="Comp", year="2021")
        plan = AlbumPlan(group=group, route=Route.COMPILATIONS, release_type=ReleaseType.COMPILATION)
        dest = build_destination_dir(plan, tmp_path)
        assert dest == tmp_path / "Compilations" / "Various Artists" / "Comp [2021]"

    def test_labels_route(self, tmp_path):
        group = AlbumGroup(
            album_artist="DJ X",
            album="EP",
            year="2023",
            label="Tech Records",
            catalog_number="TECH001",
        )
        plan = AlbumPlan(group=group, route=Route.LABELS, release_type=ReleaseType.EP)
        dest = build_destination_dir(plan, tmp_path)
        assert dest == tmp_path / "Labels" / "Tech Records" / "TECH001 - DJ X - EP [2023]"
