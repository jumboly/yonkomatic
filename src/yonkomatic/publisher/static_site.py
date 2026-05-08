"""Static site publisher: writes a small HTML archive under ``output_dir``.

Layout produced::

    {output_dir}/
      index.html              # newest 30 entries
      posts/{date}.html       # individual episode pages
      images/{date}.png       # copied artwork
      css/style.css           # bundled stylesheet (copied on first publish)
      .posts-index.json       # internal: per-episode metadata, used to
                              # rebuild index.html without re-parsing HTML

Default ``output_dir`` is ``./docs`` because GitHub Pages' "Deploy from
a branch" only supports ``/(root)`` or ``/docs`` as the publishing
source. Repo documentation (ROADMAP.md / SPEC.md / README.md /
CLAUDE.md) lives at the repo root to avoid colliding with the
generated site.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from yonkomatic.publisher.base import Episode, PublishResult

INDEX_LIMIT = 30
INDEX_FILE = ".posts-index.json"


class StaticSitePublisher:
    name = "static_site"

    def __init__(
        self,
        output_dir: Path,
        base_url: str = "",
        templates_dir: Path | None = None,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.base_url = base_url.rstrip("/")
        self._templates_dir = templates_dir or Path(__file__).parent / "templates"
        self._env = Environment(
            loader=FileSystemLoader(str(self._templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            keep_trailing_newline=True,
        )

    def publish(self, episode: Episode, image_path: Path) -> PublishResult:
        try:
            image_filename = self._copy_image(image_path, episode.date)
            self._ensure_static_assets()
            entry = _entry_from_episode(episode, image_filename)
            entries = self._upsert_index_entry(entry)
            self._render_post(episode, image_filename)
            self._render_index(entries[:INDEX_LIMIT])
        except Exception as e:
            return PublishResult(ok=False, publisher=self.name, error=str(e))

        url = self._post_url(episode.date)
        return PublishResult(ok=True, publisher=self.name, url=url)

    def _copy_image(self, image_path: Path, date: str) -> str:
        # Why preserve suffix: Gemini may return JPEG even when callers asked
        # for PNG (it ignores output_mime_type), and the archive ext is fixed
        # in cli.py to match the actual MIME. The static site URL must align
        # so browsers receive the right Content-Type.
        ext = image_path.suffix or ".png"
        dest_dir = self.output_dir / "images"
        dest_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{date}{ext}"
        shutil.copy(image_path, dest_dir / filename)
        return filename

    def _ensure_static_assets(self) -> None:
        css_dir = self.output_dir / "css"
        css_dir.mkdir(parents=True, exist_ok=True)
        dest = css_dir / "style.css"
        # Why "if not exists": users may customize style.css in their fork;
        # copying every publish would clobber their edits.
        if not dest.exists():
            src = self._templates_dir / "static" / "style.css"
            shutil.copy(src, dest)

    def _upsert_index_entry(self, entry: dict[str, Any]) -> list[dict[str, Any]]:
        index_path = self.output_dir / INDEX_FILE
        entries: list[dict[str, Any]] = []
        if index_path.exists():
            entries = json.loads(index_path.read_text(encoding="utf-8"))

        entries = [e for e in entries if e.get("date") != entry["date"]]
        entries.append(entry)
        entries.sort(key=lambda e: e["date"], reverse=True)

        index_path.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return entries

    def _render_post(self, episode: Episode, image_filename: str) -> Path:
        posts_dir = self.output_dir / "posts"
        posts_dir.mkdir(parents=True, exist_ok=True)
        template = self._env.get_template("post.html.j2")
        html = template.render(
            episode=episode, image_filename=image_filename, base_url=self.base_url
        )
        dest = posts_dir / f"{episode.date}.html"
        dest.write_text(html, encoding="utf-8")
        return dest

    def _render_index(self, entries: list[dict[str, Any]]) -> Path:
        template = self._env.get_template("index.html.j2")
        html = template.render(entries=entries, base_url=self.base_url)
        dest = self.output_dir / "index.html"
        dest.write_text(html, encoding="utf-8")
        return dest

    def _post_url(self, date: str) -> str:
        if self.base_url:
            return f"{self.base_url}/posts/{date}.html"
        return f"posts/{date}.html"


def _entry_from_episode(episode: Episode, image_filename: str) -> dict[str, Any]:
    return {
        "episode_number": episode.number,
        "title": episode.title,
        "summary_no_spoiler": episode.summary_no_spoiler,
        "week": episode.week,
        "date": episode.date,
        "image_filename": image_filename,
    }
