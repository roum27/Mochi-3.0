"""Display-language selection and the French catalogue."""

from __future__ import annotations

import ast
from pathlib import Path
from string import Formatter

import pytest

from mochi import i18n
from mochi.i18n import language_from_environment, tr
from mochi.locale.fr import FR, PAIRS
from mochi.presence.bond_progress_overlay import LEVEL_UP_REACTION_LINE
from mochi.presence.fedora_mode import FedoraModeMixin
from mochi.presence.focus_session import (
    FOCUS_BREAK_LINE,
    FOCUS_CANCEL_LINE,
    FOCUS_COMPLETE_LINE,
    FOCUS_PAUSE_LINE,
    FOCUS_RESUME_LINE,
    FOCUS_START_LINE,
)
from mochi.presence.phrases import (
    BOND_DIALOGUE,
    CONTEXT_PHRASES,
    EVENT_PHRASES,
    INTRO_MARKUP,
    INTRO_TEXT,
    PHRASES,
)
from mochi.presence.update_controls import UPDATE_BUBBLE_TEXT


SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src" / "mochi"
LOCALE_ROOT = SOURCE_ROOT / "locale"


def _source_trees():
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        if LOCALE_ROOT in path.parents:
            continue
        yield path, ast.parse(path.read_text(encoding="utf-8"))


def _source_string_constants() -> set[str]:
    return {
        node.value
        for _path, tree in _source_trees()
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def _literal_tr_arguments() -> list[tuple[str, str]]:
    found = []
    for path, tree in _source_trees():
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "tr"
                and node.args
            ):
                for candidate in ast.walk(node.args[0]):
                    if isinstance(candidate, ast.Constant) and isinstance(
                        candidate.value, str
                    ):
                        found.append((path.name, candidate.value))
    return found


def _fields(text: str) -> set[str]:
    return {field for _literal, field, _spec, _conv in Formatter().parse(text) if field}


def _spoken_lines() -> set[str]:
    lines = {line.text for phase in BOND_DIALOGUE.values() for line in phase}
    for bank in (PHRASES, CONTEXT_PHRASES, EVENT_PHRASES):
        for choices in bank.values():
            lines.update(choices)
    lines.update(
        {
            FOCUS_START_LINE,
            FOCUS_PAUSE_LINE,
            FOCUS_BREAK_LINE,
            FOCUS_RESUME_LINE,
            FOCUS_COMPLETE_LINE,
            FOCUS_CANCEL_LINE,
            UPDATE_BUBBLE_TEXT,
            FedoraModeMixin.FEDORA_ENGAGED_TEXT,
            LEVEL_UP_REACTION_LINE,
            "wheee!",
        }
    )
    return lines


@pytest.mark.parametrize(
    ("environment", "expected"),
    [
        ({}, "en"),
        ({"LANG": "fr_CA.UTF-8"}, "fr"),
        ({"LANG": "fr_FR.UTF-8"}, "fr"),
        ({"LANG": "en_US.UTF-8"}, "en"),
        ({"LANG": "de_DE.UTF-8"}, "en"),
        ({"LANG": "C.UTF-8"}, "en"),
        ({"LANG": "POSIX"}, "en"),
        ({"LANGUAGE": "fr_CA:fr", "LANG": "en_US.UTF-8"}, "fr"),
        ({"LC_ALL": "en_US.UTF-8", "LANG": "fr_CA.UTF-8"}, "en"),
        ({"LC_MESSAGES": "fr_BE.UTF-8", "LANG": "en_GB.UTF-8"}, "fr"),
        ({"LANG": "fr_CA.UTF-8", "MOCHI_LANGUAGE": "en"}, "en"),
        ({"LANG": "en_US.UTF-8", "MOCHI_LANGUAGE": "FR"}, "fr"),
        ({"LANG": "fr_CA.UTF-8", "MOCHI_LANGUAGE": "klingon"}, "fr"),
    ],
)
def test_language_follows_mochi_override_then_the_locale(environment, expected) -> None:
    assert language_from_environment(environment) == expected


def test_active_language_is_detected_once_and_can_be_reset(monkeypatch) -> None:
    monkeypatch.setenv("MOCHI_LANGUAGE", "fr")
    i18n.set_language(None)
    assert i18n.active_language() == "fr"

    monkeypatch.setenv("MOCHI_LANGUAGE", "en")
    assert i18n.active_language() == "fr"

    i18n.set_language(None)
    assert i18n.active_language() == "en"


def test_unsupported_forced_language_is_rejected() -> None:
    with pytest.raises(ValueError):
        i18n.set_language("de")


def test_tr_is_identity_in_english() -> None:
    assert tr("Feed") == "Feed"
    assert tr("not a catalogue entry") == "not a catalogue entry"


def test_tr_translates_in_french_and_falls_back_to_english() -> None:
    i18n.set_language("fr")
    assert tr("Feed") == "Nourrir"
    assert tr("break time 🌱") == "c'est la pause 🌱"
    assert tr("not a catalogue entry") == "not a catalogue entry"
    assert tr("Bond Lv. {level}").format(level=3) == "Lien niv. 3"


def test_every_spoken_line_has_a_french_translation() -> None:
    missing = sorted(line for line in _spoken_lines() if line not in FR)
    assert not missing


def test_intro_text_and_markup_are_translated() -> None:
    assert FR[INTRO_TEXT].startswith("Salut!")
    assert FR[INTRO_MARKUP].startswith("<b>Salut!")
    assert FR[INTRO_MARKUP].count("<b>") == INTRO_MARKUP.count("<b>")


def test_every_literal_passed_to_tr_has_a_french_translation() -> None:
    missing = sorted({text for _name, text in _literal_tr_arguments() if text not in FR})
    assert not missing


def test_every_catalogue_key_is_real_mochi_source_text() -> None:
    source = _source_string_constants() | {INTRO_TEXT, INTRO_MARKUP}
    unknown = sorted(key for key in FR if key not in source)
    assert not unknown


def test_no_english_string_is_translated_two_ways() -> None:
    seen: dict[str, str] = {}
    conflicts = []
    for english, french in PAIRS:
        if english in seen and seen[english] != french:
            conflicts.append(english)
        seen[english] = french
    assert not conflicts


def test_translations_are_nonempty_and_keep_their_placeholders() -> None:
    for english, french in FR.items():
        assert french.strip(), english
        assert _fields(english) == _fields(french), english


def test_french_speech_keeps_mochis_lowercase_voice() -> None:
    for english in _spoken_lines():
        if english == english.lower():
            assert FR[english] == FR[english].lower(), english
