"""Album grouper: group tracks by (album_normalized, year), then resolve album artist."""

from __future__ import annotations

from typing import Optional

from .config import Config
from .errors import ErrorLog
from .metadata import TrackMetadata
from .models import AlbumGroup, GroupingResult


def _album_key(album: str, year: Optional[str]) -> str:
    """Create a unique key for an album (artist-agnostic)."""
    return f"{album}|||{year or 'unknown'}"


def validate_track(meta: TrackMetadata, config: Config, error_log: ErrorLog) -> bool:
    """Check if a track has all required metadata. Returns True if valid."""
    missing = []

    if not meta.album:
        missing.append("album")
    if not meta.title:
        missing.append("title")
    if meta.tracknumber is None:
        missing.append("tracknumber")

    # Note: albumartist/artist is NOT required for validation.
    # The album artist is resolved at the group level in _resolve_group_artist(),
    # so individual tracks are accepted even without albumartist.
    # This correctly handles cases like soundtracks or EPs where some tracks
    # have albumartist set and others don't.

    if missing:
        error_log.add_skip(
            f"Missing required metadata: {', '.join(missing)}",
            meta.source_path,
            operation="validate",
        )
        return False

    return True


def _resolve_group_artist(group: AlbumGroup, config: Config) -> str:
    """
    Resolve the album artist for an entire group (post-grouping).

    Logic:
    1. If any track has compilation flag → "Various Artists"
    2. If any track has albumartist = "Various Artists" → "Various Artists"
    3. If all tracks share the same albumartist → use it
    4. If multiple different albumartists → "Various Artists" (soundtrack/compilation)
    5. Fallback: if fallback_to_artist and single common artist → use it
    6. Else → first track's albumartist or "Unknown Artist"
    """
    tracks = group.tracks

    # 1. Compilation flag
    if any(t.compilation for t in tracks):
        return "Various Artists"

    # 2. Any track has albumartist = "Various Artists"
    if any(t.albumartist and t.albumartist.lower() == "various artists" for t in tracks):
        return "Various Artists"

    # 3. All tracks share the same albumartist
    albumartists = {t.albumartist for t in tracks if t.albumartist}
    if len(albumartists) == 1:
        return albumartists.pop()

    # 4. Multiple different albumartists → compilation
    if len(albumartists) > 1:
        return "Various Artists"

    # 5. No albumartist set — fall back to track artists
    artists = {t.artist for t in tracks if t.artist}
    if config.fallback_to_artist and len(artists) == 1:
        return artists.pop()

    # 6. Single artist across tracks (no albumartist set)
    if len(artists) == 1:
        return artists.pop()
    if len(artists) > 1:
        return "Various Artists"

    return "Unknown Artist"


def group_tracks(
    tracks: list[TrackMetadata],
    config: Config,
    error_log: ErrorLog,
) -> GroupingResult:
    """
    Validate tracks and group them by album (artist-agnostic key).
    Album artist is resolved post-grouping to correctly handle
    soundtracks and compilations with per-track artists.
    """
    result = GroupingResult()

    # Phase 1: Group by (album, year) — artist-agnostic
    for meta in tracks:
        if not validate_track(meta, config, error_log):
            result.skipped.append(meta)
            continue

        album = meta.album or "Unknown Album"
        year = meta.year
        key = _album_key(album, year)

        if key not in result.groups:
            result.groups[key] = AlbumGroup(
                album_artist="",  # resolved in phase 2
                album=album,
                year=year,
            )

        result.groups[key].tracks.append(meta)

    # Phase 2: Resolve album artist for each group
    for group in result.groups.values():
        group.album_artist = _resolve_group_artist(group, config)

    return result
