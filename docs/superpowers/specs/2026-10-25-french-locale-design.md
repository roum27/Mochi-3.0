# French Locale — Design

**Date:** 2026-10-25

**Builds on:** Linux Mint installer support (`2026-10-25-linux-mint-installer-design.md`)

**Status:** approved by the requester ("met le en francais … fait tout") and implemented on `claude/french-locale`.

## Purpose

Mochi speaks and labels everything in English. The requester runs Linux Mint with `LANG=fr_CA.UTF-8` and wants Mochi in French. Mochi has no localization layer today.

## Goals

- Mochi shows French on a French system locale and English everywhere else. English stays the source language and the default.
- Override with `MOCHI_LANGUAGE=fr` or `MOCHI_LANGUAGE=en`.
- French covers:
  - everything Mochi says: phrase bank, bond dialogue, event and context phrases, click/drag/feed/focus/Fedora/update/Pocket speech, and the intro;
  - the right-click menu and its user-facing toggles;
  - the Quick Start, Focus, Emote Catalogue and Pocket windows, plus the update menu row;
  - bond level-up cards and XP labels;
  - nameplate feedback.
- No new dependency (no gettext `.mo` build step), no network, no GTK in the lookup logic.

## Non-goals

- Mochi Lab developer controls and bond-testing tools stay English. They are QA tools behind a developer shortcut.
- The updater window (`src/mochi/update/`). The bootstrap copies that package on its own, so it cannot import `mochi.i18n` (see `test_real_bootstrap_package_imports_without_rest_of_mochi`), and AGENTS.md keeps the updater out of scope.
- Log messages, CLI help (`mochi --help`, `mochi-update`), D-Bus names, and the GNOME extension stay English.
- A language picker in the menu. The locale and the env override are enough for v1.
- Other languages. The layer allows them, but none ship.

## Design

### `src/mochi/i18n.py` (GTK-free)

- `language_from_environment(env) -> "en" | "fr"`:
  - `MOCHI_LANGUAGE` wins when it names a supported language.
  - Otherwise the first non-empty of `LANGUAGE` (first entry), `LC_ALL`, `LC_MESSAGES` and `LANG` decides.
  - `C`/`POSIX` and unknown languages mean `"en"`.
- `active_language()` resolves once and caches. `set_language(code | None)` exists for tests; `None` re-detects.
- `tr(text) -> str` returns the French catalogue entry for the exact English text when French is active, otherwise `text` unchanged. A missing entry falls back to English, so a new English string can never crash or blank the UI.

### Catalogue

- `src/mochi/locale/fr.py` exposes `FR: dict[str, str]`, keyed by the exact English source.
- It is assembled from `fr_phrases.py` (speech) and `fr_ui.py` (windows and menus).
- Templates keep their `{named}` placeholders, so call sites become `tr("Bond Lv. {level}").format(level=…)`.
- The intro's text and markup entries are built in code from translated lines with `html.escape`, exactly like `INTRO_MARKUP`. All catalogue values are Mochi source code, so the markup rule holds.

### Where translation happens

- **Speech:** `MochiSpeechBubble.show()` translates `text` and `markup` once, after the typing-preview hint is read. That single choke point covers every speech path, including ones added later. Phrase selection, recency and cooldowns keep working on the English keys.
- **Nameplate feedback:** `Nameplate.set_status()` translates the same way.
- **Formatted copy** (counts, levels, times): wrapped at the call site with `tr(template).format(...)`, because the formatted result cannot be a catalogue key.
- **Static widget labels:** wrapped at the call site with `tr("…")`.

## Testing

- **`tests/test_i18n.py`:**
  - environment resolution, override, caching and fallback;
  - every phrase in `PHRASES`, `CONTEXT_PHRASES`, `EVENT_PHRASES`, `BOND_DIALOGUE` and the focus/update/Fedora/click lines has a French entry;
  - every catalogue key occurs in Mochi's source, so there are no typo keys;
  - placeholders match between each key and its value;
  - values are non-empty;
  - French phrase lines keep the lowercase house style wherever the English is lowercase.
- **Bubble/nameplate unit tests:** French in, French out; English locale unchanged.
- **`tests/conftest.py`:** pins English for the existing suite, which runs under the requester's `fr_CA` locale.

## Risks

- **Speech timing:** `speech_display_seconds()` is computed from the English text, and French is usually 10–25 % longer. Accepted: the display minimum already covers short lines.
- **Width:** longer French labels can widen fixed-width windows. Manual QA covers the Quick Start, Focus, Catalogue and Pocket windows.
