"""OpenAI SDK wrapper covering text completion (incl. Structured Output) and
image generation (gpt-image-1 / gpt-image-2).

Centralises model id pinning, retry policy, and the choice between
``images.generate`` (text-only) and ``images.edit`` (with reference images).
"""

from __future__ import annotations

import base64
import time
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from openai import APIError, OpenAI, RateLimitError
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass
class ImageResult:
    image_bytes: bytes
    mime_type: str = "image/png"


class OpenAIClient:
    def __init__(
        self,
        *,
        api_key: str,
        text_model: str,
        image_model: str,
        timeout: float = 120.0,
    ) -> None:
        self.client = OpenAI(api_key=api_key, timeout=timeout)
        self.text_model = text_model
        self.image_model = image_model

    def complete(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.4,
    ) -> str:
        """Plain text chat completion returning the assistant's text."""
        response = self.client.chat.completions.create(
            model=self.text_model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""

    def complete_structured(
        self,
        *,
        system: str,
        user: str,
        schema: type[T],
        temperature: float = 0.7,
    ) -> T:
        """Structured output via ``response_format=PydanticModel``.

        The SDK validates the response against ``schema`` and returns a parsed
        instance directly. Raises if the model violates the schema.
        """
        response = self.client.beta.chat.completions.parse(
            model=self.text_model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format=schema,
        )
        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise RuntimeError("OpenAI returned no parsed structured response")
        return parsed

    def generate_image(
        self,
        *,
        prompt: str,
        reference_images: list[Path] | None = None,
        size: str = "1024x1536",
        max_attempts: int = 3,
    ) -> ImageResult:
        """Generate one image. With refs: ``images.edit``; without: ``images.generate``.

        Both endpoints return ``b64_json`` decoded to PNG bytes. Retries on
        RateLimitError and 5xx APIError, honoring the server's ``Retry-After``
        header when present (otherwise exponential backoff).
        """
        last_error: Exception | None = None
        for attempt in range(max_attempts):
            try:
                response = self._call_image_api(prompt, reference_images, size)
                image_b64 = response.data[0].b64_json
                if not image_b64:
                    raise RuntimeError("OpenAI returned empty image data")
                return ImageResult(image_bytes=base64.b64decode(image_b64))
            except (RateLimitError, APIError) as e:
                last_error = e
                code = getattr(e, "status_code", None) or 0
                if not isinstance(e, RateLimitError) and not (500 <= code < 600):
                    raise
                _sleep_before_next_attempt(attempt, server_hint=_extract_retry_after(e))
                continue

        raise RuntimeError(
            f"OpenAI image generation failed after {max_attempts} attempts"
        ) from last_error

    def _call_image_api(
        self,
        prompt: str,
        reference_images: list[Path] | None,
        size: str,
    ):
        """Dispatch between ``images.edit`` (with refs) and ``images.generate``.

        Why ExitStack: opening N files via list comprehension can leak earlier
        handles if a later open() raises. ExitStack guarantees every opened
        file is closed even on partial failure.
        """
        if not reference_images:
            return self.client.images.generate(
                model=self.image_model,
                prompt=prompt,
                size=size,
            )
        with ExitStack() as stack:
            files = [stack.enter_context(open(p, "rb")) for p in reference_images]
            return self.client.images.edit(
                model=self.image_model,
                image=files if len(files) > 1 else files[0],
                prompt=prompt,
                size=size,
            )


def _extract_retry_after(error: APIError) -> float | None:
    """Pull a ``Retry-After`` value (seconds) from the OpenAI error response."""
    response = getattr(error, "response", None)
    if response is None:
        return None
    headers = getattr(response, "headers", None) or {}
    raw = headers.get("retry-after") or headers.get("Retry-After")
    if not raw:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _sleep_before_next_attempt(attempt: int, *, server_hint: float | None = None) -> None:
    """Sleep before the next retry; cap at 60s so a misbehaving hint can't stall us."""
    delay = server_hint if server_hint is not None else 2**attempt
    time.sleep(min(delay, 60.0))
