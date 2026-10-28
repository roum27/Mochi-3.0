# Little Poops — Design

**Date:** 2026-10-28

**Status:** requested by the maintainer ("je veux que mochi laisse de temps en temps des petits cacas sur l'écran", "on devra cliquer dessus pour nettoyer") and implemented on `claude/little-poops`.

## Purpose

Mochi is a pet. Once in a while, a pet leaves a little poop behind. This adds a small, silly, pet-like moment: every so often a tiny cartoon poop appears on the desktop next to Mochi, and it stays there until the user clicks it to clean it up.

## Goals

- Every 15–40 minutes of Mochi being awake and free, he leaves one small poop on the screen, right beside his feet.
- The poop is its own small always-on-top window. It stays where it was left when Mochi walks away.
- A click on the poop cleans it: it fades out quickly and its window is destroyed.
- At most three poops are on screen at once. When three are waiting, Mochi leaves no more.
- A **Little poops** switch in the right-click menu turns the feature on or off. It is on by default and the choice is remembered. Turning it off removes every poop at once.
- The scheduling and placement logic is GTK-free and testable without a display.

## Non-goals

- **No consequences.** Uncleaned poops never affect mood, bond, XP or speech, and cleaning one earns nothing. This keeps the "no pressure" rule: a poop is a joke, not a chore.
- No persistence. Poops are transient and vanish when Mochi quits.
- No speech line and no new Mochi animation for now (possible follow-ups).
- No sound.
- Pure Wayland with layer shell is not supported: there, free top-level positioning is unavailable. The switch is not shown and nothing is scheduled. X11 and GNOME XWayland (the normal paths) are supported.

## Design

### `src/mochi/droppings.py` (new, GTK-free)

- Constants: `DROPPING_INTERVAL_SECONDS = (15 * 60, 40 * 60)`, `DROPPING_CHECK_INTERVAL_SECONDS = 30`, `MAX_DROPPINGS = 3`, `DROPPING_SIZE_PX = 34`.
- `DroppingSchedule(clock=time.monotonic, rng=random)`:
  - `start()` picks the next due time inside the interval;
  - `stop()` clears it;
  - `is_due()` is true once that time is reached.
- `dropping_position(...)` returns the root-coordinate top-left of a new poop window:
  - beside Mochi's visible sprite bounds, on the requested side, its bottom on his feet line;
  - flipped to the other side when it would leave the monitor, then clamped inside the monitor.
- `draw_dropping(cr, size)` paints the poop with Cairo: three stacked brown tiers, a curled tip, a highlight, two dot eyes and a small smile. No new asset file.

### `src/mochi/presence/droppings.py` (new)

- **`DroppingWindow`** — one poop.
  - An undecorated, non-focusable, transparent `Gtk.Window`, transient for Mochi's window, with a `Gtk.DrawingArea` that calls `draw_dropping`.
  - `show_at(x, y)` presents it with opacity 0. On `map` it asks for keep-above (which also sets skip-taskbar), moves the X11 window, then becomes opaque, so it never flashes at 0,0.
  - A primary-button `Gtk.GestureClick` calls `clean()`: a 0.2 s opacity fade, then `destroy()` and the `on_cleaned` callback.
  - `destroy()` removes the fade source and destroys the window. It is idempotent.
- **`DroppingsMixin`** — owns the feature.
  - State: `_droppings_enabled`, `_droppings` (live windows), `_dropping_schedule`, `_dropping_source_id`, `_droppings_switch`.
  - `_build_context_menu` loads `droppings_enabled` and registers a `"little-poops"` switch row after `"activity"`, when supported. The menu reads Sleep → Edge roam → Stay put → Activity → Little poops.
  - After `__init__`, when supported and enabled, it starts the schedule and one recurring 30 s `GLib.timeout_add_seconds` check.
  - The check leaves a poop when the schedule is due and `_can_leave_dropping()` holds:
    - enabled, fewer than `MAX_DROPPINGS`, not shutting down;
    - Mochi is `IDLE` or `WALKING` (never asleep, held, dragged, eating, dancing…);
    - the context menu is closed and no Focus session is running.
    Otherwise it simply tries again at the next check. After a poop is left, the schedule restarts.
  - Position: Mochi's X11 window position plus the current frame's visible bounds, both in device pixels, using the same scaling approach as the speech bubble. The side is random.
  - The poop window comes from `_dropping_factory`, which tests replace.
  - Toggling the switch saves the choice. Off: stop the timer, stop the schedule, destroy all poops. On: start both.
  - `shutdown_presence` stops the timer and destroys every poop (Manual rule 4).
  - Mochi Lab gets a **Leave a poop now** button (English, like the other Lab controls) that skips the schedule but still respects the cap and the eligibility rules.
- Composition: the mixin sits right before `ActivityLevelMixin` in both `PresenceBuddy` classes, so the `"activity"` row already exists when it registers its own.

### `ConfigStore`

- `load_droppings_enabled()` returns `"droppings_enabled"`, defaulting to `True` when missing or invalid.
- `save_droppings_enabled(enabled)`.

### Translation

| English | French |
|---|---|
| `Little poops` | `Petits cacas` |
| `Mochi sometimes leaves a little poop on the screen. Click it to clean up.` | `Mochi laisse parfois un petit caca à l’écran. Clique dessus pour nettoyer.` |

## Rules check

- **One state path / state is not animation:** no new state or animation. The feature only reads `state.current`.
- **Direct interaction outranks ambient behavior:** poops are only left while Mochi is idle or walking with the menu closed.
- **Owner and teardown:** the mixin owns one timer and the poop windows; each window owns its fade source. All are removed on disable and shutdown.
- **Mochi stays interactable:** poop windows sit beside Mochi's visible sprite, not on it, and are tiny.
- **No pressure / easy to ignore:** no consequences, a cap of three, an off switch, no speech.
- **Local only, privacy:** no network, reads nothing from the desktop.

## Testing

- `tests/test_droppings.py`:
  - schedule due times stay inside the interval, `stop()` and restart;
  - `dropping_position` on both sides, the flip at a monitor edge, clamping;
  - `draw_dropping` paints opaque pixels in the middle and leaves the corners transparent;
  - config default, round-trip and invalid-value fallback;
  - the mixin leaves a poop only when due and eligible, respects the cap, is blocked by sleep, drag, the menu and Focus;
  - cleaning removes it from the list; toggling off destroys all and stops the timer; shutdown destroys all;
  - no timer and no row in preview mode or with layer shell;
  - the mixin is in both buddy MROs, ahead of `ActivityLevelMixin`.
- `tests/test_i18n.py` covers the new `tr()` literals automatically.
