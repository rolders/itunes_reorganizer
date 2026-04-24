# iTunes Reorganizer

A Python CLI tool that reorganizes a legacy iTunes music folder into a clean album-based folder structure using embedded metadata. Designed to be run manually or operated by an AI agent.

## Folder Structure (V2)

Reorganizes flat or messy music libraries into a hybrid structure with **Artists**, **Compilations**, and **Labels** routes:

```
Music/
  Artists/
    Artist/
      Album [Year]/
        01 - Title.mp3
        02 - Another Track.flac

  Compilations/
    Various Artists/
      Album [Year]/
        01 - Artist A - Title.mp3
        02 - Artist B - Title.flac

  Labels/
    Label Name/
      CATNO - Artist - Release [Year]/
        01 - Title.mp3
```

### Routing Logic

| Condition | Route | Filename Format |
|---|---|---|
| Compilation (multiple artists / VA) | `Compilations/` | `01 - Artist - Title.ext` |
| Album (≥6 tracks) | `Artists/` | `01 - Title.ext` |
| EP/Single + dance genre + label | `Labels/` | `01 - Title.ext` |
| EP/Single (other) | `Artists/` | `01 - Title.ext` |

### Release Classification

| Track Count | Type |
|---|---|
| ≥ 6 | Album |
| 2–5 | EP |
| 1 | Single |
| Multiple artists | Compilation (overrides) |

## Supported Formats

All audio formats with embedded metadata via [mutagen](https://mutagen.readthedocs.io/):

| Format | Extensions |
|---|---|
| MP3 | `.mp3` |
| AAC/ALAC | `.m4a`, `.m4b`, `.m4p` |
| FLAC | `.flac` |
| OGG Vorbis | `.ogg` |
| OGG Opus | `.opus` |
| WavPack | `.wv` |
| Musepack | `.mpc` |
| AIFF | `.aiff`, `.aif` |
| WAV | `.wav` |
| Monkey's Audio | `.ape` |
| DSF | `.dsf` |
| DSDIFF | `.dff` |

## Installation

```bash
git clone https://github.com/<your-username>/itunes_reorganizer.git
cd itunes_reorganizer
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

For development (includes pytest):

```bash
pip install -e ".[dev]"
```

Optional — MusicBrainz enrichment:

```bash
pip install musicbrainzngs
```

## Usage

### 1. Create a config file

**Interactive wizard:**

```bash
python -m itunes_reorganizer.setup
```

**Non-interactive (for scripts or AI agents):**

```bash
python -m itunes_reorganizer.setup \
  --source /path/to/music \
  --dest /path/to/output \
  --operation copy \
  --output config.json
```

This creates a `config.json`:

```json
{
  "source_root": "/path/to/music",
  "destination_root": "/path/to/output",
  "dry_run": true,
  "operation": "copy",
  "fallback_to_artist": false,
  "enable_musicbrainz": true,
  "enable_label_routing": true,
  "dance_genres": ["electronic", "techno", "house", "trance", "dnb", "ambient"]
}
```

### 2. Run

```bash
python -m itunes_reorganizer config.json
```

### Config options

| Option | Values | Description |
|---|---|---|
| `source_root` | path | Your music library (required) |
| `destination_root` | path | Output location (required) |
| `dry_run` | `true` / `false` | No filesystem changes; outputs a text report (default: `true`) |
| `operation` | `copy` / `move` | How to handle files when not in dry-run (default: `copy`) |
| `fallback_to_artist` | `true` / `false` | Use track artist when album artist is missing (default: `false`) |
| `enable_musicbrainz` | `true` / `false` | Enrich metadata via MusicBrainz (default: `false`) |
| `enable_label_routing` | `true` / `false` | Route dance EPs/singles to Labels/ (default: `true`) |
| `dance_genres` | list of strings | Genres that trigger label routing (default: electronic, techno, house, etc.) |

### Recommended workflow

1. **Start with `dry_run: true`** — review `reorganization_plan.txt` in the destination folder
2. **Set `dry_run: false`** when you're happy with the plan
3. Check `run_summary.json`, `album_groups.json`, `moved_files.csv`, `skipped_files.csv`, and `collisions.csv` in the destination folder after the run

## MusicBrainz Integration

When `enable_musicbrainz` is `true`, the tool will:

- Look up each album group via the MusicBrainz API
- **Only accept results with confidence ≥ 0.9**
- **Never override existing metadata** — only fills in missing fields
- Enrich: year, label, catalog number, release type
- Cache results to `.cache/musicbrainz_cache.json` for subsequent runs

Requires `pip install musicbrainzngs`.

## Safety

- **Dry-run is the default** — no files are touched until you explicitly disable it
- **Never overwrites** — collisions are renamed with `(2)`, `(3)`, etc.
- **Skips incomplete files** — files missing required metadata (album, title, track number, album artist) are skipped and logged
- **Retries on locked files** — up to 3 attempts with 1-second delays
- **All errors logged** — with severity levels (skip, warning, error, fatal)
- **Idempotent** — re-running produces the same result

## Testing

```bash
source .venv/bin/activate
python -m pytest tests/ -v
python -m pytest tests/ --cov=itunes_reorganizer --cov-report=term-missing
```

97 tests covering config, metadata, models, grouping, classification, routing, naming, planning, reporting, and integration scenarios.

## Project Structure

```
itunes_reorganizer/
├── main.py                # Pipeline entry point (V2 flow)
├── setup.py               # Config wizard (interactive + CLI flags)
├── config.py              # Config loading & validation
├── scanner.py             # File discovery
├── metadata.py            # Mutagen abstraction, TrackMetadata dataclass
├── models.py              # Domain models (AlbumGroup, ReleaseType, Route, FilePlan)
├── album_grouper.py       # Album-level grouping with compilation detection
├── release_classifier.py  # Classify as album/EP/single/compilation
├── router.py              # Hybrid routing: Artists/Compilations/Labels
├── naming.py              # Filename & folder naming rules
├── musicbrainz_client.py  # Optional MB enrichment (high-confidence only)
├── planner.py             # Album-based path planning & collision detection
├── executor.py            # File operations (copy/move/dry-run)
├── progress.py            # Rich progress bars
├── reporting.py           # CSV/JSON/txt output
└── errors.py              # Error classification
```

### Pipeline Flow

```
scan → metadata → group → classify → (MusicBrainz) → route → build paths → execute
```

## Roadmap

- [x] ~~V1 — Album-based grouping~~
- [x] ~~V2 — Hybrid routing (Artists / Compilations / Labels)~~
- [x] ~~V2 — Release classification (album / EP / single / compilation)~~
- [x] ~~V2 — MusicBrainz integration (optional, high-confidence only)~~
- [ ] Duplicate detection mode
- [ ] Interactive review workflow
- [ ] Tag fixing workflow

## License

MIT
