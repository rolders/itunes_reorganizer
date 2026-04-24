"""Album grouper: group tracks by (album_artist_resolved, album_normalized)."""

from __future__ import annotations

from typing import Optional

from .config import Config
from .errors import ErrorLog
from .metadata import TrackMetadata
from .models import AlbumGroup, GroupingResult


def _album_artist_resolved(meta: TrackMetadata, config: Config) -> str:
    """
    Resolve album artist per spec:
    IF album_artist exists → use it
    ELIF multiple artists → "Various Artists"
    ELSE → artist
    """
    if meta.albumartist:
        return meta.albumartist
    if not meta.artist:
        return "Unknown Artist"
    return meta.artist


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
        if not meta.artist:
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


def _detect_compilation(tracks: list[TrackMetadata]) -> bool:
    """Check if a group of tracks represents a compilation."""
    artists = {t.artist for t in tracks if t.artist}
    return len(artists) > 1


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

        artist = _album_artist_resolved(meta, config)
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

    # Post-process: detect compilations from track-level hints
    # and update album_artist to "Various Artists" if needed
    for group in result.groups.values():
        # Check if any track has compilation flag or albumartist = Various Artists
        has_comp_flag = any(t.compilation for t in group.tracks)
        has_va_albumartist = any(
            t.albumartist and t.albumartist.lower() == "various artists"
            for t in group.tracks
        )
        if has_comp_flag or has_va_albumartist:
            group.album_artist = "Various Artists"

    return result
