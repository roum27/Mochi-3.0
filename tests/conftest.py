"""Shared test setup."""

from __future__ import annotations

import pytest

from mochi import i18n


@pytest.fixture(autouse=True)
def _english_display_language():
    # The suite asserts Mochi's English copy; keep it independent of the
    # developer's own locale (for example LANG=fr_CA.UTF-8).
    i18n.set_language("en")
    yield
    i18n.set_language("en")
