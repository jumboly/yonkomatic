"""Turn a structured scenario into a single image prompt for the image model.

The text LLM is given the scenario, character / world / style notes from
``prompt.md``, and the ``panel_prompt.md`` template, and is asked to
compose ONE long English prompt that instructs the image model to render
all four panels stacked vertically (3:4 aspect) as a single image.

Templates live in ``src/yonkomatic/templates/`` by default, but a
same-named file under ``content/`` overrides them so power users can
customise without forking yonkomatic.

A per-image-model **prompt-engineering** profile is injected into the
template via ``image_model_prompt_guidance``. This is distinct from the
scenario-writer's profile (``scenario/generator.py``): scenario guidance
shapes plot/dialogue density; this one shapes how the panel-prompt LLM
phrases its English output to maximise the image model's accuracy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

from yonkomatic.ai.openai_client import OpenAIClient, resolve_model_profile
from yonkomatic.config import ContentConfig
from yonkomatic.scenario.schema import Panel, ScenarioEpisode
from yonkomatic.template import RenderedPrompt, load_template, render

_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
_console = Console(stderr=True)


# Prompt-engineering tactics for each image model. Sourced 2026-05-10 from
# the OpenAI Cookbook (image-gen-models-prompting-guide), the manga workflow
# write-up at floatboat.ai/blog/gpt-image-2-manga-comic-workflow, and our
# own gpt-image-2 validation runs. Update when OpenAI publishes new
# guidance or when prompts that previously worked stop working.
_PANEL_PROMPT_GUIDANCE: dict[str, str] = {
    "gpt-image-2": (
        "The downstream image model is **gpt-image-2** (released 2026-04-21). "
        "It has built-in reasoning that plans composition and verifies text "
        "before rendering, and reaches ~95-99% character-level accuracy on "
        "Japanese / Chinese / Korean text. Apply these tactics in your output prompt:\n\n"
        "**Literal text in double quotes.** Wrap every Japanese dialogue line "
        "verbatim in straight double quotes (e.g. `\"今日は風向きがいつもと逆です\"`). "
        "Quoted text renders literally; unquoted text drifts to plausible-looking "
        "gibberish.\n\n"
        "**Sequential panel labels.** Structure the prompt as `Panel 1 (top): ...`, "
        "`Panel 2 (second from top): ...`, `Panel 3 (third from top): ...`, "
        "`Panel 4 (bottom): ...`. Sequential labels strongly bias the model toward "
        "the requested panel count.\n\n"
        "**Verbatim character anchors.** Repeat each character's visual identifiers "
        "(hair, glasses, clothing, accessory) in **identical wording** every panel "
        "where they appear. Paraphrasing causes faces and outfits to drift between "
        "panels (the OpenAI cookbook calls this out explicitly).\n\n"
        "**Per-panel framing & viewpoint.** State the camera framing (close-up / "
        "medium / wide) and angle (eye-level / low-angle / overhead) explicitly per "
        "panel; reasoning will respect it.\n\n"
        "**Short labeled segments.** Use `Style:`, `Layout:`, `Background:`, "
        "`Speech bubbles:` sub-blocks rather than one paragraph. The cookbook "
        "explicitly recommends this over long prose.\n\n"
        "**Speech bubble layout.** For each dialogue, instruct: white speech balloon "
        "with thin black outline, tail pointing at the speaker, positioned so it does "
        "not occlude the speaker's face. Multiple bubbles in one panel: arrange in "
        "reading order (top→bottom for vertical, left-character bubble on left).\n\n"
        "**SFX / onomatopoeia.** When the scenario description mentions an effect "
        "like 「ぽふ」「トン」, render it as drawn-in katakana SFX integrated into the "
        "scene art (NOT inside a speech bubble). Use a phrase like "
        "`small katakana SFX \"ぽふ\" drawn into the scene`.\n\n"
        "**Negative constraints at the end.** Append explicit exclusions: "
        "`no extra text outside the specified speech bubbles, no watermarks, no logos, "
        "no romaji captions, no English captions, no UI elements`. Stating exclusions "
        "after the positive description is the cookbook's recommended ordering.\n\n"
        "**Aspect ratio reminder.** Open the prompt with `A single vertical image "
        "(aspect ratio 3:4, 1536x2048) showing four equal-height panels stacked "
        "vertically with thin black borders between them.`"
    ),
    "gpt-image-1": (
        "The downstream image model is **gpt-image-1** (legacy). Text accuracy and "
        "instruction following are weaker than gpt-image-2; common failures are "
        "panel-count violations (4 → 2-3) and Japanese kanji hallucinations.\n\n"
        "Risk-mitigation tactics:\n"
        "- **Hard-emphasise panel count**: phrases like `EXACTLY four panels, no fewer, "
        "  no more. Each panel is mandatory.` repeated near the start and end of the prompt\n"
        "- **Quote dialogue in double quotes** verbatim; expect imperfect rendering\n"
        "- **Prefer short ASCII-friendly panel descriptions** with explicit time-of-day, "
        "  location, and camera differences between panels\n"
        "- **Repeat character anchors** every panel\n"
        "- **Limit to 1 dialogue per panel** in the output prompt to reduce text errors\n"
        "- **Strict negative constraints**: `no skipped panels, no merged panels, "
        "  no extra text, no romaji`"
    ),
    "gemini-3.1-flash-image-preview": (
        "The downstream image model is **Gemini 3.1 Flash + PIL overlay**. The image "
        "model itself must NOT render Japanese — text is composited downstream by PIL.\n\n"
        "Tactics:\n"
        "- Add explicit prohibitions: `absolutely no speech bubbles, no text, no captions, "
        "  no letters of any language (no hiragana, katakana, kanji, latin)`\n"
        "- Instruct the model to **leave generous empty space** above and to the side of "
        "  each character so PIL can composite bubbles in post-processing\n"
        "- Forbid empty/text-less bubble shapes: `no white rounded shapes, any white "
        "  area must be a real diegetic object (paper, cloth, sky, fog)`\n"
        "- Per-panel framing and character anchors are still useful for visual consistency"
    ),
}


def _panel_prompt_guidance(model: str) -> str:
    """Return panel-prompt tactics for ``model``; fall back by prefix then default."""
    return resolve_model_profile(
        _PANEL_PROMPT_GUIDANCE,
        model,
        default=(
            f"The downstream image model (`{model}`) is not in the prompt-engineering "
            "profile table. Use generic best practices: quote literal text in double quotes, "
            "label panels sequentially (Panel 1 / Panel 2 / ...), repeat character anchors "
            "verbatim per panel, and end with negative constraints (`no extra text, no logos`)."
        ),
    )


@dataclass
class ContentPack:
    """Plain-text + image material loaded from the user's content/ tree."""

    prompt: str
    images: list[Path] = field(default_factory=list)

    @classmethod
    def from_dir(
        cls,
        base: Path,
        content_cfg: ContentConfig | None = None,
    ) -> ContentPack:
        """Load ``prompt.md`` and the recursive image set under ``images/``."""
        cfg = content_cfg or ContentConfig()
        prompt_path = cfg.prompt_path(base)
        images_root = cfg.images_path(base)
        return cls(
            prompt=prompt_path.read_text(encoding="utf-8"),
            images=_collect_images(images_root, max_count=cfg.max_images),
        )


def _collect_images(root: Path, *, max_count: int) -> list[Path]:
    """Recursively glob the images tree for AI-acceptable image files.

    Why ``rglob`` + sorted: subdirectories are allowed for organisational
    reasons (the user may group ``images/alice/`` separately from
    ``images/bob/``), but the AI model never sees folder names — only the
    bytes. ``sorted`` ensures stable ordering across runs and lets users
    control sequence with numeric prefixes (``01-...``, ``02-...``) when
    they care.

    Truncation past ``max_count`` is loud (warn to stderr) so the user
    notices that some refs were dropped, rather than silently mismatching
    expectations.
    """
    if not root.exists():
        return []
    candidates = sorted(
        p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in _IMAGE_EXTENSIONS
    )
    if len(candidates) > max_count:
        _console.print(
            f"[yellow]warning:[/yellow] {len(candidates)} images found under "
            f"{root}, truncating to max_images={max_count}"
        )
        candidates = candidates[:max_count]
    return candidates


def _format_panel(panel: Panel) -> str:
    lines = [
        f"Panel {panel.index}",
        f"  description: {panel.description}",
        f"  characters: {', '.join(panel.characters) or '(none)'}",
    ]
    if panel.dialogue:
        lines.append(
            "  dialogue (render exactly as Japanese text inside speech bubbles, "
            "attributed to the speaker; preserve every character verbatim):"
        )
        lines.extend(f'    - {d.speaker}: 「{d.text}」' for d in panel.dialogue)
    else:
        lines.append("  dialogue: (none)")
    return "\n".join(lines)


def _format_panels(panels: list[Panel]) -> str:
    return "\n\n".join(_format_panel(p) for p in panels)


def resolve_template_path(
    *,
    template_filename: str,
    content_dir: Path,
    builtin_dir: Path,
) -> Path:
    """Pick ``content_dir/{template_filename}`` if it exists, else builtin.

    Why fallback: ships sane defaults so utilisateurs only need ``prompt.md``
    and ``images/``, while still letting power users override the prompt
    structure by dropping a same-named file under ``content/``.
    """
    override = content_dir / template_filename
    if override.exists():
        return override
    return builtin_dir / template_filename


def build_image_prompt(
    *,
    episode: ScenarioEpisode,
    pack: ContentPack,
    openai: OpenAIClient,
    template_path: Path,
    image_model: str,
    temperature: float = 0.4,
) -> tuple[str, RenderedPrompt]:
    """Render ``panel_prompt.md`` and ask the text LLM for the final image prompt.

    ``image_model`` selects the prompt-engineering profile (e.g. quote-text
    tactics for gpt-image-2 vs panel-count emphasis for gpt-image-1) so the
    output English prompt is shaped to that model's strengths and pitfalls.

    Returns the assistant text plus the rendered system+user pair — callers
    persist the latter into ``output/archive/{date}.yaml`` for traceability.
    """
    template = load_template(template_path)
    variables = {
        "episode_title": episode.title,
        "episode_summary": episode.summary_no_spoiler,
        "panels_block": _format_panels(episode.panels),
        "prompt_main": pack.prompt,
        "image_model": image_model,
        "image_model_prompt_guidance": _panel_prompt_guidance(image_model),
    }
    user = render(template.body, variables)
    system = render(template.system, variables)

    rendered = RenderedPrompt(system=system, user=user)
    image_prompt = openai.complete(
        system=system,
        user=user,
        temperature=temperature,
    ).strip()
    return image_prompt, rendered
