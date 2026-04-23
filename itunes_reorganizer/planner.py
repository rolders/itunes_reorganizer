"""Planner: build file operation plans from album groups."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .config import Config
from .errors import ErrorLog
from .grouping import AlbumGroup, GroupingResult
from .metadata import TrackMetadata


@dataclass
class FilePlan:
    """A planned file operation."""
    source: Path
    destination: Path
    album_artist: str
    album: str
    year: Optional[str]
    title: str
    tracknumber: int
    extension: str
    collision_suffix: int = 0  # 0 = no collision

    @property
    def display_source(self) -> str:
        return str(self.source)

    @property
    def display_destination(self) -> str:
        return str(self.destination)


@dataclass
class PlanResult:
    """Result of the planning step."""
    plans: list[FilePlan] = field(default_factory=list)
    collisions: list[FilePlan] = field(default_factory=list)


def _sanitize_name(name: str) -> str:
    """Remove or replace characters that are invalid in filenames."""
    # Remove characters invalid on Windows/macOS/Linux
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Replace multiple spaces with single
    name = re.sub(r'\s+', ' ', name)
    # Strip leading/trailing spaces and dots
    name = name.strip(' .')
    # Don't allow empty
    return name or "Unknown"


def _build_album_folder(group: AlbumGroup) -> str:
    """Build the album folder name: 'Year - Album' or just 'Album'."""
    album_name = _sanitize_name(group.album)
    if group.year:
        return f"{group.year} - {album_name}"
    return album_name


def _build_track_filename(track: TrackMetadata) -> tuple[str, str]:
    """Build the track filename. Returns (base_name, extension)."""
    title = _sanitize_name(track.title or "Unknown Title")
    tracknum = track.tracknumber or 0
    ext = track.source_path.suffix.lower()

    # Format track number with leading zero if needed
    filename = f"{tracknum:02d} - {title}{ext}"
    return filename


def _resolve_collision(dest: Path, existing_destinations: set[Path]) -> Path:
    """
    If dest already exists in the plan, append (2), (3), etc.
    Returns the resolved path.
    """
    if dest not in existing_destinations:
        return dest

    stem = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    counter = 2

    while True:
        new_name = f"{stem} ({counter}){suffix}"
        new_path = parent / new_name
        if new_path not in existing_destinations:
            return new_path
        counter += 1


def build_plans(
    grouping_result: GroupingResult,
    config: Config,
    error_log: ErrorLog,
) -> PlanResult:
    """
    Build file operation plans from grouped albums.
    Detects and resolves collisions.
    """
    result = PlanResult()
    existing_destinations: set[Path] = set()

    # Sort groups for deterministic output
    sorted_groups = sorted(grouping_result.groups.values(), key=lambda g: g.sort_key)

    for group in sorted_groups:
        artist_folder = _sanitize_name(group.album_artist)
        album_folder = _build_album_folder(group)

        # Sort tracks by track number
        sorted_tracks = sorted(group.tracks, key=lambda t: t.tracknumber or 0)

        for track in sorted_tracks:
            filename = _build_track_filename(track)
            dest_dir = config.destination_root / artist_folder / album_folder
            dest_path = dest_dir / filename

            # Resolve collisions
            original_dest = dest_path
            dest_path = _resolve_collision(dest_path, existing_destinations)

            plan = FilePlan(
                source=track.source_path,
                destination=dest_path,
                album_artist=group.album_artist,
                album=group.album,
                year=group.year,
                title=track.title or "Unknown Title",
                tracknumber=track.tracknumber or 0,
                extension=track.source_path.suffix.lower(),
                collision_suffix=0 if dest_path == original_dest else 1,
            )

            if plan.collision_suffix > 0:
                result.collisions.append(plan)

            existing_destinations.add(dest_path)
            result.plans.append(plan)

    return result
