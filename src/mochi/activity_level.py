"""GTK-free Activity levels that tune Mochi's autonomous idle cadence."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActivityProfile:
    """How often Mochi gets an idle opportunity and what he does with it."""

    idle_action_interval_seconds: tuple[int, int]
    walk_chance: float
    catalogue_emote_chance: float
    walk_distance_px: tuple[int, int]


ACTIVITY_LEVELS = ("calm", "lively", "energetic")
DEFAULT_ACTIVITY_LEVEL = "calm"

# Calm is Mochi's original cadence and must stay identical to Buddy's class
# constants so existing users see no change.
ACTIVITY_PROFILES: dict[str, ActivityProfile] = {
    "calm": ActivityProfile(
        idle_action_interval_seconds=(20, 45),
        walk_chance=0.10,
        catalogue_emote_chance=0.20,
        walk_distance_px=(60, 240),
    ),
    "lively": ActivityProfile(
        idle_action_interval_seconds=(12, 28),
        walk_chance=0.25,
        catalogue_emote_chance=0.25,
        walk_distance_px=(80, 300),
    ),
    "energetic": ActivityProfile(
        idle_action_interval_seconds=(6, 15),
        walk_chance=0.40,
        catalogue_emote_chance=0.25,
        walk_distance_px=(120, 400),
    ),
}

# English source text for the menu value; translated at the call site.
ACTIVITY_LABELS: dict[str, str] = {
    "calm": "Calm",
    "lively": "Lively",
    "energetic": "Energetic",
}


def normalize_activity_level(value: object) -> str:
    """Return a known level, falling back to calm for anything else."""
    if isinstance(value, str) and value in ACTIVITY_PROFILES:
        return value
    return DEFAULT_ACTIVITY_LEVEL


def next_activity_level(level: str) -> str:
    """Cycle calm -> lively -> energetic -> calm."""
    index = ACTIVITY_LEVELS.index(normalize_activity_level(level))
    return ACTIVITY_LEVELS[(index + 1) % len(ACTIVITY_LEVELS)]


def activity_profile(level: str) -> ActivityProfile:
    return ACTIVITY_PROFILES[normalize_activity_level(level)]
