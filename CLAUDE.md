# CLAUDE.md — Mochi 3.0

**Read `AGENTS.md` first.** Its product rules, engineering rules, feature workflow (spec → plan → approval → test-first) and verification/final-report rules apply here unchanged. This file only adds what is specific to this fork.

The maintainer speaks French (Québec, `LANG=fr_CA.UTF-8`). Reply in French. Code, comments, commits and docs stay in English, matching the repo.

## What this fork is

`roum27/Mochi-3.0` is a fork of `miflow13/mochi-desktop` (the `origin` upstream, v0.4.1). The primary target here is **Linux Mint 22 + Cinnamon 6 + X11**, not Fedora/GNOME/Wayland. Keep GNOME and Fedora working anyway: every upstream test still has to pass.

Fork additions, one feature per commit with a spec and plan in `docs/superpowers/` dated 2026-10-25:

1. **apt support in `install.sh`** (Mint/Ubuntu/Debian):
   - The package map is in the spec.
   - `gir1.2-gtk4layershell-1.0` is requested only when `apt-cache` has it. Mint 22 does not.
2. **French locale:**
   - `src/mochi/i18n.py` provides `tr()`, keyed by the exact English source text.
   - Catalogues live in `src/mochi/locale/fr_phrases.py` (speech) and `fr_ui.py` (menus and windows), assembled in `fr.py`.
   - `MOCHI_LANGUAGE=en|fr` overrides the locale.
3. **Cinnamon helper:**
   - `cinnamon-extension/mochi-activity@miflow13/` is a CJS port of `gnome-extension/mochi-typing@miflow13`.
   - It has the same D-Bus name, signals and privacy reductions, so `src/` has no Cinnamon code.
   - `scripts/install-cinnamon-extension.sh` installs it to `~/.local/share/cinnamon/extensions/` and toggles `org.cinnamon enabled-extensions`. Cinnamon loads it live, with no logout.

## Rules learned in this fork

### Translation

- **New user-facing copy:** wrap it in `tr()` and add the French entry.
  - Formatted text uses `tr("Lv. {level}").format(level=…)`, never an f-string inside `tr()`.
  - `tests/test_i18n.py` fails when a literal passed to `tr()` has no French entry, when a key is not real source text, or when placeholders differ.
- **Speech:**
  - It is translated once in `SpeechBubble.show()`, and nameplate feedback in `Nameplate.set_status()`. Do not translate again upstream; phrase recency and cooldowns work on the English keys.
  - French speech keeps Mochi's voice: lowercase, short, informal "tu", gender-neutral toward the user. Mochi himself is masculine.
- **Out of scope:** Mochi Lab developer controls stay English.
- **Test locale:** `tests/conftest.py` pins English for every test. Use `i18n.set_language("fr")` inside a test to exercise French.

### The updater

- **Never import anything from `src/mochi/update/`** — `mochi.i18n` included. The bootstrap copies that package on its own (`test_real_bootstrap_package_imports_without_rest_of_mochi`). That is why the updater window stays English.
- **Update source:** at the maintainer's request (2026-10-25), `OFFICIAL_REPOSITORY` in `src/mochi/update/constants.py` is `roum27/Mochi-3.0`. Updates must never come from upstream again; do not reintroduce `miflow13/mochi-desktop` anywhere in the update path.
  - The updater uses unauthenticated GitHub API calls, so it only works once the fork is public.
  - The default `release` channel needs a published GitHub release on the fork (a tag, not a prerelease). Until then, checks fail quietly; `mochi-update --channel main` follows every push to `main`.

### The Cinnamon helper

- **Keep the two helpers in step.** Change the GNOME and Cinnamon helpers together. `tests/test_cinnamon_helper.py` enforces:
  - the same signal names and `*_MS` constants;
  - a superset of the GNOME classification markers;
  - no key identity or logging;
  - `get_title()` used only in the YouTube check and the tab digest;
  - full teardown in `disable()`;
  - a `cjs` parse check.
- **Muffin equivalents:**

  | GNOME | Muffin |
  |---|---|
  | `global.backend` | `Meta.get_backend()` |
  | `get_core_idle_monitor()` | `Meta.IdleMonitor.get_core()` |
  | `Main.wm.addKeybinding` | `Main.keybindingManager.addHotKey` / `removeHotKey` |
  | `export default class` | top-level `init`/`enable`/`disable` |

### Installer and uninstaller tests

- **Never let them reach real desktop settings.** They use a fake `gsettings` (`_write_gsettings` in `tests/test_installer.py`) and `GSETTINGS_BACKEND=memory`.
- **Desktop detection:** `install.sh` checks `*cinnamon*` before `*gnome*`.

## Commands

- **Tests:** `python3 -m pytest -q`. pytest is not a system package on Mint; use a venv created with `--system-site-packages` so `gi` stays importable. Current baseline: 1432 passed, 6 skipped.
- **Install locally:** `./install.sh`. Uninstall with `mochi-uninstall`.
- **Inspect the live Cinnamon session** (read-only probes; remove anything you attach):
  - `gdbus call --session --dest org.Cinnamon --object-path /org/Cinnamon --method org.Cinnamon.Eval '<js>'`
  - Extension logs are in `~/.xsession-errors`.
- **Check the helper:**
  - `gdbus call --session --dest io.github.mochi_desktop.Mochi.TypingMonitor --object-path /io/github/mochi_desktop/Mochi/TypingMonitor --method io.github.mochi_desktop.Mochi.TypingMonitor.GetState`
  - Watch its signals with `dbus-monitor --session "type='signal',interface='io.github.mochi_desktop.Mochi.TypingMonitor'"`.

You still cannot see the screen. Report what you verified over D-Bus or in the logs, and leave visual QA to the maintainer, with steps from `REGRESSION_WATCHLIST.md`.

## Git

- `origin` is the upstream `miflow13/mochi-desktop`. Never push there.
- `mochi3` (`git@github.com:roum27/Mochi-3.0.git`) is this fork. `main` is the branch to build on.
- Git has no global identity on this machine. Commit with `git -c user.name=michaelinux -c user.email=roum27@hotmail.com commit …`.
