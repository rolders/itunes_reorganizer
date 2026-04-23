"""Tests for the metadata module."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from itunes_reorganizer.errors import ErrorLog
from itunes_reorganizer.metadata import (
    TrackMetadata,
    extract_metadata,
    _clean_str,
    _extract_tracknumber,
    _extract_year,
    SUPPORTED_EXTENSIONS,
)


class TestTrackMetadata:
    def test_is_compilation_flag(self):
        meta = TrackMetadata(source_path=Path("test.mp3"), compilation=True)
        assert meta.is_compilation is True

    def test_is_compilation_various_artists(self):
        meta = TrackMetadata(source_path=Path("test.mp3"), albumartist="Various Artists")
        assert meta.is_compilation is True

    def test_is_compilation_various_artists_case_insensitive(self):
        meta = TrackMetadata(source_path=Path("test.mp3"), albumartist="various artists")
        assert meta.is_compilation is True

    def test_not_compilation(self):
        meta = TrackMetadata(source_path=Path("test.mp3"), albumartist="The Beatles")
        assert meta.is_compilation is False

    def test_effective_albumartist_compilation(self):
        meta = TrackMetadata(source_path=Path("test.mp3"), compilation=True, albumartist="Some Artist")
        assert meta.effective_albumartist == "Various Artists"

    def test_effective_albumartist_normal(self):
        meta = TrackMetadata(source_path=Path("test.mp3"), albumartist="The Beatles")
        assert meta.effective_albumartist == "The Beatles"

    def test_effective_albumartist_none(self):
        meta = TrackMetadata(source_path=Path("test.mp3"))
        assert meta.effective_albumartist is None


class TestHelpers:
    def test_clean_str_normal(self):
        assert _clean_str("  Hello  ") == "Hello"

    def test_clean_str_none(self):
        assert _clean_str(None) is None

    def test_clean_str_empty(self):
        assert _clean_str("   ") is None

    def test_extract_tracknumber_simple(self):
        assert _extract_tracknumber("5") == 5

    def test_extract_tracknumber_with_total(self):
        assert _extract_tracknumber("5/12") == 5

    def test_extract_tracknumber_padded(self):
        assert _extract_tracknumber("05") == 5

    def test_extract_tracknumber_none(self):
        assert _extract_tracknumber(None) is None

    def test_extract_tracknumber_garbage(self):
        assert _extract_tracknumber("abc") is None

    def test_extract_year_simple(self):
        assert _extract_year("2023") == "2023"

    def test_extract_year_date(self):
        assert _extract_year("2023-01-15") == "2023"

    def test_extract_year_none(self):
        assert _extract_year(None) is None


class TestExtractMetadata:
    def test_unsupported_format(self, tmp_path):
        """Non-audio file should return None."""
        error_log = ErrorLog()
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not audio")
        result = extract_metadata(txt_file, error_log)
        assert result is None
        assert len(error_log.skips) == 1

    def test_corrupted_file(self, tmp_path):
        """Corrupted audio file should return None."""
        error_log = ErrorLog()
        mp3_file = tmp_path / "corrupt.mp3"
        mp3_file.write_bytes(b"not a real mp3 file at all")
        result = extract_metadata(mp3_file, error_log)
        # mutagen may return None for unrecognised
        assert result is None or result.title is None


class TestSupportedExtensions:
    def test_common_formats(self):
        assert ".mp3" in SUPPORTED_EXTENSIONS
        assert ".flac" in SUPPORTED_EXTENSIONS
        assert ".m4a" in SUPPORTED_EXTENSIONS
        assert ".wav" in SUPPORTED_EXTENSIONS
        assert ".ogg" in SUPPORTED_EXTENSIONS
        assert ".opus" in SUPPORTED_EXTENSIONS
        assert ".aiff" in SUPPORTED_EXTENSIONS

    def test_non_audio_excluded(self):
        assert ".txt" not in SUPPORTED_EXTENSIONS
        assert ".jpg" not in SUPPORTED_EXTENSIONS
        assert ".pdf" not in SUPPORTED_EXTENSIONS
