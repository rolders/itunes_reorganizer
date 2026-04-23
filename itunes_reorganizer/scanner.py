"""Scanner: recursively discovers audio files in the source directory."""

from __future__ import annotations

from pathlib import Path

from .errors import ErrorLog
from .metadata import SUPPORTED_EXTENSIONS


def scan_audio_files(source_root: Path, error_log: ErrorLog) -> list[Path]:
    """
    Recursively scan source_root for audio files.
    Returns a sorted list of paths to supported audio files.
    """
    if not source_root.is_dir():
        error_log.add_fatal(f"Source is not a directory: {source_root}", operation="scan")
        return []

    audio_files: list[Path] = []

    try:
        for path in source_root.rglob("*"):
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                audio_files.append(path)
    except PermissionError as e:
        error_log.add_fatal(f"Permission denied scanning directory: {e}", operation="scan")
        return []

    audio_files.sort()
    return audio_files
