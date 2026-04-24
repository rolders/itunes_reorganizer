"""Metadata extraction using mutagen. Normalises all formats to TrackMetadata."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import mutagen
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus
from mutagen.apev2 import APEv2File
from mutagen.wavpack import WavPack
from mutagen.musepack import Musepack
from mutagen.aiff import AIFF
from mutagen.wave import WAVE
from mutagen.dsf import DSF
from mutagen.dsdiff import DSDIFF

from .errors import ErrorLog


# Extensions we attempt to process
SUPPORTED_EXTENSIONS: set[str] = {
    ".mp3", ".m4a", ".m4b", ".m4p",
    ".flac", ".ogg", ".opus",
    ".wv", ".mpc",
    ".aiff", ".aif",
    ".wav",
    ".ape",
    ".dsf", ".dff",
}


@dataclass
class TrackMetadata:
    """Normalised metadata for a single track."""
    source_path: Path
    title: Optional[str] = None
    album: Optional[str] = None
    albumartist: Optional[str] = None
    artist: Optional[str] = None
    tracknumber: Optional[int] = None
    tracktotal: Optional[int] = None
    discnumber: Optional[int] = None
    disctotal: Optional[int] = None
    year: Optional[str] = None
    genre: Optional[str] = None
    compilation: bool = False
    format: str = ""  # e.g. "mp3", "flac"

    @property
    def is_compilation(self) -> bool:
        """True if this track is part of a compilation."""
        if self.compilation:
            return True
        if self.albumartist and self.albumartist.lower() == "various artists":
            return True
        return False

    @property
    def effective_albumartist(self) -> Optional[str]:
        """The artist to use for the folder name."""
        if self.is_compilation:
            return "Various Artists"
        if self.albumartist:
            return self.albumartist
        return None


def _clean_str(value: Optional[str]) -> Optional[str]:
    """Clean a string value: strip whitespace, return None if empty."""
    if value is None:
        return None
    value = value.strip()
    return value if value else None


def _extract_tracknumber(raw: Optional[str]) -> Optional[int]:
    """Extract track number from formats like '5', '5/12', '05'."""
    if raw is None:
        return None
    raw = raw.strip().split("/")[0].split("\\")[0]
    match = re.match(r"(\d+)", raw)
    if match:
        return int(match.group(1))
    return None


def _extract_year(raw: Optional[str]) -> Optional[str]:
    """Extract year from date strings like '2023', '2023-01-15', '2023-01-15T00:00:00'."""
    if raw is None:
        return None
    raw = raw.strip()
    match = re.match(r"(\d{4})", raw)
    return match.group(1) if match else None


def _extract_from_id3(audio: mutagen.File) -> dict:
    """Extract from ID3-tagged files (MP3, AIFF, WAV, DSF, DSDIFF)."""
    tags = audio.tags
    result = {}

    if tags is None:
        return result

    # ID3 frames
    frame_map = {
        "title": ("TIT2",),
        "album": ("TALB",),
        "albumartist": ("TPE2",),
        "artist": ("TPE1",),
        "year": ("TDRC", "TYER", "TDAT"),
        "genre": ("TCON",),
        "compilation": ("TCMP",),
    }

    for key, frames in frame_map.items():
        for frame_id in frames:
            if frame_id in tags:
                val = tags[frame_id]
                if hasattr(val, "text"):
                    text = str(val.text[0]) if val.text else None
                else:
                    text = str(val)
                result[key] = text
                break

    # Track number
    if "TRCK" in tags:
        result["tracknumber"] = str(tags["TRCK"])

    return result


def _extract_from_mp4(audio: MP4) -> dict:
    """Extract from MPEG-4 files (M4A, M4B, M4P)."""
    tags = audio.tags
    result = {}

    if tags is None:
        return result

    mp4_map = {
        "title": ("\xa9nam",),
        "album": ("\xa9alb",),
        "albumartist": ("aART",),
        "artist": ("\xa9ART",),
        "year": ("\xa9day",),
        "tracknumber": ("trkn",),
        "genre": ("\xa9gen",),
        "compilation": ("cpil",),
    }

    for key, frames in mp4_map.items():
        for frame_id in frames:
            if frame_id in tags:
                val = tags[frame_id]
                if key == "tracknumber":
                    # MP4 track number is a tuple: (track, total)
                    if isinstance(val, list) and len(val) > 0:
                        result["tracknumber"] = str(val[0][0]) if isinstance(val[0], tuple) else str(val[0])
                elif key == "compilation":
                    result["compilation"] = val
                elif isinstance(val, list) and val:
                    result[key] = str(val[0])
                else:
                    result[key] = str(val)
                break

    return result


def _extract_from_vorbis(audio) -> dict:
    """Extract from Vorbis-comment files (FLAC, OGG, Opus)."""
    tags = audio.tags
    result = {}

    if tags is None:
        return result

    vorbis_map = {
        "title": ("title",),
        "album": ("album",),
        "albumartist": ("albumartist",),
        "artist": ("artist",),
        "year": ("date",),
        "tracknumber": ("tracknumber",),
        "genre": ("genre",),
        "compilation": ("compilation",),
    }

    for key, fields in vorbis_map.items():
        for field_name in fields:
            if field_name in tags:
                val = tags[field_name]
                if isinstance(val, list) and val:
                    result[key] = str(val[0])
                else:
                    result[key] = str(val)
                break

    return result


def _extract_from_ape(audio) -> dict:
    """Extract from APEv2-tagged files (WavPack, Musepack, APE)."""
    tags = audio.tags
    result = {}

    if tags is None:
        return result

    ape_map = {
        "title": ("Title",),
        "album": ("Album",),
        "albumartist": ("Album Artist", "ALBUM ARTIST"),
        "artist": ("Artist",),
        "year": ("Year", "Date", "Recording Date"),
        "tracknumber": ("Track", "Track Number"),
        "genre": ("Genre",),
        "compilation": ("Compilation",),
    }

    for key, fields in ape_map.items():
        for field_name in fields:
            if field_name in tags:
                val = tags[field_name]
                if isinstance(val, list) and val:
                    result[key] = str(val[0])
                else:
                    result[key] = str(val)
                break

    return result


def extract_metadata(file_path: Path, error_log: ErrorLog) -> Optional[TrackMetadata]:
    """
    Extract metadata from an audio file.
    Returns TrackMetadata on success, None on failure (logs error).
    """
    try:
        audio = mutagen.File(file_path, easy=False)
    except Exception as e:
        error_log.add_skip(f"Could not read file: {e}", file_path, operation="metadata")
        return None

    if audio is None:
        error_log.add_skip("Unrecognised audio format", file_path, operation="metadata")
        return None

    # Determine format and extract raw values
    raw: dict = {}

    if isinstance(audio, MP4):
        raw = _extract_from_mp4(audio)
        fmt = "mp4"
    elif isinstance(audio, FLAC) or isinstance(audio, OggVorbis) or isinstance(audio, OggOpus):
        raw = _extract_from_vorbis(audio)
        fmt = "flac" if isinstance(audio, FLAC) else "ogg"
    elif isinstance(audio, (WavPack, Musepack)) or _has_ape_tags(audio):
        raw = _extract_from_ape(audio)
        fmt = "ape"
    elif isinstance(audio, MP3):
        raw = _extract_from_id3(audio)
        fmt = "mp3"
    elif isinstance(audio, AIFF):
        raw = _extract_from_id3(audio)
        fmt = "aiff"
    elif isinstance(audio, WAVE):
        raw = _extract_from_id3(audio)
        fmt = "wav"
    elif isinstance(audio, DSF):
        raw = _extract_from_id3(audio)
        fmt = "dsf"
    elif isinstance(audio, DSDIFF):
        raw = _extract_from_id3(audio)
        fmt = "dff"
    else:
        # Fallback: try ID3 then vorbis
        if audio.tags is not None:
            if hasattr(audio.tags, "keys"):
                if "TIT2" in audio.tags or "TALB" in audio.tags:
                    raw = _extract_from_id3(audio)
                    fmt = "id3"
                else:
                    raw = _extract_from_vorbis(audio)
                    fmt = "vorbis"
            else:
                fmt = "unknown"
        else:
            fmt = "unknown"

    # Normalise into TrackMetadata
    tracknumber = _extract_tracknumber(raw.get("tracknumber"))

    compilation_val = raw.get("compilation")
    is_compilation = False
    if isinstance(compilation_val, bool):
        is_compilation = compilation_val
    elif isinstance(compilation_val, str):
        is_compilation = compilation_val.strip().lower() in ("1", "true", "yes")

    year = _extract_year(raw.get("year"))

    return TrackMetadata(
        source_path=file_path,
        title=_clean_str(raw.get("title")),
        album=_clean_str(raw.get("album")),
        albumartist=_clean_str(raw.get("albumartist")),
        artist=_clean_str(raw.get("artist")),
        tracknumber=tracknumber,
        year=year,
        genre=_clean_str(raw.get("genre")),
        compilation=is_compilation,
        format=fmt,
    )


def _has_ape_tags(audio) -> bool:
    """Check if an audio file has APEv2 tags."""
    try:
        return isinstance(audio.tags, APEv2File) or isinstance(audio, APEv2File)
    except Exception:
        return False
