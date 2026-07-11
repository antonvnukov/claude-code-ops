# Session-Retro — Trigger Architecture & Telemetry

This document captures the trigger architecture for `/session-retro` and how to query its history. Lives next to `SKILL.md` so it doesn't get lost on /compact.

---

## The trigger problem

Manual invocation alone is unreliable — depends on Anton remembering to type `/session-retro` at the right moment. We need automatic triggers, but **`SessionEnd` hook is unreliable** (this is documented in `~/.claude/skills/capture-progress/SKILL.md`: "the SessionEnd hook is unreliable").

**Why SessionEnd fails:** Sessions don't end cleanly. They end via `/compact`, `/clear`, terminal-close, crash, or timeout. There's no single hookable "session end" event.

**Reliable hookable moments:**
- ✅ `SessionStart` — fires on every new session
- ✅ `Stop` — fires after every Claude turn
- ✅ `UserPromptSubmit` — fires on every user message (Anton already uses this for `docs-health`)
- ✅ `/loop` — periodic time-based trigger (Anton already uses for `/loop 2h /capture-progress`)
- ❌ `SessionEnd` — unreliable

So the right architecture hooks the moments that ARE reliable, layered by escalation.

---

## Order of operations

**ALWAYS:** `/capture-progress` → `/session-retro` → `/compact` (or `/clear`)

**Why this order:**
- `/capture-progress` is the **safer baseline** — fast, dumps to che-brain, low failure risk
- `/session-retro` is **heavier** — edits files, creates skills, can fail mid-execution
- If retro is interrupted, progress is already safely captured
- They use separate capture sources (`session_progress` vs `session_retro`) — no content overlap
- Risk-first principle: do the cheap save before the expensive transformation

**Never run them in reverse order.** It looks intuitive ("retro then summarize") but it's wrong because retro is the riskier operation.

---

## 5 Triggers (in escalation order)

### Trigger 0 — Loop safety net ✅ READY (manual start)

Periodic time-based trigger via existing `/loop` mechanism. Catches sessions that never hit `/compact` or `/clear`.

**Setup at session start (when expecting >2h of work):**
```
/loop 2h /capture-progress
/loop 4h /session-retro
```

**Why different intervals:**
- capture-progress every 2h: cheap, safe, baseline
- session-retro every 4h: heavier, less frequent, self-skips on idle

**Self-skip behavior:** Both skills exit cleanly with "nothing new to capture/encode" if no friction or progress occurred since last run. No-op cost is near zero.

**When to use:** Long sessions where you expect to forget ceremony triggers. Daily driver pattern when working on a multi-hour project.

---

### Trigger 1 — Ceremony tie-in ✅ SHIPPED (2026-04-07)

Automatic invocation at Anton's existing manual ceremonies:

```
At ~70% context → /capture-progress → /session-retro → /compact
Before /clear   → /capture-progress → /session-retro → progress.md → commit
```

**Why this works:** /compact and /clear are the moments where context (and learnings) actually get lost. They're already part of Anton's workflow — adding capture+retro to them is no new ceremony to learn.

**Encoded in:** `~/.claude/CLAUDE.md` Workflow Preferences.

**Coverage estimate:** ~80% of sessions where learnings exist. Misses sessions that end via terminal-close without compaction.

---

### Trigger 2 — Voluntary breakpoints ✅ SHIPPED (2026-04-07)

Proactive Claude suggestion at natural session breakpoints, even before /compact threshold:

- Finished a focused work block where friction occurred
- About to switch projects (Client A → my-startup → my-agency)
- End of day if any retro-worthy events happened
- User signals session-ending intent ("let's wrap up", "done for today")
- Just made a major decision worth encoding

**Encoded in:** `~/.claude/CLAUDE.md` Default Behaviors → "Session-retro voluntary triggers".

**Coverage estimate:** Catches the high-friction sessions Trigger 1 misses. Combined with Trigger 1 = ~95% coverage.

---

### Trigger 3 — Stop hook friction counter ⏳ NOT YET SHIPPED

**When to escalate from Triggers 0-2:** if after 1-2 weeks of real use you notice friction happening but no retros being run (sessions ending via terminal-close without ceremonies, voluntary triggers being missed).

**Mechanism:**
1. `Stop` hook fires after every Claude turn
2. Tiny script scans the prior user message for friction signals: `"no"`, `"instead"`, `"actually"`, `"you could have"`, `"wrong"`, `"again"`, `"why didn't you"`
3. Increments `~/.claude/.session-retro/friction-count-{session-id}`
4. When count > 3, append soft note to `~/.claude/.session-retro/pending-prompts`

**Reset:** `/session-retro` invocation clears the counter for the current session.

**Implementation sketch:**
```bash
# ~/.claude/hooks/stop-friction-scanner.sh
SESSION_ID="${CLAUDE_SESSION_ID:-default}"
COUNT_FILE="$HOME/.claude/.session-retro/friction-count-$SESSION_ID"
LAST_USER_MSG="$1"

if echo "$LAST_USER_MSG" | grep -qiE "(^no\b|instead|actually|you could have|^wrong|^again|why didn'?t you)"; then
  COUNT=$(cat "$COUNT_FILE" 2>/dev/null || echo 0)
  echo $((COUNT + 1)) > "$COUNT_FILE"
fi
```

---

### Trigger 4 — SessionStart hook reminder ⏳ NOT YET SHIPPED

**When to escalate to Trigger 4:** after Trigger 3 is in place. Trigger 4 surfaces previous session's friction count at the start of the next session.

**Mechanism:**
1. `SessionStart` hook reads `~/.claude/.session-retro/friction-count-*`
2. If any file has count > 3, prepend soft note to next user prompt:
   > ⚠️ Previous session had N friction events without a retro. Run `/session-retro` first?
3. After retro runs (or user dismisses), delete stale counter files

**Catches:** the "closed terminal mid-session" case — next session opens with the prompt automatically.

---

## Escalation criteria

| Signal | Action |
|---|---|
| Triggers 0-2 catching most retros, friction encoded weekly | Stay current |
| 2+ weeks of real friction with 0 retros run | Ship Trigger 3 |
| Trigger 3 catches friction but reminders never seen | Ship Trigger 4 |
| All triggers in place but encoded rules don't fire next session | Problem is CLAUDE.md size/density, not the trigger — refactor rules |

**Review checkpoint:** Notion task scheduled for 2026-04-21 — query che-brain for `source = session_retro` count, decide if escalation needed.

---

## Querying retro history

All `/session-retro` runs capture a meta summary to che-brain with `source: "session_retro"`.

### Via che-brain MCP
```
mcp__che-brain__search_knowledge with query "session_retro"
```

### Via SQL (Supabase direct)
```sql
SELECT created_at, content, project
FROM thoughts
WHERE source = 'session_retro'
ORDER BY created_at DESC
LIMIT 30;
```

### Compounding report (monthly review pattern)
At month end, query last 30 days of `source = session_retro`:
- How many retros ran? (target: 1+ per week of active work)
- What patterns repeat? (3+ retros mentioning same friction = systemic issue)
- How many new skills were created? (target: 1 per month)
- Which destination files grew the most? (signal for where the system is learning fastest)

Could be auto-generated via `/loop 30d /session-retro-monthly` — TBD if monthly pattern justifies a new skill.

---

## Status (2026-04-07)

- ✅ Skill: `~/.claude/skills/session-retro/SKILL.md`
- ✅ Documented: `~/.claude/CLAUDE.md` Default Behaviors + Workflow Preferences
- ✅ Listed: `MEMORY.md` Skills Created registry
- ✅ Trigger 0 (loop): documented, ready to start manually at session start
- ✅ Trigger 1 (ceremony): shipped — fixed order to capture-progress → session-retro → compact
- ✅ Trigger 2 (voluntary): shipped — encoded in Default Behaviors
- ⏳ Trigger 3 (Stop hook): not shipped — wait for usage data, escalate if needed
- ⏳ Trigger 4 (SessionStart hook): not shipped — depends on Trigger 3
- ✅ Telemetry: che-brain `source: session_retro` (queryable)
- ✅ Layer 1 review scheduled: Notion task 2026-04-21
- ⏳ Monthly compounding report: TBD if data justifies it

**First retro run on itself:** 2026-04-07, 6 learnings encoded across 3 files (CLAUDE.md, MEMORY.md, Client A/CLAUDE.md), 1 new skill created. che-brain IDs: 1339-1345.
