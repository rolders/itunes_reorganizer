"""Router: determine destination route (Artists, Compilations, or Labels)."""

from __future__ import annotations

from .config import Config
from .models import AlbumGroup, Route, ReleaseType


DEFAULT_DANCE_GENRES = frozenset({
    "electronic", "techno", "house", "trance", "dnb", "ambient",
    "drum and bass", "drum & bass", "dubstep", "breakbeat",
    "deep house", "tech house", "progressive house",
})


def route_album(group: AlbumGroup, config: Config) -> Route:
    """
    Determine the routing for an album group.

    Logic:
    IF compilation → Compilations
    ELIF album → Artists
    ELIF EP/single AND dance + label → Labels
    ELSE → Artists
    """
    release_type = group.release_type

    if release_type == ReleaseType.COMPILATION:
        return Route.COMPILATIONS

    if release_type == ReleaseType.ALBUM:
        return Route.ARTISTS

    # EP or single
    if config.enable_label_routing and group.label:
        # Check if genre is dance-related
        if _has_dance_genre(group, config):
            return Route.LABELS

    return Route.ARTISTS


def _has_dance_genre(group: AlbumGroup, config: Config) -> bool:
    """Check if any track in the group has a dance genre."""
    dance_genres = set(config.dance_genres) if config.dance_genres else set(DEFAULT_DANCE_GENRES)
    dance_genres = {g.lower() for g in dance_genres}

    for track in group.tracks:
        if track.genre:
            track_genres = {g.strip().lower() for g in track.genre.split(",")}
            if track_genres & dance_genres:
                return True

    return False
