"""Thin wrapper around google-genai for Gemini Flash Image generation.

Returns raw image bytes (with the actual MIME type) so callers can save /
archive / forward without caring about SDK-specific response shapes.
Reference images (character sheets, style samples) are passed as
``Path`` objects and read on demand.
"""

from __future__ import annotations

import mimetypes
import re
import time
from dataclasses import dataclass
from pathlib import Path

from google import genai
from google.genai import types
from google.genai.errors import APIError

PartLike = types.Part | str

# google-genai's APIError surfaces server-side retry hints inside its
# message JSON (look for ``"retryDelay": "20s"``). We honor it on 503/429
# instead of using our own short backoff, which would otherwise hammer
# the API far before the suggested cooldown.
_RETRY_DELAY_RE = re.compile(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s"')


@dataclass
class GeminiImageResult:
    image_bytes: bytes
    mime_type: str = "image/png"


class GeminiImageClient:
    def __init__(self, *, model: str, api_key: str) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate_image(
        self,
        *,
        prompt: str,
        reference_images: list[Path] | None = None,
        aspect_ratio: str = "3:4",
        image_size: str = "2K",
        max_attempts: int = 3,
    ) -> GeminiImageResult:
        """Generate one image; references are inlined before the text prompt.

        Retries on (a) ``finish_reason=NO_IMAGE`` (the model is non-deterministic
        and re-running with the same prompt usually succeeds) and (b) transient
        APIError (429, 5xx). Server-suggested ``retryDelay`` is honored; falls
        back to exponential 1s/2s/4s.
        """
        parts: list[PartLike] = [
            types.Part.from_bytes(
                data=ref.read_bytes(),
                mime_type=mimetypes.guess_type(ref.name)[0] or "image/png",
            )
            for ref in reference_images or []
        ]
        parts.append(prompt)

        last_reasons: list[str] = []
        last_api_error: APIError | None = None

        for attempt in range(max_attempts):
            try:
                response = self._call(parts, aspect_ratio, image_size)
            except APIError as e:
                last_api_error = e
                code = getattr(e, "code", None) or 0
                # Other 4xx (auth / invalid request) won't recover from a retry.
                if code != 429 and not (500 <= code < 600):
                    raise
                _sleep_before_next_attempt(attempt, server_hint=_extract_retry_delay(e))
                continue

            image = _extract_image(response)
            if image is not None:
                return image

            last_reasons = [
                str(getattr(c, "finish_reason", "unknown"))
                for c in (response.candidates or [])
            ]
            _sleep_before_next_attempt(attempt, server_hint=None)

        if last_api_error is not None:
            raise RuntimeError(
                f"Gemini API error after {max_attempts} attempts: "
                f"{last_api_error.code} {last_api_error.message}"
            ) from last_api_error
        raise RuntimeError(
            f"Gemini returned no image data after {max_attempts} attempts "
            f"(finish_reason={last_reasons or ['no candidates']})"
        )

    def _call(
        self, parts: list[PartLike], aspect_ratio: str, image_size: str
    ) -> types.GenerateContentResponse:
        return self.client.models.generate_content(
            model=self.model,
            contents=parts,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                ),
            ),
        )


def _extract_image(response: types.GenerateContentResponse) -> GeminiImageResult | None:
    """Defensive parse: SDK part shapes have shifted across versions, so we probe."""
    for candidate in response.candidates or []:
        content = getattr(candidate, "content", None)
        if content is None:
            continue
        for part in content.parts or []:
            inline = getattr(part, "inline_data", None)
            if inline and inline.data:
                return GeminiImageResult(
                    image_bytes=inline.data,
                    mime_type=inline.mime_type or "image/png",
                )
    return None


def _extract_retry_delay(error: APIError) -> float | None:
    match = _RETRY_DELAY_RE.search(str(error))
    return float(match.group(1)) if match else None


def _sleep_before_next_attempt(attempt: int, *, server_hint: float | None) -> None:
    """Sleep between attempts; cap at 60s so a misbehaving hint can't stall us."""
    delay = server_hint if server_hint is not None else 2**attempt
    time.sleep(min(delay, 60.0))
