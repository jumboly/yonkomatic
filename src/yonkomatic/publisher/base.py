"""Publisher Protocol and shared dataclasses.

Each Publisher takes an Episode + image path and returns a PublishResult.
Implementations must NEVER raise on platform failure — they catch exceptions
and surface them as ``PublishResult(ok=False, error=...)`` so a single
broken publisher cannot stop the daily pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class Episode:
    number: int
    title: str
    summary_no_spoiler: str
    week: str | None  # ISO week, e.g. "2026-W19"; None when the scenario lacks one
    date: str  # ISO date, e.g. "2026-05-09"


@dataclass
class PublishResult:
    ok: bool
    publisher: str
    artifact_id: str | None = None  # slack ts, discord message_id, etc.
    url: str | None = None
    error: str | None = None


class Publisher(Protocol):
    """Structural interface every publisher must satisfy."""

    name: str

    def publish(self, episode: Episode, image_path: Path) -> PublishResult: ...
