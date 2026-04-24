"""Configuration loading and validation."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .errors import ErrorLog, Severity


DEFAULT_DANCE_GENRES = [
    "electronic", "techno", "house", "trance", "dnb", "ambient",
    "drum and bass", "drum & bass", "dubstep", "breakbeat",
    "deep house", "tech house", "progressive house",
]


@dataclass
class Config:
    source_root: Path
    destination_root: Path
    dry_run: bool = True
    operation: str = "copy"  # "copy" or "move"
    fallback_to_artist: bool = False
    # V2 options
    enable_musicbrainz: bool = False
    enable_label_routing: bool = True
    dance_genres: list[str] = field(default_factory=lambda: list(DEFAULT_DANCE_GENRES))

    @classmethod
    def from_dict(cls, data: dict) -> Config:
        return cls(
            source_root=Path(data["source_root"]),
            destination_root=Path(data["destination_root"]),
            dry_run=data.get("dry_run", True),
            operation=data.get("operation", "copy"),
            fallback_to_artist=data.get("fallback_to_artist", False),
            enable_musicbrainz=data.get("enable_musicbrainz", False),
            enable_label_routing=data.get("enable_label_routing", True),
            dance_genres=data.get("dance_genres", list(DEFAULT_DANCE_GENRES)),
        )

    @classmethod
    def from_file(cls, path: str | Path) -> Config:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Config file not found: {p}")
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def to_dict(self) -> dict:
        return {
            "source_root": str(self.source_root),
            "destination_root": str(self.destination_root),
            "dry_run": self.dry_run,
            "operation": self.operation,
            "fallback_to_artist": self.fallback_to_artist,
            "enable_musicbrainz": self.enable_musicbrainz,
            "enable_label_routing": self.enable_label_routing,
            "dance_genres": self.dance_genres,
        }

    def save(self, path: str | Path) -> None:
        p = Path(path)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
            f.write("\n")

    def validate(self, error_log: ErrorLog) -> bool:
        """Validate config. Returns False if fatal errors found."""
        valid = True

        if not self.source_root.exists():
            error_log.add_fatal(f"Source directory does not exist: {self.source_root}", operation="config")
            valid = False
        elif not self.source_root.is_dir():
            error_log.add_fatal(f"Source path is not a directory: {self.source_root}", operation="config")
            valid = False

        if self.dry_run:
            pass
        else:
            try:
                self.destination_root.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                error_log.add_fatal(f"Cannot create destination directory: {self.destination_root} ({e})", operation="config")
                valid = False

        if self.operation not in ("copy", "move"):
            error_log.add_fatal(f"Invalid operation: {self.operation}. Must be 'copy' or 'move'.", operation="config")
            valid = False

        return valid
