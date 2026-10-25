# Linux Mint Installer Support — Design

**Date:** 2026-10-25

**Status:** approved by the requester ("ok go … fait tout") and implemented on `claude/linux-mint-installer`.

## Purpose

`install.sh` only knows how to install system dependencies with `dnf`. On Linux Mint (and other Debian/Ubuntu derivatives) it prints "Automatic dependency installation currently supports Fedora only" and carries on, so a fresh Mint machine fails later with an opaque PyGObject/GTK4 error. The install summary also points Cinnamon users at the "GNOME app grid", which does not exist there.

Mochi itself already runs on Mint: Cinnamon is an X11 session, so `configure_display_backend()` leaves GDK alone and the existing X11 window path is used. Only the installer and docs need to learn about it.

## Goals

- When `apt-get` and `dpkg-query` are available (and `dnf`/`rpm` are not), install the Debian/Ubuntu equivalents of the Fedora dependency list with `sudo apt-get install -y`, only for packages that are missing.
- Install `gir1.2-gtk4layershell-1.0` only when the archive offers it (`apt-cache show` succeeds). Ubuntu 24.04 / Mint 22 do not ship it, and Mochi already treats layer shell as optional.
- Never pull `gnome-shell` onto a non-GNOME Debian desktop. On a GNOME Debian/Ubuntu desktop, add `gnome-shell`, mirroring Fedora.
- Replace "GNOME app grid → Mochi" with "applications menu → Mochi" so the summary is true on every desktop.
- Document Linux Mint (Cinnamon, X11) as a supported install path in README and the changelog.

## Non-goals

- A Cinnamon replacement for the GNOME Shell helper (typing pulses, idle, global shortcuts). That is a separate, much larger feature.
- Any runtime code change. `src/` is untouched.
- Other package managers (pacman, zypper).
- Changing the Fedora path. Fedora is still checked first and behaves byte-for-byte as before.

## Package map

| Fedora | Debian / Ubuntu / Mint | Notes |
|---|---|---|
| `python3` | `python3` | |
| `python3-pip` | `python3-venv` | Debian splits `ensurepip` out; the private venv needs it to get pip. |
| `python3-gobject` | `python3-gi` | |
| `python3-cairo` | `python3-gi-cairo`, `python3-cairo` | `gi-cairo` is the foreign-struct glue Cairo drawing needs. |
| `gtk4` | `gir1.2-gtk-4.0` | Pulls `libgtk-4-1`. |
| `gtk4-layer-shell` | `gir1.2-gtk4layershell-1.0` | Only when available. |
| `gstreamer1`, `gstreamer1-plugins-base` | `gir1.2-gstreamer-1.0`, `gstreamer1.0-plugins-base` | |
| `libX11` | `libx11-6` | |
| `xorg-x11-server-Xwayland` | — | Not needed on X11 Cinnamon; Ubuntu GNOME ships it by default. |
| `pipewire-utils` | `pipewire-bin` | Provides `pw-play`; `paplay` is the existing fallback. |
| `glib2` | `libglib2.0-bin` | Provides `gdbus`/`glib-compile-schemas` used by the helper path. |
| — | `gir1.2-atspi-2.0` | Typing-activity fallback backend imports `Atspi`. |
| `gnome-shell` (GNOME only) | `gnome-shell` (GNOME only) | |

## Behavior

- Detection order: `dnf`+`rpm` → `apt-get`+`dpkg-query` → warn and continue (message now says "Fedora and Debian/Ubuntu/Linux Mint").
- A package is "installed" when `dpkg-query -W -f='${Status}'` reports `install ok installed`.
- When nothing is missing the installer prints "Required Debian/Ubuntu packages are already installed" and never invokes `sudo`.
- The step runs in the same place as the Fedora step, so `--stage-runtime` and `--refresh-integrations` behave exactly as they do on Fedora today.

## Testing

Behavioral tests in `tests/test_installer.py` with fake `apt-get`, `apt-cache`, `dpkg-query` and `sudo`:
- Missing packages are passed to `apt-get install -y`; installed ones are not.
- Nothing missing → `apt-get` is never called.
- Layer shell is requested only when `apt-cache show` finds it.
- `gnome-shell` is requested only on GNOME.
- Fedora tooling wins when both are present (existing tests keep `dnf` in the toolbox).
- The summary says "applications menu".

## Manual QA (maintainer)

On a fresh Linux Mint 22.x Cinnamon VM: run `./install.sh`, confirm the apt prompt lists only missing packages, launch Mochi from the Cinnamon menu, drag him, right-click him, and confirm he stays on top across workspaces.
