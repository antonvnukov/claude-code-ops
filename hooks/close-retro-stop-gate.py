#!/usr/bin/env python3
"""
Stop hook — enforces the /session-retro convergence loop during /close-session
INDEPENDENT of whether checkpoint.md is ever written.

Closes the hole in retro-gate.py: that hook only fires on `Write` to
checkpoint.md, so any close path that doesn't write a checkpoint (non-GSD
projects, external/parallel checkpoint.md, or simply not writing one) escaped
the convergence loop entirely and silently. This is what happened 2026-05-30.

Gate logic:
1. /close-session creates ~/.claude/close-pending-{session_id} AFTER the
   step-1 approval (so the approval question itself is never blocked).
2. /session-retro's convergence loop writes /tmp/retro-converged-{session_id}.json
   with {"passes": N, "total_items": M}.
3. On turn-end (Stop), if close-pending exists but convergence didn't run
   (or passes < 2), BLOCK the stop and force the retro to run.
4. /close-session removes close-pending at true completion → releases the gate.

Safety:
- stop_hook_active guard prevents infinite loops (block at most once per chain).
- 2-hour staleness guard releases an abandoned close-pending marker.
- No session marker / cwd mismatch = allow (can't enforce reliably).
"""
import json, sys, os, glob, time

# Categories that count as a reusable "artifact/component" produced this session.
_ARTIFACT_CATS = {"lego", "sop", "script", "component", "automation",
                  "stack", "workflow", "skill", "playbook"}


def trajectory_gate(session_id):
    """Mechanical trajectory check — reads the ACTUAL logged retro items.
    Returns True (satisfied), False (block: artifacts>=3 but no trajectory),
    or None (can't determine → don't enforce).

    Satisfied by EITHER a real trajectory item OR an explicit not-reusable line
    logged as {"category":"trajectory","item":"not reusable: ..."}. This keys the
    gate off the artifact COUNT, not the session's framing — so mis-labeling a
    multi-step build as "infra, no trajectory" can't silently suppress it.
    """
    items_path = f"/tmp/retro-items-{session_id}.jsonl"
    if not os.path.exists(items_path):
        return None
    artifacts = 0
    has_traj = False
    try:
        with open(items_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    it = json.loads(line)
                except Exception:
                    continue
                cat = str(it.get("category", "")).lower()
                layer = str(it.get("layer", "")).upper()
                if cat in _ARTIFACT_CATS:
                    artifacts += 1
                if layer == "L3" or cat == "trajectory":
                    has_traj = True
    except Exception:
        return None
    if artifacts >= 3 and not has_traj:
        return False
    return True


# Tools that edit/create files — used to size the session's work from the transcript.
_EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def _transcript_stats(transcript_path):
    """Read the FULL on-disk transcript and return (is_compacted, distinct_files_edited).
    The transcript retains ALL pre-compaction entries (compaction only trims the live
    context window, not the file) — so this is the ONE denominator the scanner cannot
    bias by scanning narrowly. Returns (None, None) if unreadable (fail-open)."""
    if not transcript_path or not os.path.exists(transcript_path):
        return (None, None)
    is_compacted = False
    files = set()
    try:
        with open(transcript_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("isCompactSummary") or d.get("subtype") == "compact_boundary":
                    is_compacted = True
                msg = d.get("message") or {}
                content = msg.get("content") if isinstance(msg, dict) else None
                if isinstance(content, list):
                    for blk in content:
                        if (isinstance(blk, dict) and blk.get("type") == "tool_use"
                                and blk.get("name") in _EDIT_TOOLS):
                            fp = (blk.get("input") or {}).get("file_path")
                            if fp:
                                files.add(fp)
    except Exception:
        return (None, None)
    return (is_compacted, len(files))


def compaction_scope_gate(session_id, transcript_path):
    """The compaction-aware DENOMINATOR (2026-06-05). When the session was COMPACTED and
    substantial (>=5 distinct files edited across the full transcript), require a 'scope-ack'
    retro item whose declared file count MATCHES the disk-computed count (+-20%). This forces
    the scanner to actually read the full pre-compaction transcript: a narrow post-compaction
    scan can't know the right number, and a wrong number fails the match. This closes the hole
    the user caught on 2026-06-05 — the convergence loop + trajectory gate both PASSED on a
    narrow scan because they only measure what the scanner logged, never the scan's SCOPE.
    Returns True (ok / N/A), False+reason (block), or None (can't determine → fail-open)."""
    is_compacted, files_full = _transcript_stats(transcript_path)
    if is_compacted is None:
        return (None, "")
    if not is_compacted or files_full < 5:
        return (True, "")  # not a compacted+substantial session → existing gates suffice
    items_path = f"/tmp/retro-items-{session_id}.jsonl"
    declared = None
    if os.path.exists(items_path):
        try:
            with open(items_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        it = json.loads(line)
                    except Exception:
                        continue
                    if str(it.get("category", "")).lower() == "scope-ack":
                        for k in ("files_full", "files", "files_edited"):
                            if isinstance(it.get(k), (int, float)):
                                declared = int(it[k])
                                break
        except Exception:
            return (None, "")
    tol = max(1, int(files_full * 0.2))
    if declared is not None and abs(declared - files_full) <= tol:
        return (True, "")
    reason = (
        "CLOSE GATE (compaction-scope): this session was COMPACTED and the FULL on-disk "
        f"transcript shows {files_full} distinct files edited — most of that work lives in the "
        "compaction SUMMARY, not the live context. A retro scoped to the post-compaction slice "
        "silently misses it (the 2026-06-05 miss: convergence + trajectory gates both PASSED on "
        "a narrow scan). Re-scan the compaction summary's 'All user messages' + 'Files' / "
        "'Errors' / 'Problem Solving' sections, log the missed artifacts/trajectory, THEN append "
        "a scope-ack proving you read the full transcript: "
        f'{{"category":"scope-ack","files_full":{files_full},"item":"scanned full pre-compaction '
        'transcript; <one line on coverage>"}} to '
        f"/tmp/retro-items-{session_id}.jsonl (files_full must match {files_full} +-{tol}). "
    )
    if declared is not None:
        reason += (f"Your scope-ack declared {declared}, which does NOT match {files_full} — "
                   "that means you did not scan the full session.")
    return (False, reason)


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:
        return  # unparseable = allow

    # Prevent infinite loop: if we already blocked once and are in a
    # stop-hook continuation, don't block again.
    if event.get("stop_hook_active"):
        return

    # Session id comes STRAIGHT FROM THE HOOK EVENT — Claude Code includes
    # session_id (and cwd) in every hook payload. Do NOT glob marker files and
    # guess by cwd: that's indirect and silently disables the gate when the
    # global-latest marker belongs to a parallel session, OR when launch-dir
    # != project-dir. (claim-reminder.py / track-reminder.py already do this.)
    session_id = event.get("session_id") or ""
    if not session_id:
        return  # no session id in event = can't enforce

    # Transcript path (Claude Code includes it in hook events) — used by the
    # compaction-scope gate as a denominator the scanner can't bias. Fallback: glob
    # the project dirs for <session_id>.jsonl.
    transcript_path = event.get("transcript_path") or ""
    if not transcript_path or not os.path.exists(transcript_path):
        cand = glob.glob(os.path.expanduser(f"~/.claude/projects/*/{session_id}.jsonl"))
        transcript_path = cand[0] if cand else ""

    close_pending = os.path.expanduser(f"~/.claude/close-pending-{session_id}")
    if not os.path.exists(close_pending):
        return  # not in a close-session flow

    # Staleness guard: abandoned close-pending (>2h) should not lock the session
    try:
        if time.time() - os.path.getmtime(close_pending) > 7200:
            return
    except OSError:
        return

    # Did the convergence loop actually run with >=2 passes?
    conv = f"/tmp/retro-converged-{session_id}.json"
    if os.path.exists(conv):
        try:
            with open(conv) as f:
                c = json.load(f)
            if int(c.get("passes", 0)) >= 2:
                # Passes satisfied — now the TRAJECTORY gate (mechanical).
                tg = trajectory_gate(session_id)
                if tg is False:
                    print(json.dumps({
                        "decision": "block",
                        "reason": (
                            "CLOSE GATE (trajectory): the retro logged >=3 reusable "
                            "artifacts/components but NO trajectory item. A multi-step "
                            "build always has a reusable PROCESS — extract it. Either "
                            "(a) capture the connecting process as a trajectory/SOP "
                            "(che-brain source=session_retro_trajectory + MEMORY pointer) "
                            "AND append a retro item with \"layer\":\"L3\" or "
                            "\"category\":\"trajectory\" to "
                            f"/tmp/retro-items-{session_id}.jsonl, OR (b) if it genuinely "
                            "isn't reusable, append {\"category\":\"trajectory\",\"item\":"
                            "\"not reusable: <one-line why>\"}. Then stop again. This is the "
                            "2026-06-02 fix: artifact count forces the trajectory check, not framing."
                        )
                    }))
                    return
                # Compaction-scope gate (the independent denominator).
                csg, csg_reason = compaction_scope_gate(session_id, transcript_path)
                if csg is False:
                    print(json.dumps({"decision": "block", "reason": csg_reason}))
                    return
                return  # converged + trajectory + scope resolved (or N/A) → allow stop
        except Exception:
            pass  # corrupted = fall through to block

    # BLOCK: close-session active, convergence loop not satisfied
    print(json.dumps({
        "decision": "block",
        "reason": (
            "CLOSE GATE: /close-session is active but the /session-retro "
            "convergence loop has not run (need /tmp/retro-converged-"
            f"{session_id}.json with passes >= 2). Do NOT declare the session "
            "closed yet. Invoke /session-retro now — run the convergence loop "
            "(min 2 passes, continue until delta < 3 new items per pass), which "
            "writes the marker. Then finish closing. Inline ad-hoc retros do "
            "not satisfy this gate — the looped skill must run."
        )
    }))


if __name__ == "__main__":
    main()
