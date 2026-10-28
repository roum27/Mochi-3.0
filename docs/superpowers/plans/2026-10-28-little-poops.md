# Little Poops Implementation Plan

> Steps use checkbox (`- [ ]`) syntax.

**Goal:** Mochi sometimes leaves a small poop on the screen beside him; the user clicks it to clean it up.

**Spec:** `docs/superpowers/specs/2026-10-28-little-poops-design.md`

## Global Constraints

- No new dependency, no asset file, no network.
- `src/mochi/droppings.py` imports no GTK (Cairo only, like `bond_orbs.py`).
- One owned recurring timer; every poop window is destroyed on disable and shutdown.
- No effect on mood, bond, XP or speech.
- Test command: `.venv/bin/python -m pytest -q`.

## File Map

| File | Change | Task |
|---|---|---|
| `src/mochi/droppings.py` (new), `tests/test_droppings.py` (new) | Schedule, placement, Cairo drawing | 1 |
| `src/mochi/config.py` | `load_droppings_enabled` / `save_droppings_enabled` | 2 |
| `src/mochi/presence/droppings.py` (new), `src/mochi/presence/click_dialogue.py` | Poop window, mixin, composition | 3 |
| `src/mochi/locale/fr_ui.py` | French labels | 3 |
| `README.md`, `CHANGELOG.md`, `REGRESSION_WATCHLIST.md` | Docs | 4 |

## Tasks

- [ ] **1.** Write failing tests for the schedule, placement and drawing, then implement `droppings.py`.
- [ ] **2.** Write failing config default/round-trip/fallback tests, then implement them in `ConfigStore`.
- [ ] **3.** Write failing mixin tests (eligibility, cap, cleaning, toggle, shutdown, unsupported paths, MRO), then implement the window and mixin, wire them into both buddies, and add the French entries.
- [ ] **4.** Update the docs, run the full suite, and run `git diff --check`.
