"""Turn a structured scenario into a single image prompt for the image model.

The text LLM is given the scenario, character / world / style notes from
``prompt.md``, and the ``panel_prompt.md`` template, and is asked to
compose ONE long English prompt that instructs the image model to render
all four panels stacked vertically (3:4 aspect) as a single image.

Templates live in ``src/yonkomatic/templates/`` by default, but a
same-named file under ``content/`` overrides them so power users can
customise without forking yonkomatic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

from yonkomatic.ai.openai_client import OpenAIClient
from yonkomatic.config import ContentConfig
from yonkomatic.scenario.schema import Panel, ScenarioEpisode
from yonkomatic.template import RenderedPrompt, load_template, render

_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
_console = Console(stderr=True)


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
    temperature: float = 0.4,
) -> tuple[str, RenderedPrompt]:
    """Render ``panel_prompt.md`` and ask the text LLM for the final image prompt.

    Returns the assistant text plus the rendered system+user pair — callers
    persist the latter into ``output/archive/{date}.yaml`` for traceability.
    """
    template = load_template(template_path)
    variables = {
        "episode_title": episode.title,
        "episode_summary": episode.summary_no_spoiler,
        "panels_block": _format_panels(episode.panels),
        "prompt_main": pack.prompt,
    }
    user = render(template.body, variables)
    system = template.system

    rendered = RenderedPrompt(system=system, user=user)
    image_prompt = openai.complete(
        system=system,
        user=user,
        temperature=temperature,
    ).strip()
    return image_prompt, rendered
