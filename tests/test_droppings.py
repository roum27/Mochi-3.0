"""Regression coverage for Mochi's occasional little poops."""

from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import cairo

from mochi.droppings import (
    DROPPING_INTERVAL_SECONDS,
    MAX_DROPPINGS,
    DroppingSchedule,
    draw_dropping,
    dropping_position,
)
from mochi.presence.activity_controls import ActivityLevelMixin
from mochi.presence.click_dialogue import PresenceBuddy, PresenceX11Buddy
from mochi.presence.droppings import DroppingsMixin
from mochi.state import MochiState


class _Clock:
    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


class _Rng:
    def __init__(self, value: float) -> None:
        self.value = value
        self.calls: list[tuple[float, float]] = []

    def uniform(self, low: float, high: float) -> float:
        self.calls.append((low, high))
        return low + (high - low) * self.value


class DroppingScheduleTests(unittest.TestCase):
    def test_not_due_until_started(self) -> None:
        schedule = DroppingSchedule(clock=_Clock(), rng=_Rng(0.0))
        self.assertFalse(schedule.is_due())

    def test_due_time_is_drawn_from_the_interval(self) -> None:
        clock = _Clock()
        rng = _Rng(0.5)
        schedule = DroppingSchedule(clock=clock, rng=rng)
        schedule.start()

        self.assertEqual(rng.calls, [DROPPING_INTERVAL_SECONDS])
        low, high = DROPPING_INTERVAL_SECONDS
        clock.now += (low + high) / 2 - 1
        self.assertFalse(schedule.is_due())
        clock.now += 1
        self.assertTrue(schedule.is_due())

    def test_interval_is_minutes_not_seconds(self) -> None:
        low, high = DROPPING_INTERVAL_SECONDS
        self.assertGreaterEqual(low, 10 * 60)
        self.assertLess(low, high)

    def test_stop_clears_and_start_restarts(self) -> None:
        clock = _Clock()
        schedule = DroppingSchedule(clock=clock, rng=_Rng(0.0))
        schedule.start()
        clock.now += DROPPING_INTERVAL_SECONDS[0]
        self.assertTrue(schedule.is_due())

        schedule.stop()
        self.assertFalse(schedule.is_due())

        schedule.start()
        self.assertFalse(schedule.is_due())


MONITOR = (0, 0, 1000, 800)


class DroppingPositionTests(unittest.TestCase):
    def test_left_side_sits_beside_the_feet(self) -> None:
        x, y = dropping_position(
            visible_left=400,
            visible_right=500,
            visible_bottom=600,
            size=34,
            side="left",
            monitor=MONITOR,
        )
        self.assertEqual((x, y), (366, 566))

    def test_right_side_sits_beside_the_feet(self) -> None:
        x, y = dropping_position(
            visible_left=400,
            visible_right=500,
            visible_bottom=600,
            size=34,
            side="right",
            monitor=MONITOR,
        )
        self.assertEqual((x, y), (500, 566))

    def test_flips_side_at_the_monitor_edge(self) -> None:
        x, _y = dropping_position(
            visible_left=10,
            visible_right=110,
            visible_bottom=600,
            size=34,
            side="left",
            monitor=MONITOR,
        )
        self.assertEqual(x, 110)

        x, _y = dropping_position(
            visible_left=890,
            visible_right=990,
            visible_bottom=600,
            size=34,
            side="right",
            monitor=MONITOR,
        )
        self.assertEqual(x, 856)

    def test_clamps_inside_the_monitor(self) -> None:
        x, y = dropping_position(
            visible_left=1200,
            visible_right=1300,
            visible_bottom=900,
            size=34,
            side="right",
            monitor=MONITOR,
        )
        self.assertEqual((x, y), (966, 766))

    def test_respects_a_monitor_offset(self) -> None:
        x, y = dropping_position(
            visible_left=1000,
            visible_right=1100,
            visible_bottom=10,
            size=34,
            side="left",
            monitor=(1000, 0, 1920, 1080),
        )
        self.assertEqual((x, y), (1100, 0))


class DrawDroppingTests(unittest.TestCase):
    def test_paints_the_middle_and_leaves_corners_transparent(self) -> None:
        size = 34
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
        context = cairo.Context(surface)
        draw_dropping(context, size)
        surface.flush()

        data = surface.get_data()
        stride = surface.get_stride()

        def alpha(x: int, y: int) -> int:
            return data[y * stride + x * 4 + 3]

        self.assertGreater(alpha(size // 2, int(size * 0.75)), 200)
        self.assertEqual(alpha(0, 0), 0)
        self.assertEqual(alpha(size - 1, 0), 0)


class _FakeDropping:
    def __init__(self, *, owner, on_cleaned) -> None:
        self.owner = owner
        self.on_cleaned = on_cleaned
        self.shown_at = None
        self.destroyed = False

    def show_at(self, x, y) -> None:
        self.shown_at = (x, y)

    def destroy(self) -> None:
        self.destroyed = True

    def clean(self) -> None:
        self.destroy()
        self.on_cleaned(self)


class _Base:
    def __init__(self, *, preview_mode=False, layer_shell=False, enabled=True) -> None:
        self._preview_mode = preview_mode
        self._placement = SimpleNamespace(layer_shell_enabled=layer_shell)
        self._config = SimpleNamespace(
            load_droppings_enabled=Mock(return_value=enabled),
            save_droppings_enabled=Mock(),
        )
        self._logger = Mock()
        self._window = object()
        self.state = SimpleNamespace(current=MochiState.IDLE)
        self._context_menu_open = False
        self._focus_session = None
        self._presence_shutting_down = False
        self.registered_rows = []
        self.shutdown_called = False
        self._context_menu = self._build_context_menu()

    def _build_context_menu(self):
        return "menu"

    def _register_context_menu_row(self, row_id, widget, **kwargs):
        self.registered_rows.append((row_id, kwargs))

    def shutdown_presence(self) -> None:
        self.shutdown_called = True


class _Harness(DroppingsMixin, _Base):
    def _make_droppings_row(self):
        return "row", Mock()

    def _dropping_anchor(self):
        return (400, 500, 600, (0, 0, 1000, 800), 34)


class _Due:
    def __init__(self) -> None:
        self.due = True
        self.starts = 0
        self.stops = 0

    def start(self) -> None:
        self.starts += 1

    def stop(self) -> None:
        self.stops += 1

    def is_due(self) -> bool:
        return self.due


def _harness(**kwargs):
    glib = Mock()
    glib.timeout_add_seconds.return_value = 77
    glib.SOURCE_CONTINUE = True
    with patch("mochi.presence.droppings.GLib", glib):
        harness = _Harness(**kwargs)
    harness._dropping_factory = _FakeDropping
    harness._dropping_schedule = _Due()
    return harness, glib


class DroppingsMixinTests(unittest.TestCase):
    def test_registers_row_after_activity_and_starts_one_timer(self) -> None:
        harness, glib = _harness()
        self.assertEqual(harness.registered_rows, [("little-poops", {"after": "activity"})])
        glib.timeout_add_seconds.assert_called_once()
        self.assertEqual(harness._dropping_source_id, 77)

    def test_disabled_in_config_starts_no_timer(self) -> None:
        harness, glib = _harness(enabled=False)
        glib.timeout_add_seconds.assert_not_called()
        self.assertIsNone(harness._dropping_source_id)

    def test_unsupported_paths_have_no_row_and_no_timer(self) -> None:
        for kwargs in ({"preview_mode": True}, {"layer_shell": True}):
            harness, glib = _harness(**kwargs)
            self.assertEqual(harness.registered_rows, [])
            glib.timeout_add_seconds.assert_not_called()
            self.assertFalse(harness._leave_dropping())

    def test_leaves_a_poop_beside_mochi_when_due(self) -> None:
        harness, _glib = _harness()
        with patch("mochi.presence.droppings.random.choice", return_value="right"):
            harness._on_dropping_check()

        self.assertEqual(len(harness._droppings), 1)
        dropping = harness._droppings[0]
        self.assertEqual(dropping.shown_at, (500, 566))
        self.assertIs(dropping.owner, harness._window)
        self.assertEqual(harness._dropping_schedule.starts, 1)

    def test_nothing_happens_when_not_due(self) -> None:
        harness, _glib = _harness()
        harness._dropping_schedule.due = False
        harness._on_dropping_check()
        self.assertEqual(harness._droppings, [])

    def test_busy_mochi_waits_and_keeps_the_due_time(self) -> None:
        blockers = (
            lambda h: setattr(h.state, "current", MochiState.SLEEPING),
            lambda h: setattr(h.state, "current", MochiState.DRAGGED),
            lambda h: setattr(h.state, "current", MochiState.EATING),
            lambda h: setattr(h, "_context_menu_open", True),
            lambda h: setattr(h, "_focus_session", object()),
            lambda h: setattr(h, "_presence_shutting_down", True),
        )
        for block in blockers:
            harness, _glib = _harness()
            block(harness)
            harness._on_dropping_check()
            self.assertEqual(harness._droppings, [])
            self.assertEqual(harness._dropping_schedule.starts, 0)

    def test_walking_mochi_can_leave_one(self) -> None:
        harness, _glib = _harness()
        harness.state.current = MochiState.WALKING
        self.assertTrue(harness._leave_dropping())

    def test_cap_limits_poops_on_screen(self) -> None:
        harness, _glib = _harness()
        for _ in range(MAX_DROPPINGS + 2):
            harness._on_dropping_check()
        self.assertEqual(len(harness._droppings), MAX_DROPPINGS)

    def test_cleaning_frees_a_slot(self) -> None:
        harness, _glib = _harness()
        for _ in range(MAX_DROPPINGS):
            harness._leave_dropping()
        harness._droppings[0].clean()
        self.assertEqual(len(harness._droppings), MAX_DROPPINGS - 1)
        self.assertTrue(harness._leave_dropping())

    def test_toggle_off_removes_everything_and_on_restarts(self) -> None:
        harness, _glib = _harness()
        harness._leave_dropping()
        harness._leave_dropping()
        droppings = list(harness._droppings)

        glib = Mock()
        glib.timeout_add_seconds.return_value = 88
        with patch("mochi.presence.droppings.GLib", glib):
            harness._toggle_droppings()
            glib.source_remove.assert_called_once_with(77)
            self.assertIsNone(harness._dropping_source_id)
            self.assertEqual(harness._droppings, [])
            self.assertTrue(all(d.destroyed for d in droppings))
            harness._config.save_droppings_enabled.assert_called_with(False)

            harness._toggle_droppings()
            self.assertEqual(harness._dropping_source_id, 88)
            harness._config.save_droppings_enabled.assert_called_with(True)

    def test_shutdown_removes_timer_and_poops(self) -> None:
        harness, _glib = _harness()
        harness._leave_dropping()
        dropping = harness._droppings[0]
        glib = Mock()
        with patch("mochi.presence.droppings.GLib", glib):
            harness.shutdown_presence()
        glib.source_remove.assert_called_once_with(77)
        self.assertTrue(dropping.destroyed)
        self.assertEqual(harness._droppings, [])
        self.assertTrue(harness.shutdown_called)

    def test_mixin_is_composed_before_activity_in_both_buddies(self) -> None:
        for buddy in (PresenceBuddy, PresenceX11Buddy):
            mro = buddy.__mro__
            self.assertIn(DroppingsMixin, mro)
            self.assertLess(mro.index(DroppingsMixin), mro.index(ActivityLevelMixin))


if __name__ == "__main__":
    unittest.main()
