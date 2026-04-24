"""Domain models for V2 album-based logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from .metadata import TrackMetadata


class ReleaseType(str, Enum):
    ALBUM = "album"
    EP = "ep"
    SINGLE = "single"
    COMPILATION = "compilation"


class Route(str, Enum):
    ARTISTS = "Artists"
    COMPILATIONS = "Compilations"
    LABELS = "Labels"


@dataclass
class AlbumGroup:
    """A group of tracks belonging to the same album."""
    album_artist: str
    album: str
    year: Optional[str] = None
    label: Optional[str] = None
    catalog_number: Optional[str] = None
    tracks: list[TrackMetadata] = field(default_factory=list)

    @property
    def is_compilation(self) -> bool:
        """True if this album is a compilation (multiple track artists)."""
        if self.album_artist.lower() == "various artists":
            return True
        artists = {t.artist for t in self.tracks if t.artist}
        return len(artists) > 1

    @property
    def release_type(self) -> ReleaseType:
        """Classify the release based on track count."""
        if self.is_compilation:
            return ReleaseType.COMPILATION
        count = len(self.tracks)
        if count >= 6:
            return ReleaseType.ALBUM
        if count >= 2:
            return ReleaseType.EP
        return ReleaseType.SINGLE

    @property
    def sort_key(self) -> str:
        year_str = self.year or "0000"
        return f"{self.album_artist}::{year_str}::{self.album}".lower()


@dataclass
class AlbumPlan:
    """A planned album-level operation with resolved route and paths."""
    group: AlbumGroup
    route: Route
    release_type: ReleaseType
    destination_dir: Path = field(default_factory=Path)
    file_plans: list[FilePlan] = field(default_factory=list)


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
    artist: Optional[str] = None
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
    album_plans: list[AlbumPlan] = field(default_factory=list)
    plans: list[FilePlan] = field(default_factory=list)
    collisions: list[FilePlan] = field(default_factory=list)


@dataclass
class GroupingResult:
    """Result of the grouping step."""
    groups: dict[str, AlbumGroup] = field(default_factory=dict)
    skipped: list[TrackMetadata] = field(default_factory=list)
