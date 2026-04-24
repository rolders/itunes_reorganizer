"""Main entry point: load config and run the full reorganization pipeline (V2)."""

from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console

from .config import Config
from .errors import ErrorLog, Severity
from .executor import execute_plans, generate_dry_run_report
from .album_grouper import group_tracks
from .metadata import extract_metadata
from .musicbrainz_client import MusicBrainzClient
from .planner import build_plans
from .progress import ProgressReporter, SilentReporter
from .reporting import (
    RunStats,
    write_album_groups_json,
    write_collisions_csv,
    write_dry_run_report,
    write_moved_csv,
    write_run_summary,
    write_skipped_csv,
)
from .scanner import scan_audio_files


def run(config_path: str) -> int:
    """
    Run the full reorganization pipeline.
    Returns exit code: 0 = success, 1 = errors, 2 = fatal.
    """
    console = Console()
    error_log = ErrorLog()

    # --- Load config ---
    try:
        config = Config.from_file(config_path)
    except FileNotFoundError as e:
        console.print(f"[red]Fatal:[/red] {e}")
        return 2
    except Exception as e:
        console.print(f"[red]Fatal:[/red] Invalid config file: {e}")
        return 2

    # --- Validate config ---
    if not config.validate(error_log):
        for err in error_log.entries:
            console.print(f"[red]Fatal:[/red] {err.reason}")
        return 2

    console.print(f"\n[bold]iTunes Reorganizer V2[/bold]")
    console.print(f"  Source:      {config.source_root}")
    console.print(f"  Destination: {config.destination_root}")
    console.print(f"  Mode:        {'DRY-RUN' if config.dry_run else config.operation.upper()}")
    console.print(f"  MusicBrainz: {'enabled' if config.enable_musicbrainz else 'disabled'}")
    console.print(f"  Label routing: {'enabled' if config.enable_label_routing else 'disabled'}")
    console.print()

    # --- Step 1: Scan ---
    console.print("[bold blue]Scanning files...[/bold blue]")
    audio_files = scan_audio_files(config.source_root, error_log)

    if error_log.has_fatal:
        console.print("[red]Fatal error during scan.[/red]")
        return 2

    console.print(f"  Found {len(audio_files)} audio files.")

    if not audio_files:
        console.print("[yellow]No audio files found. Nothing to do.[/yellow]")
        return 0

    # --- Step 2: Extract metadata ---
    console.print("[bold blue]Extracting metadata...[/bold blue]")
    tracks = []

    with ProgressReporter(total=len(audio_files), description="Extracting metadata") as progress:
        for file_path in audio_files:
            progress.update(current_file=file_path.name)
            meta = extract_metadata(file_path, error_log)
            if meta is not None:
                tracks.append(meta)

    files_skipped_metadata = len(audio_files) - len(tracks)
    console.print(f"  Extracted metadata from {len(tracks)} files.")
    if files_skipped_metadata:
        console.print(f"  [yellow]Skipped {files_skipped_metadata} files (no/invalid metadata).[/yellow]")

    # --- Step 3: Group into albums ---
    console.print("[bold blue]Grouping into albums...[/bold blue]")
    grouping_result = group_tracks(tracks, config, error_log)

    num_groups = len(grouping_result.groups)
    total_grouped = sum(len(g.tracks) for g in grouping_result.groups.values())
    console.print(f"  Found {num_groups} albums with {total_grouped} tracks.")
    if grouping_result.skipped:
        console.print(f"  [yellow]Skipped {len(grouping_result.skipped)} tracks (missing required metadata).[/yellow]")

    # --- Step 4: MusicBrainz enrichment (optional) ---
    mb_client = None
    if config.enable_musicbrainz:
        console.print("[bold blue]MusicBrainz enrichment...[/bold blue]")
        mb_client = MusicBrainzClient(cache_dir=config.destination_root / ".cache")
        if mb_client.available:
            with ProgressReporter(total=num_groups, description="MusicBrainz lookup") as progress:
                for idx, group in enumerate(grouping_result.groups.values(), 1):
                    progress.update(current_file=f"{idx}/{num_groups} {group.album}")
                    mb_client.enrich_group(group)
            console.print("  MusicBrainz enrichment complete.")
        else:
            console.print("  [yellow]musicbrainzngs not installed — skipping enrichment.[/yellow]")

    # --- Step 5: Build plans (classify → route → build paths) ---
    console.print("[bold blue]Planning operations...[/bold blue]")
    plan_result = build_plans(grouping_result, config, error_log)
    console.print(f"  Planned {len(plan_result.plans)} file operations.")
    if plan_result.collisions:
        console.print(f"  [yellow]{len(plan_result.collisions)} collisions detected (will be renamed).[/yellow]")

    # Print routing summary
    route_counts = {}
    for ap in plan_result.album_plans:
        route_counts[ap.route.value] = route_counts.get(ap.route.value, 0) + 1
    for route_name, count in sorted(route_counts.items()):
        console.print(f"    {route_name}: {count} albums")

    # --- Step 6: Execute or dry-run ---
    if config.dry_run:
        console.print("\n[bold green]DRY-RUN MODE — no changes made.[/bold green]")
        report_text = generate_dry_run_report(plan_result, config)
        executed = plan_result.plans

        report_path = write_dry_run_report(report_text, config.destination_root)
        console.print(f"\n  Dry-run report written to: {report_path}")
    else:
        console.print(f"\n[bold]Executing {config.operation} operations...[/bold]")
        with ProgressReporter(total=len(plan_result.plans), description=f"{config.operation.capitalize()}ing") as progress:
            executed = execute_plans(plan_result, config, error_log, progress)
        console.print(f"  Successfully processed {len(executed)} files.")

    # --- Step 7: Report ---
    stats = RunStats(
        total_files_scanned=len(audio_files),
        files_with_metadata=len(tracks),
        files_skipped_metadata=files_skipped_metadata,
        files_planned=len(plan_result.plans),
        files_executed=len(executed),
        files_skipped=len(grouping_result.skipped) + files_skipped_metadata,
        collisions=len(plan_result.collisions),
        errors=len(error_log.errors),
        warnings=len(error_log.warnings),
        dry_run=config.dry_run,
        operation=config.operation,
        source_root=str(config.source_root),
        destination_root=str(config.destination_root),
    )

    write_run_summary(stats, config.destination_root)
    write_moved_csv(executed, config.destination_root)
    write_skipped_csv(error_log, config.destination_root)
    write_album_groups_json(grouping_result, config.destination_root)
    if plan_result.collisions:
        write_collisions_csv(plan_result.collisions, config.destination_root)

    # Print summary
    console.print(f"\n[bold]Summary[/bold]")
    console.print(f"  Scanned:  {stats.total_files_scanned}")
    console.print(f"  Albums:   {num_groups}")
    console.print(f"  Planned:  {stats.files_planned}")
    console.print(f"  Executed: {stats.files_executed}")
    console.print(f"  Skipped:  {stats.files_skipped}")
    console.print(f"  Errors:   {stats.errors}")

    if error_log.has_fatal:
        return 2
    if error_log.errors:
        return 1
    return 0


def main():
    if len(sys.argv) != 2:
        print(f"Usage: python -m itunes_reorganizer <config.json>", file=sys.stderr)
        sys.exit(2)

    exit_code = run(sys.argv[1])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
