# iTunes Library Album Reorganizer – Spec

## Purpose
A Python CLI tool that reorganizes a legacy iTunes music folder into a clean album-based folder structure using embedded metadata. Designed to be run manually or operated by an AI agent.

## Target Folder Structure
```
Music/
  Album Artist/
    Year - Album/
      Track - Title.ext
```

### Compilation Handling
- If `compilation` tag is `true` or `1` → artist folder = `"Various Artists"`
- If `albumartist` is `"Various Artists"` → same behavior
- `albumartist` always takes priority over `compilation` flag when present and non-empty
- If neither applies but `fallback_to_artist` is enabled → use track `artist` (compilations scatter by artist; user opted in)

## Supported Audio Formats
Uses **mutagen** for metadata extraction. All formats with embedded metadata are supported:

| Format | Extension(s) | Tag Type |
|---|---|---|
| MP3 | `.mp3` | ID3v1/v2 |
| AAC/ALAC | `.m4a`, `.m4b`, `.m4p` | MPEG-4 |
| FLAC | `.flac` | Vorbis comments |
| OGG Vorbis | `.ogg` | Vorbis comments |
| OGG Opus | `.opus` | Vorbis comments |
| WavPack | `.wv` | APEv2 |
| Musepack | `.mpc` | APEv2 |
| AIFF | `.aiff`, `.aif` | ID3v2 |
| WAV | `.wav` | ID3v2 / RIFF INFO |
| Monkey's Audio | `.ape` | APEv2 |
| DSF | `.dsf` | ID3v2 |
| DSDIFF | `.dff` | ID3v2 |

Unsupported formats (e.g., `.txt`, `.jpg`, `.pdf`) are skipped silently.

## Metadata Requirements

### Required fields
- `album`
- `title`
- `tracknumber`
- `albumartist` (unless `fallback_to_artist` is enabled)

### Normalisation
`metadata.py` provides a thin abstraction over mutagen's format-specific APIs, returning a normalised `TrackMetadata` dataclass for all formats.

### Skip Conditions
Files are skipped (not moved/copied) when:
- Missing `album`
- Missing `title`
- Missing `tracknumber`
- Missing `albumartist` and `fallback_to_artist` is disabled
- File is corrupted or unreadable
- Format is unsupported

## CLI Interface

### Two entry points

**1. `setup.py` — Config wizard**
```
# Interactive mode (manual user):
python setup.py

# Non-interactive mode (AI agent):
python setup.py \
  --source /path/to/music \
  --dest /path/to/output \
  --operation copy \
  --fallback-to-artist \
  --output config.json
```
- Validates that paths exist
- Guides user through all config options
- Writes `config.json`

**2. `main.py` — Reorganizer**
```
python main.py config.json
```
- Single required argument: path to config file
- All behaviour controlled by config

### Config Schema
```json
{
  "source_root": "/path/to/source",
  "destination_root": "/path/to/destination",
  "dry_run": true,
  "operation": "copy",
  "fallback_to_artist": false
}
```

**`dry_run` vs `operation`:**
- `dry_run: true` → no filesystem changes whatsoever; outputs a text report for review
- `dry_run: false` + `operation: "copy"` → copy files
- `dry_run: false` + `operation: "move"` → move files

## dry_run Mode

When `dry_run` is `true`:
- **Does NOT:** create folders, copy files, move files, or modify anything on disk
- **Does:** scan, extract metadata, validate, group, plan
- **Outputs:** `reorganization_plan.txt` containing:
  - Source → planned destination for every file
  - Skipped files and reasons
  - Detected collisions
  - Summary stats (total, to move/copy, skipped, collisions)

## File Operations

### Modes
- `copy` — copy files to new structure
- `move` — move files to new structure

### Collision Handling
Never overwrite. On collision, append `(2)`, `(3)`, etc. to the filename.

## Progress Reporting
- Progress bar for overall run (files processed / total)
- Current file and/or folder shown in progress display
- Uses `rich` or `tqdm` library

## Logging Outputs
All runs produce in the destination root:
- `run_summary.json` — high-level stats
- `moved_files.csv` — source, destination, status
- `skipped_files.csv` — source, reason
- `collisions.csv` — resolved path, original path, suffix applied

## Error Handling

### Recoverable (skip and continue)
- Corrupted/unreadable file → log to `skipped_files.csv` with reason
- Missing required metadata → log to `skipped_files.csv` with reason
- Unsupported format → skip silently

### Recoverable with retry
- File locked by another process → retry up to 3 times with 1s delay, then skip
- Permission denied → log and skip
- Disk space low → log warning, continue until failure

### Fatal (abort run)
- Source directory doesn't exist or isn't readable
- Destination directory doesn't exist and can't be created
- Config file invalid or missing required fields
- Unrecoverable I/O error on critical operation

All errors include a `severity` field: `skip`, `warning`, `error`, `fatal`.

## Modules
```
itunes_reorganizer/
├── main.py                  # CLI entry point
├── setup.py                 # Config wizard
├── config.py                # Config loading & validation
├── scanner.py               # File discovery & filtering
├── metadata.py              # mutagen abstraction, TrackMetadata dataclass
├── grouping.py              # Album grouping logic, compilation handling
├── planner.py               # Build move/copy plans, collision detection
├── executor.py              # Execute plans (copy/move), dry-run report
├── reporting.py             # CSV/JSON/txt output generation
├── progress.py              # Progress bar display
└── errors.py                # Error classification & handling
```

## Execution Flow
1. Load and validate config
2. Scan source directory for audio files
3. Extract and normalise metadata for each file
4. Validate metadata (skip files with missing required fields)
5. Group tracks into albums (handle Various Artists / compilations)
6. Plan file operations (generate destination paths, detect collisions)
7. Execute operations (copy/move) **or** generate dry-run report
8. Write logs and summary

## Testing Plan

### Unit tests (`tests/unit/`)
- `test_metadata.py` — mock mutagen returns, verify normalisation per format
- `test_grouping.py` — album grouping, Various Artists, edge cases
- `test_planner.py` — path generation, collision handling, skip conditions
- `test_config.py` — config validation, missing fields, invalid values
- `test_reporting.py` — CSV/JSON/txt output correctness

### Integration tests (`tests/integration/`)
- `test_pipeline.py` — end-to-end run with curated test music library
- `test_dry_run.py` — verify zero filesystem changes in dry-run mode
- `test_collision.py` — verify files are never overwritten
- `test_move.py` — verify source files removed after move

### Test fixtures (`tests/fixtures/`)
- Small audio files with known metadata (one per supported format)
- Edge-case files: missing tags, compilation flag, unicode, long filenames

### Coverage target
80%+ on all modules except `main.py` and `setup.py` (glue / interactive code).

## Future Enhancements (v2)
- MusicBrainz integration for validation and enrichment
- Duplicate detection mode
- Interactive review workflow
- Tag fixing workflow
