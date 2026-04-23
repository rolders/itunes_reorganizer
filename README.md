# iTunes Reorganizer

A Python CLI tool that reorganizes a legacy iTunes music folder into a clean album-based folder structure using embedded metadata. Designed to be run manually or operated by an AI agent.

## Folder Structure

Reorganizes flat or messy music libraries into:

```
Music/
  Album Artist/
    Year - Album/
      01 - Track Title.mp3
      02 - Another Track.flac
```

### Compilations

Tracks tagged as compilations or with `albumartist: "Various Artists"` are grouped under a `Various Artists/` folder.

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
  "fallback_to_artist": false
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

### Recommended workflow

1. **Start with `dry_run: true`** — review `reorganization_plan.txt` in the destination folder
2. **Set `dry_run: false`** when you're happy with the plan
3. Check `run_summary.json`, `moved_files.csv`, `skipped_files.csv`, and `collisions.csv` in the destination folder after the run

## Safety

- **Dry-run is the default** — no files are touched until you explicitly disable it
- **Never overwrites** — collisions are renamed with `(2)`, `(3)`, etc.
- **Skips incomplete files** — files missing required metadata (album, title, track number, album artist) are skipped and logged
- **Retries on locked files** — up to 3 attempts with 1-second delays
- **All errors logged** — with severity levels (skip, warning, error, fatal)

## Testing

```bash
source .venv/bin/activate
python -m pytest tests/ -v
python -m pytest tests/ --cov=itunes_reorganizer --cov-report=term-missing
```

67 tests covering config, metadata, grouping, planning, reporting, and integration scenarios.

## Project Structure

```
itunes_reorganizer/
├── main.py          # Pipeline entry point
├── setup.py         # Config wizard (interactive + CLI flags)
├── config.py        # Config loading & validation
├── scanner.py       # File discovery
├── metadata.py      # Mutagen abstraction, TrackMetadata dataclass
├── grouping.py      # Album grouping, compilation handling
├── planner.py       # Path planning, collision detection
├── executor.py      # File operations (copy/move/dry-run)
├── progress.py      # Rich progress bars
├── reporting.py     # CSV/JSON/txt output
└── errors.py        # Error classification
```

## Roadmap

- [ ] **v1.1** — Real audio test fixtures for fuller metadata coverage
- [ ] **v2** — MusicBrainz integration for validation & enrichment
- [ ] **v2** — Duplicate detection mode
- [ ] **v2** — Interactive review workflow
- [ ] **v2** — Tag fixing workflow

## License

MIT
