"""Regression coverage for the user-selectable Activity level."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from mochi.activity_level import (
    ACTIVITY_LABELS,
    ACTIVITY_LEVELS,
    ACTIVITY_PROFILES,
    DEFAULT_ACTIVITY_LEVEL,
    activity_profile,
    next_activity_level,
    normalize_activity_level,
)
from mochi.buddy import Buddy
from mochi.config import ConfigStore, Position
from mochi.presence.activity_controls import ActivityLevelMixin
from mochi.presence.click_dialogue import PresenceBuddy, PresenceX11Buddy
from mochi.presence.edge_roam_controls import EdgeRoamMixin


class ActivityProfileTests(unittest.TestCase):
    def test_calm_is_the_default_and_matches_buddys_constants(self) -> None:
        self.assertEqual(DEFAULT_ACTIVITY_LEVEL, "calm")
        calm = activity_profile("calm")
        self.assertEqual(
            calm.idle_action_interval_seconds, Buddy.IDLE_ACTION_INTERVAL_SECONDS
        )
        self.assertEqual(calm.walk_chance, Buddy.IDLE_WALK_CHANCE)
        self.assertEqual(calm.catalogue_emote_chance, Buddy.IDLE_CATALOGUE_EMOTE_CHANCE)
        self.assertEqual(calm.walk_distance_px, Buddy.WALK_DISTANCE_PX)

    def test_levels_get_progressively_more_active(self) -> None:
        self.assertEqual(ACTIVITY_LEVELS, ("calm", "lively", "energetic"))
        profiles = [ACTIVITY_PROFILES[level] for level in ACTIVITY_LEVELS]
        for quieter, busier in zip(profiles, profiles[1:]):
            self.assertLess(
                busier.idle_action_interval_seconds[1],
                quieter.idle_action_interval_seconds[1],
            )
            self.assertGreater(busier.walk_chance, quieter.walk_chance)
            self.assertGreaterEqual(
                busier.catalogue_emote_chance, quieter.catalogue_emote_chance
            )

    def test_every_profile_is_a_valid_idle_roll(self) -> None:
        for level, profile in ACTIVITY_PROFILES.items():
            with self.subTest(level=level):
                low, high = profile.idle_action_interval_seconds
                self.assertGreaterEqual(low, 1)
                self.assertLessEqual(low, high)
                self.assertLessEqual(
                    profile.walk_chance + profile.catalogue_emote_chance, 1.0
                )
                near, far = profile.walk_distance_px
                self.assertLessEqual(near, far)

    def test_every_level_has_a_label(self) -> None:
        self.assertEqual(set(ACTIVITY_LABELS), set(ACTIVITY_LEVELS))

    def test_unknown_values_normalize_to_calm(self) -> None:
        for value in ("lively", "energetic", "calm"):
            self.assertEqual(normalize_activity_level(value), value)
        for value in (None, "", "hyper", 3, True):
            self.assertEqual(normalize_activity_level(value), "calm")

    def test_levels_cycle_back_to_calm(self) -> None:
        self.assertEqual(next_activity_level("calm"), "lively")
        self.assertEqual(next_activity_level("lively"), "energetic")
        self.assertEqual(next_activity_level("energetic"), "calm")
        self.assertEqual(next_activity_level("bogus"), "lively")


class ActivityConfigTests(unittest.TestCase):
    def test_activity_level_defaults_to_calm_and_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ConfigStore(Path(directory) / "config.json")
            self.assertEqual(store.load_activity_level(), "calm")
            store.save_activity_level("energetic")
            self.assertEqual(store.load_activity_level(), "energetic")
            store.save_activity_level("nonsense")
            self.assertEqual(store.load_activity_level(), "calm")

    def test_corrupt_activity_level_falls_back_to_calm(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps({"activity_level": ["lively"]}))
            self.assertEqual(ConfigStore(path).load_activity_level(), "calm")
            path.write_text("{not json")
            self.assertEqual(ConfigStore(path).load_activity_level(), "calm")

    def test_saving_activity_level_preserves_other_settings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ConfigStore(Path(directory) / "config.json")
            store.save_stay_put(True)
            store.save_activity_level("lively")
            self.assertTrue(store.load_stay_put())


class FreeWalkDistanceTests(unittest.TestCase):
    def test_free_walk_draws_its_distance_from_the_instance_range(self) -> None:
        placement = SimpleNamespace(
            sync_from_window=Mock(return_value=Position(0, 0)),
            clamp_position=Mock(return_value=Position(0, 0)),
        )
        buddy = SimpleNamespace(WALK_DISTANCE_PX=(120, 400), _placement=placement)

        with patch("mochi.buddy.random.randint", return_value=200) as randint:
            Buddy._start_walk(buddy)

        randint.assert_called_once_with(120, 400)


class _Base:
    IDLE_ACTION_INTERVAL_SECONDS = Buddy.IDLE_ACTION_INTERVAL_SECONDS
    IDLE_WALK_CHANCE = Buddy.IDLE_WALK_CHANCE
    IDLE_CATALOGUE_EMOTE_CHANCE = Buddy.IDLE_CATALOGUE_EMOTE_CHANCE
    WALK_DISTANCE_PX = Buddy.WALK_DISTANCE_PX

    def __init__(self) -> None:
        self._config = SimpleNamespace(save_activity_level=Mock())
        self._logger = SimpleNamespace(info=Mock(), debug=Mock())
        self._idle_action_source_id: int | None = None
        self._schedule_idle_action = Mock()


class _Buddy(ActivityLevelMixin, _Base):
    pass


class ActivityMixinTests(unittest.TestCase):
    def test_applying_a_profile_shadows_the_calm_class_constants(self) -> None:
        buddy = _Buddy()
        buddy._activity_level = "energetic"

        buddy._apply_activity_profile()

        energetic = activity_profile("energetic")
        self.assertEqual(
            buddy.IDLE_ACTION_INTERVAL_SECONDS, energetic.idle_action_interval_seconds
        )
        self.assertEqual(buddy.IDLE_WALK_CHANCE, energetic.walk_chance)
        self.assertEqual(
            buddy.IDLE_CATALOGUE_EMOTE_CHANCE, energetic.catalogue_emote_chance
        )
        self.assertEqual(buddy.WALK_DISTANCE_PX, energetic.walk_distance_px)
        self.assertEqual(_Base.IDLE_WALK_CHANCE, Buddy.IDLE_WALK_CHANCE)

    def test_toggle_cycles_saves_and_updates_the_value_label(self) -> None:
        buddy = _Buddy()
        buddy._activity_value_label = SimpleNamespace(set_text=Mock())

        buddy._toggle_activity_level(None)

        self.assertEqual(buddy._activity_level, "lively")
        buddy._config.save_activity_level.assert_called_once_with("lively")
        buddy._activity_value_label.set_text.assert_called_once_with("Lively")
        self.assertEqual(buddy.IDLE_WALK_CHANCE, activity_profile("lively").walk_chance)

    def test_toggle_replaces_a_pending_idle_opportunity(self) -> None:
        buddy = _Buddy()
        buddy._idle_action_source_id = 42

        with patch("mochi.presence.activity_controls.GLib.source_remove") as remove:
            buddy._toggle_activity_level(None)

        remove.assert_called_once_with(42)
        self.assertIsNone(buddy._idle_action_source_id)
        buddy._schedule_idle_action.assert_called_once_with()

    def test_toggle_does_not_start_idle_actions_when_none_are_pending(self) -> None:
        buddy = _Buddy()

        with patch("mochi.presence.activity_controls.GLib.source_remove") as remove:
            buddy._toggle_activity_level(None)

        remove.assert_not_called()
        buddy._schedule_idle_action.assert_not_called()

    def test_both_buddies_compose_the_mixin_ahead_of_edge_roam(self) -> None:
        for cls in (PresenceBuddy, PresenceX11Buddy):
            with self.subTest(cls=cls.__name__):
                mro = cls.__mro__
                self.assertIn(ActivityLevelMixin, mro)
                self.assertLess(mro.index(ActivityLevelMixin), mro.index(EdgeRoamMixin))


if __name__ == "__main__":
    unittest.main()
