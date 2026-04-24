"""Naming rules for album folders and track filenames."""

from __future__ import annotations

import re
from typing import Optional

from .models import AlbumGroup, AlbumPlan, Route, ReleaseType


def sanitize_name(name: str) -> str:
    """Remove or replace characters that are invalid in filenames."""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name)
    name = name.strip(' .')
    return name or "Unknown"


def build_album_folder(group: AlbumGroup) -> str:
    """Build album folder name: 'Album [Year]'."""
    album_name = sanitize_name(group.album)
    if group.year:
        return f"{album_name} [{group.year}]"
    return album_name


def build_artist_track_filename(tracknumber: int, title: str, extension: str) -> str:
    """Build filename for artist-routed tracks: '01 - Title.ext'."""
    tn = tracknumber or 0
    clean_title = sanitize_name(title or "Unknown Title")
    return f"{tn:02d} - {clean_title}{extension}"


def build_compilation_track_filename(tracknumber: int, artist: str, title: str, extension: str) -> str:
    """Build filename for compilation tracks: '01 - Artist - Title.ext'."""
    tn = tracknumber or 0
    clean_artist = sanitize_name(artist or "Unknown Artist")
    clean_title = sanitize_name(title or "Unknown Title")
    return f"{tn:02d} - {clean_artist} - {clean_title}{extension}"


def build_label_folder(group: AlbumGroup) -> str:
    """Build label folder name: 'CATNO - Artist - Album [Year]'."""
    catno = sanitize_name(group.catalog_number or "Unknown")
    artist = sanitize_name(group.album_artist)
    album_name = sanitize_name(group.album)
    if group.year:
        return f"{catno} - {artist} - {album_name} [{group.year}]"
    return f"{catno} - {artist} - {album_name}"


def build_destination_dir(
    plan: AlbumPlan,
    destination_root,
) -> "Path":
    """Build the full destination directory path for an album plan."""
    from pathlib import Path

    dest_root = Path(destination_root)

    if plan.route == Route.COMPILATIONS:
        album_folder = build_album_folder(plan.group)
        artist_folder = sanitize_name(plan.group.album_artist)
        return dest_root / "Compilations" / artist_folder / album_folder

    elif plan.route == Route.LABELS:
        label_folder = build_label_folder(plan.group)
        label_name = sanitize_name(plan.group.label or "Unknown Label")
        return dest_root / "Labels" / label_name / label_folder

    else:  # Route.ARTISTS
        album_folder = build_album_folder(plan.group)
        artist_folder = sanitize_name(plan.group.album_artist)
        return dest_root / "Artists" / artist_folder / album_folder
