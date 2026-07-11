---
name: release
description: "Release a task lock claimed via /claim. Removes the lock file so another session can pick up the task. Idempotent — no error if no lock exists. Auto-runs at end of /close-session. Use when task is complete, or when you realize you don't actually need the lock anymore."
uses: []
requires: []
bets:     []
maturity: proven
chain:
  consumes: "task lock file"
  produces: "released lock"
  chains: ["close-session"]
  position: 99
---

# /release — Task Lock Release

Removes a task lock created by `/claim`. Signals to other parallel Claude sessions "this task is free again — either I'm done or I gave up."

## When to run

- Task is complete (commit landed, deploy verified, work finished)
- You claimed the wrong thing and need to re-claim
- You're handing off to another session on purpose
- Automatic: end of `/close-session` ritual
- Automatic: end of work block if it wraps cleanly

## Usage

```
/release                      # release most recently claimed lock for current cwd
/release <slug>               # release specific slug
/release --all                # release all locks for current cwd (end-of-session cleanup)
```

## Instructions

### Step 1: Resolve which lock to release

**If `<slug>` argument provided** — target `~/.claude/task-locks/{slug}.lock`.

**If `--all` flag** — target all locks where the `cwd` field matches current `pwd`.

**If no argument** — target the most recent lock where `cwd` matches current `pwd`, ordered by `started_at` descending. This is the "release the thing I just claimed" default.

```bash
LOCKS_DIR="$HOME/.claude/task-locks"
CWD="$(pwd)"

# Default: find most recent lock for current cwd
most_recent=$(python3 -c "
import json, os, glob
locks = []
for f in glob.glob('$LOCKS_DIR/*.lock'):
    try:
        with open(f) as fh:
            d = json.load(fh)
        if d.get('cwd') == '$CWD':
            locks.append((d.get('started_at', ''), f))
    except Exception:
        pass
locks.sort(reverse=True)
print(locks[0][1] if locks else '')
")
```

### Step 2: Confirm (soft)

If the target lock is more than 10 minutes old OR has status `in_progress` with no visible progress markers, print the lock details and ask:

```
🔓 About to release:
  slug: {slug}
  task: {task}
  age: {N} minutes
  status: {status}

Release? (Y/n)
```

Proceed on `y`, `yes`, or empty input. Abort on explicit `n`.

**For auto-invocation from `/close-session`** — skip the confirmation. Closing ritual is intentional.

### Step 3: Remove the lock file(s)

```bash
rm -f "$TARGET_LOCK"
```

Idempotent — no error if file doesn't exist.

### Step 4: Clear STATE.md ## Tracking if Notion URL matches

When releasing a lock that has a `notion_task_url` set (not null), check if `.planning/STATE.md` exists in the lock's `cwd`. If it does AND `active_notion_task_url` matches the lock's `notion_task_url`, clear the tracking section — the task is no longer being actively worked:

```python
import json, re

with open(lock_file) as f:
    lock = json.load(f)

notion_url = lock.get("notion_task_url")
if notion_url and notion_url != "null":
    state_path = f"{lock['cwd']}/.planning/STATE.md"
    try:
        with open(state_path) as f:
            content = f.read()
        if notion_url in content:
            content = re.sub(
                r"(## Tracking\n\nactive_notion_task_url: .*?\nlast_linked: .*?\n)",
                f"## Tracking\n\nactive_notion_task_url: (none — released {today_date})\n",
                content, flags=re.DOTALL
            )
            with open(state_path, "w") as f:
                f.write(content)
    except FileNotFoundError:
        pass  # not a GSD project, skip
```

Only clears if the URL in STATE.md matches — never blindly overwrites if another task was claimed after this one.

### Step 5: Confirm to user

Print a single line per released lock:
```
🔓 Released: {slug}
```

If nothing was released, print:
```
(no active lock to release for /path/to/cwd)
```

## Integration

- **`/claim`** — creates the lock this skill removes
- **`/close-session`** — invokes `/release --all` at the end of the ritual
- **SessionStart hook** — surfaces remaining active locks; released locks disappear from the next session's context immediately

## Rules

- **Never release someone else's lock silently** — if the lock's `session_id` doesn't match the current session AND the age is less than the TTL, warn before removing. Another parallel session may still be working.
- **--all is scoped to cwd** — never removes locks from other project directories, even with --all
- **Idempotent** — running `/release` twice in a row on the same task is never an error

## Anti-patterns

- ❌ Releasing right before committing — release AFTER the commit lands, so parallel sessions don't pick up the task during the final push
- ❌ Using --all mid-session — that flag is for cleanup only
- ❌ Force-releasing another session's active lock — if you genuinely need to take over, first verify the other session is actually dead (check transcripts, ask the user)
