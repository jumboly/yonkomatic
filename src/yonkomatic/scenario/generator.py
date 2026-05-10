"""Generate a week of seven yonkoma scenarios in a single LLM call.

Generation runs once per ISO week (typically from a Sunday cron job). The
contract is the ``ScenarioWeek`` Pydantic schema — OpenAI Structured Output
enforces it server-side via JSON Schema, so the caller can rely on the
parsed object without ad-hoc fence/brace extraction.
"""

from __future__ import annotations

from pathlib import Path

from yonkomatic.ai.openai_client import OpenAIClient
from yonkomatic.panel.description import ContentPack
from yonkomatic.scenario.schema import ScenarioWeek
from yonkomatic.template import RenderedPrompt, load_template, render

_TEMPERATURE = 0.8


def _format_news_block(news_headlines: list[str] | None) -> str:
    """Pre-render the news section so the template stays free of conditionals."""
    if not news_headlines:
        return ""
    bullets = "\n".join(f"- {h}" for h in news_headlines)
    return f"# ニュース見出し (先週分・参考)\n\n{bullets}\n"


def generate_week(
    *,
    openai: OpenAIClient,
    pack: ContentPack,
    week: str,
    template_path: Path,
    news_headlines: list[str] | None = None,
) -> tuple[ScenarioWeek, RenderedPrompt]:
    """Generate a full ScenarioWeek (7 episodes) in one OpenAI call.

    Returns the validated ScenarioWeek plus the rendered prompt pair, so the
    caller can persist the prompt to ``scenarios/{week}.rendered.txt`` for
    later inspection.
    """
    template = load_template(template_path)
    variables = {
        "week": week,
        "prompt_main": pack.prompt,
        "news_block": _format_news_block(news_headlines),
    }
    user = render(template.body, variables)
    system = template.system

    rendered = RenderedPrompt(system=system, user=user)
    scenario = openai.complete_structured(
        system=system,
        user=user,
        schema=ScenarioWeek,
        temperature=_TEMPERATURE,
    )
    return scenario, rendered
