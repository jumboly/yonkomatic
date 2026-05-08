"""Stage 0: ask Claude to draft a week of seven yonkoma scenarios in one call.

Generation runs once per ISO week (typically from a Sunday cron job). The
contract is the ScenarioWeek Pydantic schema — Claude must return JSON
that validates against it, otherwise the caller treats it as a hard
failure and the cron retries on the next run.
"""

from __future__ import annotations

import re

from yonkomatic.ai.claude_client import ClaudeClient
from yonkomatic.panel.description import ContentPack
from yonkomatic.scenario.schema import ScenarioWeek

_MAX_TOKENS = 8192
_TEMPERATURE = 0.8

SYSTEM_PROMPT = """\
あなたは日本語の4コマ漫画シナリオを書く脚本家です。指定された ISO 週 (例 "2026-W19") に
向けて、独立した 7 話分のシナリオを 1 回の呼び出しで生成してください。

## 出力形式

応答は **有効な JSON オブジェクト 1 つだけ** とし、前置き・後置き・コードフェンス・解説を
含めないでください。スキーマは以下:

{
  "week": "YYYY-Www",
  "episodes": [
    {
      "week": "YYYY-Www",
      "episode_number": 1,
      "title": "...",
      "summary_no_spoiler": "...",
      "panels": [
        {
          "index": 1,
          "description": "そのコマで何が起きているかの具体的な描写 (日本語)",
          "characters": ["キャラ識別子", "..."],
          "dialogue": [
            {"speaker": "キャラ識別子", "text": "セリフ", "kind": "speech"}
          ]
        }
      ]
    }
  ]
}

## 厳守事項

- episodes は **正確に 7 件**、各 episode の panels は **正確に 4 件**
- episode_number は 1〜7 の連番
- 各 episode の "week" フィールドは入力された週と同一値を埋める
- 各話は 1 話完結。前後の話に依存させない
- 4 コマは起承転結 (1: 状況提示 / 2: 展開 / 3: 転換 / 4: オチ)
- summary_no_spoiler はオチを書かない 1〜2 文の要約
- characters はキャラ設定 (settings.md) の識別子を使う (例 "yonko")
- description は次工程で英語の画像生成プロンプトに翻訳される。具体的な行動・表情・場所を
  書く。「面白い表情をする」のような曖昧表現は禁止
- dialogue は必要なときだけ。1 行 30 字以内目安
- 各 dialogue の "kind" は次のいずれか。デフォルトは "speech":
  - "speech": 通常台詞 (楕円の吹き出しで描画される)
  - "thought": 内心モノローグ・心の声 (雲形の吹き出しで描画される)
  - "shout": 叫び・驚き (ジグザグ枠で描画される)
  これは後段の PIL オーバーレイで吹き出し形状を切り替えるためのメタデータ

## 時事ネタの扱い (任意で渡される場合)

ニュース見出しが提供された場合、これらは「世間のムード・話題の傾向」として薄く反映させて
ください。直接的な時事言及 (特定の人名・事件・政治・災害) は避け、当該ジャンルが流行って
いる空気感だけを取り込むこと。

避けるべき題材:
- 政治、宗教、災害、訃報、犯罪
- 特定の実在人物への言及
- 商標・著作権のあるキャラやブランド名
"""


def _build_user_prompt(
    *,
    week: str,
    pack: ContentPack,
    news_headlines: list[str] | None,
) -> str:
    parts = [
        f"# 対象週\n\n{week}\n",
        f"# キャラクター設定\n\n{pack.characters_md}\n",
        f"# 世界観設定\n\n{pack.world_md}\n",
        f"# 画風 (STYLE.md)\n\n{pack.style_md}\n",
    ]
    if pack.theme_md:
        parts.append(f"# 月別テーマ\n\n{pack.theme_md}\n")
    if news_headlines:
        bullets = "\n".join(f"- {h}" for h in news_headlines)
        parts.append(f"# ニュース見出し (先週分・参考)\n\n{bullets}\n")
    return "\n".join(parts)


def _extract_json(raw: str) -> str:
    """Pull a JSON object out of Claude's reply.

    Why two-step: the system prompt forbids code fences, but Claude
    occasionally adds them anyway. ``` blocks are accepted as a courtesy
    and a brace-balanced scan handles a stray prose preamble.
    """
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fence:
        return fence.group(1)

    start = raw.find("{")
    if start < 0:
        raise ValueError("Claude reply contained no JSON object")

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(raw)):
        ch = raw[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return raw[start : i + 1]
    raise ValueError("Claude reply has unbalanced braces")


def generate_week(
    *,
    claude: ClaudeClient,
    pack: ContentPack,
    week: str,
    news_headlines: list[str] | None = None,
) -> ScenarioWeek:
    """Generate a full ScenarioWeek (7 episodes) in one Claude call."""
    user = _build_user_prompt(week=week, pack=pack, news_headlines=news_headlines)
    raw = claude.complete(
        system=SYSTEM_PROMPT,
        user=user,
        max_tokens=_MAX_TOKENS,
        temperature=_TEMPERATURE,
    )
    json_text = _extract_json(raw)
    return ScenarioWeek.model_validate_json(json_text)
