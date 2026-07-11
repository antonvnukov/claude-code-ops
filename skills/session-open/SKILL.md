---
name: session-open
description: "Session startup orchestrator — auto-reads .continue-here.md resume context, shows Rebel's task queue, surfaces task lock collisions. Run at session start to get oriented in zero manual steps. Hooks handle work-style inject + session marker independently."
uses: []
requires: [track]
bets:     []
maturity: proven
chain:
  produces: "session context + resume state"
  chains: ["session-startup"]
  position: 1
---

# Session Open

Get oriented at session start in one command. Replaces the manual sequence of reading handoff files, checking Notion, and scanning for collisions.

## When to run

- Start of any session where you're picking up prior work
- After `/compact` when resuming
- User says "where was I", "what's next", "pick up where I left off"

Not needed for clean-slate sessions (new feature, new project, no prior context).

## Process (no approval gate — runs sequentially without prompting)

### Step 1 — Resume context (GSD projects only)

Check if current cwd is a GSD project (`.planning/PROJECT.md` exists). If YES:

Find the most recent `.continue-here.md`:
```bash
find .planning/phases -name ".continue-here.md" -type f 2>/dev/null | head -5
```

If found, read the most recently modified one and print a compact summary:
```
Resume context (.continue-here.md):
  Phase: {phase name from path}
  Next action: {next_action content}
  Decisions: {key decisions, max 3}
  Blockers: {blockers if any}
```

If NOT found: "No .continue-here.md — starting fresh or previous session didn't pause cleanly."

### Step 2 — Rebel's task queue

Invoke `/track list` to show all tasks assigned to Rebel across both task databases. This surfaces the full queue so the user can pick what to work on.

If a `.planning/STATE.md` exists with an `active_notion_task_url` that is NOT "(none...)", highlight it:
```
Active task from last session: {task title} — {url}
  Resume this? Or pick from queue below.
```

### Step 3 — Work-style context (already injected by hook)

The `work-style-inject.sh` SessionStart hook already injects the profile summary into context. Confirm it's present:

```
Work-style: injected via hook ✓
```

If for some reason the profile wasn't loaded (e.g., hook didn't fire), read and display the first paragraph of each section from `~/.claude/work-style-profile.md` (same as `/work-style` default mode).

### Step 4 — Task lock scan

Check for any active task locks in current cwd:
```bash
python3 <<'PYEOF'
import json, os, glob
locks_dir = os.path.expanduser("~/.claude/task-locks")
cwd = os.getcwd()
active = []
for lock in glob.glob(os.path.join(locks_dir, "*.lock")):
    try:
        with open(lock) as f:
            d = json.load(f)
        if d.get("cwd") == cwd:
            active.append(d)
    except Exception:
        pass
if active:
    for a in active:
        print(f"  LOCKED: {a.get('slug', '?')} — claimed by session {a.get('session_id', '?')[:8]}...")
else:
    print("  No active task locks in this project.")
PYEOF
```

If locks exist from another session, warn:
```
Task locks in {cwd}:
  LOCKED: {slug} — claimed by session {id}
  Run /release {slug} in the other session, or /claim --force to take over.
```

### Step 5 — SOP backlog check

Check if `~/.claude/sop-backlog.md` exists and has entries:
```bash
if [ -f "$HOME/.claude/sop-backlog.md" ] && [ -s "$HOME/.claude/sop-backlog.md" ]; then
    echo "Pending SOP candidates:"
    cat "$HOME/.claude/sop-backlog.md"
fi
```

If entries exist, display them. If any entry's origin session has since completed the work (e.g., "analysis incomplete" is now complete), remind to forge or delete:
```
SOP backlog: {N} pending
  - {entry 1} — still relevant? [forge now / delete / keep]
```

If file is empty or doesn't exist: skip silently.

### Step 6 — Session summary

Print one block:
```
Session open — {timestamp}

{resume context or "no prior context"}
{task queue summary: N tasks in Rebel's queue}
{work-style: injected ✓}
{task locks: clean / N locks active}
{sop backlog: N pending / clean}

Ready. Pick a task or tell me what to work on.
```

## Rules

- **No approval gates** — run all 5 steps sequentially without asking
- **Non-blocking** — if any step fails (e.g., Notion API down), continue to the next, note the failure
- **Don't auto-claim** — show the queue, let the user pick. `/claim` happens when they choose.
- **Don't auto-resume** — show the resume context, but wait for user confirmation before diving back into the paused work
- **Idempotent** — safe to run multiple times per session
- **Hooks stay as hooks** — session-start-marker.sh, work-style-inject.sh, claim-reminder.py run independently via SessionStart event. This skill orchestrates the interactive steps that need display output.
