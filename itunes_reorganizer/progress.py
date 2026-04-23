"""Progress display using rich."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.progress import Progress, TaskID, BarColumn, TextColumn, TimeRemainingColumn


class ProgressReporter:
    """Wraps rich.progress for tracking file operations."""

    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.description = description
        self._progress: Optional[Progress] = None
        self._task_id: Optional[TaskID] = None

    def __enter__(self):
        self._progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TextColumn("[dim]{task.fields[current_file]}"),
            TimeRemainingColumn(),
        )
        self._progress.__enter__()
        self._task_id = self._progress.add_task(
            self.description,
            total=self.total,
            current_file="",
        )
        return self

    def __exit__(self, *args):
        if self._progress:
            self._progress.__exit__(*args)

    def update(self, advance: int = 1, current_file: str = "") -> None:
        if self._progress and self._task_id is not None:
            self._progress.update(
                self._task_id,
                advance=advance,
                current_file=current_file,
            )

    def set_description(self, description: str) -> None:
        if self._progress and self._task_id is not None:
            self._progress.update(self._task_id, description=description)


class SilentReporter:
    """No-op progress reporter for testing or non-interactive use."""

    def __init__(self, total: int = 0, description: str = ""):
        self.total = total
        self.description = description
        self.count = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def update(self, advance: int = 1, current_file: str = "") -> None:
        self.count += advance

    def set_description(self, description: str) -> None:
        self.description = description
