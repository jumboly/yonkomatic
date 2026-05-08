"""Thin wrapper around google-genai for Gemini Flash Image generation.

Returns raw PNG bytes so callers can save / archive / forward without
caring about SDK-specific response shapes. Reference images (character
sheets, style samples) are passed as ``Path`` objects and read locally.

We deliberately use the env var name from yonkomatic's .env
(``GOOGLE_AI_STUDIO_API_KEY``) rather than the SDK's default
``GOOGLE_API_KEY`` / ``GEMINI_API_KEY`` so the project keeps a single
naming convention across providers.
"""

from __future__ import annotations

import mimetypes
import os
import time
from dataclasses import dataclass
from pathlib import Path

from google import genai
from google.genai import types
from google.genai.errors import APIError


@dataclass
class GeminiImageResult:
    image_bytes: bytes
    mime_type: str = "image/png"


class GeminiImageClient:
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        api_key_env: str = "GOOGLE_AI_STUDIO_API_KEY",
    ) -> None:
        key = api_key or os.environ.get(api_key_env)
        if not key:
            raise RuntimeError(
                f"Google AI Studio API key missing. Set {api_key_env} or pass api_key=..."
            )
        self.client = genai.Client(api_key=key)
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

        Retries on the empirically-common case where Gemini returns
        ``finish_reason=NO_IMAGE`` despite a perfectly concrete prompt
        (the model is non-deterministic — re-running usually succeeds).
        """
        parts: list[object] = []
        for ref in reference_images or []:
            mime, _ = mimetypes.guess_type(ref.name)
            mime = mime or "image/png"
            parts.append(types.Part.from_bytes(data=ref.read_bytes(), mime_type=mime))
        parts.append(prompt)

        last_reasons: list[str] = []
        last_api_error: APIError | None = None
        for attempt in range(max_attempts):
            if attempt > 0:
                time.sleep(2 ** (attempt - 1))  # 1s, 2s, 4s, ...

            try:
                response = self.client.models.generate_content(
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
            except APIError as e:
                last_api_error = e
                # 429 (rate limit) and 5xx (server) are transient — keep trying.
                # Other 4xx (auth / invalid request) won't recover from a retry.
                if e.code != 429 and not (500 <= e.code < 600):
                    raise
                continue

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

            last_reasons = [
                str(getattr(c, "finish_reason", "unknown"))
                for c in (response.candidates or [])
            ]

        if last_api_error is not None:
            raise RuntimeError(
                f"Gemini API error after {max_attempts} attempts: "
                f"{last_api_error.code} {last_api_error.message}"
            ) from last_api_error
        raise RuntimeError(
            f"Gemini returned no image data after {max_attempts} attempts "
            f"(finish_reason={last_reasons or ['no candidates']})"
        )
