"""Pick Mochi's display language and translate Mochi's own English copy.

English is the source language. Translations are looked up by the exact
English text, so a string without a translation simply stays English. Only
Mochi's own source strings are ever looked up; nothing here reads user content.
"""

from __future__ import annotations

from collections.abc import Mapping
import os

SUPPORTED_LANGUAGES = ("en", "fr")
DEFAULT_LANGUAGE = "en"

# gettext's precedence: LANGUAGE is a priority list, then the usual LC_* chain.
_LOCALE_VARIABLES = ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG")

_active_language: str | None = None
_catalogue: Mapping[str, str] | None = None


def language_from_environment(environment: Mapping[str, str]) -> str:
    """Return the supported language Mochi should use for this environment."""
    override = environment.get("MOCHI_LANGUAGE", "").strip().casefold()
    if override in SUPPORTED_LANGUAGES:
        return override

    for name in _LOCALE_VARIABLES:
        value = environment.get(name, "").split(":")[0].strip().casefold()
        if not value:
            continue
        if value in ("c", "posix") or value.startswith("c."):
            return DEFAULT_LANGUAGE
        code = value.split("_")[0].split(".")[0].split("@")[0]
        return code if code in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    return DEFAULT_LANGUAGE


def active_language() -> str:
    """Return the display language, resolving it once from the environment."""
    global _active_language
    if _active_language is None:
        _active_language = language_from_environment(os.environ)
    return _active_language


def set_language(language: str | None) -> None:
    """Force a display language, or re-detect it from the environment on None."""
    global _active_language
    if language is not None and language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"unsupported Mochi language: {language}")
    _active_language = language


def tr(text: str) -> str:
    """Translate one of Mochi's English source strings into the active language."""
    if active_language() != "fr":
        return text
    global _catalogue
    if _catalogue is None:
        from mochi.locale.fr import FR

        _catalogue = FR
    return _catalogue.get(text, text)
