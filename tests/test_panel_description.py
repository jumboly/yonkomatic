"""Unit tests for build_image_prompt — Jinja-free template render + LLM mock."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from yonkomatic.ai.openai_client import OpenAIClient
from yonkomatic.panel.description import ContentPack, build_image_prompt
from yonkomatic.scenario.schema import Dialogue, Panel, ScenarioEpisode

_TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "yonkomatic"
    / "templates"
    / "panel_prompt.md"
)


def _episode() -> ScenarioEpisode:
    return ScenarioEpisode(
        episode_number=1,
        title="風の予告",
        summary_no_spoiler="風向きから一日の予告を読み取る話",
        panels=[
            Panel(
                index=1,
                description="朝の窓辺",
                characters=["yonko"],
                dialogue=[Dialogue(speaker="yonko", text="今日は風が逆だ")],
            ),
            Panel(index=2, description="廊下を歩く", characters=["yonko"], dialogue=[]),
            Panel(index=3, description="教室に入る", characters=["yonko"], dialogue=[]),
            Panel(
                index=4,
                description="窓の外を見る",
                characters=["yonko"],
                dialogue=[Dialogue(speaker="yonko", text="やっぱりね")],
            ),
        ],
    )


def _mock_client(mocker: MockerFixture, *, response: str = "english prompt") -> MagicMock:
    # Why spec=OpenAIClient: typo in the mocked attribute (e.g. ``.completion``)
    # would silently return a new Mock without spec. Spec catches API drift.
    mock = mocker.MagicMock(spec=OpenAIClient)
    mock.complete.return_value = response
    return mock


def test_build_image_prompt_calls_complete_once_with_rendered_pair(
    mocker: MockerFixture,
) -> None:
    mock = _mock_client(mocker)
    build_image_prompt(
        episode=_episode(),
        pack=ContentPack(prompt="主人公スタイル", images=[]),
        openai=mock,
        template_path=_TEMPLATE_PATH,
        image_model="gpt-image-2",
    )
    mock.complete.assert_called_once()
    kwargs = mock.complete.call_args.kwargs
    assert kwargs["system"]
    assert kwargs["user"]


def test_build_image_prompt_strips_assistant_response(mocker: MockerFixture) -> None:
    mock = _mock_client(mocker, response="  english prompt  \n")
    image_prompt, _ = build_image_prompt(
        episode=_episode(),
        pack=ContentPack(prompt="主人公スタイル"),
        openai=mock,
        template_path=_TEMPLATE_PATH,
        image_model="gpt-image-2",
    )
    assert image_prompt == "english prompt"


def test_build_image_prompt_returns_rendered_prompt_with_both_blocks(
    mocker: MockerFixture,
) -> None:
    mock = _mock_client(mocker)
    _, rendered = build_image_prompt(
        episode=_episode(),
        pack=ContentPack(prompt="主人公スタイル"),
        openai=mock,
        template_path=_TEMPLATE_PATH,
        image_model="gpt-image-2",
    )
    assert isinstance(rendered.system, str) and rendered.system
    assert isinstance(rendered.user, str) and rendered.user


def test_user_prompt_includes_episode_title_and_summary(mocker: MockerFixture) -> None:
    mock = _mock_client(mocker)
    _, rendered = build_image_prompt(
        episode=_episode(),
        pack=ContentPack(prompt="主人公スタイル"),
        openai=mock,
        template_path=_TEMPLATE_PATH,
        image_model="gpt-image-2",
    )
    assert "風の予告" in rendered.user
    assert "風向きから一日の予告を読み取る話" in rendered.user


def test_user_prompt_includes_panel_descriptions_in_order(mocker: MockerFixture) -> None:
    mock = _mock_client(mocker)
    _, rendered = build_image_prompt(
        episode=_episode(),
        pack=ContentPack(prompt="主人公スタイル"),
        openai=mock,
        template_path=_TEMPLATE_PATH,
        image_model="gpt-image-2",
    )
    positions = [rendered.user.find(f"Panel {i}") for i in range(1, 5)]
    assert all(p >= 0 for p in positions)
    assert positions == sorted(positions)


def test_system_prompt_includes_image_model_guidance_for_known_model(
    mocker: MockerFixture,
) -> None:
    mock = _mock_client(mocker)
    _, rendered = build_image_prompt(
        episode=_episode(),
        pack=ContentPack(prompt="主人公スタイル"),
        openai=mock,
        template_path=_TEMPLATE_PATH,
        image_model="gpt-image-2",
    )
    assert "Literal text in double quotes" in rendered.system


def test_system_prompt_uses_default_guidance_for_unknown_model(
    mocker: MockerFixture,
) -> None:
    mock = _mock_client(mocker)
    _, rendered = build_image_prompt(
        episode=_episode(),
        pack=ContentPack(prompt="主人公スタイル"),
        openai=mock,
        template_path=_TEMPLATE_PATH,
        image_model="some-unknown-model-2099",
    )
    assert "not in the prompt-engineering profile table" in rendered.system


def test_temperature_is_forwarded(mocker: MockerFixture) -> None:
    mock = _mock_client(mocker)
    build_image_prompt(
        episode=_episode(),
        pack=ContentPack(prompt="主人公スタイル"),
        openai=mock,
        template_path=_TEMPLATE_PATH,
        image_model="gpt-image-2",
        temperature=0.7,
    )
    assert mock.complete.call_args.kwargs["temperature"] == pytest.approx(0.7)
