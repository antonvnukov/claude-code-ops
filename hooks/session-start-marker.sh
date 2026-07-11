#!/usr/bin/env bash
# SessionStart hook — writes a marker file capturing session_id + cwd + HEAD SHA + start time
# Used by /close-session to distinguish "MINE" from "EXTERNAL" modifications at commit time
# in multi-session environments (Anton runs 10-20 parallel Claude Code sessions).
#
# Also runs cleanup: deletes session markers older than 7 days.
#
# Input: JSON on stdin from Claude Code hook system
#   { "session_id": "...", "cwd": "/path/to/project", ... }
# Output: /tmp/claude-sessions/session-{session_id}.json

set -eu

INPUT=$(cat)

# Parse session_id and cwd from stdin JSON (fall back to env/pwd if not provided)
SESSION_ID=$(echo "$INPUT" | python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
    print(d.get("session_id", ""))
except Exception:
    print("")' 2>/dev/null || echo "")

if [ -z "$SESSION_ID" ]; then
    SESSION_ID="${CLAUDE_SESSION_ID:-unknown-$(date +%s)-$$}"
fi

CWD=$(echo "$INPUT" | python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
    print(d.get("cwd", ""))
except Exception:
    print("")' 2>/dev/null || echo "")

if [ -z "$CWD" ]; then
    CWD="${PWD:-$(pwd)}"
fi

# Determine HEAD SHA if cwd is inside a git repo
HEAD_SHA="nogit"
if git -C "$CWD" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    HEAD_SHA=$(git -C "$CWD" rev-parse HEAD 2>/dev/null || echo "nogit")
fi

MARKER_DIR="/tmp/claude-sessions"
mkdir -p "$MARKER_DIR"

STARTED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

cat > "$MARKER_DIR/session-$SESSION_ID.json" <<EOF
{
  "session_id": "$SESSION_ID",
  "cwd": "$CWD",
  "head_sha": "$HEAD_SHA",
  "started_at": "$STARTED_AT"
}
EOF

# Cleanup markers older than 7 days
find "$MARKER_DIR" -name "session-*.json" -mtime +7 -delete 2>/dev/null || true

# Exit 0 — never block session start
exit 0
