# Cinnamon Awareness Helper — Design

**Date:** 2026-10-25

**Builds on:** Linux Mint installer support and French locale (same date). The GNOME Shell helper lives in `gnome-extension/mochi-typing@miflow13` and is documented in `docs/ambisense.md`.

**Status:** approved by the requester ("ok fait l'option B pour cinnamon") and implemented on `claude/cinnamon-helper`.

## Purpose

On GNOME, a tiny Shell extension owns the session-bus name `io.github.mochi_desktop.Mochi.TypingMonitor`. It emits content-free signals that Mochi reacts to:

- anonymous typing `Pulse`s;
- `UserIdle` / `UserActive`;
- file-browsing start and stop;
- focused-YouTube start and stop;
- coarse app category and focus pulses;
- browser tab pulses;
- the Emote Catalogue and developer-menu shortcuts.

On Cinnamon (Linux Mint) nothing owns that name, so Mochi runs with reduced awareness and no global shortcuts.

Cinnamon is a fork of GNOME Shell on Muffin, a fork of Mutter. Every API the GNOME helper relies on exists there under the same or a nearby name. This was checked on Cinnamon 6.6.9 by introspecting Muffin's `Meta-0` typelib and with a temporary probe in a live session. The probe recorded only device types and was removed afterwards. It saw:

| GNOME Shell | Cinnamon / Muffin | Verified |
|---|---|---|
| `global.backend` `last-device-changed` | `Meta.get_backend()` `last-device-changed` | Yes. XTEST Shift press reported `KEYBOARD_DEVICE`; pointer motion reported `POINTER_DEVICE`. |
| `global.backend.get_core_idle_monitor()` | `Meta.IdleMonitor.get_core()` (`get_idletime`, `add_idle_watch`, `add_user_active_watch`, `remove_watch`) | Yes |
| `global.display` `notify::focus-window` | Same property on `Meta.Display` | Yes |
| `Meta.Window` `get_gtk_application_id` / `get_wm_class` / `get_wm_class_instance` / `get_title`, `notify::title` | Same | Yes |
| `Main.wm.addKeybinding(name, settings, …)` | `Main.keybindingManager.addHotKey(name, "<Ctrl><Alt>e", cb)` / `removeHotKey(name)` | Yes |
| ES module `export default class … extends Extension` | Legacy CJS `init()` / `enable()` / `disable()` | Loader read in `extensionSystem.js` |

## Goals

- Add `cinnamon-extension/mochi-activity@miflow13/` (`metadata.json`, `extension.js`, `README.md`). It is a faithful port of the GNOME helper with the same:
  - bus name, object path, interface and `GetState` method;
  - signal names, payloads and timing constants;
  - privacy reductions.
- The Python side is unchanged: `HelperConnection` and the backends already speak this protocol.
- Shortcuts: `<Ctrl><Alt>e` opens the Emote Catalogue and `<Ctrl><Alt><Shift>m` opens Mochi Lab. Both are fixed, with no settings schema. Cinnamon has no per-extension gschema convention, and these are the GNOME defaults.
- Add Mint defaults to the classification lists:
  - terminals: `xfce4-terminal`, `mate-terminal`, `tilix`, `terminator`;
  - editors: Xed (`org.x.editor`, `xed`);
  - media: Xplayer (`xplayer`).

  Every GNOME marker is kept.
- `scripts/install-cinnamon-extension.sh` copies the extension to `$XDG_DATA_HOME/cinnamon/extensions/<uuid>` and adds the uuid to `org.cinnamon enabled-extensions`. Cinnamon loads it live, so no logout is needed. If it was already enabled, the script removes and re-adds the uuid so new code reloads.
- `install.sh` detects Cinnamon (`*cinnamon*` in the desktop variables) and runs that script in the same place it runs the GNOME helper step. The refresh and update paths then reinstall it too.
- `uninstall.sh` removes the uuid from `enabled-extensions` and deletes the extension directory.

## Non-goals

- Changes under `src/`. The protocol is reused as-is.
- A settings UI for rebinding shortcuts.
- MATE, Xfce, KDE or other desktops.
- Sharing code between the two extensions. GNOME 45+ needs ES modules and Cinnamon needs legacy CJS imports, so a static test enforces parity instead.

## Privacy

Identical to the GNOME helper and `docs/ambisense.md`:

- **Keyboard:** only the device *type* is inspected — never key symbols, codes, modifiers or text.
- **Window titles:**
  - read only for browsers, to reduce them to the focused-YouTube boolean;
  - reduced to a SHA-256 digest for tab-change detection;
  - never stored raw, logged or sent.
- **App identity:** reduced to a category inside Cinnamon before it reaches D-Bus.
- **Network:** none.

## Lifecycle (Manual rule 4)

`disable()` removes every source it created:

- the poll and heartbeat timeouts;
- both idle-monitor watches;
- the `last-device-changed` and `notify::focus-window` handlers;
- the tab-title handler;
- both hotkeys;
- the D-Bus export and the name ownership.

A test pairs each `connect`/`timeout_add`/`addHotKey` with its teardown.

## Testing

**`tests/test_cinnamon_helper.py`** (static, like `test_gnome_shortcuts.py`):

- **Protocol parity:** same bus constants, every GNOME signal name is present, and the same timing constants.
- **Markers:** every GNOME marker is present, plus the Mint additions.
- **Privacy:**
  - no key-symbol or keycode APIs and no `console`/`log` of titles;
  - `get_title()` appears only in the YouTube check and the tab digest.
- **Teardown:** each `connect`, timeout, idle watch and hotkey has its matching removal.
- **Metadata:** valid JSON with `cinnamon-version`.
- **Syntax:** `cjs` parses `extension.js` with `new Function`, skipped when `cjs` is missing.

**`tests/test_installer.py`:**

- the Cinnamon desktop runs the Cinnamon helper script, adds the uuid once, and reloads it when it is already enabled;
- GNOME and other desktops do not;
- the uninstaller removes the uuid and the directory.

**Live check on the requester's machine:**

- the extension is installed and enabled;
- `gdbus` shows the bus name owned and `GetState` answering.

This is not full desktop QA.

## Manual QA (maintainer)

On Linux Mint 22 Cinnamon, after `./install.sh`:

1. In System Settings → Extensions, "Mochi Desktop Activity" is listed and enabled.
2. Type in a terminal: Mochi reacts to typing.
3. Leave the machine idle for more than 2 minutes, then return: Mochi gets sleepy, then wakes or welcomes you back.
4. Open Nemo and Firefox; play a YouTube video in the foreground: the matching reactions appear.
5. `Ctrl+Alt+E` opens the Emote Catalogue.
6. Disable the extension in System Settings: Mochi keeps running with reduced awareness and no errors in `~/.xsession-errors`.
7. `mochi-uninstall`: the extension disappears from System Settings.
