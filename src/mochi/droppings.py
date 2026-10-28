"""GTK-free scheduling, placement and drawing for Mochi's little poops.

Once in a while Mochi leaves a tiny cartoon poop beside him on the desktop.
It is a joke, not a chore: nothing ever depends on whether it is cleaned up.
The GTK window and the buddy wiring live in ``mochi.presence.droppings``.
"""

from __future__ import annotations

from collections.abc import Callable
import math
import random
import time

import cairo


# Minutes, not seconds: this should stay a rare, surprising moment.
DROPPING_INTERVAL_SECONDS = (15 * 60, 40 * 60)
DROPPING_CHECK_INTERVAL_SECONDS = 30
MAX_DROPPINGS = 3
DROPPING_SIZE_PX = 34


class DroppingSchedule:
    """Track when Mochi may next leave a poop."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        rng=random,
    ) -> None:
        self._clock = clock
        self._rng = rng
        self._due_at: float | None = None

    def start(self) -> None:
        self._due_at = self._clock() + self._rng.uniform(*DROPPING_INTERVAL_SECONDS)

    def stop(self) -> None:
        self._due_at = None

    def is_due(self) -> bool:
        return self._due_at is not None and self._clock() >= self._due_at


def dropping_position(
    *,
    visible_left: float,
    visible_right: float,
    visible_bottom: float,
    size: float,
    side: str,
    monitor: tuple[float, float, float, float],
) -> tuple[int, int]:
    """Return the top-left of a poop window beside Mochi's feet.

    All values share one coordinate space (X11 root pixels in practice).
    The poop sits just outside the visible sprite so it never covers Mochi;
    it flips sides at a monitor edge and is finally clamped onto the monitor.
    """
    monitor_x, monitor_y, monitor_width, monitor_height = monitor
    monitor_right = monitor_x + monitor_width
    monitor_bottom = monitor_y + monitor_height

    def x_for(which: str) -> float:
        return visible_left - size if which == "left" else visible_right

    x = x_for(side)
    if x < monitor_x or x + size > monitor_right:
        x = x_for("right" if side == "left" else "left")
    y = visible_bottom - size

    x = max(monitor_x, min(x, monitor_right - size))
    y = max(monitor_y, min(y, monitor_bottom - size))
    return round(x), round(y)


_BODY = (0.54, 0.35, 0.21)
_OUTLINE = (0.36, 0.22, 0.13)
_HIGHLIGHT = (0.74, 0.53, 0.36)
_FACE = (0.20, 0.12, 0.07)


def draw_dropping(cr: cairo.Context, size: float) -> None:
    """Paint one cute soft-serve poop filling a ``size`` square."""
    s = float(size)
    line_width = max(1.0, s * 0.04)

    def tier(center_y: float, radius_x: float, radius_y: float) -> None:
        cr.save()
        cr.translate(s * 0.5, s * center_y)
        cr.scale(s * radius_x, s * radius_y)
        cr.arc(0.0, 0.0, 1.0, 0.0, 2.0 * math.pi)
        cr.restore()
        cr.set_source_rgb(*_BODY)
        cr.fill_preserve()
        cr.set_source_rgb(*_OUTLINE)
        cr.set_line_width(line_width)
        cr.stroke()

    cr.save()
    # Curled tip first so the top tier overlaps its base.
    cr.move_to(s * 0.40, s * 0.36)
    cr.curve_to(s * 0.44, s * 0.18, s * 0.58, s * 0.16, s * 0.60, s * 0.08)
    cr.curve_to(s * 0.70, s * 0.20, s * 0.64, s * 0.32, s * 0.60, s * 0.36)
    cr.close_path()
    cr.set_source_rgb(*_BODY)
    cr.fill_preserve()
    cr.set_source_rgb(*_OUTLINE)
    cr.set_line_width(line_width)
    cr.stroke()

    tier(0.80, 0.42, 0.15)
    tier(0.62, 0.32, 0.13)
    tier(0.44, 0.21, 0.11)

    # Soft highlight on each tier.
    cr.set_source_rgba(*_HIGHLIGHT, 0.85)
    cr.set_line_width(max(1.0, s * 0.035))
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    for center_y, radius_x in ((0.80, 0.30), (0.62, 0.22), (0.44, 0.13)):
        cr.move_to(s * (0.5 - radius_x), s * (center_y - 0.05))
        cr.line_to(s * (0.5 - radius_x * 0.45), s * (center_y - 0.08))
        cr.stroke()

    # Dot eyes and a tiny smile on the middle tier.
    cr.set_source_rgb(*_FACE)
    for eye_x in (0.42, 0.58):
        cr.arc(s * eye_x, s * 0.61, max(0.8, s * 0.035), 0.0, 2.0 * math.pi)
        cr.fill()
    cr.set_line_width(max(0.8, s * 0.03))
    cr.arc(s * 0.5, s * 0.64, s * 0.06, math.pi * 0.2, math.pi * 0.8)
    cr.stroke()
    cr.restore()
