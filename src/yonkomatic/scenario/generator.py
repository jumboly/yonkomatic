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
#
# Numbers in the gpt-image-2 entry (95-99% CJK accuracy, 15 chars/bubble
# threshold, 25% hand-pose failure rate, 6-8 panel face-drift threshold)
# are sourced 2026-05-10 from:
#   - developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide
#   - floatboat.ai/blog/gpt-image-2-manga-comic-workflow
#   - openai.com/index/introducing-chatgpt-images-2-0
# Update this table when OpenAI publishes new benchmarks or when our
# own validation runs (ROADMAP "Step 6.5") shift the failure profile.
_IMAGE_MODEL_GUIDANCE: dict[str, str] = {
    "gpt-image-2": (
        "画像生成モデルは **gpt-image-2** (2026-04-21 リリース、`/v1/images/generations`) を使用します。"
        "ChatGPT Images 2.0 の API 版で、reasoning (思考) を画像生成前に行うため、"
        "前世代 (gpt-image-1) と比べて指示遵守・テキスト精度・空間整合が劇的に向上しています。\n\n"
        "## 公式ベンチマーク確認済みの強み\n"
        "- **CJK テキスト精度 ~95-99%**: 日本語・中国語・韓国語で文字レベル一致。漢字・ひらがな・カタカナ混在の自然な台詞を恐れず書ける\n"
        "- **マルチパネル構図最適化**: comics をユースケース筆頭に謳い、4 コマや webtoon のような縦並びレイアウトに強い\n"
        "- **Reasoning 内蔵**: 描画前に構図・空間関係・テキスト整合を内部検証する。yonkomatic の検証 (W19 全 7 話) で完全一致 6/7 / 致命的バグ 0/7 を確認済み\n\n"
        "## 既知の制約 (シナリオで回避)\n"
        "- **1 吹き出し 15 字超で精度低下**: 長い台詞は文を 2 つに分けるか改行を入れる。30 字制限はそのまま守りつつ、できれば 15 字以内に収める\n"
        "- **動的ポーズの手は ~25% 失敗**: 「指差し」「物を握る」などをオチの決め手に使わない (失敗時にネタが崩壊する)。手は支えに留め、オチは表情・台詞で取る\n"
        "- **6-8 パネル超で顔ドリフト**: 4 コマ範囲なら気にしなくてよい\n"
        "- **話者スワップが稀発**: 同 panel に 2 人以上いると、台詞が逆のキャラに割り当てられることがある\n\n"
        "## 能力を最大限活かす指針\n"
        "- **dialogue 密度**: 4 コマで合計 6〜8 吹き出し (1 panel 平均 1.5〜2) まで安定。台詞のリズム・掛け合いの応酬で魅せる\n"
        "- **擬音 (オノマトペ)**: 「ぽふ」「トン」「ピッ」「ザワッ」などは **dialogue ではなく description に書く** (例: 「画面右下に小さく『ぽふ』の擬音」)。dialogue 配列に入れると吹き出しになるが、効果音として浮かせたい場合は description 経由が正解\n"
        "- **構図の切替**: panel ごとに寄り (バストアップ) と引き (全身)、視点の前後・俯瞰/煽りを積極的に変える。モデルは正確に追随する\n"
        "- **話者の毎パネル再記述**: 各 description で話者の見た目特徴を具体的に再記述する (例: 「赤パーカのマチカが」「黒髪眼鏡のヨンコが」)。**パラフレーズせず一字一句同じ表現を繰り返す**ことでキャラ識別精度が上がる (公式 cookbook 推奨)\n"
        "- **panel 間の時刻・場所差を明示**: 「同じ部屋」でも「カーテンが半開きになった」「夕日が差している」のような小さな変化を入れる。reasoning が時間経過を読み取り、4 コマ漫画として整える\n"
        "- **negative constraint は不要**: 「文字を描くな」「ロゴを入れるな」などの禁止指示は panel-prompt 側 (英語化レイヤ) で扱う。シナリオ側は描いてほしい絵を素直に書けばよい"
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
