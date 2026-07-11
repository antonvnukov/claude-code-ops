---
name: checkpoint
description: "Write a resumable checkpoint of current work state. Detects work type (carousel, gsd-phase, script, report), writes .claude/checkpoint.md in project dir, then chains /capture-progress. Run before /compact or at context monitor WARNING. Closes the context-loss gap for non-GSD iterative work."
uses:     []
requires: [capture-progress]
bets:     []
maturity: proven
chain:
  produces: ".claude/checkpoint.md + che-brain items"
  chains: ["capture-progress"]
  position: 1
---

# Checkpoint

Write a resumable checkpoint for the current session. This is the skill that closes the context-loss gap for iterative work (carousels, scripts, reports) that doesn't have GSD phase tracking. Chains into `/capture-progress` automatically.

## When to run

- Context monitor fires WARNING (≤35%) — run this instead of `/mid-sess-check`
- About to run `/compact`
- Switching tasks mid-session
- End of an iterative review block (carousel slides, script debugging, report iteration)

## Chain

```
/checkpoint
  Step 1: detect work type
  Step 2: assemble state
  Step 3: write .claude/checkpoint.md
  Step 4: → /capture-progress  (knowledge items + session status → che-brain)
  Step 5: confirm
```

## Process

### Step 1 — Detect work type

Scan conversation context and recent file activity:

| Signal | Work type |
|---|---|
| `/tmp/*.html` recently written + `/tmp/*-slides/` PNG dirs | `carousel` |
| `.planning/STATE.md` has active phase | `gsd-phase` |
| Python/JS/shell files being iterated | `script` |
| Google Sheets, Notion, slide output | `report` |
| Everything else | `general` |

### Step 2 — Assemble checkpoint state

Extract these fields regardless of work type:

```
work_type: carousel | gsd-phase | script | report | general
current_file: <abs path to most recently edited/created file>
last_completed: <one sentence — what was just finished>
pending_next: <one sentence — the SPECIFIC next action, concrete enough to execute cold>
key_files:
  - <abs path>: <one-line description>
context_notes: <anything a cold-start agent MUST know to not redo work>
captured_at: <ISO timestamp>
```

**Work-type additions:**

For `carousel`:
```
carousel_html: <abs path to latest .html file>
carousel_slides_dir: <abs path to latest slides dir>
slides_total: N
slides_reviewed: N
slide_status:
  slide-1: approved | pending-fix | not-reviewed
  slide-2: ...
  ...
```

For `gsd-phase`:
```
phase: <phase dir name>
plan: <plan file name>
task_last: <last completed task subject>
task_next: <next task subject>
continue_here: <abs path to .continue-here.md>
```

### Step 3 — Write checkpoint file

**Primary location:** `{cwd}/.claude/checkpoint.md`
**Fallback** (if cwd has no `.git`): `/tmp/session-checkpoint.md`

Always overwrite — checkpoint.md is always latest state, no versioning.

Format:

```markdown
---
checkpoint_version: 1
captured_at: {ISO timestamp}
project: {basename of cwd}
work_type: {type}
---

# Session Checkpoint

## Current Work

**File:** {current_file}
**Last completed:** {last_completed}
**Pending next:** {pending_next}

## Key Files

- `{abs path}` — {description}

## Context Notes

{context_notes — include gotchas, decisions made, things NOT to redo}

## Decisions Made

1. {Decision: what was chosen, what was ruled out, why. Include tradeoffs.}

{work-type-specific section here if applicable}

---

## Session Log

### Session {N} — {YYYY-MM-DD}
**Completed:** {specific outputs with absolute file paths and numbers — e.g. "wrote 3 slides, slide-2 approved, slide-3 pending-fix at /tmp/carousel-v3/slide-3.png"}
**Next:** {exact next step — specific enough to execute without questions, e.g. "fix slide-3 copy: shorten headline to <8 words, then re-export /tmp/carousel-v3/"}

---

## Resume Prompt

{A 3-5 sentence paragraph written in second person. Quality bar: MUST contain specific file paths, numerical outputs, and exact next steps. Vague summaries ("we were working on the carousel") = unacceptable. Self-test: could a cold-start agent read ONLY this paragraph and execute the next step without asking a single clarifying question? If no, rewrite.}
```

The **Resume Prompt** is the highest-value output. It must be a complete standalone instruction — precise enough that reading it is sufficient to resume with zero session memory.

### Step 4 — Chain to /capture-progress

After writing the file, run `/capture-progress` to extract knowledge items and session status to che-brain. The checkpoint file handles operational state; che-brain handles reusable knowledge. Both are needed.

### Step 5 — Confirm

```
Checkpoint written: {path}
Chained: /capture-progress — {N} items captured
Resume: checkpoint auto-injects on next session start (checkpoint-inject.sh)
```

## Rules

- **Resume Prompt must be self-contained** — no "as discussed" or session references
- **All paths absolute** — checkpoint file is read cold; relative paths are useless
- **Overwrite freely** — always latest state, no history
- **Never truncate** — this is a file write, not a chat message; write the full content
- **carousel: list every slide status** — approved / pending-fix / not-reviewed for each
- **Handoff readiness self-test** — after writing, evaluate: "Could a fresh session resume from this file alone, without asking any clarifying questions?" If YES → note `HANDOFF READY`. If NO → note `COMPRESS NEEDED` (working memory not fully captured — compact in-place instead of starting a new session).

## Verification

1. `{cwd}/.claude/checkpoint.md` exists and has a Resume Prompt section
2. Resume Prompt contains at least one absolute file path
3. `/capture-progress` completed without error
