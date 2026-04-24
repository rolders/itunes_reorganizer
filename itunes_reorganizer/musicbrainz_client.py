"""MusicBrainz client: optional enrichment and validation."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .models import AlbumGroup

logger = logging.getLogger(__name__)

MIN_CONFIDENCE = 0.9


@dataclass
class MBResult:
    """Result from a MusicBrainz lookup."""
    release_id: Optional[str] = None
    title: Optional[str] = None
    artist: Optional[str] = None
    year: Optional[str] = None
    label: Optional[str] = None
    catalog_number: Optional[str] = None
    release_type: Optional[str] = None
    confidence: float = 0.0


class MusicBrainzCache:
    """Simple file-based cache for MusicBrainz results."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir
        self._memory: dict[str, MBResult] = {}
        if cache_dir:
            self._load_disk_cache()

    def _cache_path(self) -> Path:
        return self.cache_dir / "musicbrainz_cache.json" if self.cache_dir else Path("musicbrainz_cache.json")

    def _load_disk_cache(self) -> None:
        path = self._cache_path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for key, val in data.items():
                    self._memory[key] = MBResult(**val)
            except Exception:
                logger.warning("Could not load MusicBrainz cache from %s", path)

    def _save_disk_cache(self) -> None:
        if not self.cache_dir:
            return
        path = self._cache_path()
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            data = {k: vars(v) for k, v in self._memory.items()}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            logger.warning("Could not save MusicBrainz cache to %s", path)

    def get(self, key: str) -> Optional[MBResult]:
        return self._memory.get(key)

    def put(self, key: str, result: MBResult) -> None:
        self._memory[key] = result
        self._save_disk_cache()


class MusicBrainzClient:
    """
    MusicBrainz lookup client.
    Uses musicbrainzngs if available, otherwise no-ops.
    Only accepts results with confidence >= MIN_CONFIDENCE.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache = MusicBrainzCache(cache_dir)
        self._mb_module = None
        try:
            import musicbrainzngs
            musicbrainzngs.set_useragent("itunes_reorganizer", "2.0", "https://github.com/example")
            self._mb_module = musicbrainzngs
        except ImportError:
            logger.info("musicbrainzngs not installed; MusicBrainz enrichment disabled")

    @property
    def available(self) -> bool:
        return self._mb_module is not None

    def lookup_release(self, artist: str, album: str) -> Optional[MBResult]:
        """Look up a release by artist and album name."""
        if not self.available:
            return None

        cache_key = f"{artist}|||{album}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            result = self._do_lookup(artist, album)
            if result:
                self.cache.put(cache_key, result)
            return result
        except Exception as e:
            logger.warning("MusicBrainz lookup failed for %s / %s: %s", artist, album, e)
            return None

    def _do_lookup(self, artist: str, album: str) -> Optional[MBResult]:
        """Perform the actual MusicBrainz lookup."""
        mb = self._mb_module

        # Search for the release
        search_result = mb.search_releases(
            artist=artist,
            release=album,
            limit=5,
        )

        releases = search_result.get("release-list", [])
        if not releases:
            return None

        # Find the best match
        best = None
        best_score = 0.0

        for rel in releases:
            score = int(rel.get("ext:score", 0)) / 100.0
            if score > best_score:
                best_score = score
                best = rel

        if best is None or best_score < MIN_CONFIDENCE:
            return None

        # Get detailed release info
        release_id = best["id"]
        try:
            detail = mb.get_release_by_id(
                release_id,
                includes=["labels", "media", "release-groups"],
            )
        except Exception:
            detail = {"release": best}

        release = detail.get("release", best)

        result = MBResult(
            release_id=release_id,
            title=release.get("title"),
            year=_extract_year(release),
            confidence=best_score,
        )

        # Extract label info
        label_info = release.get("label-info-list", [])
        if label_info:
            first_label = label_info[0]
            label_obj = first_label.get("label", {})
            if label_obj:
                result.label = label_obj.get("name")
            result.catalog_number = first_label.get("catalog-number")

        # Extract release type from release group
        rg = release.get("release-group", {})
        if rg:
            result.release_type = rg.get("primary-type", "").lower()

        # Extract artist
        artist_credit = release.get("artist-credit", [])
        if artist_credit:
            result.artist = artist_credit[0].get("artist", {}).get("name")

        return result

    def enrich_group(self, group: AlbumGroup) -> None:
        """
        Enrich an AlbumGroup with MusicBrainz data.
        Never overrides existing values blindly — only fills in missing data.
        """
        if not self.available:
            return

        result = self.lookup_release(group.album_artist, group.album)
        if result is None:
            return

        if result.confidence < MIN_CONFIDENCE:
            return

        # Only fill in missing values
        if not group.year and result.year:
            group.year = result.year
        if not group.label and result.label:
            group.label = result.label
        if not group.catalog_number and result.catalog_number:
            group.catalog_number = result.catalog_number


def _extract_year(release: dict) -> Optional[str]:
    """Extract year from a MusicBrainz release dict."""
    date = release.get("date", "")
    if date:
        return date[:4] if len(date) >= 4 else None
    return None
