// Mochi's Cinnamon helper: a port of gnome-extension/mochi-typing@miflow13.
//
// Cinnamon runs on Muffin (a Mutter fork) and loads extensions as legacy CJS
// scripts with init()/enable()/disable(). The D-Bus protocol, timing, and
// privacy reductions below match the GNOME helper exactly, so Mochi's Python
// side needs no Cinnamon-specific code. tests/test_cinnamon_helper.py keeps
// the two in step.

const Clutter = imports.gi.Clutter;
const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;
const Meta = imports.gi.Meta;

const Main = imports.ui.main;

const BUS_NAME = 'io.github.mochi_desktop.Mochi.TypingMonitor';
const OBJECT_PATH = '/io/github/mochi_desktop/Mochi/TypingMonitor';
const INTERFACE_NAME = 'io.github.mochi_desktop.Mochi.TypingMonitor';
const TYPING_SIGNAL_NAME = 'Pulse';
const USER_IDLE_SIGNAL_NAME = 'UserIdle';
const USER_ACTIVE_SIGNAL_NAME = 'UserActive';
const FILE_BROWSING_STARTED_SIGNAL_NAME = 'FileBrowsingStarted';
const FILE_BROWSING_STOPPED_SIGNAL_NAME = 'FileBrowsingStopped';
const YOUTUBE_FOCUSED_STARTED_SIGNAL_NAME = 'YouTubeFocusedStarted';
const YOUTUBE_FOCUSED_STOPPED_SIGNAL_NAME = 'YouTubeFocusedStopped';
const APP_CATEGORY_SIGNAL_NAME = 'AppCategoryChanged';
const APP_FOCUS_SIGNAL_NAME = 'AppFocusChanged';
const BROWSER_TAB_SIGNAL_NAME = 'BrowserTabChanged';
// Tab switches and link clicks follow real input within this window. Unread
// counters, title blinkers, and autoplay retitles happen hands-off.
const TAB_INPUT_WINDOW_MS = 2000;
// "(3) Inbox" and "(99+) Chat": an unread badge is not a new tab or page.
const TAB_TITLE_BADGE_PATTERN = /^\(\d+\+?\)\s*/;
const DEVELOPER_MENU_SIGNAL_NAME = 'DeveloperMenuRequested';
const EMOTE_CATALOGUE_SIGNAL_NAME = 'EmoteCatalogueRequested';
// Cinnamon has no per-extension settings schema convention, so the GNOME
// helper's default bindings are fixed here.
const DEVELOPER_MENU_KEYBINDING = 'mochi-developer-menu-shortcut';
const DEVELOPER_MENU_HOTKEY = '<Ctrl><Alt><Shift>m';
const EMOTE_CATALOGUE_KEYBINDING = 'mochi-emote-catalogue-shortcut';
const EMOTE_CATALOGUE_HOTKEY = '<Ctrl><Alt>e';

// These are application identifiers only. Window titles, folder names, file
// names, and paths are never inspected or transmitted to Mochi.
const FILE_MANAGER_MARKERS = [
    'org.gnome.nautilus',
    'nautilus',
    'org.kde.dolphin',
    'dolphin',
    'thunar',
    'nemo',
    'pcmanfm',
    'pcmanfm-qt',
    'caja',
];

// Presence receives only one of these broad categories. The raw application
// identity used to classify it remains inside Cinnamon.
const VSCODE_MARKERS = [
    'code',
    'code-oss',
    'com.visualstudio.code',
    'com.visualstudio.code.oss',
    'visual-studio-code',
];
const EDITOR_MARKERS = [
    'vscodium',
    'codium',
    'cursor',
    'zed',
    'sublime_text',
    'sublime-text',
    'org.gnome.builder',
    'gnome-builder',
    'jetbrains-',
    'pycharm',
    'idea',
    'kate',
    // Linux Mint's default text editor.
    'org.x.editor',
    'xed',
];
const TERMINAL_MARKERS = [
    'org.gnome.terminal',
    'gnome-terminal',
    'org.gnome.ptyxis',
    'ptyxis',
    'kitty',
    'alacritty',
    'wezterm',
    'org.gnome.console',
    'kgx',
    'konsole',
    'foot',
    // Terminals commonly found on Linux Mint.
    'xfce4-terminal',
    'mate-terminal',
    'tilix',
    'terminator',
];
const PIXEL_ART_MARKERS = [
    'pixelorama',
    'com.orama-interactive.pixelorama',
];
const MEDIA_APP_MARKERS = [
    'org.videolan.vlc',
    'vlc',
    'mpv',
    'celluloid',
    'org.gnome.totem',
    'totem',
    'showtime',
    // Linux Mint's X-Apps video player.
    'xplayer',
];

// Same two-minute sleep behavior as the GNOME helper, driven by Muffin's
// server-global idle monitor.
const USER_IDLE_AFTER_MS = 120_000;

// Muffin reports which hardware class produced the latest input through
// Meta.Backend's last-device-changed signal; the core idle monitor resets on
// every input event. Together they yield an anonymous keyboard pulse.
//
// Privacy boundary: we never inspect key symbols, keycodes, Unicode values,
// modifiers, text, shortcuts, file names, folder names, or application content.
// Application identity is inspected only inside Cinnamon and reduced to a
// coarse category before it crosses D-Bus.
const POLL_INTERVAL_MS = 50;
const EVENT_TIME_EPSILON_MS = 12;
const VIDEO_FOCUS_HEARTBEAT_MS = 1_000;
const BROWSER_MARKERS = [
    'google-chrome',
    'com.google.chrome',
    'chromium',
    'chrome',
    'firefox',
    'mozilla.firefox',
    'brave',
    'vivaldi',
    'microsoft-edge',
    'microsoft.edge',
    'msedge',
];
const BROWSER_TITLE_NAMES = [
    'google chrome',
    'chromium',
    'chrome',
    'mozilla firefox',
    'firefox',
    'brave',
    'vivaldi',
    'microsoft edge',
];

function normalizeTabTitle(title) {
    return String(title ?? '').trim().replace(TAB_TITLE_BADGE_PATTERN, '');
}

function shouldEmitTabPulse(idleMs) {
    return Number.isFinite(idleMs) && idleMs >= 0 && idleMs < TAB_INPUT_WINDOW_MS;
}

function windowIdentities(window) {
    const identities = [];
    for (const methodName of [
        'get_gtk_application_id',
        'get_wm_class',
        'get_wm_class_instance',
    ]) {
        try {
            const method = window[methodName];
            if (typeof method !== 'function')
                continue;
            const value = method.call(window);
            if (typeof value === 'string' && value.length > 0)
                identities.push(value.toLowerCase());
        } catch (_error) {
            // A missing identifier simply means this window cannot be
            // classified by that field. Never inspect its title instead.
        }
    }
    return identities;
}

class MochiActivityHelper {
    enable() {
        this._connection = Gio.DBus.session;
        this._backend = Meta.get_backend();
        this._nameReady = false;
        this._pollSourceId = 0;
        this._lastInputEventAtMs = null;
        this._lastInputWasKeyboard = false;
        this._presenceIdleWatchId = 0;
        this._presenceActiveWatchId = 0;
        this._presenceIsIdle = false;
        this._fileBrowsingActive = false;
        this._youtubeFocusedActive = false;
        this._appCategory = 'unknown';
        this._videoFocusHeartbeatId = 0;
        this._focusChangedId = 0;
        this._lastFocusedWindow = global.display.get_focus_window();
        this._tabWindow = null;
        this._tabTitleChangedId = 0;
        this._tabTitleDigest = null;
        this._tabPausedWindow = null;

        Main.keybindingManager.addHotKey(
            DEVELOPER_MENU_KEYBINDING,
            DEVELOPER_MENU_HOTKEY,
            () => {
                // Semantic request only: no key identity, typed data, or window data.
                this._emitSignal(DEVELOPER_MENU_SIGNAL_NAME);
            },
        );
        Main.keybindingManager.addHotKey(
            EMOTE_CATALOGUE_KEYBINDING,
            EMOTE_CATALOGUE_HOTKEY,
            () => {
                // User-facing semantic action; no key identity crosses D-Bus.
                this._emitSignal(EMOTE_CATALOGUE_SIGNAL_NAME);
            },
        );

        this._lastDeviceChangedId = this._backend.connect(
            'last-device-changed',
            (_backend, device) => {
                // Privacy boundary: inspect only the broad device TYPE. Never
                // inspect key symbols, codes, modifiers, text, or application data.
                this._lastInputWasKeyboard = device !== null &&
                    device.get_device_type() === Clutter.InputDeviceType.KEYBOARD_DEVICE;
            },
        );

        this._idleMonitor = Meta.IdleMonitor.get_core();

        this._focusChangedId = global.display.connect(
            'notify::focus-window',
            () => {
                const focusedWindow = global.display.get_focus_window();
                this._updateFileBrowsingState();
                this._updateYouTubeFocusedState(false);
                const category = this._updateAppCategory();
                this._trackBrowserTabTitle(focusedWindow, category);

                // Focus can be notified more than once while the same
                // Meta.Window remains focused. Curiosity should represent an
                // actual change of attention, not notification churn.
                if (focusedWindow === this._lastFocusedWindow)
                    return;

                // Temporary focus loss (Expo, panels, transitions) is not a new
                // desktop target and should not make Mochi curious.
                if (focusedWindow !== null) {
                    this._lastFocusedWindow = focusedWindow;
                    this._emitAppFocus(category);
                }
            },
        );
        this._updateFileBrowsingState();
        this._updateYouTubeFocusedState(false);
        this._updateAppCategory();
        this._trackBrowserTabTitle(global.display.get_focus_window(), this._appCategory);
        this._videoFocusHeartbeatId = GLib.timeout_add(
            GLib.PRIORITY_DEFAULT,
            VIDEO_FOCUS_HEARTBEAT_MS,
            () => {
                this._updateYouTubeFocusedState(false);
                this._updateAppCategory();
                // Identity can arrive after a window is focused, so re-sync to
                // pick up a browser that classified late. Idempotent when the
                // target is unchanged.
                this._trackBrowserTabTitle(global.display.get_focus_window(), this._appCategory);
                return GLib.SOURCE_CONTINUE;
            },
        );

        // Export before acquiring the name so late clients can subscribe and
        // obtain one privacy-reduced snapshot without waiting for a transition.
        this._dbusObject = Gio.DBusExportedObject.wrapJSObject(
            `<node><interface name="${INTERFACE_NAME}">
                <method name="GetState">
                    <arg type="b" direction="out" name="idle"/>
                    <arg type="b" direction="out" name="fileBrowsing"/>
                    <arg type="b" direction="out" name="youtubeFocused"/>
                    <arg type="s" direction="out" name="appCategory"/>
                </method>
            </interface></node>`,
            this,
        );
        this._dbusObject.export(this._connection, OBJECT_PATH);

        this._nameOwnerId = Gio.bus_own_name_on_connection(
            this._connection,
            BUS_NAME,
            Gio.BusNameOwnerFlags.NONE,
            () => {
                this._nameReady = true;
                // If semantic state changed before D-Bus ownership completed,
                // publish the current state once ownership is ready.
                if (this._presenceIsIdle)
                    this._emitSignal(USER_IDLE_SIGNAL_NAME);
                if (this._fileBrowsingActive)
                    this._emitSignal(FILE_BROWSING_STARTED_SIGNAL_NAME);
                this._emitSignal(
                    this._youtubeFocusedActive
                        ? YOUTUBE_FOCUSED_STARTED_SIGNAL_NAME
                        : YOUTUBE_FOCUSED_STOPPED_SIGNAL_NAME,
                );
                this._emitAppCategory();
            },
            () => {
                this._nameReady = false;
            },
        );

        // Establish a baseline so pre-existing activity does not emit a typing
        // pulse when the extension starts.
        this._sampleInput(false);

        this._pollSourceId = GLib.timeout_add(
            GLib.PRIORITY_DEFAULT,
            POLL_INTERVAL_MS,
            () => {
                this._sampleInput(true);
                return GLib.SOURCE_CONTINUE;
            },
        );

        this._armPresenceIdleWatch();
    }

    GetState() {
        return [this._presenceIsIdle, this._fileBrowsingActive,
            this._youtubeFocusedActive, this._appCategory];
    }

    _emitSignal(signalName) {
        if (!this._nameReady || this._connection === null)
            return;

        try {
            this._connection.emit_signal(
                null,
                OBJECT_PATH,
                INTERFACE_NAME,
                signalName,
                null,
            );
        } catch (_error) {
            // Never log input-, window-, or file-related data. Dropping a
            // semantic signal is safe.
        }
    }

    _emitAppCategory() {
        if (!this._nameReady || this._connection === null)
            return;

        try {
            this._connection.emit_signal(
                null,
                OBJECT_PATH,
                INTERFACE_NAME,
                APP_CATEGORY_SIGNAL_NAME,
                new GLib.Variant('(s)', [this._appCategory]),
            );
        } catch (_error) {
            // Category is best-effort. Never fall back to transmitting raw
            // application identity when this semantic signal cannot be sent.
        }
    }

    _emitAppFocus(category) {
        if (!this._nameReady || this._connection === null)
            return;

        try {
            this._connection.emit_signal(
                null,
                OBJECT_PATH,
                INTERFACE_NAME,
                APP_FOCUS_SIGNAL_NAME,
                new GLib.Variant('(s)', [category]),
            );
        } catch (_error) {
            // Focus pulses carry only the same coarse semantic category. Never
            // fall back to sending a title or application identifier.
        }
    }

    _trackBrowserTabTitle(window, category) {
        // Only browser titles are observed; every other app stays unwatched.
        const target = category === 'browser' ? window : null;
        // Any focused media window (e.g. a YouTube tab) is paused, whether it
        // was tracked first or focus landed on it directly. Only its reference
        // is kept: a media window's title is never read for tab tracking.
        const paused = category === 'media' ? window : null;
        if (target === this._tabWindow && paused === this._tabPausedWindow)
            return;

        // Leaving media for another tab in the SAME window is a tab change.
        // Any other window becoming the target is a window switch, which
        // AppFocusChanged already covers. Read this before untracking clears
        // the pause; a pause lasts only while that window stays media.
        const resuming = target !== null && target === this._tabPausedWindow;
        this._untrackBrowserTabTitle();
        if (paused !== null) {
            this._tabPausedWindow = paused;
            return;
        }
        if (target === null)
            return;

        this._tabWindow = target;
        // A newly focused window is a baseline, not a tab change.
        this._tabTitleDigest = this._tabTitleDigestFor(target);
        this._tabTitleChangedId = target.connect(
            'notify::title',
            () => this._onBrowserTabTitleChanged(),
        );

        // Same input gate as a title change; an unreadable baseline is not one.
        if (!resuming || this._tabTitleDigest === null || this._idleMonitor === null)
            return;
        if (shouldEmitTabPulse(Number(this._idleMonitor.get_idletime())))
            this._emitSignal(BROWSER_TAB_SIGNAL_NAME);
    }

    _untrackBrowserTabTitle() {
        if (this._tabWindow !== null && this._tabTitleChangedId) {
            try {
                this._tabWindow.disconnect(this._tabTitleChangedId);
            } catch (_error) {
                // The window may already be unmanaged; nothing left to release.
            }
        }
        this._tabWindow = null;
        this._tabTitleChangedId = 0;
        this._tabTitleDigest = null;
        this._tabPausedWindow = null;
    }

    _tabTitleDigestFor(window) {
        let title = '';
        try {
            title = window.get_title();
        } catch (_error) {
            return null;
        }
        // Privacy boundary: keep only a one-way digest for change detection.
        // The title itself is never stored, logged, or sent over D-Bus.
        return GLib.compute_checksum_for_string(
            GLib.ChecksumType.SHA256,
            normalizeTabTitle(title),
            -1,
        );
    }

    _onBrowserTabTitleChanged() {
        if (this._tabWindow === null)
            return;

        const digest = this._tabTitleDigestFor(this._tabWindow);
        if (digest === null || digest === this._tabTitleDigest)
            return;
        const hadBaseline = this._tabTitleDigest !== null;
        // Store first so hands-off churn still becomes the new baseline.
        this._tabTitleDigest = digest;
        // An unreadable baseline cannot show a change; this title replaces it.
        if (!hadBaseline)
            return;

        if (this._idleMonitor === null)
            return;
        if (!shouldEmitTabPulse(Number(this._idleMonitor.get_idletime())))
            return;

        this._emitSignal(BROWSER_TAB_SIGNAL_NAME);
    }

    _updateAppCategory() {
        const category = this._classifyAppCategory(global.display.get_focus_window());
        if (category !== this._appCategory) {
            this._appCategory = category;
            this._emitAppCategory();
        }
        return category;
    }

    _classifyAppCategory(window) {
        if (window === null)
            return 'unknown';

        // Unknown identity means unknown category; never inspect the title as
        // a fallback for general application classification.
        const identities = windowIdentities(window);
        const matches = markers => identities.some(identity =>
            markers.some(marker => identity === marker || identity.includes(marker))
        );
        if (matches(PIXEL_ART_MARKERS))
            return 'pixel_art';
        if (matches(VSCODE_MARKERS))
            return 'vscode';
        if (matches(EDITOR_MARKERS))
            return 'editor';
        if (matches(TERMINAL_MARKERS))
            return 'terminal';
        if (matches(BROWSER_MARKERS))
            return this._isFocusedYouTubeWindow(window) ? 'media' : 'browser';
        if (matches(MEDIA_APP_MARKERS))
            return 'media';
        return 'unknown';
    }

    _updateFileBrowsingState() {
        const window = global.display.get_focus_window();
        const active = this._isFileManagerWindow(window);
        if (active === this._fileBrowsingActive)
            return;

        this._fileBrowsingActive = active;
        this._emitSignal(
            active
                ? FILE_BROWSING_STARTED_SIGNAL_NAME
                : FILE_BROWSING_STOPPED_SIGNAL_NAME,
        );
    }

    _isFileManagerWindow(window) {
        if (window === null)
            return false;

        return windowIdentities(window).some(identity =>
            FILE_MANAGER_MARKERS.some(marker =>
                identity === marker || identity.includes(marker)
            )
        );
    }

    _updateYouTubeFocusedState(emitHeartbeat) {
        const window = global.display.get_focus_window();
        const active = this._isFocusedYouTubeWindow(window);
        const changed = active !== this._youtubeFocusedActive;

        this._youtubeFocusedActive = active;
        if (!changed && !emitHeartbeat)
            return;

        // Privacy boundary: only this boolean leaves Cinnamon. The title
        // itself is never logged, stored, or sent over D-Bus.
        this._emitSignal(
            active
                ? YOUTUBE_FOCUSED_STARTED_SIGNAL_NAME
                : YOUTUBE_FOCUSED_STOPPED_SIGNAL_NAME,
        );
    }

    _isFocusedYouTubeWindow(window) {
        if (window === null)
            return false;

        const isBrowser = windowIdentities(window).some(identity =>
            BROWSER_MARKERS.some(marker => identity.includes(marker))
        );
        if (!isBrowser)
            return false;

        // Browser MPRIS data often omits the page URL. Inspect the focused title
        // only long enough to reduce it to a boolean; the raw title is never
        // logged, retained, or sent over D-Bus.
        let title = '';
        try {
            title = String(window.get_title() ?? '').trim().toLowerCase();
        } catch (_error) {
            return false;
        }

        if (title.includes('youtube music'))
            return false;

        // Chrome/Chromium/Firefox can append their own application name after
        // the page title, e.g. "Video - YouTube - Google Chrome". Strip only a
        // known browser suffix, then require YouTube to be the page-brand suffix.
        for (const browserName of BROWSER_TITLE_NAMES) {
            for (const separator of [' - ', ' – ', ' — ']) {
                const suffix = `${separator}${browserName}`;
                if (title.endsWith(suffix)) {
                    title = title.slice(0, -suffix.length).trim();
                    break;
                }
            }
        }

        return (
            title.endsWith(' - youtube') ||
            title.endsWith(' – youtube') ||
            title.endsWith(' — youtube') ||
            title === 'youtube'
        );
    }

    _armPresenceIdleWatch() {
        if (this._idleMonitor === null || this._presenceIdleWatchId)
            return;

        this._presenceIdleWatchId = this._idleMonitor.add_idle_watch(
            USER_IDLE_AFTER_MS,
            () => {
                // Idle watches persist across activity cycles. Keep the ID so
                // rearming does not leak another watch and disable removes it.
                if (!this._presenceIsIdle) {
                    this._presenceIsIdle = true;
                    this._emitSignal(USER_IDLE_SIGNAL_NAME);
                }
                this._armPresenceActiveWatch();
            },
        );
    }

    _armPresenceActiveWatch() {
        if (this._idleMonitor === null || this._presenceActiveWatchId)
            return;

        // A one-shot watch armed after an idle watch fires. Any real user input
        // (keyboard, pointer, touch, etc.) wakes it; no input contents are
        // inspected.
        this._presenceActiveWatchId = this._idleMonitor.add_user_active_watch(
            () => {
                this._presenceActiveWatchId = 0;
                if (this._presenceIsIdle) {
                    this._presenceIsIdle = false;
                    this._emitSignal(USER_ACTIVE_SIGNAL_NAME);
                }
                this._armPresenceIdleWatch();
            },
        );
    }

    _sampleInput(allowPulse) {
        if (this._idleMonitor === null)
            return;

        const idleMs = Number(this._idleMonitor.get_idletime());
        if (!Number.isFinite(idleMs) || idleMs < 0)
            return;

        const nowMs = GLib.get_monotonic_time() / 1000;
        const inputEventAtMs = nowMs - idleMs;

        // get_idletime() advances with monotonic time, so now-idle remains
        // approximately constant until a NEW input event resets idle time.
        const isNewInput = this._lastInputEventAtMs === null ||
            inputEventAtMs > this._lastInputEventAtMs + EVENT_TIME_EPSILON_MS;

        if (!isNewInput)
            return;

        // Record every new input event, not only keyboard events. That prevents
        // pointer activity from being mistaken for a later keyboard pulse.
        this._lastInputEventAtMs = inputEventAtMs;

        if (!allowPulse)
            return;

        // The signal above maintains only whether the most recently active
        // hardware class is a keyboard. Once the keyboard becomes current,
        // repeated keypresses keep this true while each idle-time reset
        // produces a fresh anonymous pulse.
        if (this._lastInputWasKeyboard)
            this._emitSignal(TYPING_SIGNAL_NAME);
    }

    disable() {
        Main.keybindingManager.removeHotKey(DEVELOPER_MENU_KEYBINDING);
        Main.keybindingManager.removeHotKey(EMOTE_CATALOGUE_KEYBINDING);

        if (this._pollSourceId) {
            GLib.Source.remove(this._pollSourceId);
            this._pollSourceId = 0;
        }
        if (this._videoFocusHeartbeatId) {
            GLib.Source.remove(this._videoFocusHeartbeatId);
            this._videoFocusHeartbeatId = 0;
        }

        if (this._idleMonitor !== null) {
            if (this._presenceIdleWatchId) {
                this._idleMonitor.remove_watch(this._presenceIdleWatchId);
                this._presenceIdleWatchId = 0;
            }
            if (this._presenceActiveWatchId) {
                this._idleMonitor.remove_watch(this._presenceActiveWatchId);
                this._presenceActiveWatchId = 0;
            }
        }

        if (this._lastDeviceChangedId) {
            this._backend.disconnect(this._lastDeviceChangedId);
            this._lastDeviceChangedId = 0;
        }

        if (this._focusChangedId) {
            global.display.disconnect(this._focusChangedId);
            this._focusChangedId = 0;
        }
        this._untrackBrowserTabTitle();

        this._idleMonitor = null;
        this._backend = null;
        this._lastInputEventAtMs = null;
        this._lastInputWasKeyboard = false;
        this._presenceIsIdle = false;
        this._fileBrowsingActive = false;
        this._youtubeFocusedActive = false;
        this._appCategory = 'unknown';
        this._lastFocusedWindow = null;
        this._nameReady = false;

        if (this._dbusObject) {
            this._dbusObject.unexport();
            this._dbusObject = null;
        }

        if (this._nameOwnerId) {
            Gio.bus_unown_name(this._nameOwnerId);
            this._nameOwnerId = 0;
        }

        this._connection = null;
    }
}

let helper = null;

function init(_metadata) {
}

function enable() {
    helper = new MochiActivityHelper();
    helper.enable();
}

function disable() {
    if (helper !== null) {
        helper.disable();
        helper = null;
    }
}
