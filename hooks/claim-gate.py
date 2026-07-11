#!/usr/bin/env python3
"""Hook: claim-gate (PreToolUse, matcher *)

HARD gate that closes the resumed/compacted-session blind spot: the
claim-reminder (UserPromptSubmit) and task-lock-surface (SessionStart) hooks
do NOT fire on resume, so a resumed session can run a whole build without ever
running /claim. This gate blocks *mutating* work once a session has done real
work in a project dir without holding a task lock.

DESIGN (safety-first — this is a GLOBAL PreToolUse hook, high blast radius):
- FAIL-OPEN. Any exception, missing field, or uncertainty -> ALLOW (exit 0).
  A bug here must never freeze a session.
- SCOPED to real project work: only engages when cwd is under ~/projects/ or
  ~/conductor/workspaces/. This is ALSO the daemon-exemption — the HeavyPope /
  Ekko channel daemons run from home (~), never these paths, so they are never
  gated (a daemon has no human to run /claim).
- Gates ONLY file-mutation / heavy-delegation tools (Write, Edit, NotebookEdit,
  Task). Read/Grep/Glob/Bash/Skill/ToolSearch/MCP always pass — so you can look
  around AND run /claim (a Skill) even while gated.
- Grace budget: the first GRACE mutating calls pass freely (small edits, quick
  fixes). Only after that does a lock become mandatory.
- Kill-switch: env CLAUDE_CLAIM_GATE_OFF=1 disables it entirely.

Exit 0 = allow. Exit 2 + stderr = block (stderr is shown to the model).
"""
import sys
import os
import json
import glob

GRACE = 3               # this many mutating calls are free before a lock is required
GATED_TOOLS = {"Write", "Edit", "NotebookEdit", "Task"}
STATE_DIR = "/tmp/claim-gate"


def allow():
    sys.exit(0)


def main():
    # Kill-switch
    if os.environ.get("CLAUDE_CLAIM_GATE_OFF") == "1":
        allow()

    raw = sys.stdin.read()
    data = json.loads(raw)  # any parse failure -> except -> allow

    tool = data.get("tool_name", "")
    cwd = data.get("cwd") or os.getcwd()
    sid = data.get("session_id", "")

    # Only ever gate mutating tools; everything else passes (incl. Skill=/claim).
    if tool not in GATED_TOOLS:
        allow()

    # Scope: only real project work. Excludes the channel daemons (run from ~).
    home = os.path.expanduser("~")
    scoped_roots = (
        os.path.join(home, "projects") + os.sep,
        os.path.join(home, "conductor", "workspaces") + os.sep,
    )
    if not any(cwd.startswith(r) for r in scoped_roots):
        allow()

    # Already holding a lock for this cwd? -> allow (the whole point).
    for lk in glob.glob(os.path.expanduser("~/.claude/task-locks/*.lock")):
        try:
            if json.load(open(lk)).get("cwd") == cwd:
                allow()
        except Exception:
            continue  # unreadable lock never blocks

    # Count mutating calls this session against the grace budget.
    if not sid:
        allow()  # can't track reliably -> fail open
    os.makedirs(STATE_DIR, exist_ok=True)
    cnt_path = os.path.join(STATE_DIR, sid.replace("/", "_") + ".json")
    try:
        st = json.load(open(cnt_path))
    except Exception:
        st = {}
    n = int(st.get("mutating_calls", 0)) + 1
    st["mutating_calls"] = n
    st["cwd"] = cwd
    try:
        json.dump(st, open(cnt_path, "w"))
    except Exception:
        allow()  # can't persist -> don't hold the session hostage

    if n <= GRACE:
        allow()

    # Over budget, in-scope, no lock: BLOCK.
    proj = os.path.basename(cwd.rstrip(os.sep))
    msg = (
        f"\n🔒 claim-gate: {n} mutating actions in '{proj}' with NO task lock.\n"
        f"   Resumed/compacted sessions don't fire the /claim reminder — this is that gap.\n"
        f"   Run  /claim \"<task>\"  (or /track) to register the lock, then retry.\n"
        f"   Reads, Bash, and Skills still work; only file edits + Task are gated.\n"
        f"   Escape hatch: CLAUDE_CLAIM_GATE_OFF=1 (e.g. one-off scripts).\n"
    )
    sys.stderr.write(msg)
    sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        # Absolute backstop: never break a session on hook error.
        sys.exit(0)
