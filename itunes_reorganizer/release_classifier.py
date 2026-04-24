"""Release classifier: classify albums as album, EP, single, or compilation."""

from __future__ import annotations

from .models import AlbumGroup, ReleaseType


def classify_release(group: AlbumGroup) -> ReleaseType:
    """
    Classify a release based on its properties.

    Logic:
    - compilation if multiple track artists or album_artist = Various Artists
    - >= 6 tracks → album
    - 2–5 tracks → EP
    - 1 track → single
    """
    if group.is_compilation:
        return ReleaseType.COMPILATION

    count = len(group.tracks)
    if count >= 6:
        return ReleaseType.ALBUM
    if count >= 2:
        return ReleaseType.EP
    return ReleaseType.SINGLE
