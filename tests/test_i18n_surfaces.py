"""The speech bubble and nameplate translate Mochi's English copy on display."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from mochi import i18n
from mochi.presence.bubble import SpeechBubble
from mochi.presence.engine import SpeechText
from mochi.presence.nameplate import Nameplate
from mochi.presence.phrases import INTRO_MARKUP, INTRO_TEXT


def _bubble() -> SpeechBubble:
    bubble = object.__new__(SpeechBubble)
    bubble._can_show = None
    bubble._logger = Mock()
    bubble._window = Mock(get_visible=Mock(return_value=False))
    bubble._popover = Mock(get_visible=Mock(return_value=False))
    bubble._owner = Mock()
    bubble._animation_serial = 0
    for name in (
        "_cancel_sources",
        "_set_text",
        "_position_wayland_anchor",
        "_fade",
        "_schedule_hide",
    ):
        setattr(bubble, name, Mock())
    return bubble


def _show(bubble: SpeechBubble, text: str, **kwargs) -> bool:
    with patch("mochi.presence.bubble.get_window_position", return_value=None):
        return bubble.show(text, duration_seconds=2.0, **kwargs)


@pytest.mark.parametrize(
    ("language", "expected"),
    [("en", "break time 🌱"), ("fr", "c'est la pause 🌱")],
)
def test_bubble_speaks_in_the_display_language(language, expected) -> None:
    i18n.set_language(language)
    bubble = _bubble()

    assert _show(bubble, "break time 🌱") is True

    bubble._set_text.assert_called_once_with(expected, typing=False, markup=None)


def test_bubble_translates_trusted_intro_markup() -> None:
    i18n.set_language("fr")
    bubble = _bubble()

    assert _show(bubble, INTRO_TEXT, markup=INTRO_MARKUP) is True

    text, = bubble._set_text.call_args.args
    assert text.startswith("Salut!")
    assert bubble._set_text.call_args.kwargs["markup"].startswith("<b>Salut!")


def test_bubble_typing_preview_survives_translation() -> None:
    i18n.set_language("fr")
    bubble = _bubble()

    with patch("mochi.presence.bubble.GLib.timeout_add", return_value=7):
        assert _show(bubble, SpeechText("break time 🌱", typing_preview=True)) is True

    assert bubble._pending_text == "c'est la pause 🌱"
    bubble._set_text.assert_called_once_with("Mochi écrit", typing=True)


def test_bubble_leaves_untranslated_text_alone() -> None:
    i18n.set_language("fr")
    bubble = _bubble()

    assert _show(bubble, "some brand new line") is True

    bubble._set_text.assert_called_once_with(
        "some brand new line", typing=False, markup=None
    )


def test_nameplate_feedback_is_translated() -> None:
    i18n.set_language("fr")
    plate = object.__new__(Nameplate)
    plate._refresh_label_text = Mock()

    plate.set_status("  My paws are full ")

    assert plate._status == "J’ai les pattes pleines"
