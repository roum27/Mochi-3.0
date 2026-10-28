"""Little poops Mochi leaves on the desktop, cleaned up with a click."""

from __future__ import annotations

from collections.abc import Callable
import random
import time

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from mochi.droppings import (  # noqa: E402
    DROPPING_CHECK_INTERVAL_SECONDS,
    DROPPING_SIZE_PX,
    MAX_DROPPINGS,
    DroppingSchedule,
    draw_dropping,
    dropping_position,
)
from mochi.i18n import tr  # noqa: E402
from mochi.state import MochiState  # noqa: E402
from mochi.x11 import get_window_position, move_window, request_keep_above  # noqa: E402


class DroppingWindow:
    """One tiny always-on-top poop window that a click cleans away."""

    FADE_SECONDS = 0.2
    _css_installed = False

    def __init__(
        self,
        *,
        owner: Gtk.Window,
        on_cleaned: Callable[["DroppingWindow"], None],
    ) -> None:
        self._on_cleaned = on_cleaned
        self._fade_source_id: int | None = None
        self._position: tuple[int, int] | None = None
        self._cleaning = False
        self._destroyed = False

        area = Gtk.DrawingArea()
        area.set_content_width(DROPPING_SIZE_PX)
        area.set_content_height(DROPPING_SIZE_PX)
        area.set_draw_func(self._draw)
        area.set_cursor_from_name("pointer")
        click = Gtk.GestureClick()
        click.set_button(Gdk.BUTTON_PRIMARY)
        click.connect("released", self._on_released)
        area.add_controller(click)

        self._window = Gtk.Window()
        self._window.set_decorated(False)
        self._window.set_resizable(False)
        self._window.set_modal(False)
        self._window.set_focusable(False)
        self._window.set_transient_for(owner)
        self._window.set_default_size(DROPPING_SIZE_PX, DROPPING_SIZE_PX)
        self._window.add_css_class("mochi-dropping-window")
        self._window.set_child(area)
        self._window.connect("map", self._on_map)
        self._install_css(owner.get_display())

    def show_at(self, x: int, y: int) -> None:
        self._position = (x, y)
        # Stay invisible until the X11 move lands so it never flashes at 0,0.
        self._window.set_opacity(0.0)
        self._window.present()

    def clean(self) -> None:
        if self._cleaning or self._destroyed:
            return
        self._cleaning = True
        started_at = time.monotonic()

        def fade() -> bool:
            progress = (time.monotonic() - started_at) / self.FADE_SECONDS
            if progress < 1.0:
                self._window.set_opacity(max(0.0, 1.0 - progress))
                return GLib.SOURCE_CONTINUE
            self._fade_source_id = None
            self.destroy()
            self._on_cleaned(self)
            return GLib.SOURCE_REMOVE

        self._fade_source_id = GLib.timeout_add(16, fade)

    def destroy(self) -> None:
        if self._destroyed:
            return
        self._destroyed = True
        source_id = self._fade_source_id
        self._fade_source_id = None
        if source_id is not None:
            try:
                GLib.source_remove(source_id)
            except Exception:
                pass
        self._window.destroy()

    def _draw(self, _area, cr, width: int, height: int, *_args) -> None:
        draw_dropping(cr, min(width, height))

    def _on_released(self, _gesture, _n_press, _x, _y) -> None:
        self.clean()

    def _on_map(self, _window: Gtk.Window) -> None:
        request_keep_above(self._window)
        if self._position is not None:
            move_window(self._window, *self._position)
        if not self._cleaning:
            self._window.set_opacity(1.0)

    @classmethod
    def _install_css(cls, display: Gdk.Display) -> None:
        if cls._css_installed:
            return
        cls._css_installed = True
        provider = Gtk.CssProvider()
        provider.load_from_string(
            """
            window.mochi-dropping-window {
                background: transparent;
            }
            """
        )
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )


class DroppingsMixin:
    """Let Mochi leave a little poop now and then; a click cleans it up.

    Poops are a joke, not a chore: they never touch mood, bond, XP or speech.
    The mixin owns one recurring check timer and every live poop window, and
    removes all of them when the switch is turned off or Mochi shuts down.
    """

    DROPPING_ELIGIBLE_STATES = (MochiState.IDLE, MochiState.WALKING)

    def __init__(self, *args, **kwargs) -> None:
        self._droppings_enabled = False
        self._droppings: list = []
        self._dropping_schedule = DroppingSchedule()
        self._dropping_source_id: int | None = None
        self._droppings_switch: Gtk.Switch | None = None
        self._dropping_factory = DroppingWindow
        super().__init__(*args, **kwargs)
        self._start_droppings()

    def _droppings_supported(self) -> bool:
        # Layer shell cannot place free top-level windows, so poops need X11.
        return not self._preview_mode and not getattr(
            self._placement, "layer_shell_enabled", False
        )

    def _build_context_menu(self):
        popover = super()._build_context_menu()
        self._droppings_enabled = self._config.load_droppings_enabled()
        if self._droppings_supported():
            row, self._droppings_switch = self._make_droppings_row()
            # Sleep -> Edge roam -> Stay put -> Activity -> Little poops -> Close.
            self._register_context_menu_row("little-poops", row, after="activity")
        return popover

    def _build_developer_menu(self):
        popover = super()._build_developer_menu()
        if self._droppings_supported():
            button, _ = self._make_menu_button(
                "Leave a poop now",
                "user-trash-symbolic",
                self._test_leave_dropping,
            )
            self._developer_menu_content.append(button)
            self._developer_menu_animated_rows = (
                *self._developer_menu_animated_rows,
                button,
            )
        return popover

    def _make_droppings_row(self) -> tuple[Gtk.Button, Gtk.Switch]:
        button = Gtk.Button()
        button.add_css_class("mochi-menu-row")
        button.set_tooltip_text(
            tr("Mochi sometimes leaves a little poop on the screen. Click it to clean up.")
        )

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        icon = Gtk.Image.new_from_icon_name("user-trash-symbolic")
        icon.add_css_class("mochi-menu-icon")
        row.append(icon)

        text = Gtk.Label(label=tr("Little poops"))
        text.set_xalign(0)
        text.set_hexpand(True)
        row.append(text)

        switch = Gtk.Switch()
        switch.set_valign(Gtk.Align.CENTER)
        switch.set_active(self._droppings_enabled)
        # Keep the whole row as one reliable target, matching Stay put.
        switch.set_can_target(False)
        switch.set_focusable(False)
        row.append(switch)

        button.set_child(row)
        button.connect("clicked", self._toggle_droppings)
        return button, switch

    def _toggle_droppings(self, _button=None) -> None:
        self._droppings_enabled = not self._droppings_enabled
        self._config.save_droppings_enabled(self._droppings_enabled)
        if self._droppings_switch is not None:
            self._droppings_switch.set_active(self._droppings_enabled)
        if self._droppings_enabled:
            self._start_droppings()
        else:
            self._stop_droppings()
        self._logger.info(
            "Little poops %s", "enabled" if self._droppings_enabled else "disabled"
        )

    def _start_droppings(self) -> None:
        if (
            not self._droppings_enabled
            or not self._droppings_supported()
            or getattr(self, "_presence_shutting_down", False)
            or self._dropping_source_id is not None
        ):
            return
        self._dropping_schedule.start()
        self._dropping_source_id = GLib.timeout_add_seconds(
            DROPPING_CHECK_INTERVAL_SECONDS, self._on_dropping_check
        )

    def _stop_droppings(self) -> None:
        source_id = self._dropping_source_id
        self._dropping_source_id = None
        if source_id is not None:
            try:
                GLib.source_remove(source_id)
            except Exception:
                pass
        self._dropping_schedule.stop()
        droppings = list(self._droppings)
        self._droppings.clear()
        for dropping in droppings:
            dropping.destroy()

    def _on_dropping_check(self) -> bool:
        if self._dropping_schedule.is_due() and self._leave_dropping():
            self._dropping_schedule.start()
        # Not due or not a good moment: just look again at the next check.
        return GLib.SOURCE_CONTINUE

    def _can_leave_dropping(self) -> bool:
        return (
            self._droppings_supported()
            and len(self._droppings) < MAX_DROPPINGS
            and not getattr(self, "_presence_shutting_down", False)
            and self.state.current in self.DROPPING_ELIGIBLE_STATES
            and not self._context_menu_open
            and getattr(self, "_focus_session", None) is None
        )

    def _leave_dropping(self) -> bool:
        if not self._can_leave_dropping():
            return False
        anchor = self._dropping_anchor()
        if anchor is None:
            return False
        left, right, bottom, monitor, size = anchor
        x, y = dropping_position(
            visible_left=left,
            visible_right=right,
            visible_bottom=bottom,
            size=size,
            side=random.choice(("left", "right")),
            monitor=monitor,
        )
        dropping = self._dropping_factory(
            owner=self._window,
            on_cleaned=self._on_dropping_cleaned,
        )
        self._droppings.append(dropping)
        dropping.show_at(x, y)
        self._logger.debug("Little poop left at (%d,%d)", x, y)
        return True

    def _dropping_anchor(self):
        """Return Mochi's visible feet line and monitor in X11 root pixels."""
        origin = get_window_position(self._window)
        if origin is None:
            return None
        owner_x, owner_y = origin
        scale = self._placement._x11_coordinate_scale()
        width = max(1, self.get_width())
        height = max(1, self.get_height())
        frame = self.player.frame
        if frame is not None:
            visible_x, visible_y, visible_width, visible_height = (
                self.atlas.visible_bounds(frame, width, height)
            )
        else:
            visible_x, visible_y, visible_width, visible_height = 0, 0, width, height

        monitor = self._placement._monitor_for_position(owner_x, owner_y)
        if monitor is None:
            return None
        geometry = monitor.get_geometry()
        left = owner_x + visible_x * scale
        return (
            left,
            left + visible_width * scale,
            owner_y + (visible_y + visible_height) * scale,
            (
                geometry.x * scale,
                geometry.y * scale,
                geometry.width * scale,
                geometry.height * scale,
            ),
            DROPPING_SIZE_PX * scale,
        )

    def _on_dropping_cleaned(self, dropping) -> None:
        if dropping in self._droppings:
            self._droppings.remove(dropping)
            self._logger.debug("Little poop cleaned up")

    def _test_leave_dropping(self, _button=None) -> None:
        self._close_developer_menu_then(self._leave_dropping)

    def shutdown_presence(self) -> None:
        self._stop_droppings()
        super().shutdown_presence()
