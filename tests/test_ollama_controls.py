from __future__ import annotations

from unittest.mock import Mock

import pytest

from mochi.ollama_chat import OllamaError
from mochi.presence import ollama_controls
from mochi.presence.click_dialogue import PresenceBuddy, PresenceX11Buddy
from mochi.presence.ollama_controls import (
    OLLAMA_THINKING_TEXT,
    OLLAMA_UNREACHABLE_TEXT,
    OllamaChatMixin,
    bubble_text,
    ollama_reply_seconds,
)


class _Base:
    def __init__(self) -> None:
        self._logger = Mock()
        self._presence_bubble = Mock()
        self._presence_bubble.show.return_value = True
        self.dismissed = 0
        self.registered = []
        self.shutdown_calls = 0
        self.workers = []
        self.clicks = 0
        self._press = None
        self._drag_started = False
        self._drag_release_handled = False

    def _on_pressed(self, *args) -> None:
        self._press = (1.0, 1.0)
        self._drag_started = False
        self._drag_release_handled = False

    def _on_released(self, *args) -> None:
        self._press = None
        if not self._drag_release_handled:
            self.clicks += 1

    def _build_context_menu(self):
        return "menu"

    def _make_menu_button(self, label, icon, callback):
        return (label, callback), None

    def _register_context_menu_row(self, row_id, widget, **kwargs):
        self.registered.append((row_id, widget, kwargs))

    def _dismiss_presence_bubble(self, *, user_initiated: bool) -> None:
        self.dismissed += 1

    def shutdown_presence(self) -> None:
        self.shutdown_calls += 1


class _Harness(OllamaChatMixin, _Base):
    def _run_ollama_worker(self, work) -> None:
        self.workers.append(work)


class _Chat:
    def __init__(self, reply=None, error=None) -> None:
        self._reply = reply
        self._error = error
        self.compacted = 0

    def reply(self, text):
        if self._error is not None:
            raise self._error
        return self._reply

    def compact_if_needed(self):
        self.compacted += 1
        return False


class _Window:
    def __init__(self) -> None:
        self.thinking = 0
        self.replies = []

    def show_thinking(self) -> None:
        self.thinking += 1

    def show_reply(self, text, *, copyable) -> None:
        self.replies.append((text, copyable))


class _Timers:
    def __init__(self) -> None:
        self.pending = {}
        self.removed = []
        self._next = 1

    def add(self, delay, callback):
        source_id = self._next
        self._next += 1
        self.pending[source_id] = (delay, callback)
        return source_id

    def remove(self, source_id) -> None:
        self.removed.append(source_id)
        self.pending.pop(source_id, None)

    def fire_all(self) -> None:
        for source_id in list(self.pending):
            _delay, callback = self.pending.pop(source_id)
            callback()


@pytest.fixture(autouse=True)
def timers(monkeypatch):
    monkeypatch.setattr(
        ollama_controls.GLib, "idle_add", lambda callback, *args: callback(*args)
    )
    fake = _Timers()
    monkeypatch.setattr(ollama_controls.GLib, "timeout_add", fake.add)
    monkeypatch.setattr(ollama_controls.GLib, "source_remove", fake.remove)
    return fake


def test_both_buddies_compose_the_chat_mixin() -> None:
    assert issubclass(PresenceBuddy, OllamaChatMixin)
    assert issubclass(PresenceX11Buddy, OllamaChatMixin)


def test_menu_row_sits_before_sleep() -> None:
    harness = _Harness()
    assert harness._build_context_menu() == "menu"
    row_id, (label, _callback), kwargs = harness.registered[0]
    assert row_id == "ollama-chat"
    assert label == "Talk to Mochi..."
    assert kwargs == {"before": "sleep"}


def test_window_shows_thinking_then_keeps_the_full_copyable_reply() -> None:
    harness = _Harness()
    harness._ollama_chat = _Chat(reply="hello there")
    harness._ollama_window = window = _Window()

    harness._send_ollama_message("traduis: salut")
    assert window.thinking == 1
    harness.workers.pop()()

    assert window.replies == [("hello there", True)]
    shown = [call.args[0] for call in harness._presence_bubble.show.call_args_list]
    assert shown == [OLLAMA_THINKING_TEXT]
    assert harness._ollama_last_reply == ("hello there", False)


def test_unreachable_server_in_window_is_not_copyable() -> None:
    harness = _Harness()
    harness._ollama_chat = _Chat(error=OllamaError("connection refused"))
    harness._ollama_window = window = _Window()

    harness._send_ollama_message("salut")
    harness.workers.pop()()

    assert window.replies == [(OLLAMA_UNREACHABLE_TEXT, False)]


def test_holding_mochi_opens_the_chat_without_a_click(timers) -> None:
    harness = _Harness()
    opened = []
    harness._open_ollama_window = lambda: opened.append(True)

    harness._on_pressed()
    [(delay, _callback)] = timers.pending.values()
    assert delay == ollama_controls.OLLAMA_LONG_PRESS_MS
    timers.fire_all()
    harness._on_released()

    assert opened == [True]
    assert harness.clicks == 0


def test_short_click_cancels_the_hold(timers) -> None:
    harness = _Harness()
    opened = []
    harness._open_ollama_window = lambda: opened.append(True)

    harness._on_pressed()
    harness._on_released()

    assert timers.pending == {}
    assert opened == []
    assert harness.clicks == 1


def test_drag_does_not_open_the_chat(timers) -> None:
    harness = _Harness()
    opened = []
    harness._open_ollama_window = lambda: opened.append(True)

    harness._on_pressed()
    harness._drag_started = True
    timers.fire_all()

    assert opened == []


def test_shutdown_cancels_a_pending_hold(timers) -> None:
    harness = _Harness()
    harness._on_pressed()
    harness.shutdown_presence()
    assert timers.pending == {}


def test_message_without_window_answers_in_the_bubble_and_compacts() -> None:
    harness = _Harness()
    harness._ollama_chat = _Chat(reply="allo toi 🌱")

    assert harness._send_ollama_message("salut") is True
    first = harness._presence_bubble.show.call_args_list[0]
    assert first.args == (OLLAMA_THINKING_TEXT,)
    assert harness._send_ollama_message("encore") is False  # busy

    harness.workers.pop()()

    last = harness._presence_bubble.show.call_args_list[-1]
    assert last.args == ("allo toi 🌱",)
    assert "markup" not in last.kwargs
    assert harness._ollama_busy is False
    assert harness._ollama_chat.compacted == 1
    assert harness.dismissed == 2


def test_unreachable_server_shows_fallback_line_without_compacting() -> None:
    harness = _Harness()
    harness._ollama_chat = _Chat(error=OllamaError("connection refused"))

    harness._send_ollama_message("salut")
    harness.workers.pop()()

    last = harness._presence_bubble.show.call_args_list[-1]
    assert last.args == (OLLAMA_UNREACHABLE_TEXT,)
    assert harness._ollama_chat.compacted == 0
    assert harness._ollama_busy is False


def test_reply_after_shutdown_is_dropped() -> None:
    harness = _Harness()
    harness._ollama_chat = _Chat(reply="trop tard")
    harness._send_ollama_message("salut")
    harness.shutdown_presence()

    harness.workers.pop()()

    shown = [call.args[0] for call in harness._presence_bubble.show.call_args_list]
    assert "trop tard" not in shown
    assert harness.shutdown_calls == 1
    assert harness._send_ollama_message("encore") is False


def test_bubble_text_shortens_long_replies() -> None:
    assert bubble_text("oui") == "oui"
    short = bubble_text("a" * 1000)
    assert len(short) == ollama_controls.OLLAMA_MAX_BUBBLE_CHARS
    assert short.endswith("…")


def test_long_replies_stay_up_longer_but_capped() -> None:
    assert ollama_reply_seconds("oui") == 3.5
    assert ollama_reply_seconds("a" * 300) == 20.0
    assert ollama_reply_seconds("a" * 2000) == ollama_controls.OLLAMA_MAX_REPLY_SECONDS
