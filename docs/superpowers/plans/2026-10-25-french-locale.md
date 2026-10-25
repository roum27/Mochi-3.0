# French Locale Implementation Plan

> Steps use checkbox (`- [ ]`) syntax.

**Goal:** Mochi speaks and labels his user-facing UI in French on a French locale.

**Spec:** `docs/superpowers/specs/2026-10-25-french-locale-design.md`

## Global Constraints

- English is the source and the default; French is a lookup keyed by exact English text.
- No new dependency, no network, `i18n.py` imports no GTK.
- Developer (Mochi Lab) controls, logs, and CLI stay English.
- Test command: `python3 -m pytest -q`. Existing tests are pinned to English by `tests/conftest.py`.

## File Map

| File | Change | Task |
|---|---|---|
| `src/mochi/i18n.py` (new), `tests/test_i18n.py` (new), `tests/conftest.py` (new) | Language resolution + `tr()` | 1 |
| `src/mochi/locale/{__init__,fr,fr_phrases,fr_ui}.py` (new) | Catalogue | 2 |
| `src/mochi/presence/bubble.py`, `src/mochi/presence/nameplate.py` | Speech/nameplate choke points | 3 |
| Menu/window modules | `tr()` around user-facing labels and templates | 4 |
| `README.md`, `CHANGELOG.md`, `REGRESSION_WATCHLIST.md` | Docs | 5 |

## Tasks

- [ ] **1.** Failing tests for `language_from_environment`, `tr`, then implement `i18n.py`.
- [ ] **2.** Catalogue plus coverage tests (every phrase translated, every key real, placeholders match).
- [ ] **3.** Bubble/nameplate translate; unit tests with French active.
- [ ] **4.** Wrap labels: buddy menu, integration toggles, edge roam, feeding, quick start, focus, catalogue, emotes, bond meter/overlay, pocket, update menu row (the updater package itself stays English). Convert formatted f-strings to `tr(template).format`.
- [ ] **5.** Docs; full suite; `git diff --check`.
