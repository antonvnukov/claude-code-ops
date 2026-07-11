#!/usr/bin/env bash
# auto-release-session.sh — SessionStop/SessionEnd hook
# Automatically releases all task locks owned by this session.
# Prevents ghost locks from blocking other sessions after a crash or /clear.
#
# Input: JSON on stdin from Claude Code hook system
#   { "session_id": "...", "cwd": "/path/to/project", ... }

set -eu

INPUT=$(cat)

SESSION_ID=$(echo "$INPUT" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get("session_id", ""))
except Exception:
    print("")
' 2>/dev/null || echo "")

if [ -z "$SESSION_ID" ]; then
    exit 0
fi

LOCKS_DIR="$HOME/.claude/task-locks"
[ -d "$LOCKS_DIR" ] || exit 0

python3 <<PYEOF
import json, os, glob

locks_dir = "$LOCKS_DIR"
session_id = "$SESSION_ID"
released = []

for lock_path in glob.glob(os.path.join(locks_dir, "*.lock")):
    try:
        with open(lock_path) as f:
            lock = json.load(f)
        if lock.get("session_id") == session_id:
            os.remove(lock_path)
            released.append(lock.get("slug", os.path.basename(lock_path)))
    except Exception:
        pass

if released:
    for slug in released:
        print(f"🔓 Auto-released: {slug}")
PYEOF

exit 0
