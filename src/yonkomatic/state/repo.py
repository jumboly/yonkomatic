"""Persistent state for what has already been published.

``state/state.json`` is the single source of truth for "did we already
post episode N today?". The format is intentionally small so a human
operator can fix it by hand if the cron job goes off the rails.

``auto_commit`` is provided for daily-cron use; ``yonkomatic publish``
itself does not call it.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class HistoryEntry(BaseModel):
    episode_number: int
    week: str | None = None
    date: str  # ISO date, e.g. "2026-05-09"
    title: str
    archive_path: str | None = None
    publishers: dict[str, dict[str, Any]] = Field(default_factory=dict)


class StateData(BaseModel):
    last_published_episode: int | None = None
    current_week_index: str | None = None
    history: list[HistoryEntry] = Field(default_factory=list)


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> StateData:
        if not self.path.exists():
            return StateData()
        return StateData.model_validate_json(self.path.read_text(encoding="utf-8"))

    def save(self, data: StateData) -> None:
        # atomic write: write to a sibling temp file, then rename. Why: a
        # crash mid-write would otherwise leave state.json half-empty and
        # break the next run's load().
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = data.model_dump_json(indent=2) + "\n"
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", dir=str(self.path.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(tmp_name, self.path)
        except Exception:
            Path(tmp_name).unlink(missing_ok=True)
            raise

    def append(self, entry: HistoryEntry) -> StateData:
        data = self.load()
        data.history.append(entry)
        data.last_published_episode = entry.episode_number
        if entry.week is not None:
            data.current_week_index = entry.week
        self.save(data)
        return data

    def auto_commit(self, message: str, *, paths: list[Path] | None = None) -> bool:
        """Stage state.json (and given paths) and commit. Returns True on success.

        Why no exception: the daily cron should never abort over a commit
        failure — the publish itself already happened. Caller logs the
        boolean and moves on.
        """
        targets = [str(self.path)]
        if paths:
            targets.extend(str(p) for p in paths)

        try:
            subprocess.run(["git", "add", *targets], check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", message],
                check=True,
                capture_output=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
        return True
