"""Pydantic boundary checks for ScenarioWeek / ScenarioEpisode / Panel / Dialogue."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from yonkomatic.scenario.schema import (
    Dialogue,
    Panel,
    ScenarioEpisode,
    ScenarioWeek,
)


def _panel(index: int) -> Panel:
    return Panel(index=index, description=f"panel {index}", characters=[], dialogue=[])


def _episode(panels: int = 4, *, episode_number: int = 1) -> ScenarioEpisode:
    return ScenarioEpisode(
        episode_number=episode_number,
        title="title",
        summary_no_spoiler="summary",
        panels=[_panel(i + 1) for i in range(panels)],
    )


def test_panel_index_must_be_1_to_4() -> None:
    with pytest.raises(ValidationError):
        Panel(index=0, description="d", characters=[], dialogue=[])
    with pytest.raises(ValidationError):
        Panel(index=5, description="d", characters=[], dialogue=[])
    assert _panel(1).index == 1
    assert _panel(4).index == 4


def test_episode_requires_exactly_four_panels() -> None:
    # Why both bounds: ScenarioEpisode pins panels min_length=4 AND max_length=4.
    with pytest.raises(ValidationError):
        ScenarioEpisode(
            episode_number=1,
            title="t",
            summary_no_spoiler="s",
            panels=[_panel(i + 1) for i in range(3)],
        )
    with pytest.raises(ValidationError):
        ScenarioEpisode(
            episode_number=1,
            title="t",
            summary_no_spoiler="s",
            panels=[_panel(i + 1) for i in range(5)],
        )
    assert len(_episode(panels=4).panels) == 4


def test_episode_number_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        ScenarioEpisode(
            episode_number=0,
            title="t",
            summary_no_spoiler="s",
            panels=[_panel(i + 1) for i in range(4)],
        )
    assert _episode(episode_number=1).episode_number == 1


def test_dialogue_minimal_construction_roundtrip() -> None:
    d = Dialogue(speaker="yonko", text="今日は風が逆だ")
    assert d.model_dump() == {"speaker": "yonko", "text": "今日は風が逆だ"}


def test_panel_optional_fields_default_empty() -> None:
    p = Panel(index=2, description="d")
    assert p.characters == []
    assert p.dialogue == []


def test_scenario_week_episodes_capped_at_seven() -> None:
    with pytest.raises(ValidationError):
        ScenarioWeek(
            week="2026-W19",
            episodes=[_episode(episode_number=i + 1) for i in range(8)],
        )
    week = ScenarioWeek(
        week="2026-W19",
        episodes=[_episode(episode_number=i + 1) for i in range(7)],
    )
    assert len(week.episodes) == 7


def test_scenario_week_episodes_min_one() -> None:
    with pytest.raises(ValidationError):
        ScenarioWeek(week="2026-W19", episodes=[])
    week = ScenarioWeek(week="2026-W19", episodes=[_episode()])
    assert len(week.episodes) == 1
