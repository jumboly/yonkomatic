"""StaticSitePublisher.publish — Jinja2 output structure on tmp_path."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from yonkomatic.publisher.base import Episode
from yonkomatic.publisher.static_site import INDEX_LIMIT, StaticSitePublisher

# Minimal valid 1x1 PNG. Decoded once at import to avoid repeating bytes.
_PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4"
    "2mNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
)


def _episode(*, number: int = 5, date: str = "2026-05-09") -> Episode:
    return Episode(
        number=number,
        title=f"第{number}話タイトル",
        summary_no_spoiler=f"summary {number}",
        week="2026-W19",
        date=date,
    )


def _png(tmp_path: Path, name: str = "src.png") -> Path:
    path = tmp_path / name
    path.write_bytes(_PNG_1X1)
    return path


def test_publish_creates_index_post_image_css(tmp_path: Path) -> None:
    out = tmp_path / "site"
    pub = StaticSitePublisher(out)
    result = pub.publish(_episode(), _png(tmp_path))
    assert result.ok
    assert (out / "index.html").exists()
    assert (out / "posts" / "2026-05-09.html").exists()
    assert (out / "images" / "2026-05-09.png").exists()
    assert (out / "css" / "style.css").exists()
    assert (out / ".posts-index.json").exists()


def test_publish_returns_relative_url_when_no_base_url(tmp_path: Path) -> None:
    pub = StaticSitePublisher(tmp_path / "site")
    result = pub.publish(_episode(), _png(tmp_path))
    assert result.url == "posts/2026-05-09.html"


def test_publish_returns_absolute_url_with_base_url(tmp_path: Path) -> None:
    pub = StaticSitePublisher(tmp_path / "site", base_url="https://example.com")
    result = pub.publish(_episode(), _png(tmp_path))
    assert result.url == "https://example.com/posts/2026-05-09.html"


def test_post_html_contains_episode_title_and_summary(tmp_path: Path) -> None:
    pub = StaticSitePublisher(tmp_path / "site")
    pub.publish(_episode(number=7), _png(tmp_path))
    body = (tmp_path / "site" / "posts" / "2026-05-09.html").read_text(encoding="utf-8")
    assert "第7話タイトル" in body
    assert "summary 7" in body


def test_index_upserts_same_date_no_duplicates(tmp_path: Path) -> None:
    pub = StaticSitePublisher(tmp_path / "site")
    pub.publish(_episode(number=1), _png(tmp_path))
    pub.publish(_episode(number=2), _png(tmp_path))
    entries = json.loads(
        (tmp_path / "site" / ".posts-index.json").read_text(encoding="utf-8")
    )
    assert len(entries) == 1
    assert entries[0]["episode_number"] == 2


def test_index_limited_to_thirty_entries(tmp_path: Path) -> None:
    # Why unique dates: _upsert_index_entry deduplicates on date, so re-using
    # one would mask the size cap we are checking.
    pub = StaticSitePublisher(tmp_path / "site")
    for i in range(INDEX_LIMIT + 1):
        month = (i // 28) + 5
        day = (i % 28) + 1
        pub.publish(
            _episode(number=i + 1, date=f"2026-{month:02d}-{day:02d}"),
            _png(tmp_path),
        )
    index_html = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    rendered_count = index_html.count('<li class="entry">')
    assert rendered_count == INDEX_LIMIT


def test_css_not_overwritten_on_second_publish(tmp_path: Path) -> None:
    pub = StaticSitePublisher(tmp_path / "site")
    pub.publish(_episode(number=1, date="2026-05-09"), _png(tmp_path))
    css_path = tmp_path / "site" / "css" / "style.css"
    css_path.write_text("/* user customisation */", encoding="utf-8")
    pub.publish(_episode(number=2, date="2026-05-10"), _png(tmp_path))
    assert css_path.read_text(encoding="utf-8") == "/* user customisation */"


def test_image_extension_preserved(tmp_path: Path) -> None:
    pub = StaticSitePublisher(tmp_path / "site")
    pub.publish(_episode(), _png(tmp_path, name="src.jpg"))
    assert (tmp_path / "site" / "images" / "2026-05-09.jpg").exists()
    assert not (tmp_path / "site" / "images" / "2026-05-09.png").exists()
