"""Stage 1: turn a structured scenario into a single image prompt for Gemini.

Claude is given the scenario JSON, the character settings, the world
settings and the STYLE.md, and is asked to compose ONE long prompt that
instructs Gemini to render all four panels stacked vertically (3:4
aspect) as a single PNG. The dialogue text is included in the prompt so
the model can attempt to render it; the PIL fallback (Step 3) covers
cases where Gemini's Japanese typography is poor.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from yonkomatic.ai.claude_client import ClaudeClient
from yonkomatic.scenario.schema import ScenarioEpisode


@dataclass
class ContentPack:
    """Plain-text material loaded from the user's content/ tree (or examples/)."""

    characters_md: str
    world_md: str
    style_md: str
    theme_md: str | None = None

    @classmethod
    def from_dir(cls, base: Path) -> ContentPack:
        """Load required markdown from a content-style directory.

        Layout expected (matches ``examples/minimal/``)::

            base/
              characters/settings.md
              world/settings.md
              samples/STYLE.md
              themes/default.md   (optional)
        """
        return cls(
            characters_md=(base / "characters" / "settings.md").read_text(encoding="utf-8"),
            world_md=(base / "world" / "settings.md").read_text(encoding="utf-8"),
            style_md=(base / "samples" / "STYLE.md").read_text(encoding="utf-8"),
            theme_md=_read_optional(base / "themes" / "default.md"),
        )


def _read_optional(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


SYSTEM_PROMPT = """\
あなたは4コマ漫画の画像生成プロンプトを書く専門家です。日本語のシナリオと
キャラクター・世界観・画風の資料を受け取り、Gemini 3.1 Flash Image が
1枚の縦長 PNG (アスペクト比 3:4) として 4 コマ全体を描けるよう、
英語の単一プロンプトを出力してください。

要件:
- 4 コマを縦に等しい高さで並べる構成。各コマの境界は細い黒線
- 各パネルの構図、キャラクター配置、表情、背景を具体的に
- 吹き出しは記載するが、テキスト描画が苦手な場合に備えて PIL でも上から
  描けるようにシンプルな配置にする
- 画風は与えられた STYLE.md に厳密に従う
- 出力は **プロンプト本文だけ**。前置きや解説は書かない
"""


def build_image_prompt(
    *,
    episode: ScenarioEpisode,
    pack: ContentPack,
    claude: ClaudeClient,
) -> str:
    """Ask Claude to assemble a single English prompt for Gemini."""
    panels_block = "\n\n".join(
        f"Panel {p.index}\n"
        f"  description: {p.description}\n"
        f"  characters: {', '.join(p.characters) or '(none)'}\n"
        + ("  dialogue:\n" + "\n".join(f'    - {d.speaker}: 「{d.text}」' for d in p.dialogue)
           if p.dialogue else "  dialogue: (none)")
        for p in episode.panels
    )

    user = f"""\
# シナリオ

タイトル: {episode.title}
あらすじ (ネタバレなし): {episode.summary_no_spoiler}

{panels_block}

# キャラクター設定

{pack.characters_md}

# 世界観設定

{pack.world_md}

# 画風 (STYLE.md)

{pack.style_md}
"""
    if pack.theme_md:
        user += f"\n# 月別テーマ\n\n{pack.theme_md}\n"

    return claude.complete(
        system=SYSTEM_PROMPT,
        user=user,
        temperature=0.4,
    ).strip()
