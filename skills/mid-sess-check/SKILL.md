---
name: mid-sess-check
description: "Mid-session safety checkpoint — runs automatically at 35% context remaining. Captures progress to che-brain, shows git work at risk, checks Notion link (actively searches for Doing tasks if none linked), surfaces .continue-here.md status. Lighter than /close-session — doesn't commit or end session. Run anytime during a long session to make sure nothing will be lost. Use `--subtask` mode to wrap up a COMPLETED subtask tab in a shared Conductor workspace (multiple tabs, one worktree/branch): reports up via .context/, releases its own task lock, and NEVER writes the shared checkpoint.md — the main tab stays the sole closer."
uses: []
requires: [checkpoint]
bets:     []
maturity: proven
chain:
  consumes: "mid-session state at 35% context"
  produces: "checkpoint + che-brain capture + retro Pass 0"
  chains: ["close-session"]
  position: 1
---

# Mid-Session Check

Lightweight safety checkpoint. Run when context monitor warns at 35%, or any time during a long session. Does NOT end the session — just makes sure work is captured and risks are visible.

## When to run

- Context monitor injects WARNING (≤35% remaining) → run this immediately
- You've been working 90+ minutes without a checkpoint
- About to start a complex new subtask and want a clean state
- User says "check in", "how are we doing", "what have we done"

## Mode: subtask wrap-up (`--subtask`)

For the **multi-tab-one-workspace** pattern: a main tab + N subtask tabs sharing ONE Conductor worktree/branch/files. When a SUBTASK tab finishes its piece, it must NOT run `/close-session` (that rewrites the shared `checkpoint.md`, commits, and sweeps locks — N closers on one branch collide). Instead it runs `/mid-sess-check --subtask`, which "reports up" to the main tab and gets out of the way.

`--subtask` flips three things vs. the normal run; everything else (capture-progress, git-risk scan, retro warm-up to JSONL, asset scan) is identical:
1. **No shared checkpoint write.** Step 1 redirects the handoff to a PER-TAB file `.context/subtask-{lock-slug}.md` (Conductor's gitignored cross-tab dir) instead of `.claude/checkpoint.md`. → no clobber of the main tab.
2. **Release THIS tab's own lock** (Step 1d) — a finished subtask is *done*, not paused.
3. **Commit guidance, not a commit** — commit own files only if disjoint from other tabs; if they overlap, leave them for the main-tab closer.

The **main tab** stays the sole closer: it runs `/close-session` once at the end, reconciling the `.context/subtask-*.md` notes + all tabs' edits into one commit + one checkpoint. Detect mode from the `--subtask` arg (or, if absent but a sibling task-lock with a different `session_id` shares this cwd, suggest `--subtask`).

## Process (no approval gate — runs sequentially without prompting)

### Step 1 — Write checkpoint + capture progress

**Subtask mode (`--subtask`):** do NOT invoke `/checkpoint` (it writes the shared `.claude/checkpoint.md`). Instead write the resume/handoff note to `.context/subtask-{lock-slug}.md` (create `.context/` if absent; `{lock-slug}` = this tab's task-lock slug, else a short kebab of the subtask), then invoke `/capture-progress` directly (che-brain is append-only — no collision). Skip Step 1b's checkpoint-readiness framing; the `.context/` note IS the handoff. Then continue to Step 1d.

**Normal mode:** Invoke `/checkpoint` skill immediately. This is the most important step — it:
1. Writes `.claude/checkpoint.md` with full resume context (auto-injected on next session start)
2. Chains into `/capture-progress` automatically (knowledge items → che-brain)

Both the local file AND che-brain are updated in one call. If `/checkpoint` is unavailable, fall back to `/capture-progress` directly.

**Step 1c — qmd sync (lightweight).** If this is project/client work and any project `.md` was written/updated this session, re-index the project's qmd collection so mid-session knowledge is searchable immediately (qmd indexes files, not a push API like che-brain): `~/.claude/scripts/qmd-sync.sh` (auto-detects collection from cwd; worktree-aware; non-blocking). Skip silently if it reports no matching collection.

**Step 1b — Handoff readiness gate** (runs immediately after checkpoint is written):

Evaluate the Resume Prompt just written:
> "Could a fresh session resume from this checkpoint file alone, without asking any clarifying questions?"

- **HANDOFF READY** — Resume Prompt has specific file paths, numerical outputs, exact next steps. Starting a new session is safe. Present the Resume Prompt as a ready handoff block.
- **COMPRESS NEEDED** — Resume Prompt contains vague progress summaries, session-specific working memory, or unresolved decisions not yet in files. Compact in-place instead of starting a new session — new session would start blind.

Display: `Handoff: [READY | COMPRESS NEEDED] — {one sentence reason}`

**Step 1b-R — Handoff REACHABILITY gate (the surface must auto-load, not just exist).**
Readiness (1b) asks "is the content good enough?"; reachability asks "will next session actually SEE it?" A handoff is worthless if it lives only on a surface that does not auto-inject. Auto-loading surfaces: `.claude/checkpoint.md` (SessionStart hook) and the project's MEMORY.md-indexed memory file (loaded every session for that project). NOT auto-loading: `.context/subtask-*.md`, `/tmp/*` JSONL, che-brain (recall-only, must be queried).

Trigger when EITHER: (a) `--subtask` mode (handoff went to `.context/`, which does not auto-load), OR (b) normal mode but `.claude/checkpoint.md` is **unreliable for you** — a sibling task-lock with a *different* `session_id` shares this cwd (multi-tab worktree: another tab can overwrite the checkpoint), OR the existing checkpoint's content belongs to a different lane than yours.

When triggered AND there are open decisions / next-actions that must survive to a fresh session: **upsert a compact `▶ RESUME` block into the auto-loading memory surface** for this project:
1. In the project memory file (`~/.claude/projects/<proj>/memory/project_<slug>.md`), **replace** (never append) a single delimited block:
   ```
   ## ▶ RESUME HERE (paused <date> → resume <next>)
   <2-6 lines: report-movement-first instruction · the open-decision queue (D1..DN with the recommendation for each) · exact resume commands/paths · pointer to the `.context/` handoff for depth>
   ```
   Idempotent: if a `▶ RESUME HERE` block exists, overwrite it wholesale — one block per project, never accumulate.
2. Flag it in `MEMORY.md`'s index line for that project (append/replace a `▶ RESUME <date>: <one-line>` tail), so it's visible the instant the index loads.
Keep it to the **decision queue + pointers only** — durable facts and full detail stay in the `.context/` handoff and che-brain. Do NOT dump session logs into memory (pollution). If there are no open decisions (clean stop), skip — nothing to route.

**Two hard rules on the RESUME block (else it becomes a liability, not an aid):**
- **DURABLE = the decision; STALE = the instances.** Write the *decisions* ("handle warm waiting replies", "decide FU2 artifact") as durable, but mark every concrete instance/count/name inside them as a **point-in-time snapshot that MUST be re-fetched from live state before acting** — never execute a recommendation off the frozen block. (Failure mode: a "reply to Lead X + Lead Y" note executed next day double-touches a lead a sibling tab already answered — the exact harm the live-state check exists to prevent.) Put a literal `⟳ re-fetch live before acting — counts/names below are a {timestamp} snapshot` line at the top of the block.
- **CONSUME-AND-CLEAR.** The block is a baton, not a monument. Whoever resumes it (this project's next session, or `/close-session`) MUST delete or rewrite the `▶ RESUME HERE` block + its MEMORY.md index tail once the decisions are picked up or resolved — a RESUME block older than its pause date is stale and misleading. State this obligation inside the block itself.

Display: `Reachability: [AUTO-LOADS | ROUTED-TO-MEMORY | N/A no open decisions] — {surface}`

### Step 1c — Trajectory tagging (client work only)

If the current session involves client work (check cwd for `clients/` path, or task lock name contains a client name):

1. Determine a `trajectory_id` from the work context: `{client}-{phase}` (e.g., `Client A-audit`, `client-b-discovery`).
2. Check if this trajectory already exists in che-brain:
   ```
   search_knowledge(query="{trajectory_id} trajectory", project="gotomoney_io", limit=3)
   ```
3. Capture a trajectory checkpoint to che-brain:
   ```
   capture_thought(
     content="TRAJECTORY:{trajectory_id} | Session checkpoint: {1-sentence summary of what was done + what's next}",
     project="gotomoney_io",
     source="trajectory_checkpoint"
   )
   ```

This is lightweight — just tags decisions with a trajectory_id so `/close-session` can stitch them into a full SOP later. No extraction here.

Skip if: internal/infra work, no client context in cwd or task lock.

### Step 1d — Release own lock + commit guidance (SUBTASK MODE ONLY)

Skip entirely in normal mode (mid-sess-check never ends or releases). In `--subtask` mode the subtask is DONE, so:

1. **Release THIS tab's own task lock** — scoped by `session_id` (never sweep a sibling tab's lock). Same logic as `/close-session` Step 9:
```bash
python3 - <<'PYEOF'
import json, os, glob
locks=os.path.expanduser("~/.claude/task-locks"); cwd=os.getcwd()
sid=os.environ.get("CLAUDE_SESSION_ID","")
if not sid:
    ms=sorted(glob.glob("/tmp/claude-sessions/session-*.json"), key=os.path.getmtime, reverse=True)
    for m in ms:
        try:
            d=json.load(open(m))
            if d.get("cwd")==cwd: sid=d.get("session_id",""); break
        except: pass
for lk in glob.glob(os.path.join(locks,"*.lock")):
    try:
        d=json.load(open(lk))
        if d.get("cwd")==cwd and sid and d.get("session_id")==sid:
            os.remove(lk); print("🔓 released own lock:", d.get("slug", os.path.basename(lk)))
    except: pass
PYEOF
```
2. **Commit guidance (do NOT auto-commit).** Run `git status --short`; classify this tab's files (MINE) vs other tabs' edits (EXTERNAL). If MINE are DISJOINT from EXTERNAL → you MAY commit only the MINE list (explicit paths, never `git add .`). If MINE OVERLAP any file another tab is editing → leave uncommitted and note it in the `.context/` handoff so the main-tab closer reconciles into one commit. Print: `Commit: {committed N mine | left for main-tab closer — overlaps: <files>}`.

### Step 2 — Work-style micro-signal

Append a raw signal line to `~/.claude/work-style-profile.md` — same format as `/close-session` step 3. Gives the weekly synthesis mid-session data points, not just session boundaries.

```bash
PROFILE="$HOME/.claude/work-style-profile.md"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
PROJECT=$(basename "$PWD")
ENTRY="- $TIMESTAMP | project: $PROJECT | cwd: $PWD"

if [ -f "$PROFILE" ]; then
    if ! grep -q "^## Raw Signals Buffer" "$PROFILE"; then
        printf "\n## Raw Signals Buffer\n<!-- Auto-appended by SessionStop hook. Not for direct reading. Consumed by /work-style learn. -->\n" >> "$PROFILE"
    fi
    echo "$ENTRY" >> "$PROFILE"
fi
```

Non-blocking: if write fails, continue.

### Step 3 — Git risk scan

Check git status in current cwd. Classify and display:

```bash
git status --short
```

Show:
```
Git risk in {cwd}:
  Uncommitted tracked changes (LOST if session crashes):
    M path/to/file1
    M path/to/file2
  Untracked new files (also at risk):
    ?? new-script.py
```

If clean → "Git clean ✓ — no work at risk"

### Step 3.25 — Session activity summary (from brain observations)

Read today's PostToolUse observations JSONL to show what this session actually did (files touched, commands run, tool distribution). This is objective data from the `brain-observe-post-tool.sh` hook, not reconstructed from memory.

```bash
TODAY=$(date +%Y-%m-%d)
OBS_FILE="$HOME/.che-brain/observations/observations-$TODAY.jsonl"
if [ -f "$OBS_FILE" ]; then
  python3 -c "
import json, sys, collections
lines = open(sys.argv[1]).read().strip().split('\n')
tools = collections.Counter()
files = set()
cmds = []
for line in lines:
    try:
        obs = json.loads(line)
        tools[obs.get('tool', '?')] += 1
        ctx = obs.get('context', {})
        if ctx.get('file_path'):
            files.add(ctx['file_path'].split('/')[-1])
        if ctx.get('command'):
            c = ctx['command'][:60]
            if c not in cmds: cmds.append(c)
    except: continue
print(f'Observations today: {len(lines)} actions')
print(f'Tools: {dict(tools)}')
if files: print(f'Files: {', '.join(sorted(files)[:12])}')
if cmds: print(f'Commands: {'; '.join(cmds[:5])}')
" "$OBS_FILE"
fi
```

Include the experience type detected for this session's work:
```bash
# Detected from .openexp.yaml or prompt keywords
python3 ~/projects/che-brain/scripts/brain-recall.py --query "session check" --cwd "$PWD" --json --limit 1 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Experience: {d.get(\"experience\", \"default\")}')" 2>/dev/null
```

Display: `Session activity: {N} observations | Experience: {type} | Files: {list}`

Non-blocking: if no observations file exists, note "no observations captured" and continue.

### Step 3.5 — Asset discoverability scan

Scan what this session produced or acquired. "Acquired" = installed tools, imported workflows, received templates from others, cloned repos for use. "Produced" = new files, new Notion tasks, new skills.

**Check 3 surfaces:**

1. **Registries** — for each asset, is it registered?
   - New tool/workflow installed → Lego Registry + Workflows Registry?
   - New skill installed → Skills Registry (auto-synced, but verify it appears in skill list)?
   - Reusable block built → Lego Registry?

2. **Project CLAUDE.md** — if tools were installed or workflows acquired for a specific client/project, does that project's CLAUDE.md reference them? A future session in that directory should know the tools exist without reading session history.

3. **Notion task bodies** — scan tasks created this session. Do they have structured bodies (What/Why/Action Steps/Links/Limitations)? A title-only or Description-only task is incomplete per global CLAUDE.md rules.

**Output:**
```
Asset discoverability:
  [asset name]: Registry {ok|MISSING} | CLAUDE.md {ok|MISSING} | che-brain {ok|MISSING}
  Notion tasks created: {N} total, {M} with full bodies, {P} need enrichment
```

If gaps found, list them but do NOT fix during mid-sess-check (that's close-session's job). Just make them visible so they're addressed before session ends.

Non-blocking: if no assets were produced/acquired, note "no assets to check" and continue.

### Step 4 — Notion task link check

**Applies to:** Any project with `.planning/STATE.md` in cwd.

Read `## Tracking` → `active_notion_task_url`.

**If a task IS linked:**
- Confirm "Notion linked ✓ — {url}"
- **Agent task sub-check:** Fetch the task and check `🤖 Agent` checkbox. If true:
  - Check `Agent Context` property — warn if empty: "⚠️ Agent task missing Agent Context — Rebel/poller won't know what to do"
  - Check `Agent Status` — report current value (Queued/Executing/Blocked/Review)
  - Check task body for structured prompt (Objective + Instructions sections) — warn if missing: "⚠️ Agent task body has no structured prompt"
  - Include in risk summary: "Agent task: {title} — context: {✓|⚠️ missing} | status: {value} | body: {✓|⚠️ no prompt}"

**If NO task is linked (missing, `(none)`, or empty):**

Do NOT just warn passively. Actively search for matching Doing tasks and offer to link one.

1. Determine which Tasks DB to query based on cwd (see `/track` skill Project Mapping):
   - `~/projects/my-startup` or `~/projects/che-research` → `YOUR-NOTION-DB-ID`
   - All other projects → `YOUR-NOTION-DB-ID`

2. Query Notion for tasks in `Doing` status, sorted by last-edited descending:

```bash
NOTION_KEY=$(doppler secrets get YOUR_SECRET --config dev --project che-all --plain 2>/dev/null)
DB_ID="YOUR-NOTION-DB-ID"  # or my-startup DB based on cwd

curl -s -X POST "https://api.notion.com/v1/databases/$DB_ID/query" \
  -H "Authorization: Bearer $NOTION_KEY" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {"property": "Status", "status": {"equals": "Doing"}},
    "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}],
    "page_size": 10
  }'
```

3. Present matches (up to 5) with title, project, and URL:

```
⚠️ No Notion task linked. Active "Doing" tasks found:
  1. [Task title] — {project} — https://notion.so/YOUR-PAGE
  2. [Task title] — {project} — https://notion.so/YOUR-PAGE
  3. [Task title] — {project} — https://notion.so/YOUR-PAGE

Link one? Pick a number, or type "skip" to continue without linking.
→ To link: /claim --notion <url>
→ To create new: /track "task description"
```

4. If user picks a task, run `/claim --notion <url>` to link it to STATE.md.
5. If no Doing tasks match the current work, suggest: "Run `/track` to find or create a matching task."

**Why active search, not passive warning:** A passive "no task linked" message gets ignored. Showing actual Doing tasks makes it trivial to link the right one, and catches stale Doing tasks (tasks that should be Done but aren't).

### Step 5 — Handoff file check (GSD projects only)

Check if `.planning/phases/**/.continue-here.md` exists (any phase):
- If yes: "Handoff file ✓ — resume context saved"
- If no: "⚠️ No .continue-here.md — if session ends, next session starts cold. Run /gsd:pause-work to save context."

### Step 5.5 — Retro warm-up (writes to JSONL for convergence loop)

Scan the session for learnings accumulated so far and **write them to the JSONL file**. This gives `/close-session`'s convergence loop a head start - items found here become Pass 0, so Pass 1 in close-session builds on them instead of starting cold.

**Scan all 3 layers:**
- **Layer 1:** User corrections, retries, missed tools, new conventions/gotchas
- **Layer 2:** New technique/tool used for first time, user reframed output, plan step skipped, data insight mapped to engagement model
- **Layer 3:** Client work patterns, reusable processes, trajectory milestones
- **Automation/loop signal:** a task iterated to convergence in-session, a scheduled/repeated need, or a manual multi-step pattern → log as `category:"automation"`. Route later via `~/.claude/AUTOMATION-CANDIDATE-ROUTING.md` (loop vs launchd vs n8n vs delegate vs skill; `/loop`=in-session-only, scheduled→launchd). Flag it now so close-session's Step 4 doesn't miss it.

**For each item found, append to JSONL:**

```bash
SESSION_ID=$(python3 -c "
import json, glob, os
markers = glob.glob('/tmp/claude-sessions/session-*.json')
if markers:
    latest = max(markers, key=os.path.getmtime)
    data = json.load(open(latest))
    if data.get('cwd') == os.getcwd():
        print(data.get('session_id', ''))
" 2>/dev/null)
```

Each item gets one JSONL line in `/tmp/retro-items-{session_id}.jsonl`:
```json
{"pass": 0, "layer": "L1", "category": "friction", "item": "hook test cwd must match session marker", "destination": "CLAUDE.md", "source": "mid-sess-check"}
```

**Display summary:**
```
Retro warm-up: {N} items written to JSONL (L1={n} friction | L2={n} strategic | L3={n} trajectory)
  → close-session convergence loop will start from Pass 0 with {N} items pre-loaded
  → {RICH SESSION — full retro mandatory | clean session — retro optional}
```

If total items >= 3, add to risk summary: "Rich session - retro will need full convergence scan at close."

**This is NOT the full retro.** Don't present items to user, don't ask for encoding approval, don't edit files. Just write to JSONL and move on. The convergence loop in `/close-session` or `/session-retro` will read these items, exclude them from re-scanning, and continue with focused passes.

Non-blocking: always continue regardless of count.

### Step 6 — Skill Forge scan

Sessions spanning 2-6 days accumulate enough repeated patterns to justify a skill. Scan the session context for:

- A process repeated 2+ times (same tool invocation pattern, same debugging approach, same API combo)
- A multi-step flow that was assembled ad-hoc and worked end-to-end
- A prompt or extraction pattern that produced consistent results

**Gate:** Only invoke `/skill-forge` if at least one qualifying pattern is found. Don't force it.

If pattern found → invoke `/skill-forge`:
- OBSERVE: describe the pattern abstractly (strip task-specific details)
- ABSTRACT: define generic inputs/outputs
- WRITE → TEST (3 cases) → REFINE → PUBLISH if score ≥ 0.8

If no pattern → note "no skill candidate this session" and continue.

Non-blocking: if skill-forge produces nothing or scores < 0.8, continue to risk summary.

### Step 7 — Risk summary

Print one block:

```
Mid-session check — {timestamp}

✓ Checkpoint: .claude/checkpoint.md written (auto-injects on next start)
✓ Captured: che-brain ({N} items + status)
{session activity line: "Activity: {N} observations | Experience: {type} | Files: {list}"}
{git status line}
{notion status line}
{agent task line — only if 🤖 Agent = true}
{handoff status line}
{reachability line: "Reachability: [AUTO-LOADS | ROUTED-TO-MEMORY | N/A] — {surface}" — from Step 1b-R}
{skill-forge line: "Skill forged: {name} (score: {score})" | "No skill candidate this session"}

Context remaining: {X}% — {guidance}
  ≥35%: Continue working. Next checkpoint at ~25%.
  25-35%: Wrap current task, then /close-session.
  <25%: Run /close-session NOW before context cuts out.
```

Then capture the risk summary itself to che-brain via `mcp__che-brain__capture_thought`:
- `source`: `"session_check"`
- `project`: mapped project from cwd
- `content`: the same block printed above (verbatim), prefixed with `## Mid-Session Check — {timestamp}`

Non-blocking: if the capture fails, note it and continue.

## Rules

- **No approval gates** — run all steps sequentially without asking
- **Never end the session** — this is a checkpoint, not a close
- **Non-blocking** — if any step fails, continue to the next one, note the failure
- **A handoff must be REACHABLE, not just written** (Step 1b-R) — in a shared/multi-tab worktree, `.claude/checkpoint.md` can be clobbered by a sibling tab and `.context/*.md` never auto-loads, so open decisions/next-actions get routed to the auto-loading project memory as a single idempotent `▶ RESUME` block. Route the decision queue + pointers ONLY; never dump session logs into memory.
- **No git commits in normal mode** — that's /close-session's job. **Subtask mode** may commit ONLY this tab's own files and ONLY when disjoint from other tabs' edits (Step 1d); overlapping files always defer to the main-tab closer.
- **Idempotent** — safe to run multiple times per session

### Subtask-mode rules (`--subtask`)
- **Never write the shared `.claude/checkpoint.md`** — the handoff goes to per-tab `.context/subtask-{lock-slug}.md`. The main tab owns the checkpoint.
- **Release ONLY this tab's own lock** (scoped by `session_id`) — never sweep a sibling tab's lock.
- **The main tab is the sole closer** — it runs `/close-session` once, reconciling all `.context/subtask-*.md` notes + edits into one commit + one checkpoint. Subtask tabs never run `/close-session`.
- **Retro warm-up (Step 5.5) still writes to the shared JSONL** — that's intended: the main tab's close-session convergence loop reads subtask items as Pass 0.
- **Reachability applies here most of all** (Step 1b-R) — subtask mode's `.context/subtask-*.md` handoff does NOT auto-load, so any open decision that must survive to a fresh session is *also* routed to the auto-loading project memory `▶ RESUME` block. The `.context/` file holds the depth; memory holds the pointer + decision queue.
