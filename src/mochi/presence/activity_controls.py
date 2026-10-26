"""User-facing Activity preference layered onto Mochi's idle cadence."""

from __future__ import annotations

from gi.repository import GLib, Gtk

from mochi.activity_level import (
    ACTIVITY_LABELS,
    DEFAULT_ACTIVITY_LEVEL,
    activity_profile,
    next_activity_level,
)
from mochi.i18n import tr


class ActivityLevelMixin:
    """Let the user choose how often Mochi walks and plays on his own."""

    def __init__(self, *args, **kwargs) -> None:
        self._activity_level = DEFAULT_ACTIVITY_LEVEL
        self._activity_value_label: Gtk.Label | None = None
        super().__init__(*args, **kwargs)

    def _build_context_menu(self):
        popover = super()._build_context_menu()
        # Buddy builds the menu before scheduling its first idle opportunity,
        # so the saved level is in effect from startup, like Stay put.
        self._activity_level = self._config.load_activity_level()
        self._apply_activity_profile()

        activity_row, self._activity_value_label = self._make_activity_row()
        # Sleep -> Edge roam -> Stay put -> Activity -> Close.
        self._register_context_menu_row(
            "activity",
            activity_row,
            after="stay-put",
        )
        return popover

    def _apply_activity_profile(self) -> None:
        # Instance attributes shadow Buddy's calm class constants. The idle
        # scheduler, idle selector, and free walk already read them via self,
        # so the level never adds a second behavior path.
        profile = activity_profile(self._activity_level)
        self.IDLE_ACTION_INTERVAL_SECONDS = profile.idle_action_interval_seconds
        self.IDLE_WALK_CHANCE = profile.walk_chance
        self.IDLE_CATALOGUE_EMOTE_CHANCE = profile.catalogue_emote_chance
        self.WALK_DISTANCE_PX = profile.walk_distance_px

    def _make_activity_row(self) -> tuple[Gtk.Button, Gtk.Label]:
        button = Gtk.Button()
        button.add_css_class("mochi-menu-row")
        button.set_tooltip_text(tr("Choose how often Mochi moves and plays on his own"))

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        icon = Gtk.Image.new_from_icon_name("media-playlist-shuffle-symbolic")
        icon.add_css_class("mochi-menu-icon")
        row.append(icon)

        text = Gtk.Label(label=tr("Activity"))
        text.set_xalign(0)
        text.set_hexpand(True)
        row.append(text)

        value = Gtk.Label(label=tr(ACTIVITY_LABELS[self._activity_level]))
        value.set_xalign(1)
        value.add_css_class("mochi-menu-value")
        # Keep the whole row as one reliable target, matching Stay put.
        value.set_can_target(False)
        row.append(value)

        button.set_child(row)
        button.connect("clicked", self._toggle_activity_level)
        return button, value

    def _toggle_activity_level(self, _button: Gtk.Button | None) -> None:
        self._activity_level = next_activity_level(self._activity_level)
        self._config.save_activity_level(self._activity_level)
        self._apply_activity_profile()
        if self._activity_value_label is not None:
            self._activity_value_label.set_text(tr(ACTIVITY_LABELS[self._activity_level]))

        # Replace a pending idle opportunity so the new cadence applies now
        # instead of after the old, possibly 45 s, delay. Buddy keeps owning
        # the source through _idle_action_source_id.
        if self._idle_action_source_id is not None:
            GLib.source_remove(self._idle_action_source_id)
            self._idle_action_source_id = None
            self._schedule_idle_action()

        self._logger.info("Activity level: %s", self._activity_level)
