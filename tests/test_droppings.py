"""Regression coverage for Mochi's occasional little poops."""

from __future__ import annotations

import unittest

import cairo

from mochi.droppings import (
    DROPPING_INTERVAL_SECONDS,
    DroppingSchedule,
    draw_dropping,
    dropping_position,
)


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


if __name__ == "__main__":
    unittest.main()
