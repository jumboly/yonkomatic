"""_load_batch_job_meta against tmp_path-rooted manifest files.

Why monkeypatch.chdir: the helper opens ``state/batches/{week}.yaml`` as a
CWD-relative Path. Without chdir-isolation the test would read the
repository's real state/batches and could pass by accident.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from yonkomatic.cli import _load_batch_job_meta


def _write_manifest(tmp_path: Path, week: str, payload: dict) -> Path:
    manifest_dir = tmp_path / "state" / "batches"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    path = manifest_dir / f"{week}.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def test_returns_none_when_week_is_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    assert _load_batch_job_meta(None, 1) is None


def test_returns_none_when_manifest_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    assert _load_batch_job_meta("2026-W19", 1) is None


def test_returns_job_meta_for_existing_episode(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_manifest(
        tmp_path,
        "2026-W19",
        {
            "week": "2026-W19",
            "batch_id": "batch_abc",
            "jobs": [
                {"custom_id": "2026-W19-ep1", "episode_number": 1, "title": "ep1 title"},
                {"custom_id": "2026-W19-ep2", "episode_number": 2, "title": "ep2 title"},
            ],
        },
    )
    meta = _load_batch_job_meta("2026-W19", 2)
    assert meta is not None
    assert meta["custom_id"] == "2026-W19-ep2"
    assert meta["title"] == "ep2 title"


def test_returns_none_for_missing_episode_number(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_manifest(
        tmp_path,
        "2026-W19",
        {
            "week": "2026-W19",
            "jobs": [{"custom_id": "ep1", "episode_number": 1, "title": "t"}],
        },
    )
    assert _load_batch_job_meta("2026-W19", 99) is None


def test_handles_empty_manifest(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Why: an empty/half-written manifest should not raise KeyError; missing
    # ``jobs:`` must be treated as "no match" so callers fall back gracefully.
    monkeypatch.chdir(tmp_path)
    _write_manifest(tmp_path, "2026-W19", {})
    assert _load_batch_job_meta("2026-W19", 1) is None


def test_retries_block_does_not_break_lookup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Why: Step 7b appends a ``retries[]`` array alongside ``jobs[]``. The
    # helper must keep scanning only ``jobs[]``; a retry custom_id with the
    # same episode_number must not be returned in place of the original job.
    monkeypatch.chdir(tmp_path)
    _write_manifest(
        tmp_path,
        "2026-W19",
        {
            "week": "2026-W19",
            "jobs": [
                {"custom_id": "primary-ep1", "episode_number": 1, "title": "primary"},
            ],
            "retries": [
                {
                    "batch_id": "batch_retry_1",
                    "custom_ids": ["retry-ep1"],
                    "results": [
                        {"custom_id": "retry-ep1", "episode_number": 1, "title": "retry"}
                    ],
                }
            ],
        },
    )
    meta = _load_batch_job_meta("2026-W19", 1)
    assert meta is not None
    assert meta["custom_id"] == "primary-ep1"
