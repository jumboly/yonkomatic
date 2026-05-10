"""fetch_recent_headlines with feedparser fully mocked — runs offline."""

from __future__ import annotations

import socket
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from pytest_mock import MockerFixture

from yonkomatic.config import NewsConfig
from yonkomatic.news.fetcher import fetch_recent_headlines


def _entry(title: str, *, published: datetime | None) -> SimpleNamespace:
    parsed = published.timetuple() if published is not None else None
    return SimpleNamespace(title=title, published_parsed=parsed, updated_parsed=None)


def _feed(*entries: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(entries=list(entries))


def test_returns_empty_when_news_disabled(mocker: MockerFixture) -> None:
    parse = mocker.patch("yonkomatic.news.fetcher.feedparser.parse")
    cfg = NewsConfig(enabled=False, feeds=["https://example.com/rss"])
    assert fetch_recent_headlines(cfg) == []
    parse.assert_not_called()


def test_returns_empty_when_feeds_empty(mocker: MockerFixture) -> None:
    parse = mocker.patch("yonkomatic.news.fetcher.feedparser.parse")
    cfg = NewsConfig(enabled=True, feeds=[])
    assert fetch_recent_headlines(cfg) == []
    parse.assert_not_called()


def test_collects_titles_from_multiple_feeds(mocker: MockerFixture) -> None:
    now = datetime.now(UTC)
    parse = mocker.patch(
        "yonkomatic.news.fetcher.feedparser.parse",
        side_effect=[
            _feed(_entry("alpha headline", published=now)),
            _feed(_entry("beta headline", published=now)),
        ],
    )
    cfg = NewsConfig(
        enabled=True,
        feeds=["https://a", "https://b"],
        max_items_per_feed=10,
        lookback_days=7,
    )
    assert fetch_recent_headlines(cfg) == ["alpha headline", "beta headline"]
    assert parse.call_count == 2


def test_max_items_per_feed_truncates(mocker: MockerFixture) -> None:
    now = datetime.now(UTC)
    entries = [_entry(f"item {i}", published=now) for i in range(10)]
    mocker.patch("yonkomatic.news.fetcher.feedparser.parse", return_value=_feed(*entries))
    cfg = NewsConfig(
        enabled=True, feeds=["https://a"], max_items_per_feed=2, lookback_days=7
    )
    assert fetch_recent_headlines(cfg) == ["item 0", "item 1"]


def test_lookback_filters_out_old_entries(mocker: MockerFixture) -> None:
    now = datetime.now(UTC)
    old = now - timedelta(days=10)
    mocker.patch(
        "yonkomatic.news.fetcher.feedparser.parse",
        return_value=_feed(
            _entry("fresh", published=now),
            _entry("stale", published=old),
        ),
    )
    cfg = NewsConfig(
        enabled=True, feeds=["https://a"], max_items_per_feed=10, lookback_days=1
    )
    assert fetch_recent_headlines(cfg) == ["fresh"]


def test_entry_without_pubdate_is_kept(mocker: MockerFixture) -> None:
    # Why: real-world feeds sometimes omit pubDate; rejecting them outright
    # would silently drain the pool. The fetcher accepts undated entries.
    mocker.patch(
        "yonkomatic.news.fetcher.feedparser.parse",
        return_value=_feed(_entry("undated", published=None)),
    )
    cfg = NewsConfig(
        enabled=True, feeds=["https://a"], max_items_per_feed=10, lookback_days=1
    )
    assert fetch_recent_headlines(cfg) == ["undated"]


def test_single_feed_failure_does_not_abort_others(mocker: MockerFixture) -> None:
    now = datetime.now(UTC)
    mocker.patch(
        "yonkomatic.news.fetcher.feedparser.parse",
        side_effect=[
            RuntimeError("boom"),
            _feed(_entry("survived", published=now)),
        ],
    )
    cfg = NewsConfig(
        enabled=True,
        feeds=["https://broken", "https://ok"],
        max_items_per_feed=10,
        lookback_days=7,
    )
    assert fetch_recent_headlines(cfg) == ["survived"]


def test_socket_timeout_restored_after_run(mocker: MockerFixture) -> None:
    mocker.patch(
        "yonkomatic.news.fetcher.feedparser.parse",
        return_value=_feed(),
    )
    before = socket.getdefaulttimeout()
    fetch_recent_headlines(
        NewsConfig(enabled=True, feeds=["https://a"], max_items_per_feed=1, lookback_days=1)
    )
    assert socket.getdefaulttimeout() == before
