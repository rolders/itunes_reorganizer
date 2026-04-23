"""Executor: perform file operations (copy/move) or generate dry-run report."""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Optional

from .config import Config
from .errors import ErrorLog, Severity
from .planner import FilePlan, PlanResult
from .progress import ProgressReporter, SilentReporter


MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1.0


def execute_plans(
    plans: PlanResult,
    config: Config,
    error_log: ErrorLog,
    reporter: Optional[ProgressReporter | SilentReporter] = None,
) -> list[FilePlan]:
    """
    Execute file plans. Returns list of successfully executed plans.
    If config.dry_run is True, no files are touched.
    """
    if reporter is None:
        reporter = SilentReporter(len(plans.plans))

    executed: list[FilePlan] = []

    if config.dry_run:
        reporter.set_description("Planning (dry-run)")
        for plan in plans.plans:
            reporter.update(current_file=plan.source.name)
            executed.append(plan)
        return executed

    operation = config.operation
    reporter.set_description(f"{operation.capitalize()}ing files")

    for plan in plans.plans:
        reporter.update(current_file=plan.source.name)

        # Ensure destination directory exists
        dest_dir = plan.destination.parent
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            error_log.add_error(f"Cannot create directory {dest_dir}: {e}", plan.source, operation=operation)
            continue

        # Check source exists
        if not plan.source.exists():
            error_log.add_skip("Source file no longer exists", plan.source, operation=operation)
            continue

        # Check destination doesn't already exist (safety)
        if plan.destination.exists():
            error_log.add_warning(
                f"Destination already exists (skipping): {plan.destination}",
                plan.source,
                operation=operation,
            )
            continue

        # Perform operation with retry
        success = _do_operation(plan.source, plan.destination, operation, error_log)
        if success:
            executed.append(plan)

    return executed


def _do_operation(
    source: Path,
    dest: Path,
    operation: str,
    error_log: ErrorLog,
) -> bool:
    """Perform a single copy or move with retries."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if operation == "copy":
                shutil.copy2(source, dest)
            elif operation == "move":
                shutil.move(str(source), str(dest))
            return True
        except PermissionError as e:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                error_log.add_error(f"Permission denied after {MAX_RETRIES} attempts: {e}", source, operation=operation)
                return False
        except OSError as e:
            error_log.add_error(f"OS error: {e}", source, operation=operation)
            return False
        except Exception as e:
            error_log.add_error(f"Unexpected error: {e}", source, operation=operation)
            return False

    return False


def generate_dry_run_report(plans: PlanResult, config: Config) -> str:
    """Generate a human-readable text report of what would happen."""
    lines: list[str] = []

    lines.append("=" * 80)
    lines.append("DRY-RUN REORGANIZATION PLAN")
    lines.append("=" * 80)
    lines.append(f"Source:      {config.source_root}")
    lines.append(f"Destination: {config.destination_root}")
    lines.append(f"Operation:   {config.operation}")
    lines.append("")

    if not plans.plans:
        lines.append("No files to process.")
        return "\n".join(lines)

    # Group plans by destination folder for readability
    by_folder: dict[str, list[FilePlan]] = {}
    for plan in plans.plans:
        folder = str(plan.destination.parent)
        if folder not in by_folder:
            by_folder[folder] = []
        by_folder[folder].append(plan)

    # Files to be moved/copied
    lines.append(f"FILES TO {config.operation.upper()} ({len(plans.plans)} total)")
    lines.append("-" * 80)
    for folder in sorted(by_folder.keys()):
        lines.append(f"\n  {folder}/")
        for plan in sorted(by_folder[folder], key=lambda p: p.tracknumber):
            rel_source = plan.source.relative_to(config.source_root) if plan.source.is_relative_to(config.source_root) else plan.source
            lines.append(f"    {rel_source}")
            lines.append(f"      → {plan.destination.name}")

    # Collisions
    if plans.collisions:
        lines.append(f"\n\nCOLLISIONS ({len(plans.collisions)})")
        lines.append("-" * 80)
        for plan in plans.collisions:
            lines.append(f"  {plan.source}")
            lines.append(f"    → {plan.destination}  (renamed due to collision)")

    # Summary
    lines.append(f"\n\nSUMMARY")
    lines.append("-" * 80)
    lines.append(f"  Total files:   {len(plans.plans)}")
    lines.append(f"  Collisions:    {len(plans.collisions)}")
    lines.append(f"\n  No changes were made to the filesystem.")

    return "\n".join(lines)
