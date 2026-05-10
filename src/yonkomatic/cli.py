"""yonkomatic CLI — entry point for `yonkomatic` console script."""

from __future__ import annotations

import importlib.resources as resources
import mimetypes
import os
import tempfile
import uuid
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import date as _date
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any
from zoneinfo import ZoneInfo

import typer
import yaml
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel
from rich.console import Console

from yonkomatic import __version__
from yonkomatic.ai.openai_client import (
    BatchImageJob,
    ImageResult,
    OpenAIClient,
    UsageTracker,
)
from yonkomatic.config import Config, load_config
from yonkomatic.news.fetcher import fetch_recent_headlines
from yonkomatic.panel.description import (
    ContentPack,
    build_image_prompt,
    resolve_template_path,
)
from yonkomatic.publisher.base import Episode, Publisher, PublishResult
from yonkomatic.publisher.slack import SlackPublisher
from yonkomatic.publisher.static_site import StaticSitePublisher
from yonkomatic.scenario.generator import generate_week
from yonkomatic.scenario.schema import ScenarioEpisode, ScenarioWeek
from yonkomatic.state.repo import HistoryEntry, StateStore
from yonkomatic.template import RenderedPrompt

app = typer.Typer(
    name="yonkomatic",
    help="AI-generated yonkoma manga, automatically published.",
    no_args_is_help=True,
)
test_app = typer.Typer(name="test", help="Connectivity / smoke tests.", no_args_is_help=True)
app.add_typer(test_app, name="test")

console = Console()
err_console = Console(stderr=True)

# Built-in default templates bundled with the package; users can override
# by dropping a same-named file under content/.
_TEMPLATES_PACKAGE = "yonkomatic.templates"
_SCENARIO_TEMPLATE_FILENAME = "scenario_prompt.md"
_PANEL_TEMPLATE_FILENAME = "panel_prompt.md"

def _load_yaml_model[M: BaseModel](path: Path, model: type[M]) -> M:
    """Read a YAML file and validate it against the given Pydantic model."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return model.model_validate(raw)


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


def _builtin_templates_dir() -> Path:
    """Path to the bundled templates inside the installed package."""
    # importlib.resources.files returns a Traversable; in the typical
    # installed/editable layout this is a real filesystem path.
    return Path(str(resources.files(_TEMPLATES_PACKAGE)))


ImageModelOption = Annotated[
    str | None,
    typer.Option(
        "--image-model",
        help="Override ai.image_model for this run (e.g. gpt-image-2).",
    ),
]
ImageSizeOption = Annotated[
    str | None,
    typer.Option(
        "--image-size",
        help="Override ai.image_size for this run (e.g. 1152x1536).",
    ),
]
TextModelOption = Annotated[
    str | None,
    typer.Option(
        "--text-model",
        help="Override ai.text_model for this run (e.g. gpt-5.5).",
    ),
]


def _apply_cli_overrides(
    cfg: Config,
    *,
    text_model: str | None = None,
    image_model: str | None = None,
    image_size: str | None = None,
) -> Config:
    """Merge CLI flag overrides into cfg via sub-model copy."""
    updates: dict[str, Any] = {}
    if text_model is not None or image_model is not None or image_size is not None:
        ai_updates: dict[str, Any] = {}
        if text_model is not None:
            ai_updates["text_model"] = text_model
        if image_model is not None:
            ai_updates["image_model"] = image_model
        if image_size is not None:
            ai_updates["image_size"] = image_size
        updates["ai"] = cfg.ai.model_copy(update=ai_updates)
    return cfg.model_copy(update=updates) if updates else cfg


def _save_image(output: Path, image_bytes: bytes, mime_type: str) -> Path:
    """Save image bytes, fixing the extension to match the actual MIME type.

    Why: image APIs do not always honor a requested output format and may
    return JPEG when callers asked for ``.png`` — aligning extension with
    content avoids downstream tools (Slack, browsers) misreading the file.
    """
    actual_ext = mimetypes.guess_extension(mime_type) or ".bin"
    if output.suffix.lower() != actual_ext.lower():
        output = output.with_suffix(actual_ext)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(image_bytes)
    return output


def _generate_test_image(output_path: Path) -> None:
    """Render a small 4-panel-style PNG used to verify Slack delivery.

    Why default font: avoids dependence on a downloaded font asset — the
    test only needs to prove the publisher pipeline works end-to-end.
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


def _build_openai_client(
    cfg: Config, *, usage_tracker: UsageTracker | None = None
) -> OpenAIClient:
    api_key = _require_env(cfg.ai.openai_api_key_env)
    return OpenAIClient(
        api_key=api_key,
        text_model=cfg.ai.text_model,
        image_model=cfg.ai.image_model,
        usage_tracker=usage_tracker,
    )


def _print_usage_summary(tracker: UsageTracker) -> None:
    """Print per-model token totals + run total at the end of a CLI command."""
    if not tracker.calls:
        return
    summary = tracker.summary()
    console.print("[bold]usage summary:[/bold]")
    for model, agg in summary["per_model"].items():
        tokens = ", ".join(f"{k}={v}" for k, v in agg["tokens"].items() if v)
        console.print(
            f"  [cyan]{model}[/cyan]: {agg['calls']} call(s), "
            f"${agg['usd']:.4f} ({tokens or 'no usage data'})"
        )
    suffix = " [yellow](some models missing from price table)[/yellow]" \
        if tracker.has_unknown_model else ""
    console.print(
        f"  [bold]total:[/bold] ${summary['total_usd']:.4f} "
        f"across {summary['call_count']} call(s){suffix}"
    )


def _run_openai_image(
    cfg: Config,
    openai: OpenAIClient,
    *,
    prompt: str,
    refs: list[Path],
    action: str = "image generation failed",
) -> ImageResult:
    """Call OpenAI image generation using config-driven defaults."""
    console.print(
        f"calling [cyan]{cfg.ai.image_model}[/cyan] (size={cfg.ai.image_size})…"
    )
    with _fail_on(action):
        return openai.generate_image(
            prompt=prompt,
            reference_images=refs or None,
            size=cfg.ai.image_size,
            max_attempts=cfg.ai.max_image_retries,
        )


def _merge_refs(pack: ContentPack, cli_refs: list[Path]) -> list[Path]:
    """Concatenate auto-collected pack images with CLI ``--refs``.

    Why auto then CLI: image models attend to later items in the input
    contents list more strongly, so CLI-supplied "today only" refs land
    closer to the prompt and influence the result more than the persistent
    pack images.
    """
    auto = list(pack.images)
    merged = auto + list(cli_refs)
    console.print(
        f"reference images: auto {len(auto)} + CLI {len(cli_refs)} = {len(merged)} total"
    )
    return merged


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


@test_app.command("image")
def test_image(
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
        help="Optional reference images (PNG/JPEG/WebP). Can be repeated.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Where to save the generated image. "
        "Defaults to tmp/verify/test-image/{YYYYMMDD-HHMMSS}/image.png.",
    ),
    config_path: Path = typer.Option(Path("config.yaml"), "--config"),
    image_model: ImageModelOption = None,
) -> None:
    """Generate one image with OpenAI and save it locally."""
    cfg = _apply_cli_overrides(load_config(config_path), image_model=image_model)
    output = output or _default_verify_output("test-image")
    tracker = UsageTracker()
    openai = _build_openai_client(cfg, usage_tracker=tracker)
    result = _run_openai_image(cfg, openai, prompt=prompt, refs=refs)
    saved = _save_image(output, result.image_bytes, result.mime_type)
    console.print(
        f"[green]✓ saved[/green] {saved} ({len(result.image_bytes)} bytes, {result.mime_type})"
    )
    _print_usage_summary(tracker)


@test_app.command("news")
def test_news(
    config_path: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Fetch RSS feeds and print recent headlines (smoke test for news fetcher)."""
    cfg = load_config(config_path)
    if not cfg.news.enabled or not cfg.news.feeds:
        console.print(
            "[yellow]news disabled or feeds empty in config; nothing to fetch.[/yellow]"
        )
        return

    headlines = fetch_recent_headlines(cfg.news)
    console.print(
        f"[green]✓[/green] {len(headlines)} headlines from {len(cfg.news.feeds)} feed(s) "
        f"(lookback {cfg.news.lookback_days}d, max {cfg.news.max_items_per_feed}/feed)"
    )
    for h in headlines[:10]:
        console.print(f"  - {h}")
    if len(headlines) > 10:
        console.print(f"  [dim]... ({len(headlines) - 10} more)[/dim]")


@test_app.command("panel")
def test_panel(
    scenario_path: Path = typer.Option(
        Path("examples/minimal/sample-scenario.yaml"),
        "--scenario",
        "-s",
        help="Path to a scenario YAML file (single episode).",
    ),
    content_dir: Path = typer.Option(
        Path("examples/minimal"),
        "--content",
        help="Directory holding prompt.md + images/.",
    ),
    refs: list[Path] = typer.Option(
        [],
        "--refs",
        "-r",
        help="Extra reference images merged with auto-collected images/.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Where to save the generated 4-panel image. "
        "Defaults to tmp/verify/test-panel/{YYYYMMDD-HHMMSS}/image.png.",
    ),
    config_path: Path = typer.Option(Path("config.yaml"), "--config"),
    text_model: TextModelOption = None,
    image_model: ImageModelOption = None,
    image_size: ImageSizeOption = None,
    save_rendered: bool = typer.Option(
        True,
        "--save-rendered/--no-save-rendered",
        help="Also write the rendered system+user prompts next to the image.",
    ),
) -> None:
    """Run the full image pipeline once: scenario → prompt (text LLM) → image."""
    cfg = _apply_cli_overrides(
        load_config(config_path),
        text_model=text_model,
        image_model=image_model,
        image_size=image_size,
    )
    output = output or _default_verify_output("test-panel")

    episode = _load_yaml_model(scenario_path, ScenarioEpisode)
    console.print(f"loaded scenario: [cyan]{episode.title}[/cyan] ({len(episode.panels)} panels)")

    pack = ContentPack.from_dir(content_dir, content_cfg=cfg.content)
    console.print(f"loaded content pack from [cyan]{content_dir}[/cyan]")

    tracker = UsageTracker()
    openai = _build_openai_client(cfg, usage_tracker=tracker)
    panel_template = resolve_template_path(
        template_filename=_PANEL_TEMPLATE_FILENAME,
        content_dir=content_dir,
        builtin_dir=_builtin_templates_dir(),
    )
    console.print(f"using panel template: [dim]{panel_template}[/dim]")

    console.print(f"asking [cyan]{cfg.ai.text_model}[/cyan] for image prompt…")
    with _fail_on("prompt generation failed"):
        image_prompt, rendered = build_image_prompt(
            episode=episode,
            pack=pack,
            openai=openai,
            template_path=panel_template,
            image_model=cfg.ai.image_model,
        )

    if save_rendered:
        _write_rendered_prompts(output, panel_rendered=rendered, image_prompt=image_prompt)

    merged_refs = _merge_refs(pack, refs)
    result = _run_openai_image(cfg, openai, prompt=image_prompt, refs=merged_refs)
    saved = _save_image(output, result.image_bytes, result.mime_type)
    console.print(
        f"[green]✓ saved[/green] {saved} ({len(result.image_bytes)} bytes, {result.mime_type})"
    )
    _print_usage_summary(tracker)


def _default_verify_output(command: str) -> Path:
    """Default output path for ad-hoc verify commands.

    Format: ``tmp/verify/<command>/<YYYYMMDD-HHMMSS>/image.png`` — chronologically
    sortable so ``ls`` lists runs ascending and the latest is the bottom entry.
    """
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path(f"tmp/verify/{command}/{ts}/image.png")


def _write_rendered_prompts(
    output: Path,
    *,
    panel_rendered: RenderedPrompt,
    image_prompt: str,
) -> None:
    """Drop the rendered panel prompt + the resulting image prompt in the output dir."""
    out_dir = output.parent
    panel_path = out_dir / "panel-prompt.txt"
    image_path = out_dir / "image-prompt.txt"
    out_dir.mkdir(parents=True, exist_ok=True)
    panel_path.write_text(panel_rendered.as_combined_text(), encoding="utf-8")
    image_path.write_text(image_prompt, encoding="utf-8")
    console.print(f"  wrote panel prompt: [dim]{panel_path}[/dim]")
    console.print(f"  wrote image prompt: [dim]{image_path}[/dim]")


def _today_in_configured_tz(cfg: Config) -> str:
    return datetime.now(ZoneInfo(cfg.schedule.timezone)).date().isoformat()


def _iso_week_of(date_str: str) -> str:
    return _date.fromisoformat(date_str).strftime("%G-W%V")


def _current_iso_week(cfg: Config) -> str:
    return _iso_week_of(_today_in_configured_tz(cfg))


def _notify_failure(cfg: Config, message: str) -> None:
    """Post a non-blocking failure alert via Slack if it is enabled and configured."""
    if not cfg.publishers.slack.enabled:
        return
    token = os.environ.get(cfg.publishers.slack.token_env)
    channel = os.environ.get(cfg.publishers.slack.channel_env)
    if not token or not channel:
        err_console.print(
            f"[yellow]notify skipped:[/yellow] Slack token/channel not set ({message})"
        )
        return
    notifier = SlackPublisher(token=token, channel=channel)
    if notifier.notify_failure(message):
        err_console.print(f"[dim]·[/dim] notified Slack: {message}")
    else:
        err_console.print(f"[yellow]notify failed:[/yellow] {message}")


def _build_publishers(cfg: Config) -> list[Publisher]:
    """Instantiate every enabled publisher; secrets are read from os.environ here."""
    publishers: list[Publisher] = []

    if cfg.publishers.slack.enabled:
        token = _require_env(cfg.publishers.slack.token_env)
        channel = _require_env(cfg.publishers.slack.channel_env)
        publishers.append(SlackPublisher(token=token, channel=channel))

    if cfg.publishers.static_site.enabled:
        publishers.append(
            StaticSitePublisher(
                output_dir=cfg.publishers.static_site.output_dir,
                base_url=cfg.publishers.static_site.base_url,
            )
        )

    if cfg.publishers.discord.enabled:
        # Why warn rather than fail: a user who left discord.enabled: true
        # should know it's a no-op without aborting the rest of the run.
        err_console.print(
            "[yellow]warning:[/yellow] discord publisher is enabled in config but "
            "not implemented yet — skipping."
        )

    return publishers


def _run_publishers(
    publishers: list[Publisher],
    episode: Episode,
    image_path: Path,
) -> list[PublishResult]:
    if not publishers:
        return []
    with ThreadPoolExecutor(max_workers=len(publishers)) as ex:
        futures = {ex.submit(pub.publish, episode, image_path): pub.name for pub in publishers}
        results: list[PublishResult] = []
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                results.append(fut.result())
            except Exception as e:
                # Why catch: Publisher protocol forbids raising, but we
                # double-guard so one buggy publisher cannot kill the run.
                results.append(PublishResult(ok=False, publisher=name, error=str(e)))
    return results


def _print_publish_results(results: list[PublishResult]) -> None:
    for r in results:
        if r.ok:
            extra = f" → {r.url}" if r.url else ""
            console.print(f"[green]✓[/green] [cyan]{r.publisher}[/cyan]: posted{extra}")
        else:
            err_console.print(f"[red]✗[/red] [cyan]{r.publisher}[/cyan]: {r.error}")


def _result_to_meta(r: PublishResult) -> dict[str, Any]:
    return {"ok": r.ok, "artifact_id": r.artifact_id, "url": r.url, "error": r.error}


def _write_archive(
    *,
    archive_dir: Path,
    date: str,
    image_bytes: bytes,
    mime_type: str,
    episode: ScenarioEpisode,
    rendered_panel: RenderedPrompt,
    rendered_image_prompt: str,
    cfg: Config,
    usage: UsageTracker | None = None,
) -> tuple[Path, Path]:
    archive_dir.mkdir(parents=True, exist_ok=True)
    image_path = _save_image(archive_dir / f"{date}.png", image_bytes, mime_type)
    meta_path = archive_dir / f"{date}.yaml"
    meta = {
        "date": date,
        "episode_number": episode.episode_number,
        "week": episode.week,
        "title": episode.title,
        "summary_no_spoiler": episode.summary_no_spoiler,
        "ai": {
            "text_model": cfg.ai.text_model,
            "image_model": cfg.ai.image_model,
            "image_size": cfg.ai.image_size,
        },
        "rendered_panel_prompt": rendered_panel.as_combined_text(),
        "rendered_image_prompt": rendered_image_prompt,
        "image": {"mime_type": mime_type, "size_bytes": len(image_bytes)},
    }
    if usage is not None and usage.calls:
        meta["usage"] = usage.summary()
    meta_path.write_text(
        yaml.safe_dump(meta, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return image_path, meta_path


@app.command()
def publish(
    scenario_file: Path = typer.Option(
        ...,
        "--scenario-file",
        "-s",
        help="Path to a scenario YAML file (single ScenarioEpisode).",
    ),
    date_str: str | None = typer.Option(
        None,
        "--date",
        help="ISO date YYYY-MM-DD. Defaults to today in config schedule.timezone.",
    ),
    content_dir: Path = typer.Option(
        Path("examples/minimal"),
        "--content",
        help="Directory holding prompt.md + images/.",
    ),
    refs: list[Path] = typer.Option(
        [],
        "--refs",
        "-r",
        help="Extra reference images merged with auto-collected images/.",
    ),
    config_path: Path = typer.Option(Path("config.yaml"), "--config"),
    state_path: Path = typer.Option(
        Path("state/state.yaml"),
        "--state",
        help="Path to state.yaml. Updated on success unless --dry-run.",
    ),
    archive_dir: Path = typer.Option(
        Path("output/archive"),
        "--archive-dir",
        help="Where {date}.png and {date}.yaml are written for reproducibility.",
    ),
    text_model: TextModelOption = None,
    image_model: ImageModelOption = None,
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Generate image and write archive, but skip publishers and state update.",
    ),
    no_preflight: bool = typer.Option(
        False,
        "--no-preflight",
        help="Force fresh image generation even if a preflight image exists.",
    ),
) -> None:
    """Run the full pipeline: scenario → image → multi-publish + archive."""
    cfg = _apply_cli_overrides(
        load_config(config_path), text_model=text_model, image_model=image_model
    )

    with _fail_on("load scenario"):
        episode_data = _load_yaml_model(scenario_file, ScenarioEpisode)

    pub_date = date_str or _today_in_configured_tz(cfg)
    _publish_episode_pipeline(
        cfg=cfg,
        episode_data=episode_data,
        pub_date=pub_date,
        content_dir=content_dir,
        refs=refs,
        state_path=state_path,
        archive_dir=archive_dir,
        dry_run=dry_run,
        use_preflight=not no_preflight,
    )


def _publish_episode_pipeline(
    *,
    cfg: Config,
    episode_data: ScenarioEpisode,
    pub_date: str,
    content_dir: Path,
    refs: list[Path],
    state_path: Path,
    archive_dir: Path,
    dry_run: bool,
    use_preflight: bool = True,
) -> None:
    console.print(
        f"publishing for [cyan]{pub_date}[/cyan]: 「{episode_data.title}」 "
        f"(episode {episode_data.episode_number})"
    )

    tracker = UsageTracker()
    preflight_path: Path | None = None
    if use_preflight:
        preflight_path = _find_preflight_image(
            episode_data.week, episode_data.episode_number
        )

    if preflight_path is not None:
        console.print(f"  using preflight image: [dim]{preflight_path}[/dim]")
        image_result = ImageResult(
            image_bytes=preflight_path.read_bytes(),
            mime_type="image/png",
        )

        # Carry the prompts that produced this image into the archive so
        # daily archives stay self-describing even when the API was not
        # called today.
        job_meta = (
            _load_batch_job_meta(
                episode_data.week, episode_data.episode_number
            )
            or {}
        )
        image_prompt = job_meta.get(
            "rendered_image_prompt", "(preflight: prompt unavailable)"
        )
        panel_rendered = RenderedPrompt(
            system="",
            user=job_meta.get("rendered_panel_prompt", ""),
        )
    else:
        with _fail_on("load content pack"):
            pack = ContentPack.from_dir(content_dir, content_cfg=cfg.content)

        openai = _build_openai_client(cfg, usage_tracker=tracker)
        panel_template = resolve_template_path(
            template_filename=_PANEL_TEMPLATE_FILENAME,
            content_dir=content_dir,
            builtin_dir=_builtin_templates_dir(),
        )

        console.print(f"asking [cyan]{cfg.ai.text_model}[/cyan] for image prompt…")
        with _fail_on("prompt generation failed"):
            image_prompt, panel_rendered = build_image_prompt(
                episode=episode_data,
                pack=pack,
                openai=openai,
                template_path=panel_template,
                image_model=cfg.ai.image_model,
            )

        merged_refs = _merge_refs(pack, refs)
        image_result = _run_openai_image(
            cfg, openai, prompt=image_prompt, refs=merged_refs
        )

    archive_image, archive_meta = _write_archive(
        archive_dir=archive_dir,
        date=pub_date,
        image_bytes=image_result.image_bytes,
        mime_type=image_result.mime_type,
        episode=episode_data,
        rendered_panel=panel_rendered,
        rendered_image_prompt=image_prompt,
        cfg=cfg,
        usage=tracker,
    )
    console.print(f"  archive image: [dim]{archive_image}[/dim]")
    console.print(f"  archive meta:  [dim]{archive_meta}[/dim]")

    episode_obj = Episode(
        number=episode_data.episode_number,
        title=episode_data.title,
        summary_no_spoiler=episode_data.summary_no_spoiler,
        week=episode_data.week,
        date=pub_date,
    )

    publishers = _build_publishers(cfg)
    if not publishers:
        err_console.print(
            "[yellow]warning:[/yellow] no publishers are enabled in config.yaml; "
            "state not updated."
        )
        if dry_run:
            console.print("[green]✓ dry-run complete (nothing to do)[/green]")
        _print_usage_summary(tracker)
        return

    if dry_run:
        for pub in publishers:
            console.print(f"[dim]·[/dim] [cyan]{pub.name}[/cyan]: dry-run (no post)")
        console.print("[green]✓ dry-run complete[/green]")
        _print_usage_summary(tracker)
        return

    results = _run_publishers(publishers, episode_obj, archive_image)
    _print_publish_results(results)

    # Why all-failure short-circuits state: leaving state untouched lets
    # CI retry tomorrow without burning the episode_number, and signals
    # the failure with a non-zero exit. Partial success still updates
    # state so successful platforms are not reposted on retry.
    if not any(r.ok for r in results):
        err_console.print("[red]✗ all publishers failed; state not updated.[/red]")
        raise typer.Exit(code=1)

    state = StateStore(state_path)
    entry = HistoryEntry(
        episode_number=episode_data.episode_number,
        week=episode_data.week,
        date=pub_date,
        title=episode_data.title,
        archive_path=str(archive_image),
        publishers={r.publisher: _result_to_meta(r) for r in results},
    )
    state.append(entry)
    console.print(f"  state updated: [dim]{state_path}[/dim]")
    _print_usage_summary(tracker)


@app.command("publish-today")
def publish_today(
    date_str: str | None = typer.Option(
        None,
        "--date",
        help="ISO date YYYY-MM-DD. Defaults to today in config schedule.timezone.",
    ),
    content_dir: Path = typer.Option(
        Path("examples/minimal"),
        "--content",
        help="Directory holding prompt.md + images/.",
    ),
    refs: list[Path] = typer.Option(
        [],
        "--refs",
        "-r",
        help="Extra reference images merged with auto-collected images/.",
    ),
    config_path: Path = typer.Option(Path("config.yaml"), "--config"),
    state_path: Path = typer.Option(Path("state/state.yaml"), "--state"),
    scenarios_dir: Path = typer.Option(
        Path("scenarios"),
        "--scenarios-dir",
        help="Directory containing {YYYY-Www}.yaml scenario files.",
    ),
    archive_dir: Path = typer.Option(Path("output/archive"), "--archive-dir"),
    text_model: TextModelOption = None,
    image_model: ImageModelOption = None,
    dry_run: bool = typer.Option(False, "--dry-run"),
    no_preflight: bool = typer.Option(
        False,
        "--no-preflight",
        help="Force fresh image generation even if a preflight image exists.",
    ),
) -> None:
    """Pick the next episode for today's ISO week from scenarios/, then publish."""
    cfg = _apply_cli_overrides(
        load_config(config_path), text_model=text_model, image_model=image_model
    )
    pub_date = date_str or _today_in_configured_tz(cfg)
    target_week = _iso_week_of(pub_date)
    week_path = scenarios_dir / f"{target_week}.yaml"

    if not week_path.exists():
        msg = (
            f"scenarios file {week_path} not found for {target_week} "
            f"(run generate-scenarios --week {target_week} first)"
        )
        err_console.print(f"[red]error:[/red] {msg}")
        _notify_failure(cfg, msg)
        raise typer.Exit(code=1)

    with _fail_on("load week scenarios"):
        raw = yaml.safe_load(week_path.read_text(encoding="utf-8"))
        week_data = ScenarioWeek.model_validate(raw)

    state = StateStore(state_path).load()
    if (
        state.current_week_index == target_week
        and state.last_published_episode is not None
    ):
        target_n = state.last_published_episode + 1
    else:
        target_n = 1

    target = next(
        (ep for ep in week_data.episodes if ep.episode_number == target_n),
        None,
    )
    if target is None:
        msg = (
            f"episode #{target_n} is not in {week_path} "
            f"(only {len(week_data.episodes)} episode(s) defined for {target_week})"
        )
        err_console.print(f"[red]error:[/red] {msg}")
        _notify_failure(cfg, msg)
        raise typer.Exit(code=1)

    try:
        _publish_episode_pipeline(
            cfg=cfg,
            episode_data=target,
            pub_date=pub_date,
            content_dir=content_dir,
            refs=refs,
            state_path=state_path,
            archive_dir=archive_dir,
            dry_run=dry_run,
            use_preflight=not no_preflight,
        )
    except typer.Exit:
        # The pipeline already printed a specific error; the notification
        # carries the cron-level context (which episode/date/week) so an
        # operator can act without grepping the GHA log.
        _notify_failure(
            cfg,
            f"publish-today failed for {pub_date} "
            f"(episode #{target_n} 「{target.title}」 of {target_week})",
        )
        raise


def _default_batch_manifest_path(week: str) -> Path:
    return Path("state/batches") / f"{week}.yaml"


def _default_preflight_dir(week: str) -> Path:
    return Path("output/preflight") / week


def _find_preflight_image(week: str | None, episode_number: int) -> Path | None:
    """Return the preflight image path if it exists, else None.

    Preflight images are pre-rendered by ``batch-fetch-images`` from the
    weekly batch. ``publish-today`` consults this so the daily cron can
    skip a sync image generation when the batch already produced one.
    """
    if week is None:
        return None
    candidate = _default_preflight_dir(week) / f"ep{episode_number}.png"
    return candidate if candidate.exists() else None


def _load_batch_job_meta(
    week: str | None, episode_number: int
) -> dict[str, Any] | None:
    """Pull the per-episode metadata block from a saved batch manifest."""
    if week is None:
        return None
    manifest_path = _default_batch_manifest_path(week)
    if not manifest_path.exists():
        return None
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    return next(
        (
            j
            for j in manifest.get("jobs", [])
            if j.get("episode_number") == episode_number
        ),
        None,
    )


@app.command("batch-submit-images")
def batch_submit_images(
    week: str = typer.Option(
        ..., "--week", help="ISO week, e.g. 2026-W19."
    ),
    scenarios_path: Path | None = typer.Option(
        None,
        "--scenarios",
        help="Scenarios YAML. Defaults to scenarios/{week}.yaml.",
    ),
    content_dir: Path = typer.Option(
        Path("examples/minimal"), "--content"
    ),
    manifest_path: Path | None = typer.Option(
        None,
        "--out",
        help="Where to write the batch manifest. Defaults to state/batches/{week}.yaml.",
    ),
    config_path: Path = typer.Option(Path("config.yaml"), "--config"),
    text_model: TextModelOption = None,
    image_model: ImageModelOption = None,
) -> None:
    """Render 7 image prompts (text LLM, sync) and submit a 50%-off image batch.

    The text completions cost normal rates and run synchronously here so the
    submitted batch contains finalised image prompts. Image generation is
    deferred to the batch worker (up to 24h) and billed at half list price.
    """
    cfg = _apply_cli_overrides(
        load_config(config_path), text_model=text_model, image_model=image_model
    )
    manifest_out = manifest_path or _default_batch_manifest_path(week)

    if manifest_out.exists():
        err_console.print(
            f"[red]error:[/red] {manifest_out} already exists "
            "(re-running would orphan the prior batch). Delete it manually if intended."
        )
        raise typer.Exit(code=1)

    src = scenarios_path or Path("scenarios") / f"{week}.yaml"
    with _fail_on("load week scenarios"):
        week_data = ScenarioWeek.model_validate(
            yaml.safe_load(src.read_text(encoding="utf-8"))
        )
    if week_data.week != week:
        err_console.print(
            f"[yellow]warning:[/yellow] scenarios file says week={week_data.week} "
            f"but --week={week}; using --week."
        )

    with _fail_on("load content pack"):
        pack = ContentPack.from_dir(content_dir, content_cfg=cfg.content)

    tracker = UsageTracker()
    openai = _build_openai_client(cfg, usage_tracker=tracker)
    panel_template = resolve_template_path(
        template_filename=_PANEL_TEMPLATE_FILENAME,
        content_dir=content_dir,
        builtin_dir=_builtin_templates_dir(),
    )

    def _render_one(ep: ScenarioEpisode) -> tuple[BatchImageJob, dict[str, Any]]:
        cid = f"{week}-ep{ep.episode_number}"
        image_prompt, rendered = build_image_prompt(
            episode=ep,
            pack=pack,
            openai=openai,
            template_path=panel_template,
            image_model=cfg.ai.image_model,
        )
        return (
            BatchImageJob(custom_id=cid, prompt=image_prompt),
            {
                "custom_id": cid,
                "episode_number": ep.episode_number,
                "title": ep.title,
                "rendered_panel_prompt": rendered.as_combined_text(),
                "rendered_image_prompt": image_prompt,
            },
        )

    console.print(
        f"rendering [cyan]{len(week_data.episodes)}[/cyan] prompts in parallel "
        f"(via {cfg.ai.text_model})…"
    )
    # Why parallel: text completion latency dominates submit time (~2s × N).
    # ThreadPoolExecutor matches the pattern in _run_publishers; UsageTracker.add
    # is lock-guarded so concurrent records are safe. Order is preserved by
    # submitting indexed and writing back into a pre-sized list.
    rendered_jobs: list[tuple[BatchImageJob, dict[str, Any]] | None] = (
        [None] * len(week_data.episodes)
    )
    with _fail_on("prompt generation failed"):
        with ThreadPoolExecutor(max_workers=len(week_data.episodes)) as ex:
            futures = {
                ex.submit(_render_one, ep): i
                for i, ep in enumerate(week_data.episodes)
            }
            for fut in as_completed(futures):
                rendered_jobs[futures[fut]] = fut.result()

    jobs: list[BatchImageJob] = [r[0] for r in rendered_jobs if r is not None]
    job_meta: list[dict[str, Any]] = [r[1] for r in rendered_jobs if r is not None]

    console.print(
        f"submitting batch ({len(jobs)} jobs, {cfg.ai.image_model}, "
        f"size={cfg.ai.image_size})…"
    )
    with _fail_on("batch submit failed"):
        batch_id = openai.submit_image_batch(jobs=jobs, size=cfg.ai.image_size)

    manifest = {
        "week": week,
        "batch_id": batch_id,
        "submitted_at": datetime.now(ZoneInfo("UTC")).isoformat(),
        "text_model": cfg.ai.text_model,
        "image_model": cfg.ai.image_model,
        "image_size": cfg.ai.image_size,
        "status": "submitted",
        "jobs": job_meta,
        "text_usage": tracker.summary(),
        "fetched_at": None,
        "results": [],
    }
    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    manifest_out.write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    console.print(
        f"[green]✓ submitted[/green] batch [cyan]{batch_id}[/cyan]; "
        f"manifest at [dim]{manifest_out}[/dim]"
    )
    console.print(
        "  poll with: [bold]yonkomatic batch-fetch-images "
        f"--week {week}[/bold]"
    )
    _print_usage_summary(tracker)


@app.command("batch-fetch-images")
def batch_fetch_images(
    week: str = typer.Option(..., "--week"),
    manifest_path: Path | None = typer.Option(
        None,
        "--manifest",
        help="Path to the batch manifest. Defaults to state/batches/{week}.yaml.",
    ),
    out_dir: Path | None = typer.Option(
        None,
        "--out-dir",
        help="Where to save fetched images. Defaults to output/preflight/{week}/.",
    ),
    config_path: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Poll a submitted batch and download images when complete.

    Idempotent: re-running on a completed batch overwrites the same paths.
    Until the batch reaches ``completed``, only progress is printed.
    """
    cfg = load_config(config_path)
    manifest_in = manifest_path or _default_batch_manifest_path(week)
    save_dir = out_dir or _default_preflight_dir(week)

    if not manifest_in.exists():
        err_console.print(
            f"[red]error:[/red] manifest {manifest_in} not found "
            f"(run batch-submit-images --week {week} first)"
        )
        raise typer.Exit(code=1)

    manifest = yaml.safe_load(manifest_in.read_text(encoding="utf-8")) or {}
    batch_id = manifest.get("batch_id")
    if not batch_id:
        err_console.print(f"[red]error:[/red] manifest has no batch_id: {manifest_in}")
        raise typer.Exit(code=1)

    tracker = UsageTracker()
    openai = _build_openai_client(cfg, usage_tracker=tracker)

    console.print(f"polling batch [cyan]{batch_id}[/cyan]…")
    with _fail_on("batch fetch failed"):
        status = openai.fetch_image_batch(batch_id)

    console.print(
        f"  status: [bold]{status.status}[/bold] "
        f"({status.completed}/{status.total} done, {status.failed} failed)"
    )

    if status.status != "completed":
        console.print(
            "[yellow]not yet complete[/yellow] — try again later "
            "(OpenAI batches finish within 24h of submission)"
        )
        return

    save_dir.mkdir(parents=True, exist_ok=True)
    cid_to_meta = {j["custom_id"]: j for j in manifest.get("jobs", [])}
    result_records: list[dict[str, Any]] = []

    for r in status.results:
        meta = cid_to_meta.get(r.custom_id, {})
        ep_num = meta.get("episode_number")
        record = {
            "custom_id": r.custom_id,
            "episode_number": ep_num,
            "title": meta.get("title"),
            "image_path": None,
            "error": r.error,
            "usage": r.usage,
            "cost_usd": None,
        }
        if r.error or r.image_bytes is None:
            err_console.print(f"[red]✗[/red] {r.custom_id}: {r.error or 'no image'}")
            result_records.append(record)
            continue

        filename = f"ep{ep_num}.png" if ep_num is not None else f"{r.custom_id}.png"
        out_path = _save_image(save_dir / filename, r.image_bytes, r.mime_type)
        record["image_path"] = str(out_path)
        call = openai.record_batch_image_result(r)
        if call is not None:
            record["cost_usd"] = call.cost_usd
        result_records.append(record)
        console.print(f"[green]✓[/green] {r.custom_id} → [dim]{out_path}[/dim]")

    manifest["status"] = "completed"
    manifest["fetched_at"] = datetime.now(ZoneInfo("UTC")).isoformat()
    manifest["results"] = result_records
    manifest["image_usage"] = tracker.summary()
    manifest_in.write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    console.print(f"  manifest updated: [dim]{manifest_in}[/dim]")
    _print_usage_summary(tracker)


@app.command("generate-scenarios")
def generate_scenarios(
    week: str | None = typer.Option(
        None,
        "--week",
        help="ISO week (e.g. 2026-W19). Defaults to today's week in config schedule.timezone.",
    ),
    out: Path | None = typer.Option(
        None,
        "--out",
        help="Output YAML path. Defaults to scenarios/{week}.yaml.",
    ),
    content_dir: Path = typer.Option(
        Path("examples/minimal"),
        "--content",
        help="Directory holding prompt.md + images/.",
    ),
    no_news: bool = typer.Option(
        False,
        "--no-news",
        help="Skip RSS fetch even if news.enabled is true.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite an existing scenarios/{week}.yaml.",
    ),
    config_path: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Ask the text LLM for 7 episodes for the given ISO week."""
    cfg = load_config(config_path)
    target_week = week or _current_iso_week(cfg)
    output_path = out or Path("scenarios") / f"{target_week}.yaml"
    rendered_path = output_path.with_suffix(".rendered.txt")

    if output_path.exists() and not force:
        err_console.print(
            f"[red]error:[/red] {output_path} already exists. Use --force to overwrite."
        )
        raise typer.Exit(code=1)

    with _fail_on("load content pack"):
        pack = ContentPack.from_dir(content_dir, content_cfg=cfg.content)

    tracker = UsageTracker()
    openai = _build_openai_client(cfg, usage_tracker=tracker)
    scenario_template = resolve_template_path(
        template_filename=_SCENARIO_TEMPLATE_FILENAME,
        content_dir=content_dir,
        builtin_dir=_builtin_templates_dir(),
    )
    console.print(f"using scenario template: [dim]{scenario_template}[/dim]")

    headlines: list[str] = []
    if no_news or not cfg.news.enabled:
        console.print("[dim]news fetch skipped[/dim]")
    else:
        headlines = fetch_recent_headlines(cfg.news)
        console.print(
            f"  collected [cyan]{len(headlines)}[/cyan] headlines "
            f"from {len(cfg.news.feeds)} feed(s)"
        )

    console.print(
        f"asking [cyan]{cfg.ai.text_model}[/cyan] for 7 episodes "
        f"for week [cyan]{target_week}[/cyan]…"
    )
    with _fail_on("scenario generation failed"):
        scenarios, rendered = generate_week(
            openai=openai,
            pack=pack,
            week=target_week,
            template_path=scenario_template,
            image_model=cfg.ai.image_model,
            news_headlines=headlines or None,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.safe_dump(
            scenarios.model_dump(mode="json"),
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    rendered_path.write_text(rendered.as_combined_text(), encoding="utf-8")
    console.print(
        f"[green]✓ saved[/green] {output_path} ({len(scenarios.episodes)} episodes)"
    )
    console.print(f"  rendered prompt: [dim]{rendered_path}[/dim]")
    _print_usage_summary(tracker)


if __name__ == "__main__":  # pragma: no cover
    app()
