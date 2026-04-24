"""Planner: build file operation plans from album groups (V2 — album-based)."""

from __future__ import annotations

from pathlib import Path

from .album_grouper import group_tracks
from .config import Config
from .errors import ErrorLog
from .models import AlbumGroup, AlbumPlan, FilePlan, GroupingResult, PlanResult, Route
from .naming import (
    build_album_folder,
    build_artist_track_filename,
    build_compilation_track_filename,
    build_destination_dir,
    build_label_folder,
    sanitize_name,
)
from .release_classifier import classify_release
from .router import route_album
from .metadata import TrackMetadata


def build_plans(
    grouping_result: GroupingResult,
    config: Config,
    error_log: ErrorLog,
) -> PlanResult:
    """
    Build file operation plans from grouped albums.
    V2: album-based routing with Artists/Compilations/Labels structure.
    """
    result = PlanResult()
    existing_destinations: set[Path] = set()

    # Sort groups for deterministic output
    sorted_groups = sorted(grouping_result.groups.values(), key=lambda g: g.sort_key)

    for group in sorted_groups:
        release_type = classify_release(group)
        route = route_album(group, config)

        album_plan = AlbumPlan(
            group=group,
            route=route,
            release_type=release_type,
        )

        # Build destination directory
        dest_dir = build_destination_dir(album_plan, config.destination_root)
        album_plan.destination_dir = dest_dir

        # Sort tracks by track number
        sorted_tracks = sorted(group.tracks, key=lambda t: t.tracknumber or 0)

        for track in sorted_tracks:
            ext = track.source_path.suffix.lower()

            # Choose filename format based on route
            if route == Route.COMPILATIONS:
                filename = build_compilation_track_filename(
                    track.tracknumber or 0,
                    track.artist or "Unknown Artist",
                    track.title or "Unknown Title",
                    ext,
                )
            else:
                filename = build_artist_track_filename(
                    track.tracknumber or 0,
                    track.title or "Unknown Title",
                    ext,
                )

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
                extension=ext,
                artist=track.artist,
                collision_suffix=0 if dest_path == original_dest else 1,
            )

            if plan.collision_suffix > 0:
                result.collisions.append(plan)

            existing_destinations.add(dest_path)
            result.plans.append(plan)
            album_plan.file_plans.append(plan)

        result.album_plans.append(album_plan)

    return result


def _resolve_collision(dest: Path, existing_destinations: set[Path]) -> Path:
    """If dest already exists in the plan, append (2), (3), etc."""
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
