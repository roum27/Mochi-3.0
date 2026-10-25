# Mochi Desktop Activity (Cinnamon)

Cinnamon counterpart of `gnome-extension/mochi-typing@miflow13`. It owns the
same session-bus name (`io.github.mochi_desktop.Mochi.TypingMonitor`) and emits
the same content-free signals, so Mochi reacts on Linux Mint exactly as it does
on GNOME:

- `Pulse` when the latest input device is a keyboard (no key identity);
- `UserIdle` / `UserActive` after two minutes without input;
- `FileBrowsingStarted` / `FileBrowsingStopped`, `YouTubeFocusedStarted` /
  `YouTubeFocusedStopped`;
- `AppCategoryChanged` / `AppFocusChanged` with one coarse category
  (`vscode`, `editor`, `terminal`, `browser`, `media`, `pixel_art`, `unknown`);
- `BrowserTabChanged` (title reduced to a SHA-256 digest inside Cinnamon);
- `EmoteCatalogueRequested` on `Ctrl+Alt+E`, `DeveloperMenuRequested` on
  `Ctrl+Alt+Shift+M`.

No typed content, key symbols, window titles, file names, or paths ever leave
Cinnamon, and the extension makes no network requests. See
[`docs/ambisense.md`](../../docs/ambisense.md).

`./install.sh` installs it to `~/.local/share/cinnamon/extensions/` and enables
it on Cinnamon; Cinnamon loads it immediately. You can also toggle it in
**System Settings → Extensions**.
