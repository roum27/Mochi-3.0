"""User-initiated chat with Mochi through a local Ollama server."""

from __future__ import annotations

from collections.abc import Callable
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from mochi.i18n import tr  # noqa: E402
from mochi.ollama_chat import OllamaChat, OllamaError  # noqa: E402

from .engine import speech_display_seconds  # noqa: E402

OLLAMA_THINKING_TEXT = "hmm..."
OLLAMA_UNREACHABLE_TEXT = "my head's in the clouds... i can't think right now"
OLLAMA_THINKING_SECONDS = 120.0
OLLAMA_LONG_PRESS_MS = 1_500
# Generated replies run longer than authored lines; give the reader time.
OLLAMA_CHARS_PER_SECOND = 15.0
OLLAMA_MAX_REPLY_SECONDS = 25.0
OLLAMA_MAX_BUBBLE_CHARS = 300


def ollama_reply_seconds(text: str) -> float:
    return min(
        OLLAMA_MAX_REPLY_SECONDS,
        max(speech_display_seconds(text), len(text) / OLLAMA_CHARS_PER_SECOND),
    )


def bubble_text(text: str) -> str:
    """Shorten a reply for the speech bubble; the window keeps the full text."""
    if len(text) <= OLLAMA_MAX_BUBBLE_CHARS:
        return text
    return text[: OLLAMA_MAX_BUBBLE_CHARS - 1].rstrip() + "…"


class OllamaChatWindow(Gtk.Window):
    """A prompt plus a selectable reply that stays until the user closes it.

    Enter sends, Shift+Enter adds a new line, Escape closes the window.
    """

    def __init__(self, *, on_send: Callable[[str], bool]) -> None:
        super().__init__(title=tr("Talk to Mochi"))
        self.set_default_size(480, 380)
        self._on_send = on_send

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        self._input = Gtk.TextView()
        self._input.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._input.set_top_margin(6)
        self._input.set_bottom_margin(6)
        self._input.set_left_margin(6)
        self._input.set_right_margin(6)
        input_scroll = Gtk.ScrolledWindow()
        input_scroll.set_min_content_height(90)
        input_scroll.set_child(self._input)
        input_scroll.add_css_class("frame")
        box.append(input_scroll)

        hint = Gtk.Label(label=tr("Enter to send · Shift+Enter for a new line"))
        hint.set_xalign(0)
        hint.add_css_class("dim-label")
        box.append(hint)

        self._reply = Gtk.TextView()
        self._reply.set_editable(False)
        self._reply.set_cursor_visible(False)
        self._reply.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._reply.set_top_margin(6)
        self._reply.set_bottom_margin(6)
        self._reply.set_left_margin(6)
        self._reply.set_right_margin(6)
        reply_scroll = Gtk.ScrolledWindow()
        reply_scroll.set_vexpand(True)
        reply_scroll.set_child(self._reply)
        reply_scroll.add_css_class("frame")
        box.append(reply_scroll)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.set_halign(Gtk.Align.END)
        self._copy_button = Gtk.Button(label=tr("Copy"))
        self._copy_button.connect("clicked", self._on_copy_clicked)
        self._copy_button.set_sensitive(False)
        self._send_button = Gtk.Button(label=tr("Send"))
        self._send_button.add_css_class("suggested-action")
        self._send_button.connect("clicked", lambda _button: self._send())
        actions.append(self._copy_button)
        actions.append(self._send_button)
        box.append(actions)
        self.set_child(box)

        keys = Gtk.EventControllerKey()
        keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self._on_key_pressed)
        self.add_controller(keys)
        self._input.grab_focus()

    def show_thinking(self) -> None:
        self._set_reply(tr(OLLAMA_THINKING_TEXT), copyable=False)
        self._send_button.set_sensitive(False)

    def show_reply(self, text: str, *, copyable: bool) -> None:
        self._set_reply(text, copyable=copyable)
        self._send_button.set_sensitive(True)
        self._input.grab_focus()

    def _set_reply(self, text: str, *, copyable: bool) -> None:
        self._reply.get_buffer().set_text(text, -1)
        self._copy_button.set_label(tr("Copy"))
        self._copy_button.set_sensitive(copyable)

    def _send(self) -> None:
        buffer = self._input.get_buffer()
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False).strip()
        if text and self._on_send(text):
            buffer.set_text("", -1)

    def _on_copy_clicked(self, _button: Gtk.Button) -> None:
        buffer = self._reply.get_buffer()
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
        self.get_clipboard().set(text)
        self._copy_button.set_label(tr("Copied!"))

    def _on_key_pressed(self, _controller, keyval, _keycode, state) -> bool:
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        if (
            keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter)
            and self._input.has_focus()
            and not state & Gdk.ModifierType.SHIFT_MASK
        ):
            self._send()
            return True
        return False


class OllamaChatMixin:
    """Open a chat with Mochi from the menu or a 1.5 s press; replies come from Ollama."""

    def __init__(self, *args, **kwargs) -> None:
        self._ollama_chat: OllamaChat | None = None
        self._ollama_window: OllamaChatWindow | None = None
        self._ollama_busy = False
        self._ollama_last_reply: tuple[str, bool] | None = None
        self._ollama_generation = 0
        self._ollama_shutting_down = False
        self._ollama_long_press_source_id: int | None = None
        self._ollama_long_press_fired = False
        super().__init__(*args, **kwargs)

    def _build_context_menu(self):
        menu = super()._build_context_menu()
        button, _ = self._make_menu_button(
            "Talk to Mochi...",
            "user-available-symbolic",
            self._on_ollama_menu_clicked,
        )
        self._register_context_menu_row("ollama-chat", button, before="sleep")
        return menu

    def _on_ollama_menu_clicked(self, _button: Gtk.Button) -> None:
        self._close_context_menu_then(self._open_ollama_window)

    def _on_pressed(self, *args) -> None:
        super()._on_pressed(*args)
        self._cancel_ollama_long_press()
        self._ollama_long_press_fired = False
        if not getattr(self, "_preview_mode", False) and not self._ollama_shutting_down:
            self._ollama_long_press_source_id = GLib.timeout_add(
                OLLAMA_LONG_PRESS_MS,
                self._on_ollama_long_press,
            )

    def _on_ollama_long_press(self) -> bool:
        self._ollama_long_press_source_id = None
        # A press that turned into a drag, or already ended, is not a hold.
        if getattr(self, "_press", None) is None or getattr(self, "_drag_started", False):
            return GLib.SOURCE_REMOVE
        self._ollama_long_press_fired = True
        self._open_ollama_window()
        return GLib.SOURCE_REMOVE

    def _on_released(self, *args) -> None:
        self._cancel_ollama_long_press()
        if self._ollama_long_press_fired:
            # The hold already opened the chat; do not also count a click.
            self._ollama_long_press_fired = False
            self._drag_release_handled = True
        super()._on_released(*args)

    def _cancel_ollama_long_press(self) -> None:
        source_id = self._ollama_long_press_source_id
        self._ollama_long_press_source_id = None
        if source_id is not None:
            GLib.source_remove(source_id)

    def _open_ollama_window(self) -> None:
        if self._ollama_shutting_down:
            return
        if self._ollama_window is None:
            window = OllamaChatWindow(on_send=self._send_ollama_message)
            window.connect("close-request", self._on_ollama_window_close_request)
            if getattr(self, "_window", None) is not None:
                window.set_transient_for(self._window)
            if self._ollama_busy:
                window.show_thinking()
            elif self._ollama_last_reply is not None:
                text, failed = self._ollama_last_reply
                window.show_reply(text, copyable=not failed)
            self._ollama_window = window
        self._ollama_window.present()

    def _on_ollama_window_close_request(self, window: Gtk.Window) -> bool:
        if window is self._ollama_window:
            self._ollama_window = None
        return False

    def _send_ollama_message(self, text: str) -> bool:
        if self._ollama_busy or self._ollama_shutting_down:
            return False
        if self._ollama_chat is None:
            self._ollama_chat = OllamaChat(logger=self._logger)
        self._ollama_busy = True
        if self._ollama_window is not None:
            self._ollama_window.show_thinking()
        # Speech keeps English keys; the bubble translates them once.
        self._show_ollama_speech(OLLAMA_THINKING_TEXT, OLLAMA_THINKING_SECONDS)

        chat = self._ollama_chat
        generation = self._ollama_generation

        def work() -> None:
            try:
                reply, failed = chat.reply(text), False
            except (OllamaError, OSError, ValueError) as error:
                self._logger.warning("[ollama] chat failed: %s", error)
                reply, failed = OLLAMA_UNREACHABLE_TEXT, True
            GLib.idle_add(self._apply_ollama_reply, reply, failed, generation)
            if not failed:
                try:
                    chat.compact_if_needed()
                except (OllamaError, OSError, ValueError) as error:
                    self._logger.warning("[ollama] memory compaction failed: %s", error)

        self._run_ollama_worker(work)
        return True

    def _run_ollama_worker(self, work: Callable[[], None]) -> None:
        threading.Thread(target=work, name="mochi-ollama-chat", daemon=True).start()

    def _apply_ollama_reply(self, reply: str, failed: bool, generation: int) -> bool:
        if generation != self._ollama_generation or self._ollama_shutting_down:
            return GLib.SOURCE_REMOVE
        self._ollama_busy = False
        self._ollama_last_reply = (reply, failed)
        self._logger.debug("[ollama] reply failed=%s text=%r", failed, reply)
        window = self._ollama_window
        if window is not None:
            # The window holds the full, copyable reply until it is closed.
            window.show_reply(tr(reply) if failed else reply, copyable=not failed)
            self._dismiss_presence_bubble(user_initiated=False)
        else:
            short = bubble_text(reply)
            self._show_ollama_speech(short, ollama_reply_seconds(short))
        return GLib.SOURCE_REMOVE

    def _show_ollama_speech(self, text: str, seconds: float) -> bool:
        bubble = getattr(self, "_presence_bubble", None)
        if bubble is None:
            return False
        # A direct answer to the user replaces whatever Mochi was saying. The
        # text is shown as plain text, never as markup.
        self._dismiss_presence_bubble(user_initiated=False)
        return bubble.show(text, duration_seconds=seconds)

    def shutdown_presence(self) -> None:
        self._ollama_shutting_down = True
        self._ollama_generation += 1
        self._cancel_ollama_long_press()
        window = self._ollama_window
        self._ollama_window = None
        if window is not None:
            window.destroy()
        super().shutdown_presence()
