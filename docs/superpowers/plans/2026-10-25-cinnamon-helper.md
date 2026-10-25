# Cinnamon Awareness Helper Implementation Plan

> Steps use checkbox (`- [ ]`) syntax.

**Goal:** A Cinnamon extension that speaks the GNOME helper's D-Bus protocol, installed and enabled by `install.sh` on Cinnamon.

**Spec:** `docs/superpowers/specs/2026-10-25-cinnamon-helper-design.md`

## Global Constraints

- No `src/` changes. Same bus name, object path, interface, signals, payloads, constants, and privacy reductions as `gnome-extension/mochi-typing@miflow13/extension.js`.
- Every source created in `enable()` is removed in `disable()`.
- Test command: `python3 -m pytest -q`. Baseline on `claude/french-locale` (`1e4ea37`): 1407 passed, 6 skipped.

## File Map

| File | Change | Task |
|---|---|---|
| `tests/test_cinnamon_helper.py` (new) | Static parity/privacy/teardown/syntax checks | 1 |
| `cinnamon-extension/mochi-activity@miflow13/{metadata.json,extension.js,README.md}` (new) | The helper | 2 |
| `scripts/install-cinnamon-extension.sh` (new), `install.sh`, `uninstall.sh`, `tests/test_installer.py` | Install/enable/remove | 3 |
| `README.md`, `CHANGELOG.md`, `REGRESSION_WATCHLIST.md`, `docs/ambisense.md` | Docs | 4 |

## Tasks

- [ ] **1.** Write `test_cinnamon_helper.py`; it fails (no extension yet).
- [ ] **2.** Port the extension; tests pass.
- [ ] **3.** Installer tests (Cinnamon runs helper script; gsettings list add/reload; uninstall removes), then the scripts.
- [ ] **4.** Docs; full suite; `git diff --check`; install on the requester's Mint and confirm the bus name + `GetState` with `gdbus`.
