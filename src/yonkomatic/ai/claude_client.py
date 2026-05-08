"""Thin wrapper around the Anthropic Messages API.

Centralizes model id pinning and timeout/retry policy so the rest of
yonkomatic can call Claude through a uniform ``complete(system, user)``
signature without touching SDK internals.
"""

from __future__ import annotations

import anthropic


class ClaudeClient:
    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        max_tokens: int = 4096,
        timeout: float = 120.0,
    ) -> None:
        self.client = anthropic.Anthropic(api_key=api_key, timeout=timeout)
        self.model = model
        self.max_tokens = max_tokens

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Send a single system+user pair, return concatenated text from the response."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens or self.max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        # Why iterate: a Messages response is a list of content blocks
        # (text / tool_use / image). This client is text-only by design.
        return "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
