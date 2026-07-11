#!/usr/bin/env python3
"""
Stop hook — enforces the /close-asset-audit skill during /close-session.

Mirrors the retro gate pattern (close-retro-stop-gate.py):
1. /close-session creates ~/.claude/close-pending-{session_id}
2. /close-asset-audit writes /tmp/asset-audit-{session_id}.json on pass
3. On turn-end (Stop), if close-pending exists AND the session produced
   enough work (>=2 commits), BLOCK unless the audit marker exists.

This closes the gap where asset wiring (Lego Registry, Notion task) was
the only close-session gate without mechanical enforcement — skipped 9+
times under "wrap up" momentum (2026-05-27 through 2026-06-19).
"""
import json, sys, os, glob, time, subprocess


def _count_session_commits(session_id):
    """Count commits made during this session using the session-start marker."""
    marker_path = f"/tmp/claude-sessions/session-{session_id}.json"
    if not os.path.exists(marker_path):
        return None
    try:
        with open(marker_path) as f:
            data = json.load(f)
        start_sha = data.get("head_sha", "")
        cwd = data.get("cwd", "")
        if not start_sha or start_sha == "nogit" or not cwd:
            return None
        result = subprocess.run(
            ["git", "rev-list", "--count", f"{start_sha}..HEAD"],
            capture_output=True, text=True, timeout=5, cwd=cwd
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except Exception:
        pass
    return None


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:
        return

    if event.get("stop_hook_active"):
        return

    session_id = event.get("session_id") or ""
    if not session_id:
        return

    close_pending = os.path.expanduser(f"~/.claude/close-pending-{session_id}")
    if not os.path.exists(close_pending):
        return

    # Staleness guard: abandoned close-pending (>2h)
    try:
        if time.time() - os.path.getmtime(close_pending) > 7200:
            return
    except OSError:
        return

    # Check if audit already passed
    audit_marker = f"/tmp/asset-audit-{session_id}.json"
    if os.path.exists(audit_marker):
        return

    # Only enforce if session produced significant work (>=2 commits)
    commits = _count_session_commits(session_id)
    if commits is None or commits < 2:
        return

    print(json.dumps({
        "decision": "block",
        "reason": (
            "CLOSE GATE (asset-audit): /close-session is active and this session "
            f"has {commits} commits, but /close-asset-audit has not run. This gate "
            "ensures Lego Registry entries, Notion task tracking, and MEMORY.md "
            "updates are not skipped under wrap-up momentum. "
            "Invoke /close-asset-audit now — it will independently check git for "
            "new components, query Lego Registry for gaps, and verify a Notion task "
            f"exists. It writes /tmp/asset-audit-{session_id}.json on pass."
        )
    }))


if __name__ == "__main__":
    main()
