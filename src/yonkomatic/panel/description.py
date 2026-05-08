"""Stage 1: turn a structured scenario into a single image prompt for Gemini.

Claude is given the scenario JSON, the character settings, the world
settings and the STYLE.md, and is asked to compose ONE long English
prompt that instructs Gemini to render all four panels stacked vertically
(3:4 aspect) as a single image. Dialogue is passed as a *composition hint*
only — Gemini is explicitly told NOT to draw bubbles or text, since the
post-processing PIL overlay (``panel/composer.py``) handles Japanese
rendering to avoid Gemini's hallucinated-kana failure mode.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from yonkomatic.ai.claude_client import ClaudeClient
from yonkomatic.config import ContentConfig
from yonkomatic.scenario.schema import Panel, ScenarioEpisode


@dataclass
class ContentPack:
    """Plain-text material loaded from the user's content/ tree (or examples/)."""

    characters_md: str
    world_md: str
    style_md: str
    theme_md: str | None = None

    @classmethod
    def from_dir(
        cls,
        base: Path,
        content_cfg: ContentConfig | None = None,
        *,
        characters_filename: str = "settings.md",
        world_filename: str = "settings.md",
        style_filename: str = "STYLE.md",
        theme_filename: str = "default.md",
    ) -> ContentPack:
        """Load required markdown using ContentConfig's subdir names.

        Filename defaults match ``examples/minimal/``; the per-domain subdir
        names come from ``content_cfg`` so that customizing
        ``config.yaml``'s ``content.*_dir`` keys flows through here.
        """
        cfg = content_cfg or ContentConfig()
        return cls(
            characters_md=(cfg.characters_path(base) / characters_filename).read_text(
                encoding="utf-8"
            ),
            world_md=(cfg.world_path(base) / world_filename).read_text(encoding="utf-8"),
            style_md=(cfg.samples_path(base) / style_filename).read_text(encoding="utf-8"),
            theme_md=_read_optional(cfg.themes_path(base) / theme_filename),
        )


def _read_optional(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def _format_panel(panel: Panel) -> str:
    lines = [
        f"Panel {panel.index}",
        f"  description: {panel.description}",
        f"  characters: {', '.join(panel.characters) or '(none)'}",
    ]
    if panel.dialogue:
        lines.append("  dialogue (do NOT render as text in the image; for composition hints only):")
        lines.extend(f'    - {d.speaker}: 「{d.text}」' for d in panel.dialogue)
    else:
        lines.append("  dialogue: (none)")
    return "\n".join(lines)


SYSTEM_PROMPT = """\
あなたは4コマ漫画の画像生成プロンプトを書く専門家です。日本語のシナリオと
キャラクター・世界観・画風の資料を受け取り、Gemini 3.1 Flash Image が
1枚の縦長 PNG (アスペクト比 3:4) として 4 コマ全体を描けるよう、
英語の単一プロンプトを出力してください。

要件:
- 4 コマを縦に等しい高さで並べる構成。各コマの境界は細い黒線
- 各パネルの構図、キャラクター配置、表情、背景を具体的に
- **吹き出しおよびテキストは画像内に一切描画させない**。各パネル内には
  キャラクターの上部・横に吹き出しを後から重ねるための「空のスペース」
  (壁・空・背景など、人物・小物のない領域) をはっきり残すこと。プロンプト
  には英語で `absolutely no speech bubbles, no text, no captions, no letters
  of any language (no hiragana, katakana, kanji, latin); leave empty space
  above and to the side of each character so bubbles can be composited in
  post-processing` のような指示を必ず含める
- 表情・口の開き・視線・ポーズは dialogue (composition hints) を踏まえて
  描写するが、台詞そのものを画像内に書かない
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
    panels_block = "\n\n".join(_format_panel(p) for p in episode.panels)

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
