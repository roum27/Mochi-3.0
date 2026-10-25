#!/usr/bin/env bash
set -euo pipefail

UUID="mochi-activity@miflow13"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="$ROOT/cinnamon-extension/$UUID"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
TARGET_DIR="$DATA_HOME/cinnamon/extensions/$UUID"

# Print a GVariant string array of $1's entries, leaving out $UUID.
# Extension uuids contain no commas or quotes, so a plain split is enough.
enabled_without_mochi() {
    local raw="${1#@as }" item
    local -a kept=()
    raw="${raw#[}"
    raw="${raw%]}"
    IFS=',' read -ra items <<< "$raw"
    for item in "${items[@]}"; do
        item="${item#"${item%%[![:space:]]*}"}"
        item="${item%"${item##*[![:space:]]}"}"
        item="${item#\'}"
        item="${item%\'}"
        if [[ -n "$item" && "$item" != "$UUID" ]]; then
            kept+=("'$item'")
        fi
    done
    local joined=""
    for item in "${kept[@]}"; do
        joined+="${joined:+, }$item"
    done
    printf '[%s]' "$joined"
}

with_mochi() {
    local list="$1"
    if [[ "$list" == "[]" ]]; then
        printf "['%s']" "$UUID"
    else
        printf "%s, '%s']" "${list%]}" "$UUID"
    fi
}

if [[ ! -f "$SOURCE_DIR/extension.js" ]]; then
    echo "Missing Cinnamon helper source: $SOURCE_DIR" >&2
    exit 1
fi

mkdir -p "$TARGET_DIR"
install -m 0644 "$SOURCE_DIR/metadata.json" "$SOURCE_DIR/extension.js" "$SOURCE_DIR/README.md" "$TARGET_DIR/"
echo "Installed $UUID."

if ! command -v gsettings >/dev/null 2>&1; then
    echo "gsettings was not found. Enable \"Mochi Desktop Activity\" in System Settings → Extensions." >&2
    exit 0
fi

current="$(gsettings get org.cinnamon enabled-extensions)"
others="$(enabled_without_mochi "$current")"
if [[ "$current" == *"'$UUID'"* ]]; then
    # Cinnamon does not reload code for an extension that stays enabled, so
    # drop it from the list for a moment to load the files just installed.
    gsettings set org.cinnamon enabled-extensions "$others"
fi
gsettings set org.cinnamon enabled-extensions "$(with_mochi "$others")"
echo "Enabled $UUID. Cinnamon loads it right away; no logout is needed."
