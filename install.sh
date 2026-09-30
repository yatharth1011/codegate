#!/bin/bash
# Installs CodeGate into ~/Library/Application Support/CodeGate -- the location
# Dromac's dashboard looks for it in. Safe to re-run to update: members,
# starter files and certificates live in that same folder and are left alone.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
dest="$HOME/Library/Application Support/CodeGate"

mkdir -p "$dest"
cp "$here/server.py" "$here/gate.py" "$here/spaces.py" "$dest/"
rsync -a --delete "$here/docker/" "$dest/docker/"

if ! command -v docker >/dev/null 2>&1 || ! command -v colima >/dev/null 2>&1; then
  echo "CodeGate runs each member in a container. Install the runtime first:  brew install colima docker"
fi

# A running server keeps serving the old code until restarted.
if pids="$(lsof -tiTCP:8902 -sTCP:LISTEN 2>/dev/null)" && [ -n "$pids" ]; then
  kill $pids
  echo "Stopped the running CodeGate server; start it again to use the new version."
fi

echo "Installed to $dest"
echo "Start it with:  python3 \"$dest/server.py\"   (or the start button in Dromac)"
