# Activity Level — Design

**Date:** 2026-10-25

**Status:** approved by the requester ("oui on fait ca Activité dans le menu") and implemented on `claude/activity-level`.

## Purpose

Mochi's ambient cadence is deliberately calm. Every 20–45 s he gets one idle opportunity: a 10 % chance to walk 60–240 px, a 20 % chance to play an unlocked catalogue emote, and nothing otherwise. That averages about one short stroll every five minutes. With Stay put off, the requester still finds him too inactive. There is no way to change this without editing code.

## Goals

- One persistent **Activity** row in the right-click menu with three levels: **Calm**, **Lively** and **Energetic**.
- **Calm** is the default and is exactly today's behavior, so existing users see no change.
- The level changes only Mochi's autonomous idle cadence:
  - how often idle opportunities come;
  - the walk chance;
  - the catalogue-emote chance;
  - the free-walk distance.
- The change takes effect right away and survives restarts.
- The logic is GTK-free and testable without a display.

## Non-goals

- Speech frequency. AmbiSense keeps its own pacing, and "easy to ignore" still holds.
- Walk speed, blink rate, sleep timing and edge-roam step length.
- Stay put and Edge roam keep their meaning. Stay put still suppresses walking at every level; emote cadence still follows the level.
- No Mochi Lab controls. The row is the only surface.

## Design

### `src/mochi/activity_level.py` (new, GTK-free)

- `ActivityProfile`, a frozen dataclass:
  - `idle_action_interval_seconds: tuple[int, int]`;
  - `walk_chance: float`;
  - `catalogue_emote_chance: float`;
  - `walk_distance_px: tuple[int, int]`.
- `ACTIVITY_LEVELS = ("calm", "lively", "energetic")`, with `DEFAULT_ACTIVITY_LEVEL = "calm"`.
- The profiles:

  | Level | Interval (s) | Walk | Emote | Walk distance (px) | Average time between walks |
  |---|---|---|---|---|---|
  | calm | 20–45 | 0.10 | 0.20 | 60–240 | ~5 min |
  | lively | 12–28 | 0.25 | 0.25 | 80–300 | ~80 s |
  | energetic | 6–15 | 0.40 | 0.25 | 120–400 | ~26 s |

- `ACTIVITY_LABELS` maps each level to its English label, the source text for `tr()`.
- `normalize_activity_level(value)` returns the level, or `"calm"` for anything unknown.
- `next_activity_level(level)` cycles calm → lively → energetic → calm.
- `activity_profile(level)` returns the profile for a level.

### `ConfigStore`

- `load_activity_level()` returns the level stored in `"activity_level"`.
  - Unknown, missing or corrupt values fall back to `"calm"`.
- `save_activity_level(level)` saves the normalized level.

### `Buddy`

- Add `WALK_DISTANCE_PX = (60, 240)` next to the other idle constants.
- `_start_walk` uses `random.randint(*self.WALK_DISTANCE_PX)`.
- Nothing else changes. The class constants remain the calm profile, which the inherited `test_calm_idle.py` assertions keep checking.

### `ActivityLevelMixin` (new, `src/mochi/presence/activity_controls.py`)

- **Applying the profile:** `_apply_activity_profile()` sets four instance attributes that shadow Buddy's class constants:
  - `IDLE_ACTION_INTERVAL_SECONDS`;
  - `IDLE_WALK_CHANCE`;
  - `IDLE_CATALOGUE_EMOTE_CHANCE`;
  - `WALK_DISTANCE_PX`.

  `_schedule_idle_action`, `_choose_idle_action_with_walk` and `_start_walk` already read them through `self`, so the behavior-state path (Manual rule 1) is untouched.
- **Building the menu:** `_build_context_menu` loads the level, applies the profile, and registers an `"activity"` row after `"stay-put"`. Buddy builds the menu in `__init__` before the first `_schedule_idle_action`, so the saved level applies from startup, the same way Stay put does.
- **The row:** a single `Gtk.Button` with the `mochi-menu-row` class.
  - It shows an icon, the label `tr("Activity")`, and a right-aligned `mochi-menu-value` label with the translated level name.
  - Clicking it cycles the level, saves it, re-applies the profile, and updates the value label.
  - The menu stays open, as it does for Stay put, so repeated clicks step through the levels.
- **Rescheduling:** if an idle-action timeout is pending, the toggle removes it and schedules a new one from the new profile. That way, switching from calm to energetic does not wait up to 45 s.
  - The source id stays owned by Buddy's existing `_idle_action_source_id` field. Its lifetime does not change: it is a recurring timer that lives as long as the process, as it does today.
  - No new long-lived source is added (Manual rule 4).
- **Placement:** the mixin sits before `EdgeRoamMixin` in both `PresenceBuddy` classes. The menu order becomes Sleep → Edge roam → Stay put → Activity.
- **Menu height:** the `"activity"` row is not listed in `CONTEXT_MENU_MIN_HEIGHTS`, so it gets the central unknown-row increment.

### Translation

| English | French |
|---|---|
| `Activity` | `Activité` |
| `Calm` | `Calme` |
| `Lively` | `Actif` |
| `Energetic` | `Énergique` |
| `Choose how often Mochi moves and plays on his own` | `Choisir à quelle fréquence Mochi bouge et joue tout seul` |

## Rules check

- **Direct interaction outranks ambient behavior:** unchanged. The selector only feeds probabilities and intervals into the existing idle path, which still bails out unless Mochi is IDLE and the menu is closed.
- **Recovery:** no new state.
- **No pressure:** levels are neutral preferences, with no rewards or penalties.
- **Local only:** no network access.

## Testing

- `tests/test_activity_level.py`:
  - profiles and the calm default;
  - calm equals Buddy's constants;
  - probabilities stay ≤ 1;
  - normalization and cycling;
  - config round-trip and fallback;
  - the mixin applies the profile, cycles and saves on toggle, reschedules a pending idle action, and leaves the timer alone when none is pending;
  - `_start_walk` uses `WALK_DISTANCE_PX`;
  - the mixin is in both buddy MROs, ahead of `EdgeRoamMixin`.
- `tests/test_i18n.py` covers the new `tr()` literals automatically.
