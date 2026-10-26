"""User-initiated chat with Mochi through a local Ollama server."""

from __future__ import annotations

from collections.abc import Callable
import threading

from gi.repository import Gdk, GLib, Gtk

from mochi.i18n import tr
from mochi.ollama_chat import OllamaChat, OllamaError

from .engine import speech_display_seconds

OLLAMA_THINKING_TEXT = "hmm..."
OLLAMA_UNREACHABLE_TEXT = "my head's in the clouds... i can't think right now"
OLLAMA_THINKING_SECONDS = 120.0
# Generated replies run longer than authored lines; give the reader time.
OLLAMA_CHARS_PER_SECOND = 15.0
OLLAMA_MAX_REPLY_SECONDS = 25.0


def ollama_reply_seconds(text: str) -> float:
    return min(
        OLLAMA_MAX_REPLY_SECONDS,
        max(speech_display_seconds(text), len(text) / OLLAMA_CHARS_PER_SECOND),
    )


class OllamaChatWindow(Gtk.Window):
    """A one-line prompt; Enter sends the message and closes the window."""

    def __init__(self, *, on_send: Callable[[str], None]) -> None:
        super().__init__(title=tr("Talk to Mochi"))
        self.set_default_size(380, -1)
        self.set_resizable(False)
        self._on_send = on_send

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        self._entry = Gtk.Entry()
        self._entry.set_placeholder_text(tr("say something to Mochi..."))
        self._entry.connect("activate", self._on_activate)
        box.append(self._entry)
        self.set_child(box)

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key_pressed)
        self.add_controller(keys)

    def _on_activate(self, entry: Gtk.Entry) -> None:
        text = entry.get_text().strip()
        if text:
            self._on_send(text)
        self.close()

    def _on_key_pressed(self, _controller, keyval, _keycode, _state) -> bool:
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False


class OllamaChatMixin:
    """Add a "Talk to Mochi" menu row whose replies come from Ollama."""

    def __init__(self, *args, **kwargs) -> None:
        self._ollama_chat: OllamaChat | None = None
        self._ollama_window: OllamaChatWindow | None = None
        self._ollama_busy = False
        self._ollama_generation = 0
        self._ollama_shutting_down = False
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

    def _open_ollama_window(self) -> None:
        if self._ollama_shutting_down:
            return
        if self._ollama_window is None:
            window = OllamaChatWindow(on_send=self._send_ollama_message)
            window.connect("close-request", self._on_ollama_window_close_request)
            if getattr(self, "_window", None) is not None:
                window.set_transient_for(self._window)
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
        self._show_ollama_speech(reply, ollama_reply_seconds(reply))
        self._logger.debug("[ollama] reply failed=%s text=%r", failed, reply)
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
        window = self._ollama_window
        self._ollama_window = None
        if window is not None:
            window.destroy()
        super().shutdown_presence()
