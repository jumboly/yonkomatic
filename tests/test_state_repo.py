"""StateStore atomic save / append round-trip on tmp_path."""

from __future__ import annotations

from pathlib import Path

from yonkomatic.state.repo import HistoryEntry, StateData, StateStore


def _entry(
    *, episode_number: int = 1, week: str | None = "2026-W19", date: str = "2026-05-09"
) -> HistoryEntry:
    return HistoryEntry(
        episode_number=episode_number,
        week=week,
        date=date,
        title=f"episode {episode_number}",
    )


def test_load_returns_default_when_missing(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "absent.yaml")
    data = store.load()
    assert data == StateData()


def test_save_then_load_roundtrip(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.yaml")
    original = StateData(
        last_published_episode=3,
        current_week_index="2026-W19",
        history=[_entry(episode_number=3)],
    )
    store.save(original)
    assert store.load() == original


def test_save_is_atomic_no_tempfile_remains(tmp_path: Path) -> None:
    # Why: StateStore.save uses mkstemp + os.replace. After a clean save the
    # sibling temp file (".state.yaml.<rand>") must be gone — its presence
    # would mean an exception path leaked the tempfile.
    path = tmp_path / "state.yaml"
    StateStore(path).save(StateData(last_published_episode=1))
    leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(".state.yaml.")]
    assert leftovers == []


def test_append_updates_last_published_and_history(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.yaml")
    entry = _entry(episode_number=5)
    data = store.append(entry)
    assert data.last_published_episode == 5
    assert data.history[-1] == entry
    assert store.load().history[-1] == entry


def test_append_preserves_existing_history(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.yaml")
    store.append(_entry(episode_number=1, week="2026-W18"))
    data = store.append(_entry(episode_number=2, week="2026-W19"))
    assert [e.episode_number for e in data.history] == [1, 2]
    assert data.current_week_index == "2026-W19"


def test_append_keeps_week_when_entry_week_is_none(tmp_path: Path) -> None:
    # Why: append only updates current_week_index when entry.week is non-None,
    # so a week-less entry must not clobber the previously recorded week.
    store = StateStore(tmp_path / "state.yaml")
    store.append(_entry(episode_number=1, week="2026-W18"))
    data = store.append(_entry(episode_number=2, week=None))
    assert data.current_week_index == "2026-W18"


def test_save_creates_parent_dir(tmp_path: Path) -> None:
    nested = tmp_path / "nested" / "deep" / "state.yaml"
    StateStore(nested).save(StateData(last_published_episode=1))
    assert nested.exists()
