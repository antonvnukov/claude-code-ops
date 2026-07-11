---
name: claim
description: "Claim a task to prevent parallel Claude sessions from working on the same thing. Creates a lock file in ~/.claude/task-locks/. Use BEFORE starting any task that takes more than 3 tool calls, especially when picking from a 'what's next' list. Fail loud on collision — never negotiate."
uses: []
requires: []
bets:     []
maturity: proven
chain:
  consumes: "task selection"
  produces: "lock acquired"
  chains: ["session-startup"]
  position: 3
---

# /claim — Task Lock Claim

Creates a file-based lock that signals other parallel Claude sessions "this task is being worked on". Simple, fast, no external dependencies.

## When to run

**Required before:**
- Starting any task that will take more than 3 tool calls
- Picking up a task from a pending/backlog list when multiple sessions could conceivably grab it
- Working on bug fixes, feature builds, refactors, migrations, deployments
- Long debugging sessions where you'll make many edits

**Skip when:**
- Answering a one-shot question (no file changes, no multi-step work)
- The user is actively watching and told you exactly what to do
- Quick file reads, greps, explorations

## Usage

```
/claim "short task description"
/claim "Fix extract-transcript OpenRouter credits exhaustion"
/claim "Debug n8n Telegram transcription Phase 3.1 + 3.2"
/claim "phase-7-planning" --notion https://notion.so/YOUR-PAGE
```

The `--notion <url>` flag is optional. When provided:
1. Written to the lock file's `notion_task_url` field (visible to other sessions on collision)
2. Written to STATE.md `## Tracking` section in the current project (enables task tracking sync)

If the task has an obvious Notion URL from context (e.g., reading STATE.md `## Tracking`), pre-populate it automatically.

## Instructions

### Step 1: Parse the task description and optional flags

Parse `--notion <url>` from the args if present. Remove it from the description before deriving the slug.

```
task="Phase 7 planning --notion https://notion.so/YOUR-PAGE
notion_url="https://notion.so/YOUR-PAGE
description="Phase 7 planning"
```

If no `--notion` flag is provided, check STATE.md in the current project (`.planning/STATE.md`). If `active_notion_task_url:` is present, use it as the default notion_url for the lock file.

Take the task description (without flags) verbatim. Derive a slug:
- Lowercase
- Replace spaces and underscores with hyphens
- Strip all non-alphanumeric/non-hyphen characters
- Collapse multiple hyphens into one
- Trim leading/trailing hyphens
- Truncate to 60 characters max

Example: `"Fix extract-transcript OpenRouter credits"` → `fix-extract-transcript-openrouter-credits`

### Step 2: Clean up stale locks

Before checking for collision, auto-remove any lock file where `now - started_at > ttl_hours`. Default TTL is 4 hours. This handles crashed sessions that never released.

```bash
LOCKS_DIR="$HOME/.claude/task-locks"
mkdir -p "$LOCKS_DIR"
now=$(date +%s)
for lock in "$LOCKS_DIR"/*.lock; do
  [ -f "$lock" ] || continue
  started=$(python3 -c "import json,sys,datetime; d=json.load(open('$lock')); t=datetime.datetime.fromisoformat(d['started_at'].replace('Z','+00:00')); print(int(t.timestamp()))" 2>/dev/null || echo 0)
  ttl_hours=$(python3 -c "import json; print(json.load(open('$lock')).get('ttl_hours', 4))" 2>/dev/null || echo 4)
  age=$((now - started))
  max_age=$((ttl_hours * 3600))
  if [ "$age" -gt "$max_age" ]; then
    echo "stale: removing $(basename "$lock") (age ${age}s, ttl ${max_age}s)"
    rm -f "$lock"
  fi
done
```

### Step 3: Check for collision

Two kinds of collision to detect:

**a. Exact slug match** — hard fail. Another session has claimed this exact task.

```bash
LOCK_FILE="$LOCKS_DIR/${SLUG}.lock"
if [ -f "$LOCK_FILE" ]; then
  echo "🚫 COLLISION: $SLUG is already claimed"
  cat "$LOCK_FILE"
  exit 1
fi
```

**b. Substring keyword overlap** — soft warn. Another session may be working on something similar.

Extract 2+ significant keywords (3+ chars, not stopwords like "the", "fix", "add") from the incoming task description. Search all existing lock files' `task` field for matches. If 2+ keywords match a single existing lock, warn the user and ask them to confirm before proceeding.

**On collision (exact or keyword):** STOP. Do NOT create the lock. Report the collision to the user with:
- The conflicting lock's slug, task description, session_id, cwd, age in minutes, Notion task URL (if set)
- Ask: "Proceed anyway? (y/N — default N)"
- Only proceed if user explicitly confirms "y" or "yes"

### Step 4: Write the lock file

```bash
SESSION_ID="${CLAUDE_SESSION_ID:-$(date +%s)-$(hostname -s)-$$}"
CWD="$(pwd)"
PROJECT="$(basename "$CWD")"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TTL_HOURS=4
NOTION_URL="${NOTION_URL:-null}"  # from --notion flag or STATE.md

cat > "$LOCK_FILE" <<EOF
{
  "session_id": "$SESSION_ID",
  "cwd": "$CWD",
  "project": "$PROJECT",
  "task": "$TASK_DESCRIPTION",
  "slug": "$SLUG",
  "started_at": "$STARTED_AT",
  "ttl_hours": $TTL_HOURS,
  "status": "in_progress",
  "notion_task_url": "$NOTION_URL"
}
EOF
```

### Step 4b: Sync Notion URL to STATE.md (if project has .planning/)

If `NOTION_URL` is set (not null) AND `.planning/STATE.md` exists in the current project:

Use Python/sed to upsert the `## Tracking` section with the notion URL:

```python
import re, os

state_path = ".planning/STATE.md"
with open(state_path) as f:
    content = f.read()

tracking_block = f"""## Tracking

active_notion_task_url: {notion_url}
active_notion_task_id: {notion_url.split('/')[-1].split('?')[0]}
active_notion_task_title: "{task_description}"
last_linked: {today_date}
"""

if "## Tracking" in content:
    # Replace existing block
    content = re.sub(r"## Tracking\n.*?(?=\n##|\Z)", tracking_block.rstrip(), content, flags=re.DOTALL)
else:
    # Append before ## Session Continuity
    content = content.replace("## Session Continuity", tracking_block + "\n## Session Continuity")

with open(state_path, "w") as f:
    f.write(content)
```

This keeps STATE.md `## Tracking` in sync with the active lock whenever you claim a task with a Notion URL.

### Step 5: Confirm to user

Print a single line:
```
🔒 Claimed: {slug} ({ttl_hours}h TTL) → {LOCK_FILE}
```

If Notion URL was set:
```
   ↳ Notion task linked: {notion_url}
   ↳ STATE.md ## Tracking updated
```

Then continue with the task.

## Integration

- **`/release`** — removes the lock when the task is done (or `/close-session` auto-runs it)
- **SessionStart hook** — surfaces active locks in the current cwd when a new session begins, so other sessions see active claims immediately
- **Notion Phase B (future)** — extend to also create/update a Notion task with Status=Doing; store the URL in `notion_task_url`

## Rules

- **Never silently skip a collision** — always fail loud. A parallel session getting clobbered is much worse than an extra yes/no gate.
- **TTL default is 4 hours** — adjust only for tasks genuinely expected to take longer (e.g., migrations, long-running builds)
- **One active claim per slug** — if you need to re-claim after releasing, that's fine (new lock, new timestamp)
- **Don't claim exploratory work** — reading files, running greps, answering questions. Only claim when you're about to DO something.

## Anti-patterns

- ❌ Claiming after starting work — the point is to prevent collision BEFORE work begins
- ❌ Claiming then ignoring a collision warning — if another session owns it, STOP and pick a different task
- ❌ Using a vague description like "fix bug" — specific descriptions prevent false-positive keyword matches
- ❌ Forgetting to release — `/close-session` should auto-release, but manual `/release` works too
