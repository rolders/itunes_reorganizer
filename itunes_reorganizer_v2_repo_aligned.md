# 🎧 iTunes Reorganizer — V2 Spec (Repo-Aligned)

## 1. Objective

Upgrade the tool to:
- group tracks at album level
- correctly handle compilations
- support hybrid routing (Artists / Compilations / Labels)
- integrate MusicBrainz (optional, high-confidence only)
- remain safe, deterministic, idempotent

---

## 2. Target Repo Structure

```
itunes_reorganizer/
├── itunes_reorganizer/
│   ├── cli.py
│   ├── scanner.py
│   ├── metadata.py
│   ├── models.py              # NEW
│   ├── album_grouper.py       # NEW
│   ├── release_classifier.py  # NEW
│   ├── router.py              # NEW
│   ├── musicbrainz_client.py  # NEW
│   ├── planner.py             # REFACTOR
│   ├── executor.py
│   ├── naming.py              # NEW
│   ├── reporting.py
│   ├── config.py              # NEW
```

---

## 3. Library Structure

```
Music/
  Artists/
    Artist/
      Album [Year]/

  Compilations/
    Various Artists/
      Album [Year]/

  Labels/
    Label/
      CATNO - Artist - Release [Year]/
```

---

## 4. Core Change: Album Grouping

Group tracks using:

```
(album_artist_resolved, album_normalized)
```

Album artist resolution:

```
IF album_artist exists → use it
ELIF multiple artists → "Various Artists"
ELSE → artist
```

---

## 5. Compilation Handling

Compilation if:
- multiple track artists
- OR album_artist = Various Artists

Routing:

```
Compilations/
```

Filename:

```
01 - Artist - Track.ext
```

---

## 6. Release Classification

```
album | ep | single | compilation
```

Logic:
- ≥6 tracks → album
- 2–5 → EP
- 1 → single

---

## 7. Routing Logic

```
IF compilation → Compilations
ELIF album → Artists
ELIF EP/single AND dance + label → Labels
ELSE → Artists
```

Dance genres:
```
electronic, techno, house, trance, dnb, ambient
```

---

## 8. MusicBrainz Integration

Use for:
- validation
- enrichment (year, label, release type)

Rules:
- only accept if confidence ≥ 0.9
- cache results
- never override blindly

---

## 9. Naming Rules

Album:
```
Album [Year]
```

Artist track:
```
01 - Title
```

Compilation:
```
01 - Artist - Title
```

Label:
```
CATNO - Artist - Album [Year]
```

---

## 10. Planner Refactor

Old: per-file  
New: per-album

Flow:
```
scan → metadata → group → classify → MB → route → build paths
```

---

## 11. Config

```
{
  "dry_run": true,
  "enable_musicbrainz": true,
  "dance_genres": [...],
  "enable_label_routing": true
}
```

---

## 12. Logging

```
run_summary.json
album_groups.json
moved_files.csv
skipped_files.csv
```

---

## 13. Acceptance Criteria

- compilations not split
- albums grouped correctly
- EPs routed to Labels
- no destructive moves
- idempotent

---

## 14. Dev Priority

Phase 1:
- models.py
- album_grouper.py
- planner refactor

Phase 2:
- classifier + router

Phase 3:
- MusicBrainz

---

## 15. Key Principle

🔥 Move from file-based → album-based logic
