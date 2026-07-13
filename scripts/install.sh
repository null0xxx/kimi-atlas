#!/bin/sh
# Install kimi-atlas into the local Kimi Code plugins directory and register it
# in installed.json so Kimi loads it natively (no --skills-dir needed).
#
# Idempotent + re-runnable: installs the committed HEAD (a consistent state,
# never a half-written working tree), replaces any prior kimi-atlas entry, and
# preserves every other installed plugin. Safe: installed.json is backed up and
# written atomically.
#
# Usage:  ./scripts/install.sh            # install into $HOME/.kimi-code
#         KIMI_CODE_HOME=/path ./scripts/install.sh
#         ./scripts/install.sh --uninstall
set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PLUGIN_SRC=$(dirname "$SCRIPT_DIR")                 # repo root (scripts/..)
KIMI_HOME="${KIMI_CODE_HOME:-$HOME/.kimi-code}"

# 1. Verify Kimi Code is installed here.
if [ ! -x "$KIMI_HOME/bin/kimi" ]; then
    echo "Error: Kimi Code not found at '$KIMI_HOME'." >&2
    echo "       Set KIMI_CODE_HOME to your Kimi install root and retry." >&2
    exit 1
fi

# 2. Ensure the plugins directory exists (create it if Kimi has none yet).
PLUGINS_DIR="$KIMI_HOME/plugins"
mkdir -p "$PLUGINS_DIR"
DEST="$PLUGINS_DIR/kimi-atlas"
INSTALLED="$PLUGINS_DIR/installed.json"

# --- uninstall path -------------------------------------------------------
if [ "${1:-}" = "--uninstall" ]; then
    [ -f "$INSTALLED" ] && cp "$INSTALLED" "$INSTALLED.bak.$(date -u +%Y%m%dT%H%M%SZ)"
    python3 - "$INSTALLED" <<'PY'
import json, os, sys, tempfile
path = sys.argv[1]
if not os.path.exists(path):
    sys.exit(0)
data = json.load(open(path))
data["plugins"] = [p for p in data.get("plugins", []) if p.get("id") != "kimi-atlas"]
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".")
with os.fdopen(fd, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
os.replace(tmp, path)
PY
    rm -rf "$DEST"
    echo "Uninstalled kimi-atlas from $PLUGINS_DIR (start a new Kimi session to apply)."
    exit 0
fi

# 3. Copy the committed HEAD into the plugins folder (a consistent snapshot;
#    excludes .git, untracked/in-progress files, and gitignored artifacts).
if ! git -C "$PLUGIN_SRC" rev-parse HEAD >/dev/null 2>&1; then
    echo "Error: '$PLUGIN_SRC' is not a git repo with a commit; commit first." >&2
    exit 1
fi
rm -rf "$DEST"
mkdir -p "$DEST"
git -C "$PLUGIN_SRC" archive --format=tar HEAD | tar -x -C "$DEST"

# 4. Register (or replace) the kimi-atlas entry in installed.json — backed up,
#    preserving all other plugins, written atomically.
[ -f "$INSTALLED" ] && cp "$INSTALLED" "$INSTALLED.bak.$(date -u +%Y%m%dT%H%M%SZ)"
python3 - "$INSTALLED" "$DEST" <<'PY'
import json, os, sys, tempfile
path, dest = sys.argv[1], sys.argv[2]
data = {"version": 1, "plugins": []}
if os.path.exists(path):
    with open(path) as f:
        data = json.load(f)
data.setdefault("version", 1)
plugins = [p for p in data.get("plugins", []) if p.get("id") != "kimi-atlas"]
plugins.append({
    "id": "kimi-atlas",
    "root": dest,
    "source": "local-path",
    "enabled": True,
    "originalSource": dest,
})
data["plugins"] = plugins
# atomic write via temp + rename in the same dir
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".")
with os.fdopen(fd, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
os.replace(tmp, path)
print(f"registered kimi-atlas -> {dest}")
print(f"installed.json now lists: {[p['id'] for p in plugins]}")
PY

echo ""
echo "Installed kimi-atlas to $DEST"
echo "Start a NEW Kimi session (or run /plugins reload) to load it."
echo "Verify:  kimi -p \"/skill:atlas ping\" --output-format text"
