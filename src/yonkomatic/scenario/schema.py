"""Pydantic models for scenarios.

A scenario is the structured plot of one yonkoma episode: title, summary,
and four panels — each with a description, the characters present, and
zero or more dialogue lines. The week-level container holds seven episodes
plus the ISO week identifier, so a single YAML file represents one week
of content.

These models are the contract between scenario generation (Step 4) and
panel description / image generation (Step 2). Hand-written sample files
in ``content/sample-scenario.yaml`` must validate against this schema.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field


class Dialogue(BaseModel):
    speaker: str  # character key matching content/prompt.md (e.g. "yonko")
    text: str


class Panel(BaseModel):
    index: Annotated[int, Field(ge=1, le=4)]
    description: str  # what is happening in the panel — passed to the LLM
    characters: list[str] = Field(default_factory=list)
    dialogue: list[Dialogue] = Field(default_factory=list)


class ScenarioEpisode(BaseModel):
    """One episode of a yonkoma — exactly four panels."""

    week: str | None = None  # ISO week, e.g. "2026-W19"; populated when inside a ScenarioWeek
    episode_number: Annotated[int, Field(ge=1)]
    title: str
    summary_no_spoiler: str
    panels: Annotated[list[Panel], Field(min_length=4, max_length=4)]


class ScenarioWeek(BaseModel):
    """Seven episodes generated together for a given ISO week."""

    week: str  # e.g. "2026-W19"
    episodes: Annotated[list[ScenarioEpisode], Field(min_length=1, max_length=7)]
