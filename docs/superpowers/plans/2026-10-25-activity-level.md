# Activity Level Implementation Plan

> Steps use checkbox (`- [ ]`) syntax.

**Goal:** a persistent Calm / Lively / Energetic **Activity** row in the right-click menu that tunes Mochi's autonomous idle cadence.

**Spec:** `docs/superpowers/specs/2026-10-25-activity-level-design.md`

## Global Constraints

- **Calm** is the default and matches today's constants exactly.
- No new dependency, no network, and no new long-lived GLib source. The level only feeds Buddy's existing idle path.
- `src/mochi/activity_level.py` imports no GTK.
- Test command: `.venv/bin/python -m pytest -q`.

## File Map

| File | Change | Task |
|---|---|---|
| `src/mochi/activity_level.py` (new), `tests/test_activity_level.py` (new) | Profiles, normalization, cycling | 1 |
| `src/mochi/config.py` | `load_activity_level` / `save_activity_level` | 2 |
| `src/mochi/buddy.py` | `WALK_DISTANCE_PX` constant used by `_start_walk` | 3 |
| `src/mochi/presence/activity_controls.py` (new), `src/mochi/presence/click_dialogue.py` | Menu row mixin and composition | 4 |
| `src/mochi/locale/fr_ui.py` | French labels | 4 |
| `README.md`, `CHANGELOG.md`, `REGRESSION_WATCHLIST.md`, `src/mochi/quick_start.py` | Docs | 5 |

## Tasks

- [ ] **1.** Write failing tests for the profiles, the calm/Buddy parity, normalization and cycling, then implement `activity_level.py`.
- [ ] **2.** Write failing config round-trip and fallback tests, then implement them in `ConfigStore`.
- [ ] **3.** Write a failing test that `_start_walk` draws its distance from `WALK_DISTANCE_PX`, then add the constant.
- [ ] **4.** Write failing mixin tests (apply, toggle cycles and saves, reschedule a pending idle action, MRO placement), then implement the mixin, wire it into both buddies, and add the French entries.
- [ ] **5.** Update the docs, run the full suite, and run `git diff --check`.
