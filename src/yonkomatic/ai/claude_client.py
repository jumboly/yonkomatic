"""Thin wrapper around the Anthropic Messages API.

Why this exists: most yonkomatic code shouldn't care about Anthropic SDK
specifics — it just wants "send a system+user prompt, get text back."
We also want a single place to pin the model id (config-driven) and to
keep retry/timeout policy uniform.
"""

from __future__ import annotations

import os

import anthropic


class ClaudeClient:
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        api_key_env: str = "ANTHROPIC_API_KEY",
        max_tokens: int = 4096,
        timeout: float = 120.0,
    ) -> None:
        key = api_key or os.environ.get(api_key_env)
        if not key:
            raise RuntimeError(
                f"Anthropic API key missing. Set {api_key_env} or pass api_key=..."
            )
        self.client = anthropic.Anthropic(api_key=key, timeout=timeout)
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
        # Concatenate any text blocks; tool use / image blocks are unused here.
        chunks: list[str] = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                chunks.append(block.text)
        return "".join(chunks)
