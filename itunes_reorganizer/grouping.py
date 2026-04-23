"""Grouping: organise validated tracks into album groups."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .config import Config
from .errors import ErrorLog
from .metadata import TrackMetadata


@dataclass
class AlbumGroup:
    """A group of tracks belonging to the same album."""
    album_artist: str
    album: str
    year: Optional[str] = None
    tracks: list[TrackMetadata] = field(default_factory=list)

    @property
    def sort_key(self) -> str:
        year_str = self.year or "0000"
        return f"{self.album_artist}::{year_str}::{self.album}".lower()


@dataclass
class GroupingResult:
    """Result of the grouping step."""
    groups: dict[str, AlbumGroup] = field(default_factory=dict)
    skipped: list[TrackMetadata] = field(default_factory=list)


def _album_key(artist: str, album: str, year: Optional[str]) -> str:
    """Create a unique key for an album."""
    return f"{artist}|||{album}|||{year or 'unknown'}"


def validate_track(meta: TrackMetadata, config: Config, error_log: ErrorLog) -> bool:
    """Check if a track has all required metadata. Returns True if valid."""
    missing = []

    if not meta.album:
        missing.append("album")
    if not meta.title:
        missing.append("title")
    if meta.tracknumber is None:
        missing.append("tracknumber")

    effective_artist = meta.effective_albumartist
    if config.fallback_to_artist and not effective_artist:
        if meta.artist:
            # Fall back to track artist
            pass
        else:
            missing.append("albumartist/artist")
    elif not config.fallback_to_artist and not effective_artist:
        if not meta.albumartist:
            missing.append("albumartist")

    if missing:
        error_log.add_skip(
            f"Missing required metadata: {', '.join(missing)}",
            meta.source_path,
            operation="validate",
        )
        return False

    return True


def _effective_artist(meta: TrackMetadata, config: Config) -> str:
    """Determine the effective artist for folder naming."""
    effective = meta.effective_albumartist
    if effective:
        return effective
    if config.fallback_to_artist and meta.artist:
        return meta.artist
    return "Unknown Artist"


def group_tracks(
    tracks: list[TrackMetadata],
    config: Config,
    error_log: ErrorLog,
) -> GroupingResult:
    """
    Validate tracks and group them by album.
    Skipped tracks go into result.skipped.
    """
    result = GroupingResult()

    for meta in tracks:
        if not validate_track(meta, config, error_log):
            result.skipped.append(meta)
            continue

        artist = _effective_artist(meta, config)
        album = meta.album or "Unknown Album"
        year = meta.year

        key = _album_key(artist, album, year)

        if key not in result.groups:
            result.groups[key] = AlbumGroup(
                album_artist=artist,
                album=album,
                year=year,
            )

        result.groups[key].tracks.append(meta)

    return result
