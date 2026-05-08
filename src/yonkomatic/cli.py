"""yonkomatic CLI — entry point for `yonkomatic` console script."""

from __future__ import annotations

import os
import sys
import tempfile
import uuid
from datetime import date as _date
from pathlib import Path

import typer
from PIL import Image, ImageDraw, ImageFont
from rich.console import Console

from yonkomatic import __version__
from yonkomatic.config import load_config
from yonkomatic.publisher.base import Episode
from yonkomatic.publisher.slack import SlackPublisher

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


def _generate_test_image(output_path: Path) -> None:
    """Render a small 4-panel-style PNG used to verify Slack delivery.

    Pillow's default bitmap font is used so the test does not depend on
    Noto Sans JP being downloaded yet — Step 1 only needs to prove the
    publisher pipeline works end-to-end.
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
        # Frame
        draw.rectangle((10, top + 10, width - 10, bottom - 10), outline=(40, 40, 40), width=3)
        draw.text((30, top + 30), label, fill=(20, 20, 20), font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG")


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

    token = os.environ.get(slack_cfg.token_env)
    if not token:
        err_console.print(
            f"[red]error:[/red] environment variable {slack_cfg.token_env} is not set."
        )
        raise typer.Exit(code=1)

    target_channel = channel or os.environ.get(slack_cfg.channel_env)
    if not target_channel:
        err_console.print(
            f"[red]error:[/red] no channel given and {slack_cfg.channel_env} is not set."
        )
        raise typer.Exit(code=1)

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

    if result.ok:
        console.print("[green]✓ posted successfully[/green]")
        if result.url:
            console.print(f"  permalink: {result.url}")
        if result.artifact_id:
            console.print(f"  file_id:   {result.artifact_id}")
        sys.exit(0)
    else:
        err_console.print(f"[red]✗ post failed:[/red] {result.error}")
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    app()
