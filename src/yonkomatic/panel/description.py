"""Stage 1: turn a structured scenario into a single image prompt for Gemini.

Claude is given the scenario JSON, the character settings, the world
settings and the STYLE.md, and is asked to compose ONE long English
prompt that instructs Gemini to render all four panels stacked vertically
(3:4 aspect) as a single image.

Two modes (selected via ``text_rendering.mode`` in config):

- ``pil_overlay``: dialogue is passed as a *composition hint* only — Gemini
  is told NOT to draw bubbles or text, and PIL overlays Japanese after.
  Use with lower-tier models (Flash) that hallucinate kana.
- ``model_render``: Gemini is told to draw proper speech bubbles with
  the exact Japanese dialogue inside. Skips PIL overlay. Only viable on
  higher-tier models (e.g. ``gemini-3-pro-image-preview``).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from yonkomatic.ai.claude_client import ClaudeClient
from yonkomatic.config import ContentConfig, TextRenderMode
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


def _format_panel(panel: Panel, mode: TextRenderMode) -> str:
    lines = [
        f"Panel {panel.index}",
        f"  description: {panel.description}",
        f"  characters: {', '.join(panel.characters) or '(none)'}",
    ]
    if panel.dialogue:
        if mode == "pil_overlay":
            header = "  dialogue (do NOT render as text in the image; for composition hints only):"
        else:
            header = (
                "  dialogue (render exactly as Japanese text inside speech bubbles, "
                "attributed to the speaker; preserve every character verbatim):"
            )
        lines.append(header)
        lines.extend(f'    - {d.speaker}: 「{d.text}」' for d in panel.dialogue)
    else:
        lines.append("  dialogue: (none)")
    return "\n".join(lines)


SYSTEM_PROMPT_PIL_OVERLAY = """\
あなたは4コマ漫画の画像生成プロンプトを書く専門家です。日本語のシナリオと
キャラクター・世界観・画風の資料を受け取り、Gemini Image が 1枚の縦長
PNG (アスペクト比 3:4) として 4 コマ全体を描けるよう、英語の単一プロンプ
トを出力してください。

要件:
- 4 コマを縦に等しい高さで並べる構成。各コマの境界は細い黒線
- 各パネルの構図、キャラクター配置、表情、背景を具体的に
- **吹き出しおよびテキストは画像内に一切描画させない**。これは「文字を
  入れない空の吹き出し」も含む — 空の楕円・雲形・角丸枠・ジグザグ枠
  などマンガ的な吹き出し形状を画面内のどこにも置かせない。各パネル内
  にはキャラクターの上部・横に吹き出しを後から重ねるための「空のスペ
  ース」(壁・空・背景など、人物・小物のない領域) をはっきり残すこと。
  プロンプトには英語で `absolutely no speech bubbles or balloons of any
  kind — including empty, blank, or text-less ones; no white rounded
  shapes, ovals, rectangles, clouds, or burst shapes overlaid on the
  scene; no text, no captions, no letters in any language (no hiragana,
  katakana, kanji, latin, romaji). The background must be naturalistic
  only — sky, walls, foliage, plain interiors. Any white or light area
  must be a real diegetic object (paper, cloth, sky, light, fog), not a
  graphic overlay. Leave generous empty space above and to the side of
  each character so bubbles can be composited in post-processing` の
  ような指示を必ず含める
- 表情・口の開き・視線・ポーズは dialogue (composition hints) を踏まえて
  描写するが、台詞そのものを画像内に書かない
- 画風は与えられた STYLE.md に厳密に従う
- 出力は **プロンプト本文だけ**。前置きや解説は書かない
"""


SYSTEM_PROMPT_MODEL_RENDER = """\
あなたは4コマ漫画の画像生成プロンプトを書く専門家です。日本語のシナリオと
キャラクター・世界観・画風の資料を受け取り、Gemini Image が 1枚の縦長
PNG (アスペクト比 3:4) として 4 コマ全体を描けるよう、英語の単一プロンプ
トを出力してください。

このモードでは画像モデル自身に吹き出しと日本語の台詞を描かせます。

要件:
- 4 コマを縦に等しい高さで並べる構成。各コマの境界は細い黒線
- 各パネルの構図、キャラクター配置、表情、背景を具体的に
- **吹き出しと台詞テキストは画像モデルに描かせる**。各 dialogue 行を
  発言者ごとに白い吹き出しに入れ、入力された日本語テキスト (ひらがな・
  カタカナ・漢字) を **一字一句正確に** 再現する。台詞を要約・翻訳・
  英訳しない
- プロンプトには英語で `render legible Japanese speech bubbles for the
  given dialogue. Each bubble must contain the exact Japanese characters
  provided — do NOT paraphrase, translate, romanize, or substitute with
  pseudo-Japanese glyphs. Use clean white speech balloons with a thin
  black outline, attached to the corresponding speaker via a small tail.
  Position bubbles so they do not occlude faces. Preserve every hiragana,
  katakana, and kanji exactly as written in the dialogue list` の
  ような指示を必ず含める
- 同一パネル内の dialogue 件数が複数あれば、speaker 順に上→下 / 左→右で
  自然に配置するよう指示する
- 表情・口の開き・視線・ポーズは台詞のニュアンスに沿って描写する
- 画風は与えられた STYLE.md に厳密に従う
- 出力は **プロンプト本文だけ**。前置きや解説は書かない
"""


def _system_prompt_for(mode: TextRenderMode) -> str:
    return (
        SYSTEM_PROMPT_PIL_OVERLAY if mode == "pil_overlay" else SYSTEM_PROMPT_MODEL_RENDER
    )


def build_image_prompt(
    *,
    episode: ScenarioEpisode,
    pack: ContentPack,
    claude: ClaudeClient,
    mode: TextRenderMode,
) -> str:
    """Ask Claude to assemble a single English prompt for Gemini."""
    panels_block = "\n\n".join(_format_panel(p, mode) for p in episode.panels)

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
        system=_system_prompt_for(mode),
        user=user,
        temperature=0.4,
    ).strip()
