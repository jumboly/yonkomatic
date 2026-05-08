"""Post-generation quality check.

Currently a stub: ``GeminiImageClient`` already retries on NO_IMAGE / 429
/ 5xx so non-determinism is mostly absorbed there. This module exists so
the pipeline calls ``validate(...)`` at a stable seam — a real
Gemini-Vision self-check (character consistency, scenario alignment,
text legibility) can be slotted in without touching call sites.
"""

from __future__ import annotations

from dataclasses import dataclass

from yonkomatic.scenario.schema import ScenarioEpisode


@dataclass
class ValidationResult:
    ok: bool
    score: float
    reason: str


def validate(*, image_bytes: bytes, episode: ScenarioEpisode) -> ValidationResult:
    del image_bytes, episode  # interface placeholders for the real implementation
    return ValidationResult(ok=True, score=1.0, reason="stub")
