"""yonkomatic CLI — entry point for `yonkomatic` console script."""

from __future__ import annotations

import json
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
from PIL import Image, ImageDraw, ImageFont
from rich.console import Console

from yonkomatic import __version__
from yonkomatic.ai.claude_client import ClaudeClient
from yonkomatic.ai.gemini_client import GeminiImageClient, GeminiImageResult
from yonkomatic.config import Config, TextRenderMode, load_config
from yonkomatic.news.fetcher import fetch_recent_headlines
from yonkomatic.panel.composer import compose
from yonkomatic.panel.description import ContentPack, build_image_prompt
from yonkomatic.panel.validator import ValidationResult, validate
from yonkomatic.publisher.base import Episode, Publisher, PublishResult
from yonkomatic.publisher.slack import SlackPublisher
from yonkomatic.publisher.static_site import StaticSitePublisher
from yonkomatic.scenario.generator import generate_week
from yonkomatic.scenario.schema import ScenarioEpisode, ScenarioWeek
from yonkomatic.state.repo import HistoryEntry, StateStore

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


TextModeOption = Annotated[
    TextRenderMode | None,
    typer.Option(
        "--text-mode",
        help="Override text_rendering.mode for this run (pil_overlay | model_render).",
    ),
]
ImageModelOption = Annotated[
    str | None,
    typer.Option(
        "--image-model",
        help="Override ai.image_model for this run (e.g. gemini-3-pro-image-preview).",
    ),
]


def _apply_cli_overrides(
    cfg: Config,
    *,
    text_mode: TextRenderMode | None = None,
    image_model: str | None = None,
) -> Config:
    """Merge CLI flag overrides into cfg via sub-model copy.

    Lets operators A/B test ``text_rendering.mode`` (pil_overlay vs
    model_render) and ``ai.image_model`` without editing config.yaml.
    text_mode is already a typer-validated Literal; image_model is
    free-form (the SDK rejects unknown ids), so no Pydantic re-validation
    is needed.
    """
    updates: dict[str, Any] = {}
    if text_mode is not None:
        updates["text_rendering"] = cfg.text_rendering.model_copy(update={"mode": text_mode})
    if image_model is not None:
        updates["ai"] = cfg.ai.model_copy(update={"image_model": image_model})
    return cfg.model_copy(update=updates) if updates else cfg


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
    text_mode: TextModeOption = None,
    image_model: ImageModelOption = None,
    save_prompt: bool = typer.Option(
        True,
        "--save-prompt/--no-save-prompt",
        help="Also write the Claude-generated prompt next to the image.",
    ),
) -> None:
    """Run the full image pipeline once: scenario → prompt (Claude) → image (Gemini) → compose.

    Stage 3 (compose) runs as well so the saved image reflects the final
    output as it would be published — when ``mode=pil_overlay`` Japanese
    bubbles are overlaid; when ``mode=model_render`` Gemini's output is
    passed through unchanged.
    """
    cfg = _apply_cli_overrides(load_config(config_path), text_mode=text_mode, image_model=image_model)

    episode = ScenarioEpisode.model_validate_json(scenario_path.read_text(encoding="utf-8"))
    console.print(f"loaded scenario: [cyan]{episode.title}[/cyan] ({len(episode.panels)} panels)")

    pack = ContentPack.from_dir(content_dir, content_cfg=cfg.content)
    console.print(f"loaded content pack from [cyan]{content_dir}[/cyan]")

    claude_key = _require_env(cfg.ai.scenario_api_key_env)
    claude = ClaudeClient(model=cfg.ai.scenario_model, api_key=claude_key)
    console.print(
        f"asking [cyan]{cfg.ai.scenario_model}[/cyan] for image prompt "
        f"(text mode: [cyan]{cfg.text_rendering.mode}[/cyan])…"
    )
    with _fail_on("prompt generation failed"):
        image_prompt = build_image_prompt(
            episode=episode,
            pack=pack,
            claude=claude,
            mode=cfg.text_rendering.mode,
        )

    if save_prompt:
        prompt_path = output.with_suffix(".prompt.txt")
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(image_prompt, encoding="utf-8")
        console.print(f"  wrote prompt: [dim]{prompt_path}[/dim]")

    result = _run_gemini(cfg, prompt=image_prompt, refs=refs)

    with _fail_on("compose"):
        final_bytes = compose(
            image_bytes=result.image_bytes,
            episode=episode,
            mode=cfg.text_rendering.mode,
            font_path=cfg.text_rendering.font_path,
            bubble_style=cfg.text_rendering.bubble_style,
        )

    saved = _save_image(output, final_bytes, result.mime_type)
    console.print(
        f"[green]✓ saved[/green] {saved} ({len(final_bytes)} bytes, {result.mime_type})"
    )


def _today_in_configured_tz(cfg: Config) -> str:
    return datetime.now(ZoneInfo(cfg.schedule.timezone)).date().isoformat()


def _iso_week_of(date_str: str) -> str:
    return _date.fromisoformat(date_str).strftime("%G-W%V")


def _current_iso_week(cfg: Config) -> str:
    return _iso_week_of(_today_in_configured_tz(cfg))


def _resolve_theme_filename(cfg: Config, content_dir: Path) -> str:
    """Pick the monthly theme file (YYYY-MM.md) when present, otherwise default.md.

    Why: SPEC.md prescribes ``themes/{YYYY-MM}.md`` for monthly mood, but the
    bare template only ships ``default.md``. Falling back keeps fresh checkouts
    runnable while honoring the monthly file the moment a user adds one.
    """
    month = datetime.now(ZoneInfo(cfg.schedule.timezone)).strftime("%Y-%m")
    monthly = cfg.content.themes_path(content_dir) / f"{month}.md"
    return f"{month}.md" if monthly.exists() else "default.md"


def _notify_failure(cfg: Config, message: str) -> None:
    """Post a non-blocking failure alert via Slack if it is enabled and configured.

    Why isolated from _build_publishers: notification must not require any
    other publisher to be set up, and a missing Slack token should silently
    degrade to stderr rather than break the cron's error handling itself.
    """
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
    prompt: str,
    cfg: Config,
    validation: ValidationResult,
) -> tuple[Path, Path]:
    archive_dir.mkdir(parents=True, exist_ok=True)
    image_path = _save_image(archive_dir / f"{date}.png", image_bytes, mime_type)
    meta_path = archive_dir / f"{date}.json"
    meta = {
        "date": date,
        "episode_number": episode.episode_number,
        "week": episode.week,
        "title": episode.title,
        "summary_no_spoiler": episode.summary_no_spoiler,
        "image_prompt": prompt,
        "ai": {
            "scenario_model": cfg.ai.scenario_model,
            "image_model": cfg.ai.image_model,
            "image_size": cfg.ai.image_size,
            "aspect_ratio": cfg.ai.aspect_ratio,
        },
        "image": {"mime_type": mime_type, "size_bytes": len(image_bytes)},
        "text_rendering_mode": cfg.text_rendering.mode,
        "validation": {
            "ok": validation.ok,
            "score": validation.score,
            "reason": validation.reason,
        },
    }
    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return image_path, meta_path


@app.command()
def publish(
    scenario_file: Path = typer.Option(
        ...,
        "--scenario-file",
        "-s",
        help="Path to a scenario JSON file (single ScenarioEpisode).",
    ),
    date_str: str | None = typer.Option(
        None,
        "--date",
        help="ISO date YYYY-MM-DD. Defaults to today in config schedule.timezone.",
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
    config_path: Path = typer.Option(Path("config.yaml"), "--config"),
    state_path: Path = typer.Option(
        Path("state/state.json"),
        "--state",
        help="Path to state.json. Updated on success unless --dry-run.",
    ),
    archive_dir: Path = typer.Option(
        Path("output/archive"),
        "--archive-dir",
        help="Where {date}.png and {date}.json are written for reproducibility.",
    ),
    text_mode: TextModeOption = None,
    image_model: ImageModelOption = None,
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Generate image and write archive, but skip publishers and state update.",
    ),
) -> None:
    """Run the full pipeline: scenario → image → multi-publish + archive."""
    cfg = _apply_cli_overrides(load_config(config_path), text_mode=text_mode, image_model=image_model)

    with _fail_on("load scenario"):
        episode_data = ScenarioEpisode.model_validate_json(
            scenario_file.read_text(encoding="utf-8")
        )

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
) -> None:
    console.print(
        f"publishing for [cyan]{pub_date}[/cyan]: 「{episode_data.title}」 "
        f"(episode {episode_data.episode_number})"
    )

    with _fail_on("load content pack"):
        pack = ContentPack.from_dir(content_dir, content_cfg=cfg.content)

    claude_key = _require_env(cfg.ai.scenario_api_key_env)
    claude = ClaudeClient(model=cfg.ai.scenario_model, api_key=claude_key)
    console.print(f"asking [cyan]{cfg.ai.scenario_model}[/cyan] for image prompt…")
    with _fail_on("prompt generation failed"):
        image_prompt = build_image_prompt(
            episode=episode_data,
            pack=pack,
            claude=claude,
            mode=cfg.text_rendering.mode,
        )

    gemini_result = _run_gemini(cfg, prompt=image_prompt, refs=refs)

    with _fail_on("compose"):
        final_bytes = compose(
            image_bytes=gemini_result.image_bytes,
            episode=episode_data,
            mode=cfg.text_rendering.mode,
            font_path=cfg.text_rendering.font_path,
            bubble_style=cfg.text_rendering.bubble_style,
        )

    validation = validate(image_bytes=final_bytes, episode=episode_data)
    if not validation.ok:
        err_console.print(f"[red]✗ validation failed:[/red] {validation.reason}")
        raise typer.Exit(code=1)

    archive_image, archive_meta = _write_archive(
        archive_dir=archive_dir,
        date=pub_date,
        image_bytes=final_bytes,
        mime_type=gemini_result.mime_type,
        episode=episode_data,
        prompt=image_prompt,
        cfg=cfg,
        validation=validation,
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
            "[yellow]warning:[/yellow] no publishers are enabled in config.yaml"
        )

    if dry_run:
        for pub in publishers:
            console.print(f"[dim]·[/dim] [cyan]{pub.name}[/cyan]: dry-run (no post)")
        console.print("[green]✓ dry-run complete[/green]")
        return

    results = _run_publishers(publishers, episode_obj, archive_image)
    _print_publish_results(results)

    if not publishers:
        err_console.print(
            "[yellow]no publishers were configured; state not updated.[/yellow]"
        )
        return

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
        help="Directory holding characters/, world/, samples/, themes/.",
    ),
    refs: list[Path] = typer.Option(
        [],
        "--refs",
        "-r",
        help="Optional character / style reference images.",
    ),
    config_path: Path = typer.Option(Path("config.yaml"), "--config"),
    state_path: Path = typer.Option(Path("state/state.json"), "--state"),
    scenarios_dir: Path = typer.Option(
        Path("scenarios"),
        "--scenarios-dir",
        help="Directory containing {YYYY-Www}.json scenario files.",
    ),
    archive_dir: Path = typer.Option(Path("output/archive"), "--archive-dir"),
    text_mode: TextModeOption = None,
    image_model: ImageModelOption = None,
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Pick the next episode for today's ISO week from scenarios/, then publish."""
    cfg = _apply_cli_overrides(load_config(config_path), text_mode=text_mode, image_model=image_model)
    pub_date = date_str or _today_in_configured_tz(cfg)
    target_week = _iso_week_of(pub_date)
    week_path = scenarios_dir / f"{target_week}.json"

    if not week_path.exists():
        msg = (
            f"scenarios file {week_path} not found for {target_week} "
            f"(run generate-scenarios --week {target_week} first)"
        )
        err_console.print(f"[red]error:[/red] {msg}")
        _notify_failure(cfg, msg)
        raise typer.Exit(code=1)

    with _fail_on("load week scenarios"):
        week_data = ScenarioWeek.model_validate_json(
            week_path.read_text(encoding="utf-8")
        )

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
        help="Output JSON path. Defaults to scenarios/{week}.json.",
    ),
    content_dir: Path = typer.Option(
        Path("examples/minimal"),
        "--content",
        help="Directory holding characters/, world/, samples/, themes/.",
    ),
    no_news: bool = typer.Option(
        False,
        "--no-news",
        help="Skip RSS fetch even if news.enabled is true.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite an existing scenarios/{week}.json.",
    ),
    config_path: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Ask Claude for 7 episodes for the given ISO week."""
    cfg = load_config(config_path)
    target_week = week or _current_iso_week(cfg)
    output_path = out or Path("scenarios") / f"{target_week}.json"

    if output_path.exists() and not force:
        err_console.print(
            f"[red]error:[/red] {output_path} already exists. Use --force to overwrite."
        )
        raise typer.Exit(code=1)

    with _fail_on("load content pack"):
        pack = ContentPack.from_dir(
            content_dir,
            content_cfg=cfg.content,
            theme_filename=_resolve_theme_filename(cfg, content_dir),
        )

    api_key = _require_env(cfg.ai.scenario_api_key_env)
    claude = ClaudeClient(model=cfg.ai.scenario_model, api_key=api_key)

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
        f"asking [cyan]{cfg.ai.scenario_model}[/cyan] for 7 episodes "
        f"for week [cyan]{target_week}[/cyan]…"
    )
    with _fail_on("scenario generation failed"):
        scenarios = generate_week(
            claude=claude,
            pack=pack,
            week=target_week,
            news_headlines=headlines or None,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        scenarios.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    console.print(
        f"[green]✓ saved[/green] {output_path} ({len(scenarios.episodes)} episodes)"
    )


if __name__ == "__main__":  # pragma: no cover
    app()
