"""Fetch recent RSS headlines so the scenario generator can hint at the week's mood.

Headlines are passed to Claude as soft context — the prompt explicitly forbids
direct topical references (politics, real names, etc.) and asks only for the
genre's general flavor. See SPEC.md "時事ネタの安全な取り込み".
"""

from __future__ import annotations

import socket
from datetime import UTC, datetime, timedelta

import feedparser
from rich.console import Console

from yonkomatic.config import NewsConfig

_err_console = Console(stderr=True)
_FEED_TIMEOUT_SEC = 15


def fetch_recent_headlines(news_cfg: NewsConfig) -> list[str]:
    """Return up to ``max_items_per_feed`` recent titles per feed, flattened.

    A single feed failing (network, malformed XML, missing dates) does not
    abort the rest — the same independence philosophy as the publisher pool.
    """
    if not news_cfg.enabled or not news_cfg.feeds:
        return []

    cutoff = datetime.now(UTC) - timedelta(days=news_cfg.lookback_days)
    headlines: list[str] = []

    # Why scope the socket default: feedparser.parse → urlopen honors only
    # socket.getdefaulttimeout(); without this a stalled feed could hang the
    # weekly cron indefinitely. The default is restored to avoid leaking
    # the timeout into other code paths in the same process.
    previous_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(_FEED_TIMEOUT_SEC)
    try:
        for url in news_cfg.feeds:
            try:
                parsed = feedparser.parse(url)
            except Exception as e:
                _err_console.print(f"[yellow]feed parse failed for {url}: {e}[/yellow]")
                continue

            kept = 0
            for entry in parsed.entries:
                if kept >= news_cfg.max_items_per_feed:
                    break
                published = _entry_datetime(entry)
                # Why accept missing dates: some feeds omit pubDate entirely;
                # rejecting them outright would silently empty the pool.
                if published is not None and published < cutoff:
                    continue
                title = getattr(entry, "title", "").strip()
                if title:
                    headlines.append(title)
                    kept += 1
    finally:
        socket.setdefaulttimeout(previous_timeout)

    return headlines


def _entry_datetime(entry: object) -> datetime | None:
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if parsed is None:
        return None
    return datetime(*parsed[:6], tzinfo=UTC)
