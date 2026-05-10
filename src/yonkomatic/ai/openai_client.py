"""OpenAI SDK wrapper covering text completion (incl. Structured Output) and
image generation (gpt-image-1 / gpt-image-2).

Centralises model id pinning, retry policy, and the choice between
``images.generate`` (text-only) and ``images.edit`` (with reference images).
Also tracks per-call token usage and estimated cost via ``UsageTracker``.
"""

from __future__ import annotations

import base64
import sys
import time
from contextlib import ExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

from openai import APIError, OpenAI, RateLimitError
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


# Per 1M-token rates for known models, standard tier (USD).
# Source: developers.openai.com/api/docs/pricing as of 2026-05-10.
# Update when OpenAI changes the table — there is no programmatic feed.
_PRICES: dict[str, dict[str, float]] = {
    "gpt-5.4": {"text_input": 2.50, "text_cached_input": 1.25, "text_output": 15.00},
    "gpt-5.4-mini": {"text_input": 0.75, "text_cached_input": 0.075, "text_output": 4.50},
    "gpt-5.5": {"text_input": 2.50, "text_cached_input": 1.25, "text_output": 15.00},
    "gpt-image-1": {
        "text_input": 5.00,
        "image_input": 10.00,
        "image_output": 40.00,
    },
    "gpt-image-1-mini": {
        "text_input": 2.00,
        "text_cached_input": 0.20,
        "image_input": 2.50,
        "image_cached_input": 0.25,
        "image_output": 8.00,
    },
    "gpt-image-2": {
        "text_input": 5.00,
        "text_cached_input": 1.25,
        "image_input": 8.00,
        "image_cached_input": 2.00,
        "image_output": 30.00,
    },
}


@dataclass
class ImageResult:
    image_bytes: bytes
    mime_type: str = "image/png"


@dataclass
class CallRecord:
    model: str
    kind: str  # "text" | "image"
    usage: dict[str, int]  # normalised counters
    cost_usd: float | None  # None when the model is missing from _PRICES


@dataclass
class UsageTracker:
    """Collects per-call usage and cost across one CLI command run."""

    calls: list[CallRecord] = field(default_factory=list)

    def add(self, record: CallRecord) -> None:
        self.calls.append(record)

    @property
    def total_cost_usd(self) -> float:
        return sum(c.cost_usd or 0.0 for c in self.calls)

    @property
    def has_unknown_model(self) -> bool:
        return any(c.cost_usd is None for c in self.calls)

    def summary(self) -> dict[str, Any]:
        """Per-model aggregate suitable for archive YAML."""
        agg: dict[str, dict[str, Any]] = {}
        for c in self.calls:
            slot = agg.setdefault(
                c.model, {"calls": 0, "usd": 0.0, "tokens": {}}
            )
            slot["calls"] += 1
            slot["usd"] += c.cost_usd or 0.0
            for k, v in c.usage.items():
                slot["tokens"][k] = slot["tokens"].get(k, 0) + v
        return {
            "per_model": agg,
            "total_usd": round(self.total_cost_usd, 6),
            "call_count": len(self.calls),
        }


def _compute_cost(model: str, kind: str, usage: dict[str, int]) -> float | None:
    rates = _PRICES.get(model)
    if rates is None:
        return None
    cost = 0.0
    if kind == "text":
        cached = usage.get("prompt_cached_tokens", 0)
        billable = usage.get("prompt_tokens", 0) - cached
        cost += billable * rates.get("text_input", 0.0) / 1_000_000
        cost += cached * rates.get("text_cached_input", 0.0) / 1_000_000
        cost += usage.get("completion_tokens", 0) * rates.get("text_output", 0.0) / 1_000_000
    elif kind == "image":
        text_in = usage.get("text_tokens", 0)
        image_in = usage.get("image_tokens", 0)
        cached = usage.get("cached_tokens", 0)
        billable_image = max(image_in - cached, 0)
        cost += text_in * rates.get("text_input", 0.0) / 1_000_000
        cost += billable_image * rates.get("image_input", 0.0) / 1_000_000
        cost += cached * rates.get("image_cached_input", 0.0) / 1_000_000
        cost += usage.get("output_tokens", 0) * rates.get("image_output", 0.0) / 1_000_000
    return cost


def _emit_call_log(record: CallRecord) -> None:
    """One-line stderr log per API call. Dim so the main flow stays readable."""
    if record.cost_usd is None:
        cost_str = "$? (model not in price table)"
    else:
        cost_str = f"${record.cost_usd:.4f}"
    pieces = ", ".join(f"{k}={v}" for k, v in record.usage.items() if v)
    sys.stderr.write(
        f"\x1b[2m[cost]\x1b[0m {record.model} ({record.kind}): "
        f"{pieces or '(no usage)'} → {cost_str}\n"
    )


class OpenAIClient:
    def __init__(
        self,
        *,
        api_key: str,
        text_model: str,
        image_model: str,
        timeout: float = 120.0,
        usage_tracker: UsageTracker | None = None,
    ) -> None:
        self.client = OpenAI(api_key=api_key, timeout=timeout)
        self.text_model = text_model
        self.image_model = image_model
        self.usage_tracker = usage_tracker

    def _record_text(self, response: Any) -> None:
        usage = getattr(response, "usage", None)
        if usage is None:
            return
        details = getattr(usage, "prompt_tokens_details", None)
        normalised = {
            "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
            "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
            "prompt_cached_tokens": (getattr(details, "cached_tokens", 0) or 0)
            if details
            else 0,
        }
        cost = _compute_cost(self.text_model, "text", normalised)
        record = CallRecord(self.text_model, "text", normalised, cost)
        _emit_call_log(record)
        if self.usage_tracker is not None:
            self.usage_tracker.add(record)

    def _record_image(self, response: Any) -> None:
        usage = getattr(response, "usage", None)
        if usage is None:
            return
        details = getattr(usage, "input_tokens_details", None)
        normalised = {
            "input_tokens": getattr(usage, "input_tokens", 0) or 0,
            "output_tokens": getattr(usage, "output_tokens", 0) or 0,
            "text_tokens": (getattr(details, "text_tokens", 0) or 0) if details else 0,
            "image_tokens": (getattr(details, "image_tokens", 0) or 0) if details else 0,
            "cached_tokens": (getattr(details, "cached_tokens", 0) or 0) if details else 0,
        }
        cost = _compute_cost(self.image_model, "image", normalised)
        record = CallRecord(self.image_model, "image", normalised, cost)
        _emit_call_log(record)
        if self.usage_tracker is not None:
            self.usage_tracker.add(record)

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
        self._record_text(response)
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
        self._record_text(response)
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
                self._record_image(response)
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
