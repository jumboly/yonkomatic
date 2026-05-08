"""yonkomatic CLI — entry point for `yonkomatic` console script."""

from __future__ import annotations

import mimetypes
import os
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date as _date
from pathlib import Path

import typer
from PIL import Image, ImageDraw, ImageFont
from rich.console import Console

from yonkomatic import __version__
from yonkomatic.ai.claude_client import ClaudeClient
from yonkomatic.ai.gemini_client import GeminiImageClient, GeminiImageResult
from yonkomatic.config import Config, load_config
from yonkomatic.panel.description import ContentPack, build_image_prompt
from yonkomatic.publisher.base import Episode
from yonkomatic.publisher.slack import SlackPublisher
from yonkomatic.scenario.schema import ScenarioEpisode

app = typer.Typer(
    name="yonkomatic",
    help="AI-generated yonkoma manga, automatically published.",
    no_args_is_help=True,
)
test_app = typer.Typer(name="test", help="Connectivity / smoke tests.", no_args_is_help=True)
app.add_typer(test_app, name="test")

console = Console()
err_console = Console(stderr=True)


@app.command()
def version() -> None:
    """Print the yonkomatic package version."""
    console.print(f"yonkomatic {__version__}")


@contextmanager
def _fail_on(action: str) -> Iterator[None]:
    """Convert any exception into a red one-liner + ``typer.Exit(1)``."""
    try:
        yield
    except Exception as e:
        err_console.print(f"[red]✗ {action}:[/red] {e}")
        raise typer.Exit(code=1) from e


def _require_env(name: str, *, hint: str = "") -> str:
    value = os.environ.get(name)
    if not value:
        msg = f"[red]error:[/red] environment variable {name} is not set."
        if hint:
            msg += f" {hint}"
        err_console.print(msg)
        raise typer.Exit(code=1)
    return value


def _save_image(output: Path, image_bytes: bytes, mime_type: str) -> Path:
    """Save image bytes, fixing the extension to match the actual MIME type.

    Why: Gemini API does not honor ``output_mime_type`` and may return JPEG
    when callers asked for ``.png`` — aligning extension with content avoids
    downstream tools (Slack, browsers) misreading the file.
    """
    actual_ext = mimetypes.guess_extension(mime_type) or ".bin"
    if output.suffix.lower() != actual_ext.lower():
        output = output.with_suffix(actual_ext)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(image_bytes)
    return output


def _generate_test_image(output_path: Path) -> None:
    """Render a small 4-panel-style PNG used to verify Slack delivery.

    Why default font: avoids dependence on Noto Sans JP being downloaded —
    the test only needs to prove the publisher pipeline works end-to-end.
    """
    width, height = 600, 800
    panel_height = height // 4
    image = Image.new("RGB", (width, height), color=(245, 245, 245))
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.load_default()
    except Exception:  # pragma: no cover — Pillow always ships a default
        font = None

    labels = [
        "Panel 1: Hello",
        "Panel 2: yonkomatic",
        "Panel 3: smoke test",
        "Panel 4: it works!",
    ]
    for i, label in enumerate(labels):
        top = i * panel_height
        bottom = top + panel_height
        draw.rectangle((10, top + 10, width - 10, bottom - 10), outline=(40, 40, 40), width=3)
        draw.text((30, top + 30), label, fill=(20, 20, 20), font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG")


def _run_gemini(
    cfg: Config,
    *,
    prompt: str,
    refs: list[Path],
    action: str = "generation failed",
) -> GeminiImageResult:
    """Call Gemini using config-driven defaults, with a uniform error frame."""
    api_key = _require_env(cfg.ai.image_api_key_env)
    client = GeminiImageClient(model=cfg.ai.image_model, api_key=api_key)
    console.print(
        f"calling [cyan]{cfg.ai.image_model}[/cyan] "
        f"(aspect={cfg.ai.aspect_ratio}, size={cfg.ai.image_size})…"
    )
    with _fail_on(action):
        return client.generate_image(
            prompt=prompt,
            reference_images=refs or None,
            aspect_ratio=cfg.ai.aspect_ratio,
            image_size=cfg.ai.image_size,
            max_attempts=cfg.ai.max_image_retries,
        )


@test_app.command("slack")
def test_slack(
    channel: str | None = typer.Option(
        None,
        "--channel",
        "-c",
        help="Slack channel ID. Defaults to SLACK_CHANNEL_ID env var (per config.yaml).",
    ),
    config_path: Path = typer.Option(
        Path("config.yaml"),
        "--config",
        help="Path to config.yaml.",
    ),
) -> None:
    """Send a generated test image to Slack to verify credentials and scopes."""
    cfg = load_config(config_path)
    slack_cfg = cfg.publishers.slack

    token = _require_env(slack_cfg.token_env)
    target_channel = channel or _require_env(
        slack_cfg.channel_env, hint="(or pass --channel)"
    )

    image_path = Path(tempfile.gettempdir()) / f"yonkomatic-test-{uuid.uuid4().hex}.png"
    _generate_test_image(image_path)
    console.print(f"generated test image: [cyan]{image_path}[/cyan]")

    episode = Episode(
        number=0,
        title="疎通テスト",
        summary_no_spoiler="yonkomatic の Slack 疎通確認",
        week="0000-W00",
        date=_date.today().isoformat(),
    )

    publisher = SlackPublisher(token=token, channel=target_channel)
    console.print(f"posting to Slack channel [cyan]{target_channel}[/cyan]…")
    result = publisher.publish(episode, image_path)

    if not result.ok:
        err_console.print(f"[red]✗ post failed:[/red] {result.error}")
        raise typer.Exit(code=1)

    console.print("[green]✓ posted successfully[/green]")
    if result.url:
        console.print(f"  permalink: {result.url}")
    if result.artifact_id:
        console.print(f"  file_id:   {result.artifact_id}")


@test_app.command("gemini")
def test_gemini(
    prompt: str = typer.Option(
        ...,
        "--prompt",
        "-p",
        help="Text prompt for the image model.",
    ),
    refs: list[Path] = typer.Option(
        [],
        "--refs",
        "-r",
        help="Optional reference images (PNG/JPEG). Can be repeated.",
    ),
    output: Path = typer.Option(
        Path("output/test-gemini.png"),
        "--output",
        "-o",
        help="Where to save the generated image (extension auto-corrected to actual MIME).",
    ),
    config_path: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Generate one image with Gemini and save it locally."""
    cfg = load_config(config_path)
    result = _run_gemini(cfg, prompt=prompt, refs=refs)
    saved = _save_image(output, result.image_bytes, result.mime_type)
    console.print(
        f"[green]✓ saved[/green] {saved} ({len(result.image_bytes)} bytes, {result.mime_type})"
    )


@test_app.command("panel")
def test_panel(
    scenario_path: Path = typer.Option(
        Path("examples/minimal/sample-scenario.json"),
        "--scenario",
        "-s",
        help="Path to a scenario JSON file (single episode).",
    ),
    content_dir: Path = typer.Option(
        Path("examples/minimal"),
        "--content",
        help="Directory holding characters/, world/, samples/, themes/.",
    ),
    refs: list[Path] = typer.Option(
        [],
        "--refs",
        "-r",
        help="Optional character / style reference images.",
    ),
    output: Path = typer.Option(
        Path("output/test-panel.png"),
        "--output",
        "-o",
        help="Where to save the generated 4-panel image.",
    ),
    config_path: Path = typer.Option(Path("config.yaml"), "--config"),
    save_prompt: bool = typer.Option(
        True,
        "--save-prompt/--no-save-prompt",
        help="Also write the Claude-generated prompt next to the image.",
    ),
) -> None:
    """Run the Stage1+Stage2 pipeline once: scenario → prompt (Claude) → image (Gemini)."""
    cfg = load_config(config_path)

    episode = ScenarioEpisode.model_validate_json(scenario_path.read_text(encoding="utf-8"))
    console.print(f"loaded scenario: [cyan]{episode.title}[/cyan] ({len(episode.panels)} panels)")

    pack = ContentPack.from_dir(content_dir, content_cfg=cfg.content)
    console.print(f"loaded content pack from [cyan]{content_dir}[/cyan]")

    claude_key = _require_env(cfg.ai.scenario_api_key_env)
    claude = ClaudeClient(model=cfg.ai.scenario_model, api_key=claude_key)
    console.print(f"asking [cyan]{cfg.ai.scenario_model}[/cyan] for image prompt…")
    with _fail_on("prompt generation failed"):
        image_prompt = build_image_prompt(episode=episode, pack=pack, claude=claude)

    if save_prompt:
        prompt_path = output.with_suffix(".prompt.txt")
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(image_prompt, encoding="utf-8")
        console.print(f"  wrote prompt: [dim]{prompt_path}[/dim]")

    result = _run_gemini(cfg, prompt=image_prompt, refs=refs)
    saved = _save_image(output, result.image_bytes, result.mime_type)
    console.print(
        f"[green]✓ saved[/green] {saved} ({len(result.image_bytes)} bytes, {result.mime_type})"
    )


if __name__ == "__main__":  # pragma: no cover
    app()
