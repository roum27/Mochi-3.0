"""Assemble Mochi's French catalogue."""

from __future__ import annotations

from html import escape

from mochi.presence.phrases import INTRO_LINES, INTRO_MARKUP, INTRO_TEXT

from .fr_phrases import (
    BOND_DIALOGUE_FR,
    FEATURE_SPEECH_FR,
    INTRO_LINES_FR,
    PHRASES_FR,
)
from .fr_ui import UI_FR

PAIRS: tuple[tuple[str, str], ...] = (
    *BOND_DIALOGUE_FR,
    *PHRASES_FR,
    *FEATURE_SPEECH_FR,
    *UI_FR,
)

FR: dict[str, str] = dict(PAIRS)

# The intro is shown both as plain text and as Mochi-authored markup; build the
# French markup the same way phrases.py builds INTRO_MARKUP.
assert len(INTRO_LINES_FR) == len(INTRO_LINES)
FR[INTRO_TEXT] = "\n".join(INTRO_LINES_FR)
FR[INTRO_MARKUP] = "\n".join(
    f"<b>{escape(line)}</b>" if index in (0, 2) else escape(line)
    for index, line in enumerate(INTRO_LINES_FR)
)
