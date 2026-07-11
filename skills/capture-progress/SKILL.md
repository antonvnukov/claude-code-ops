---
name: capture-progress
description: "Extract knowledge and progress from current session to che-brain. Use standalone or via /loop 2h /capture-progress for periodic auto-capture."
uses:     []
requires: []
bets:     []
maturity: proven
chain:
  produces: "brain items (decisions, progress, context)"
  chains: ["close-session", "research-capture"]
  position: 3
---

# Capture Progress

Extract reusable knowledge and session progress from the current Claude Code conversation into che-brain. This is the primary way sessions that run for days/weeks get their knowledge preserved — the SessionEnd hook is unreliable.

## Instructions

### Step 1: Determine project

Map current working directory:
- `~/projects/che-brain` → `personal`
- `~/projects/my-startup` → `my-startup`
- `~/projects/my-agency` → `my-agency`
- `~/projects/gotomoney.io` → `vnukov_io`
- Anything else → omit project override

### Step 2: Check for previous captures

Look back through the conversation for any previous `/capture-progress` output (the confirmation line "Progress captured to che-brain"). Everything BEFORE that line has already been captured — only extract knowledge from messages AFTER the last capture. If no previous capture exists, scan the full conversation.

### Step 3: Extract knowledge items

Scan the conversation (new messages only — see step 2) and extract **discrete, individually useful** knowledge items. Each item must be valuable to a future session that has zero context about this one.

**Categories to extract (skip categories with nothing new):**

**Decisions** — choices made with full rationale
- Format: `Decision: Chose X over Y because Z. Considered alternatives: A, B. Tradeoff: [what was gained/lost].`
- Include: architectural choices, tool selections, approach pivots, scope changes
- Must include the WHY, not just the WHAT

**Technical insights** — things discovered that are reusable
- Format: `Insight: [thing learned]. Context: [how it was discovered]. Applies to: [where else this is useful].`
- Include: API behaviors, framework quirks, performance findings, undocumented behaviors
- Must be specific enough to act on without re-discovering

**Problems + solutions** — debugging knowledge
- Format: `Problem: [what went wrong]. Root cause: [why]. Fix: [what solved it]. Watch for: [when this might recur].`
- Include: errors encountered, workarounds found, configuration gotchas

**Patterns** — reusable approaches or cross-project connections
- Format: `Pattern: [description]. Used in: [this context]. Also applies to: [other contexts].`

### Step 4: Capture knowledge items to che-brain

For EACH knowledge item extracted in Step 3, make a **separate** `mcp__che-brain__capture_thought` call:
- `content`: the formatted knowledge item (one item per call — NOT batched)
- `project`: mapped project from Step 1
- `source`: `"session_knowledge"`

Separate calls ensure each item is individually searchable and classifiable in che-brain.

**Step 4-qmd — qmd nudge (per-project recall).** che-brain (above) is a push API; qmd only indexes local `.md`. If a knowledge item is **project-scoped** and was written to the project's qmd-indexed path (`~/projects/<proj>/...`, not `~/.claude` memory which qmd does not index), re-index it: `~/.claude/scripts/qmd-sync.sh` (auto-detects collection from cwd; worktree-aware; non-blocking). Skip if purely global/cross-project (che-brain only) or no qmd collection for this project.

If no MCP tool available, fall back to curl per item:
```bash
curl -s -X POST "https://YOUR-PROJECT.supabase.co/functions/v1/ingest" \
  -H "Authorization: Bearer $BRAIN_ACCESS_KEY" \
  -H "Content-Type: application/json" \
  -d '{"content": "<item>", "source": "session_knowledge", "project": "<project>"}'
```

### Step 5: Capture session status summary

Before capturing, check `.planning/STATE.md` in the current project for an `active_notion_task_url:` line. If found (and not "(none…)"), include it in the summary so future sessions can find the Notion task from a che-brain search.

After all knowledge items, capture ONE status summary via `mcp__che-brain__capture_thought`:
- `source`: `"session_progress"`
- `project`: mapped project from Step 1
- `content`: formatted as:

```
## Session Progress — {project} — {YYYY-MM-DD HH:MM}

### Notion Task
{active_notion_task_url from STATE.md, or "not linked"}

### Done (since last capture)
- (2-5 bullets)

### Blockers / Problems
- (What's stuck or was stuck. Skip if none.)

### Current
- (What's actively in progress)

### Next
- (What's planned next)

### Key files
- (Files created or modified, path only)
```

### Step 6: Output confirmation

Print a single summary line:
```
Captured to che-brain ({project}): {N} knowledge items + status summary
```

If invoked by `/loop`, keep output to this one line only. If invoked manually, you may add a 2-3 line breakdown of what was captured (category counts).

## Rules

- **New content only**: Never re-capture knowledge from before the last `/capture-progress` invocation in this session.
- **No code in content**: Describe what code does, don't paste it. Exception: one-liner commands or config snippets that ARE the insight.
- **No questions**: Just capture and confirm. Never ask the user anything.
- **Nothing to capture**: If the session just started or nothing meaningful happened since last capture, output `Nothing new to capture` and skip all POSTs.
- **Quality over quantity**: 2 high-value knowledge items beat 8 thin ones. If a "decision" is trivial (e.g., "named the file X"), skip it.
- **Each item must stand alone**: A future session reading this item in search results must understand it without needing the rest of this conversation.
