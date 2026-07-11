---
name: che-session-recover
description: Triage and recover Claude Code sessions after a crash (VS Code quit, OOM, accidental close). Lists every session from the last N hours classified as UNFINISHED / DONE / EMPTY, with paste-ready `claude --resume` commands and a repo-level uncommitted-work-at-risk summary. Use when the user says "recover sessions", "what was I working on", "VS Code crashed", "lost my sessions", "which sessions had unfinished work", or after any unexpected editor/terminal shutdown.
metadata:
  summary: "Triage crashed sessions — UNFINISHED/DONE/EMPTY with paste-ready resume commands"
---

# che-session-recover

Recover from a Claude Code crash (e.g. VS Code quitting while many sessions ran).

Claude Code persists every session as an append-only `~/.claude/projects/<dir>/<uuid>.jsonl`.
When the editor dies, the live processes die but the transcripts survive — so recovery is
triage + resume, never data loss.

## How it works

`~/.claude/scripts/session-triage.py` reads each transcript and classifies it from objective
signals (where the last turn stopped, whether your last prompt was answered, close-ritual
markers, and whether the session edited files in a now-dirty repo). The verdict policy lives
in `decide_verdict()` — Anton's rule: **UNFINISHED unless provably finished** (a clean
`/close-session`/`/session-retro` or an explicit "leave it"/"clear"). "Idle awaiting your
decision" counts as unfinished.

## Commands

```bash
# Full triage, last 48h (default) — grouped, with resume commands + at-risk repos
python3 ~/.claude/scripts/session-triage.py

# Only what needs attention
python3 ~/.claude/scripts/session-triage.py --unfinished --hours 24

# Crash fingerprint only (silent unless a cluster of sessions died together)
python3 ~/.claude/scripts/session-triage.py --crash-detect --fast --hours 6

# Machine-readable
python3 ~/.claude/scripts/session-triage.py --json --hours 12
```

Resume any session with the printed command: `cd <cwd> && claude --resume <uuid>`.

## When invoked as a skill

1. Run `session-triage.py --hours <window>` (default 48; widen if the user asks).
2. Present the UNFINISHED group first, newest last, with the one-line YOU/CC tail so the user
   recognizes each session.
3. Call out the **Uncommitted work at risk** repos — that's lost-work exposure independent of
   session state; offer to commit those first.
4. Offer to resume the highest-stakes UNFINISHED session (client deliverables, mid-tool stops).

## Prevention (mention proactively after a crash)

- The `crash-recovery-surface.sh` SessionStart hook auto-fires this on the next startup after a
  crash cluster is detected.
- For long client-doc sessions in Conductor worktrees, run `/loop 30m /checkpoint` so work is
  committed before any crash. (Note: `/loop` dies with the terminal — it's in-session insurance,
  not a durable daemon.)
