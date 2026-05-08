"""Optional PIL text overlay on top of the Gemini-rendered image.

``mode='never'`` is a passthrough; other modes raise NotImplementedError
until a per-panel bubble layout becomes necessary (e.g. if the image
model regresses on Japanese rendering).
"""

from __future__ import annotations

from pathlib import Path

from yonkomatic.config import TextRenderMode
from yonkomatic.scenario.schema import ScenarioEpisode


def compose(
    *,
    image_bytes: bytes,
    episode: ScenarioEpisode,
    mode: TextRenderMode,
    font_path: Path | None = None,
) -> bytes:
    if mode == "never":
        return image_bytes

    raise NotImplementedError(
        f"text_rendering.mode={mode!r} is not implemented. "
        "Only 'never' (passthrough) is supported; PIL overlay can be added "
        "when the image model regresses on Japanese rendering."
    )
