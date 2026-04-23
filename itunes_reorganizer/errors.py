"""Error classification and handling."""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class Severity(str, Enum):
    SKIP = "skip"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


@dataclass
class OrganizerError:
    """A single error or skip event."""
    severity: Severity
    source: Optional[Path] = None
    reason: str = ""
    operation: str = ""  # e.g. "scan", "metadata", "copy", "move"

    def to_dict(self) -> dict:
        return {
            "severity": self.severity.value,
            "source": str(self.source) if self.source else None,
            "reason": self.reason,
            "operation": self.operation,
        }


@dataclass
class ErrorLog:
    """Accumulates all errors during a run."""
    entries: list[OrganizerError] = field(default_factory=list)

    def add(self, severity: Severity, reason: str, source: Path | None = None, operation: str = "") -> None:
        self.entries.append(OrganizerError(
            severity=severity,
            source=source,
            reason=reason,
            operation=operation,
        ))

    def add_skip(self, reason: str, source: Path, operation: str = "") -> None:
        self.add(Severity.SKIP, reason, source, operation)

    def add_warning(self, reason: str, source: Path | None = None, operation: str = "") -> None:
        self.add(Severity.WARNING, reason, source, operation)

    def add_error(self, reason: str, source: Path | None = None, operation: str = "") -> None:
        self.add(Severity.ERROR, reason, source, operation)

    def add_fatal(self, reason: str, source: Path | None = None, operation: str = "") -> None:
        self.add(Severity.FATAL, reason, source, operation)

    @property
    def has_fatal(self) -> bool:
        return any(e.severity == Severity.FATAL for e in self.entries)

    @property
    def skips(self) -> list[OrganizerError]:
        return [e for e in self.entries if e.severity == Severity.SKIP]

    @property
    def warnings(self) -> list[OrganizerError]:
        return [e for e in self.entries if e.severity == Severity.WARNING]

    @property
    def errors(self) -> list[OrganizerError]:
        return [e for e in self.entries if e.severity in (Severity.ERROR, Severity.FATAL)]

    def to_dicts(self) -> list[dict]:
        return [e.to_dict() for e in self.entries]
