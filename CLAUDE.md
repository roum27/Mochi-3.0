# CLAUDE.md — Mochi 3.0

Mochi is a local-first Linux desktop companion: Python 3.11+, GTK4, PyGObject, Cairo.

The maintainer speaks French (Québec, `LANG=fr_CA.UTF-8`). Reply in French. Code, comments, commits and docs stay in English.

## What this fork is

`roum27/Mochi-3.0` is a fork of `miflow13/mochi-desktop` (v0.4.1, MIT). The original's `AGENTS.md` was merged into this file on 2026-10-25.

**Primary target:** Linux Mint 22 + Cinnamon 6 + X11. On X11, GDK is left alone.

**GNOME and Fedora are still supported:**
- Keep them working; every inherited test must still pass.
- On GNOME Wayland, the whole process runs with `GDK_BACKEND=x11` (XWayland), set in `src/mochi/main.py`. Do not change that.

## Read before changing runtime code

- `docs/CODEBASE_MANUAL.md`, especially section 2, "The five rules":
  - one behavior-state path through `Buddy._transition_to`;
  - state is not animation;
  - direct interaction outranks ambient behavior;
  - every long-lived thing has an owner and a teardown;
  - Mochi must always become interactable again.
- The `REGRESSION_WATCHLIST.md` sections for every area you touch.
- `docs/ambisense.md` for the privacy model.
- `docs/superpowers/specs` and `docs/superpowers/plans` for the spec and plan format.

## Product rules (non-negotiable)

- **Local only.** New features make no network requests and add no telemetry. The only network use is the opt-in updater, which reaches this fork's GitHub repository and nothing else.
- **No pressure.** No streaks, decay, penalties, or guilt-based copy.
- **Easy to ignore.** New speech respects `speech_enabled`, quiet mode, and presentation priority.
- **Privacy.**
  - Never read typed content, window titles, document names, or clipboard contents unless the user explicitly hands them to Mochi.
  - The desktop helpers may look at a title only to reduce it inside the shell, to a boolean or a digest.

## Engineering rules

- **One reviewable diff per task.** One task = one feature. No drive-by refactors, renames, or reformatting.
- **No new runtime dependencies.** `pyproject.toml` has `dependencies = []`; PyGObject comes from the system. Pillow is dev-only, for `tools/`.
- **Speech:**
  - New speech goes through `PresenceEngine` (`src/mochi/presence/engine.py`). New code never calls the speech bubble directly.
  - Never pass text that did not originate in Mochi's own source code to any `markup=` parameter.
- **Lifecycle (Manual rule 4).** Every long-lived source — GLib timeout, signal handler, D-Bus subscription, settings watch, helper connection or hotkey — has one owner and is torn down on shutdown or `disable()`.
- **Testability.**
  - Keep logic GTK-free where possible, so it is testable without a display.
  - Follow the existing injection patterns, such as `portal_factory` in `src/mochi/color_scheme.py` and the adapters in `src/mochi/presence/signals.py`.
- **Protected areas.** Do not touch the updater, `src/mochi_launcher.py`, or GDK backend selection unless the task says so.

## Workflow for feature tasks

1. Read the relevant code and the docs above.
2. Write a spec (`docs/superpowers/specs/YYYY-MM-DD-<slug>-design.md`) and a plan (`docs/superpowers/plans/YYYY-MM-DD-<slug>.md`) that match the existing files.
3. Raise any disagreement with the task design at this point, not mid-implementation.
   - Wait for approval, unless the maintainer has already said to go ahead. They usually say "fait tout" and want a short briefing at the end.
   - Ask before deleting files or making large or outward-facing changes, such as a push or a release.
4. Test-first, small commits. One branch per feature (`claude/<slug>`), fast-forwarded into `main`.

## Verification and the final report

- **Tests:** run `python3 -m pytest -q` and report the actual summary line.
- **Desktop QA:**
  - Never claim that desktop or visual QA passed.
  - You can verify helpers over D-Bus and in the logs (see Commands).
  - List exact manual QA steps for the maintainer instead.
- **Docs:** user-facing changes update `CHANGELOG.md` (Unreleased), `README.md` if usage or controls change, and `REGRESSION_WATCHLIST.md`.
- **Final report:** a short French briefing covering:
  - a summary;
  - files changed;
  - tests added;
  - the test result;
  - what is unverified;
  - risks;
  - follow-ups you noticed but did not do.

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
  - The updater uses unauthenticated GitHub API calls. The fork has been public since 2026-10-25.
  - At the maintainer's request, the default channel is `main` (`DEFAULT_UPDATE_CHANNEL`): every push to `main` reaches users through **Check for updates**, so only push what is ready. `release` is opt-in and needs a published GitHub release (a tag, not a prerelease).

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

- **Tests:** `.venv/bin/python -m pytest -q`. The repo `.venv` is gitignored. Create it with `python3 -m venv --system-site-packages .venv && .venv/bin/pip install -e . pytest`; `--system-site-packages` keeps `gi` importable, and pytest is not a system package on Mint. Baseline: 1429 passed, 6 skipped.
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
