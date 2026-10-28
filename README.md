<div align="center">

# Mochi 3.0 🌱

### A tiny Linux desktop buddy that grows with you — at home on Linux Mint.

</div>

Mochi lives quietly on your desktop — wandering, reacting, working beside you,
taking naps, sharing snacks, learning new emotes, and building a bond through
the time you naturally spend together.

**No streaks · No decay · No cloud AI · Just a little guy 🌱**

Mochi 3.0 is a fork of [mochi-desktop](https://github.com/miflow13/mochi-desktop)
(v0.4.1, MIT). It targets **Linux Mint + Cinnamon**, speaks **French** on a
French locale, and updates only from this repository. GNOME/Fedora support from
the original is kept.

[Install](#install) · [Controls](#controls) · [Documentation](docs/README.md) ·
[Changelog](CHANGELOG.md)

## What Mochi does

- **Lives on your desktop:** idles, blinks, looks around, takes walks (or
  **Stay put** / **Edge roam**), naps, and can be picked up and dragged.
  **Activity** in the right-click menu sets how often he wanders and plays on
  his own: **Calm** (default), **Lively**, or **Energetic**.
- **Reacts to you:** click chirps, bounce, squish, hearts, triple-click
  dialogue, and short, paced-out speech bubbles that are easy to ignore.
- **Shares snacks:** **Feed** from the right-click menu. There is no hunger
  meter and no penalty for being away.
- **Leaves little poops:** now and then a tiny poop appears beside him on
  the screen. Click it to clean it up. It never matters if you don't; turn
  them off with **Little poops** in the right-click menu.
- **Bonds without pressure:** a persistent, non-decaying **Bond Level** grows
  from typing together, feeding, and focus time. There are no streaks and no
  missed-day penalties.
- **Learns tricks:** the **Emote Catalogue** (`Ctrl + Alt + E`) has
  bond-gated emotes, rarity tiers, and animated previews.
- **Works beside you:** **Focus with Mochi** runs 5–120 min focus blocks with
  breaks, rounds, and an optional local rain soundscape. Completed focus
  minutes earn bond XP.
- **Holds things for you:** drop a file, link, image, or text onto Mochi and
  find it in his **Pocket**.
- **Keeps your agent company:** with
  [Agent Companion](docs/agent-companion.md), Mochi sips coffee beside a
  little monitor while Claude Code or Codex works.

<p align="center">
  <img src="docs/media/v0.3/mochi-focus.gif" width="640" alt="Mochi focusing beside the user">
</p>

### AmbiSense: local and private

Mochi's awareness is rule-based and local. **It is not an LLM and uses no cloud
service.** A small desktop helper reduces activity to content-free signals:

- anonymous typing;
- idle and return;
- a coarse app category;
- file browsing;
- focused YouTube;
- media playback;
- battery and network changes.

Mochi never sees typed characters, key values, window titles, document names,
or screen content. See [AmbiSense](docs/ambisense.md).

### Talk to Mochi (optional, Ollama)

**Talk to Mochi...** in the right-click menu, or holding the mouse on Mochi for
1.5 seconds, opens a chat window. What you type goes to an
[Ollama](https://ollama.com) server of your choice; the answer stays in the
window, ready to copy, until you close it. Mochi is set up as a small text
assistant: start with `traduis:` / `translate:` to translate or `corrige:` /
`fix:` to fix spelling. Enter sends, Shift+Enter adds a line. Nothing is sent
until you write to him. Configure it in
`~/.config/mochi/ollama/`:

- `config.json`: `{"host": "http://192.168.1.10:11434", "model": "llama3.2:3b"}`
  (created with `localhost` on first use);
- `system.md`: Mochi's identity and voice, sent as the system prompt;
- `memory.md`: facts Mochi distilled from older chats (editable);
- `history.json`: recent exchanges.

A server on another machine must listen on the network (`OLLAMA_HOST=0.0.0.0`).

## Install

```bash
git clone https://github.com/roum27/Mochi-3.0.git ~/Mochi-3.0
cd ~/Mochi-3.0 && ./install.sh
```

Mochi installs per user. To give another account on the same computer its own
Mochi, run the same commands in that account's desktop session. No GitHub
account is needed.

The installer:

- **Installs missing system packages:** with `apt` on Linux Mint, Ubuntu, and
  Debian, or `dnf` on Fedora. It asks for your password only when something is
  missing.
- **Builds Mochi:** in a private Python environment under
  `~/.local/share/mochi-desktop`.
- **Adds launchers:** `mochi`, `mochi-update`, and `mochi-uninstall` under
  `~/.local/bin`, plus a menu entry.
- **Installs the desktop helper:**
  - **On Cinnamon:** the Cinnamon helper (**System Settings → Extensions →
    Mochi Desktop Activity**). Cinnamon loads it right away; no logout needed.
  - **On GNOME:** the GNOME Shell helper. Log out and back in once.
  - **On other desktops:** Mochi runs without a helper, with fewer contextual
    reactions and no global shortcuts.

### Language

Mochi follows your system language. On a French locale, his speech, menus,
Quick Start, Focus, Emote Catalogue, and Pocket are in French. To choose
explicitly:

```bash
MOCHI_LANGUAGE=fr mochi
MOCHI_LANGUAGE=en mochi
```

Mochi Lab developer tools and the updater window stay in English.

### Updates

`mochi-update`, or **Check for updates** in the right-click menu, checks this
repository and nothing else. No GitHub account or sign-in is needed.

By default it follows every change pushed to `main`, so the button finds each
new version as soon as it is on GitHub. To follow only published GitHub
Releases instead, switch channels once:

```bash
mochi-update --channel release  # published releases only
mochi-update --channel main     # every change on main (default)
```

An update installs the exact commit it found, keeps the previous runtime as a
backup until the new one starts, and never resets your bond, unlocks, Pocket, or
settings. Run it in each user account that has Mochi installed.

#### Updating by hand

You can also update with Git. Copy and paste this block into a terminal:

```bash
rm -rf ~/Mochi-3.0
git clone https://github.com/roum27/Mochi-3.0.git ~/Mochi-3.0
cd ~/Mochi-3.0 && ./install.sh
```

Then close Mochi (right-click → **Close**) and launch him again from the
applications menu. If you kept an earlier clone, `git pull` inside it followed
by `./install.sh` works too.

Your bond, unlocks, Pocket, and settings live in `~/.config/mochi` and
`~/.local/share`, not in the clone, so removing the clone loses nothing.

## Controls

Launch Mochi from your applications menu or run `mochi`. If `~/.local/bin` is
not on `PATH`, use `~/.local/bin/mochi`.

| Interaction | What it does |
| --- | --- |
| Left-click | Chirp + tactile reaction |
| Double-click | Heart emote |
| Three quick clicks | Short playful dialogue |
| Drag | Pick up and reposition Mochi |
| Click a poop | Clean it up |
| Hold 1.5 s | Open Talk to Mochi (Ollama) |
| Right-click | Bond, Feed, Talk to Mochi, Focus, Pocket, size/audio, sleep/wake, movement, Activity, Little poops, and app controls |
| `Ctrl + Alt + E` | Open the Emote Catalogue |
| `Ctrl + Alt + Shift + M` | Open Mochi Lab developer controls |

Global shortcuts require the Cinnamon or GNOME helper.

## Compatibility

- **Linux Mint 22 (Cinnamon 6, X11):** primary target, with the Cinnamon helper.
- **Fedora + GNOME + Wayland:** supported, as in the original. On GNOME Wayland,
  Mochi uses an XWayland window for reliable positioning.
- **Other distributions and desktops** may work, with less coverage.

## Troubleshooting

- **Helper running?**

  ```bash
  gdbus call --session --dest io.github.mochi_desktop.Mochi.TypingMonitor \
    --object-path /io/github/mochi_desktop/Mochi/TypingMonitor \
    --method io.github.mochi_desktop.Mochi.TypingMonitor.GetState
  ```

  On Cinnamon, check **System Settings → Extensions**; helper messages appear in
  `~/.xsession-errors`. On GNOME, use
  `gnome-extensions info mochi-typing@miflow13`.
- **Lost Mochi off-screen?** Run `mochi --reset-position`.
- **Need logs?** Run `mochi --debug`.

## Development

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python3 -m pip install -e . pytest
python3 -m pytest -q
mochi --debug
```

`--system-site-packages` keeps the system PyGObject (`gi`) importable. Start
with:

- [CLAUDE.md](CLAUDE.md) for project rules;
- the [Codebase Manual](docs/CODEBASE_MANUAL.md);
- [REGRESSION_WATCHLIST.md](REGRESSION_WATCHLIST.md).

## Uninstall

```bash
mochi-uninstall          # keeps your saved settings
mochi-uninstall --purge  # removes them too
```

---

<div align="center">

Mochi is released under the [MIT License](LICENSE). Original character and code
by the [mochi-desktop](https://github.com/miflow13/mochi-desktop) contributors.

</div>
