# Linux Mint Installer Support Implementation Plan

> Steps use checkbox (`- [ ]`) syntax.

**Goal:** `install.sh` installs Mochi's system dependencies with apt on Linux Mint / Ubuntu / Debian, and its summary stops naming the GNOME app grid.

**Spec:** `docs/superpowers/specs/2026-10-25-linux-mint-installer-design.md`

## Global Constraints

- Fedora path unchanged and checked first.
- No `src/` changes; `dependencies = []` stays.
- Test command: `python3 -m pytest -q`.
- Baseline on `main` (`4713426`): 1370 passed, 6 skipped.

## File Map

| File | Change | Task |
|---|---|---|
| `tests/test_installer.py` | Toolbox can fake apt tooling; new apt tests | 1 |
| `install.sh` | apt branch; generic "applications menu" | 2 |
| `README.md`, `CHANGELOG.md`, `REGRESSION_WATCHLIST.md` | Mint documented; QA lines | 3 |

## Task 1: Failing tests

- [ ] Add `package_manager: str = "dnf"` to `_make_toolbox`/`_run_installer` (`"dnf"`, `"apt"`, `"none"`), plus `apt_missing` and `apt_available` sets surfaced via env vars to fake `dpkg-query`/`apt-cache`; fake `sudo` execs its arguments.
- [ ] Tests: missing packages installed; nothing missing → no apt call; layer shell only when available; gnome-shell only on GNOME; summary says "applications menu".
- [ ] Run, confirm they fail.

## Task 2: Installer

- [ ] Add the `elif command -v apt-get … && command -v dpkg-query …` branch with the spec's package map.
- [ ] Update the unsupported-manager warning and the summary line.
- [ ] Run the full suite.

## Task 3: Docs

- [ ] README install/compatibility sections mention Linux Mint.
- [ ] CHANGELOG Unreleased entry; REGRESSION_WATCHLIST install lines.
