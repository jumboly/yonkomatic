"""Tiny template engine: YAML frontmatter + ``{{var}}`` substitution.

Why custom over Jinja2: prompts only need plain variable substitution
(condition / loops are flattened by yonkomatic into pre-rendered strings),
so a few lines of regex avoid pulling in a sandboxed template engine and
keep the template syntax trivial for end users to author.

A template file looks like::

    ---
    system: |
      ... system instructions ...
    ---

    body with {{var1}} and {{var2}} placeholders.

``load_template`` returns ``PromptTemplate(system, body)`` strings, both of
which still contain raw ``{{var}}`` placeholders — call ``render`` on each
with a single ``variables`` dict to substitute.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

_PLACEHOLDER = re.compile(r"\{\{\s*(\w+)\s*\}\}")
_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)


class TemplateRenderError(KeyError):
    """Raised when a template references a variable not in the supplied dict."""


@dataclass
class PromptTemplate:
    """Result of parsing a template file's frontmatter and body."""

    system: str
    body: str
    source: Path | None = None


@dataclass
class RenderedPrompt:
    """A fully-expanded system + user pair sent to the LLM, kept for archive."""

    system: str
    user: str

    def as_combined_text(self) -> str:
        return f"[system]\n{self.system}\n\n[user]\n{self.user}"


def render(template: str, variables: dict[str, str]) -> str:
    """Replace every ``{{var}}`` in ``template`` with ``variables[var]``.

    Why eager error: a missing variable almost always indicates a typo in the
    template; surfacing it as ``TemplateRenderError`` lets the caller stop and
    point at the bad name rather than silently sending a half-rendered prompt
    to the LLM.
    """

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in variables:
            raise TemplateRenderError(
                f"unknown template variable: {{{{{key}}}}}"
            )
        return variables[key]

    return _PLACEHOLDER.sub(replace, template)


def load_template(path: Path) -> PromptTemplate:
    """Read a template file with optional ``---`` YAML frontmatter."""
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER.match(text)
    if match is None:
        return PromptTemplate(system="", body=text, source=path)

    raw_meta, body = match.groups()
    meta = yaml.safe_load(raw_meta) or {}
    system = str(meta.get("system", "")).rstrip()
    return PromptTemplate(system=system, body=body, source=path)
