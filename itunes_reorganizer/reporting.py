"""Reporting: generate output logs (CSV, JSON, text)."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .errors import ErrorLog, OrganizerError
from .executor import FilePlan
from .grouping import GroupingResult
from .planner import PlanResult


@dataclass
class RunStats:
    """Summary statistics for a run."""
    total_files_scanned: int = 0
    files_with_metadata: int = 0
    files_skipped_metadata: int = 0
    files_planned: int = 0
    files_executed: int = 0
    files_skipped: int = 0
    collisions: int = 0
    errors: int = 0
    warnings: int = 0
    dry_run: bool = True
    operation: str = ""
    source_root: str = ""
    destination_root: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "source_root": self.source_root,
            "destination_root": self.destination_root,
            "dry_run": self.dry_run,
            "operation": self.operation,
            "total_files_scanned": self.total_files_scanned,
            "files_with_metadata": self.files_with_metadata,
            "files_skipped_metadata": self.files_skipped_metadata,
            "files_planned": self.files_planned,
            "files_executed": self.files_executed,
            "files_skipped": self.files_skipped,
            "collisions": self.collisions,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def write_run_summary(stats: RunStats, dest_root: Path) -> Path:
    """Write run_summary.json."""
    path = dest_root / "run_summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(stats.to_dict(), f, indent=2)
        f.write("\n")
    return path


def write_moved_csv(executed: list[FilePlan], dest_root: Path) -> Path:
    """Write moved_files.csv (or copied_files.csv)."""
    path = dest_root / "moved_files.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["source", "destination", "album_artist", "album", "year", "track_number", "title"])
        for plan in executed:
            writer.writerow([
                str(plan.source),
                str(plan.destination),
                plan.album_artist,
                plan.album,
                plan.year or "",
                plan.tracknumber,
                plan.title,
            ])
    return path


def write_skipped_csv(error_log: ErrorLog, dest_root: Path) -> Path:
    """Write skipped_files.csv."""
    path = dest_root / "skipped_files.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["source", "reason", "severity", "operation"])
        for entry in error_log.entries:
            if entry.severity.value in ("skip", "warning", "error"):
                writer.writerow([
                    str(entry.source) if entry.source else "",
                    entry.reason,
                    entry.severity.value,
                    entry.operation,
                ])
    return path


def write_collisions_csv(collisions: list[FilePlan], dest_root: Path) -> Path:
    """Write collisions.csv."""
    path = dest_root / "collisions.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["source", "original_dest_pattern", "resolved_dest", "track_number", "title"])
        for plan in collisions:
            # Reconstruct what the "original" dest would have been (without suffix)
            writer.writerow([
                str(plan.source),
                str(plan.destination.parent / f"{plan.tracknumber:02d} - {plan.title}{plan.extension}"),
                str(plan.destination),
                plan.tracknumber,
                plan.title,
            ])
    return path


def write_dry_run_report(report_text: str, dest_root: Path) -> Path:
    """Write reorganization_plan.txt for dry-run mode."""
    path = dest_root / "reorganization_plan.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(report_text)
    return path
