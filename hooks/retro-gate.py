#!/usr/bin/env python3
"""
PreToolUse:Write hook — blocks checkpoint.md writes during /close-session
if session retro hasn't been completed.

Gate logic:
1. close-session creates ~/.claude/close-pending-{session_id}
2. /session-retro creates ~/.claude/retro-done-{session_id} on completion
3. This hook blocks Write to any checkpoint.md if close-pending exists
   but retro-done does NOT exist

This makes it PHYSICALLY IMPOSSIBLE to write a checkpoint without
completing the retro. No instruction can override a hook block.
"""
import json, sys, os, glob

def main():
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, Exception):
        return  # can't parse = allow

    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})

    # Only gate Write tool
    if tool_name != "Write":
        return

    file_path = tool_input.get("file_path", "")

    # Only gate checkpoint.md writes
    if not file_path.endswith("checkpoint.md"):
        return

    # Session id comes STRAIGHT FROM THE HOOK EVENT (Claude Code includes
    # session_id in every payload). Globbing marker files and matching by cwd
    # is indirect and silently disables the gate when the global-latest marker
    # is a parallel session OR launch-dir != project-dir. Read it from event.
    session_id = event.get("session_id") or ""
    if not session_id:
        return  # no session id in event = allow (can't enforce)

    close_pending = os.path.expanduser(f"~/.claude/close-pending-{session_id}")
    retro_done = os.path.expanduser(f"~/.claude/retro-done-{session_id}")

    # Only enforce during close-session (close-pending exists)
    if not os.path.exists(close_pending):
        return  # not in close-session flow = allow

    # Check if retro was completed
    if os.path.exists(retro_done):
        # Convergence gate: retro-done exists, but did the convergence loop run?
        retro_converged = f"/tmp/retro-converged-{session_id}.json"
        if not os.path.exists(retro_converged):
            result = {
                "decision": "block",
                "reason": "CONVERGENCE GATE: /session-retro completed but convergence loop didn't run. "
                          f"Re-run /session-retro to create /tmp/retro-converged-{session_id}.json"
            }
            print(json.dumps(result))
            return

        try:
            with open(retro_converged) as f:
                conv_data = json.load(f)
            passes = conv_data.get("passes", 0)
            total_items = conv_data.get("total_items", 0)

            if passes < 2:
                result = {
                    "decision": "block",
                    "reason": f"CONVERGENCE GATE: retro completed with only {passes} pass(es). "
                              "Minimum 2 passes required. Re-run /session-retro."
                }
                print(json.dumps(result))
                return

            # Warn (not block) if low item count in a productive session
            if total_items < 10:
                import subprocess
                try:
                    git_out = subprocess.run(
                        ["git", "status", "--porcelain"],
                        capture_output=True, text=True, timeout=5
                    ).stdout.strip()
                except Exception:
                    git_out = ""
                if git_out:
                    print(json.dumps({
                        "decision": "allow",
                        "reason": f"CONVERGENCE WARNING: retro found only {total_items} items "
                                  f"across {passes} passes. Review retro output for shallow coverage."
                    }), file=sys.stderr)
        except (json.JSONDecodeError, Exception):
            pass  # corrupted convergence file = allow (don't block on file corruption)

        return  # retro done + convergence passed = allow

    # BLOCK: close-session active but retro not done
    result = {
        "decision": "block",
        "reason": "RETRO GATE: /close-session is active but /session-retro has not been completed. "
                  "Run /session-retro FIRST, then write checkpoint. "
                  "The retro needs full context - it cannot be skipped. "
                  f"To unblock: complete retro (creates ~/.claude/retro-done-{session_id})"
    }
    print(json.dumps(result))

if __name__ == "__main__":
    main()
