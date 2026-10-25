"""Static contract checks for the Cinnamon helper.

The Cinnamon extension is a port of the GNOME Shell helper (ES modules there,
legacy CJS imports here), so these checks hold it to the same D-Bus protocol,
privacy reductions, and teardown discipline instead of sharing code.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from mochi.helper_connection import HelperConnection


ROOT = Path(__file__).resolve().parents[1]
GNOME = ROOT / "gnome-extension" / "mochi-typing@miflow13" / "extension.js"
CINNAMON_DIR = ROOT / "cinnamon-extension" / "mochi-activity@miflow13"
CINNAMON = CINNAMON_DIR / "extension.js"


def _gnome() -> str:
    return GNOME.read_text(encoding="utf-8")


def _cinnamon() -> str:
    return CINNAMON.read_text(encoding="utf-8")


def _constants(source: str) -> dict[str, str]:
    return dict(re.findall(r"^const ([A-Z_]+) = (.+);$", source, flags=re.MULTILINE))


def _markers(source: str, name: str) -> list[str]:
    body = re.search(rf"const {name} = \[(.*?)\];", source, flags=re.DOTALL)
    assert body is not None, name
    entries = re.sub(r"//[^\n]*", "", body.group(1))
    return re.findall(r"'([^']+)'", entries)


def _method_body(source: str, signature: str) -> str:
    start = source.index(signature)
    following = source.find("\n    _", start + len(signature))
    return source[start:] if following == -1 else source[start:following]


def test_metadata_is_a_valid_cinnamon_extension() -> None:
    metadata = json.loads((CINNAMON_DIR / "metadata.json").read_text(encoding="utf-8"))

    assert metadata["uuid"] == CINNAMON_DIR.name
    assert metadata["name"]
    assert metadata["description"]
    assert metadata["url"].startswith("https://")
    assert metadata["cinnamon-version"]
    assert all(re.fullmatch(r"\d+\.\d+", version) for version in metadata["cinnamon-version"])


def test_bus_identity_matches_mochis_helper_connection() -> None:
    constants = _constants(_cinnamon())

    assert constants["BUS_NAME"] == f"'{HelperConnection.BUS_NAME}'"
    assert constants["OBJECT_PATH"] == f"'{HelperConnection.OBJECT_PATH}'"
    assert constants["INTERFACE_NAME"] == f"'{HelperConnection.INTERFACE}'"


def test_signals_and_timing_match_the_gnome_helper() -> None:
    gnome = _constants(_gnome())
    cinnamon = _constants(_cinnamon())

    shared = [
        name
        for name in gnome
        if name.endswith("_SIGNAL_NAME")
        or name.endswith("_MS")
        or name in ("TAB_TITLE_BADGE_PATTERN", "BUS_NAME", "OBJECT_PATH", "INTERFACE_NAME")
    ]
    assert shared
    for name in shared:
        assert cinnamon.get(name) == gnome[name], name


def test_get_state_exports_the_same_snapshot() -> None:
    gnome = _gnome()
    cinnamon = _cinnamon()

    for snippet in (
        '<method name="GetState">',
        '<arg type="b" direction="out" name="idle"/>',
        '<arg type="b" direction="out" name="fileBrowsing"/>',
        '<arg type="b" direction="out" name="youtubeFocused"/>',
        '<arg type="s" direction="out" name="appCategory"/>',
    ):
        assert snippet in gnome
        assert snippet in cinnamon
    assert (
        "return [this._presenceIsIdle, this._fileBrowsingActive,\n"
        "            this._youtubeFocusedActive, this._appCategory];"
    ) in cinnamon


@pytest.mark.parametrize(
    "name",
    [
        "FILE_MANAGER_MARKERS",
        "VSCODE_MARKERS",
        "EDITOR_MARKERS",
        "TERMINAL_MARKERS",
        "PIXEL_ART_MARKERS",
        "MEDIA_APP_MARKERS",
        "BROWSER_MARKERS",
        "BROWSER_TITLE_NAMES",
    ],
)
def test_classification_keeps_every_gnome_marker(name: str) -> None:
    missing = set(_markers(_gnome(), name)) - set(_markers(_cinnamon(), name))
    assert not missing


def test_classification_knows_linux_mint_defaults() -> None:
    source = _cinnamon()

    for marker in ("xfce4-terminal", "mate-terminal", "tilix", "terminator"):
        assert marker in _markers(source, "TERMINAL_MARKERS")
    assert {"org.x.editor", "xed"} <= set(_markers(source, "EDITOR_MARKERS"))
    assert "xplayer" in _markers(source, "MEDIA_APP_MARKERS")
    assert "nemo" in _markers(source, "FILE_MANAGER_MARKERS")


def test_uses_muffin_entry_points() -> None:
    source = _cinnamon()

    assert "Meta.get_backend()" in source
    assert "Meta.IdleMonitor.get_core()" in source
    assert "'last-device-changed'" in source
    assert "Clutter.InputDeviceType.KEYBOARD_DEVICE" in source
    assert "'notify::focus-window'" in source
    for function in ("function init(", "function enable(", "function disable("):
        assert function in source


def test_shortcuts_are_registered_and_removed() -> None:
    source = _cinnamon()

    assert "const EMOTE_CATALOGUE_HOTKEY = '<Ctrl><Alt>e';" in source
    assert "const DEVELOPER_MENU_HOTKEY = '<Ctrl><Alt><Shift>m';" in source
    assert source.count("Main.keybindingManager.addHotKey(") == 2
    assert "Main.keybindingManager.removeHotKey(EMOTE_CATALOGUE_KEYBINDING);" in source
    assert "Main.keybindingManager.removeHotKey(DEVELOPER_MENU_KEYBINDING);" in source


def test_never_inspects_key_identity_or_logs_window_data() -> None:
    source = _cinnamon()

    for forbidden in (
        "get_key_symbol",
        "get_key_code",
        "get_key_unicode",
        "get_state()",
        "console.",
        "global.log",
        "log(",
        "print(",
    ):
        assert forbidden not in source, forbidden


def test_titles_are_read_only_for_youtube_and_tab_digests() -> None:
    source = _cinnamon()

    assert source.count("get_title()") == 2
    assert "get_title()" in _method_body(source, "_isFocusedYouTubeWindow(window) {")
    digest = _method_body(source, "_tabTitleDigestFor(window) {")
    assert "get_title()" in digest
    assert "GLib.ChecksumType.SHA256" in digest


def test_every_long_lived_source_is_torn_down() -> None:
    source = _cinnamon()
    teardown = _method_body(source, "disable() {")

    assert source.count("GLib.timeout_add(") == 2
    assert "GLib.Source.remove(this._pollSourceId);" in teardown
    assert "GLib.Source.remove(this._videoFocusHeartbeatId);" in teardown
    assert "this._idleMonitor.remove_watch(this._presenceIdleWatchId);" in teardown
    assert "this._idleMonitor.remove_watch(this._presenceActiveWatchId);" in teardown
    assert "this._backend.disconnect(this._lastDeviceChangedId);" in teardown
    assert "global.display.disconnect(this._focusChangedId);" in teardown
    assert "this._untrackBrowserTabTitle();" in teardown
    assert "this._dbusObject.unexport();" in teardown
    assert "Gio.bus_unown_name(this._nameOwnerId);" in teardown


@pytest.mark.skipif(shutil.which("cjs") is None, reason="cjs is unavailable")
def test_extension_source_parses_under_cjs() -> None:
    # Parse only: executing it would need a running Cinnamon for imports.ui.
    script = (
        "const [ok, bytes] = imports.gi.GLib.file_get_contents(ARGV[0]);\n"
        "new Function(new TextDecoder().decode(bytes));\n"
    )
    completed = subprocess.run(
        ["cjs", "-c", script, str(CINNAMON)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
