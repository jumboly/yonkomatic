"""Generate a week of seven yonkoma scenarios in a single LLM call.

Generation runs once per ISO week (typically from a Sunday cron job). The
contract is the ``ScenarioWeek`` Pydantic schema — OpenAI Structured Output
enforces it server-side via JSON Schema, so the caller can rely on the
parsed object without ad-hoc fence/brace extraction.

The scenario LLM is also informed of the *image* model that will render
the panels, so it can shape dialogue density and visual complexity to
that model's known strengths and weaknesses (see ``_image_model_guidance``).
"""

from __future__ import annotations

from pathlib import Path

from yonkomatic.ai.openai_client import OpenAIClient
from yonkomatic.panel.description import ContentPack
from yonkomatic.scenario.schema import ScenarioWeek
from yonkomatic.template import RenderedPrompt, load_template, render

_TEMPERATURE = 0.8


# Per-model capability profiles. These are the writer's guard rails: a
# strong image model gets license to use richer dialogue and composition;
# a weak one is steered toward simpler, lower-risk scenarios.
# Keys are matched against ``image_model`` exactly first, then by prefix
# (so e.g. ``gpt-image-2-2026-04-21`` falls back to ``gpt-image-2``).
_IMAGE_MODEL_GUIDANCE: dict[str, str] = {
    "gpt-image-2": (
        "画像生成モデルは **gpt-image-2** (2026-04-21 リリース) を使用します。"
        "日本語テキスト描画精度・指示遵守ともに高水準で、comics をユースケース筆頭に謳うモデルです。\n\n"
        "能力を最大限活かす指針:\n"
        "- **dialogue**: 4 コマで合計 6〜8 吹き出し (1 パネル平均 1.5〜2 吹き出し) まで余裕があります。台詞のリズムや掛け合いの応酬で魅せてください\n"
        "- **擬音**: 「ぽふ」「トン」「ピッ」のような効果音は dialogue ではなく `description` 内で指示してください (例: 「画面右下に小さく『ぽふ』の擬音」)。漫画らしさが増します\n"
        "- **構図**: 寄り (バストアップ) と引き (全身) の切替、視点の前後を panel ごとに積極的に変えて構いません — モデルは正確に追随します\n"
        "- **文字種**: 漢字・ひらがな・カタカナを混在させて自然な台詞にしてかまいません (誤字幻覚は出にくい)\n"
        "- **話者位置**: 左右や前後の配置は場面の自然さで決めて OK。ただし話者スワップが稀に出るので、**話者の特徴 (服装・髪・小物) を description に毎パネル明記**して曖昧さを残さないこと"
    ),
    "gpt-image-1": (
        "画像生成モデルは **gpt-image-1** を使用します。日本語テキスト描画と指示遵守の両面で弱点があり、"
        "4 コマが 2-3 コマに端折られる/誤字幻覚が出やすいモデルです。\n\n"
        "リスクを抑える指針:\n"
        "- **dialogue**: 1 パネル 1 吹き出しを基本、最大でも 1 パネル 2 吹き出しまで\n"
        "- **文字数**: 1 吹き出し 8 文字以内に短く保ち、漢字より **ひらがな・カタカナを優先** (誤字幻覚を回避)\n"
        "- **パネル差別化**: 各パネルの時刻・場所・カメラ位置の違いを description に**明示的に書く** (端折り防止)\n"
        "- **擬音・複雑構図は避ける**。シンプルな 2 人の掛け合いに集中する"
    ),
    "gemini-3.1-flash-image-preview": (
        "画像生成モデルは **Gemini 3.1 Flash + PIL オーバーレイ** を使用します。"
        "台詞は PIL で後段合成されるため、AI が日本語を描く必要はありません。\n\n"
        "指針:\n"
        "- **dialogue**: 文字数制限ゆるめ (PIL がレンダリング)、ただし 1 吹き出し 20 字程度を目安に\n"
        "- **余白指示**: description に「キャラの上部・横に吹き出し用の空白スペースを残す」と書く\n"
        "- **擬音**: dialogue ではなく description に書く (PIL は dialogue 配列のみオーバーレイする)"
    ),
}


def _image_model_guidance(model: str) -> str:
    """Return capability guidance for ``model``; fall back by prefix then default."""
    if model in _IMAGE_MODEL_GUIDANCE:
        return _IMAGE_MODEL_GUIDANCE[model]
    for key, text in _IMAGE_MODEL_GUIDANCE.items():
        if model.startswith(key):
            return text
    return (
        f"画像生成モデル (`{model}`) の能力プロフィールは未登録です。"
        "汎用的なシナリオを書いてください: 1 パネル平均 1〜2 吹き出し、台詞は短めに、"
        "各パネルの場面差 (時刻・場所・カメラ) を description に明確に書く。"
    )


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
    image_model: str,
    news_headlines: list[str] | None = None,
) -> tuple[ScenarioWeek, RenderedPrompt]:
    """Generate a full ScenarioWeek (7 episodes) in one OpenAI call.

    ``image_model`` is the id of the downstream image model the panels
    will be rendered with; the generator uses it to fetch capability
    guidance and shape dialogue / composition decisions accordingly.
    """
    template = load_template(template_path)
    variables = {
        "week": week,
        "prompt_main": pack.prompt,
        "news_block": _format_news_block(news_headlines),
        "image_model_guidance": _image_model_guidance(image_model),
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
