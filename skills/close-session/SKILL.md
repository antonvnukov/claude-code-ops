---
name: close-session
description: "Unified closing ritual — chains git status check, /capture-progress, /session-retro, /track done, and /gsd:pause-work into one command. Use when ending a session intentionally ('wrap up', 'close session', 'done for the day'), before /clear or /compact, or auto-triggered at 25% remaining context (CRITICAL threshold)."
uses: []
requires: [capture-progress, session-retro, track, delegate, close-asset-audit]
bets:     []
maturity: proven
chain:
  consumes: "active session work"
  produces: "captured + committed + handed-off session"
  chains: ["close-session"]
  position: 1
---

# Close Session — Unified closing ritual

Chain the 5 closing rituals into ONE command so a session never ends without capturing learnings, committing work, and handing off to the next session. Designed for parallel-session workflows where manual per-session closing doesn't scale.

## When to run

**Explicit triggers:**
- User says "wrap up", "close session", "done for the day", "let's stop"
- Before `/clear` or `/compact`
- End of any focused work block where friction occurred

**Automatic triggers (via hooks):**
- `gsd-context-monitor.js` at **25% remaining** (CRITICAL) → full ritual
- `PreCompact` hook → safety net before context overflow
- `SessionEnd` hook → catch non-graceful closes (unreliable, best-effort)

## Process

Run these steps IN ORDER. Stop on any blocking error. **Single approval gate:** after step 1, user confirms → proceed through all remaining steps (2-10) without further prompts.

**GATE MECHANISM (enforced by TWO hooks — `retro-gate.py` + `close-retro-stop-gate.py`):**

Create the gate marker **immediately AFTER the Step-1 approval** (NOT before — the Step-1 commit question is a turn-end and would otherwise be blocked by the Stop-hook gate):
```bash
SESSION_ID=$(python3 -c "
import json, glob, os
markers = glob.glob('/tmp/claude-sessions/session-*.json')
if markers:
    latest = max(markers, key=os.path.getmtime)
    print(json.load(open(latest)).get('session_id', ''))
" 2>/dev/null)
if [ -n "$SESSION_ID" ]; then
    touch "$HOME/.claude/close-pending-$SESSION_ID"
fi
```

**Two independent gates now enforce the retro convergence loop:**
1. `retro-gate.py` (PreToolUse:Write) — blocks any `checkpoint.md` write until convergence ran. Only fires IF a checkpoint is written.
2. `close-retro-stop-gate.py` (**Stop**) — blocks turn-end (the actual "session closed" moment) whenever `close-pending-{id}` exists but `/tmp/retro-converged-{id}.json` is missing or has `passes < 2`. **This closes the 2026-05-30 hole**: a close path that never writes `checkpoint.md` (non-GSD project, external/parallel checkpoint, or just not writing one) used to escape the loop silently. Now it can't end the turn without it.

**Critical:** an *inline / ad-hoc* retro does NOT satisfy either gate. You MUST actually invoke the `/session-retro` skill — its convergence loop is what writes `retro-converged-{id}.json`. Summarizing learnings yourself in close-session text is exactly the failure that produced a shallow first pass on 2026-05-30. No instruction can override a hook block.

**Step order rationale:** Retro is Step 2 (immediately after git check) because it needs full context. If context compacts during close-session, retro is what's lost first when it's at Step 4+. Git check is Step 1 because it's fast and prevents work loss. Everything else can work with less context.

### Step 1 — Git state check (PRE-FLIGHT)

Run `git status --short` in current working directory. Then **classify every modified or untracked file** into one of two buckets before proposing anything:

**MINE** — files I explicitly edited via Write/Edit/Bash tool calls in THIS session. Check your own tool call history to identify these.

**EXTERNAL** — modifications I did NOT make, which includes:
- Files present as "modified" at session start (from a prior session, a parallel session, or uncommitted work)
- Files modified by hooks DURING this session (iloom-hook, notion-capture-hook, gsd-summary-check, etc.)
- Files modified by another Claude session running in parallel on the same repo

**Detection precedence (highest confidence to lowest):**

1. **Session marker (PREFERRED — set up 2026-04-08)** — read `/tmp/claude-sessions/session-{session_id}.json` written by the `session-start-marker.sh` SessionStart hook. Contains `head_sha` (git HEAD at session start). Compute:
   ```bash
   START_SHA=$(jq -r .head_sha /tmp/claude-sessions/session-{session_id}.json)
   git diff --name-only $START_SHA HEAD        # committed files changed since start
   git diff --name-only $START_SHA -- .         # all files (committed + uncommitted) changed since start
   ```
   Intersect with `git status --short` → precise "MINE" set. Files present in git status but NOT in the diff-from-start are EXTERNAL.
2. **Tool-call history (fallback)** — if no marker exists (hook didn't fire, file deleted, or cross-worktree session), scan your own Edit/Write/Bash tool calls in this session and list every file path you modified. Intersect with `git status --short`.
3. **Heuristic (last resort)** — if neither is reliable, ASK the user: "I see modifications to X, Y, Z. Which ones did we work on together this session?"

**Reading the marker:**
```bash
MARKER="/tmp/claude-sessions/session-${SESSION_ID}.json"
if [ -f "$MARKER" ]; then
    START_SHA=$(python3 -c "import json; print(json.load(open('$MARKER'))['head_sha'])")
    MARKER_CWD=$(python3 -c "import json; print(json.load(open('$MARKER'))['cwd'])")
    # Verify cwd matches — session may have changed directories
    if [ "$PWD" = "$MARKER_CWD" ] && [ "$START_SHA" != "nogit" ]; then
        MINE_CANDIDATES=$(git diff --name-only "$START_SHA" HEAD 2>/dev/null)
        # Also include uncommitted changes since start
        MINE_CANDIDATES="$MINE_CANDIDATES"$'\n'"$(git diff --name-only 2>/dev/null)"
    fi
fi
```

**Then present the scoped commit proposal:**

```
Uncommitted tracked changes:

Mine (this session — stage + commit):
  M path/to/file1.md
  M path/to/file2.py

External (not this session — leave alone):
  M projects/other/file.md     (modified by parallel session or hook)
  M skills/track/SKILL.md      (modified by parallel session)

Untracked (REQUIRES APPROVAL — not auto-added):
  ?? scripts/new-thing.py      (mine? new file I created)
  ?? gpts/                     (parallel session output)

Propose commit: "[type](scope): short description"
  Files to include: 2 (Mine only)
  External: 2 (left as-is, another session owns them)
  Untracked: ask per file before including

Proceed with commit + close ritual? (yes/no)
```

**Rules:**
- **NEVER use `git add .` or `git add -A`** — always explicit file list scoped to MINE.
- **NEVER stage External files** — they belong to whoever modified them. Another session or hook will commit them. If you stage them, you steal someone else's work into your commit message.
- **Untracked files ALWAYS require per-file approval** — even if you think they're yours. A parallel session may have dropped scripts in the same directory.
- **Report External files in the final summary** so the user knows something else touched the repo during this session.

### Step 2 — Session retro (three-layer scan) — MUST RUN BEFORE ANYTHING ELSE

**WHY THIS IS STEP 2 (not Step 4):** Retro needs full context. If context compacts during close-session, retro is what's lost. Git check (Step 1) is fast and prevents work loss. Retro (Step 2) captures learning while context is maximally available. Everything else can work with less context.

**Trigger check — retro runs if ANY of these are true:**

1. **Layer 1 (friction):** User corrections >= 1, missed tools, repeated iterations (3+ tries), new convention/gotcha, strategy pivots
2. **Layer 2 (strategic):** A new technique/tool was used, user reframed output ("go deeper", "is that all?"), data insight maps to engagement model, plan step was skipped
3. **Layer 3 (trajectory):** Session involved client work (`clients/` in cwd), a reusable multi-step process was executed, findings map to engagement model
4. **Client work shortcut:** If cwd contains `clients/` → retro is MANDATORY. Client sessions always produce Layer 2/3 learnings even without friction.

**If ALL layers are empty** (rare — pure read-only or exploratory session with no deliverable) → skip and note "no retro-worthy events across all 3 layers".

**ACTUALLY INVOKE the `/session-retro` skill — do not summarize learnings inline.** The convergence loop lives INSIDE that skill; an inline retro writes no `retro-converged-{id}.json` marker and is now blocked by `close-retro-stop-gate.py` (you won't be able to end the turn). On 2026-05-30 the loop never ran because close-session did an ad-hoc retro instead of calling the skill → shallow single pass → user had to ask "is that all?" twice. Invoke the skill. The skill runs a three-layer scan with severity filters and confidence tagging. See `~/.claude/skills/session-retro/SKILL.md` for full spec.

**CONVERGENCE LOOP (enforced by `retro-gate.py` hook):**

Run `/session-retro` which executes a convergence loop internally. The retro runs multiple passes (minimum 2, maximum 5) until `delta < 3` new items per pass. Do NOT present retro results until convergence is reached.

**Pre-loaded items:** Before starting Pass 1, check if `/tmp/retro-items-{session_id}.jsonl` already exists (written by `/mid-sess-check` Step 5.5 or `/track done` Step 6). If it does, read existing items as Pass 0 - exclude them from re-scanning and count them toward the total. This means the convergence loop starts warm, not cold.

The convergence loop writes:
- `/tmp/retro-items-{session_id}.jsonl` — structured items per pass
- `/tmp/retro-converged-{session_id}.json` — convergence marker with pass count + item totals

The `retro-gate.py` hook blocks checkpoint.md writes if:
- Convergence marker is missing (loop didn't run)
- `passes < 2` (minimum 2 passes required)
- Warns (doesn't block) if `total_items < 10` in a productive session

**Evidence this matters (why the loop exists):**
- 2026-05-22: Pass 1 = 3 items → converged at 10
- 2026-05-26: Pass 1 = 8 items → converged at 18
- 2026-05-27: Pass 1 = 9 items → converged at 14
- 2026-05-28: Pass 1 = 18 items → converged at 42

**On completion, create the gate marker:**
```bash
SESSION_ID=$(python3 -c "
import json, glob, os
markers = glob.glob('/tmp/claude-sessions/session-*.json')
if markers:
    latest = max(markers, key=os.path.getmtime)
    print(json.load(open(latest)).get('session_id', ''))
" 2>/dev/null)
if [ -n "$SESSION_ID" ]; then
    touch "$HOME/.claude/retro-done-$SESSION_ID"
fi
```

Without this marker, `retro-gate.py` will BLOCK checkpoint.md writes.

**Anti-pattern (2026-05-12):** Retro skipped with "no technical patterns" despite 4+ corrections. Conversational sessions have the most valuable learnings.

**Anti-pattern (2026-05-21):** Retro skipped with "no friction post-compaction." Compaction does NOT erase friction — scan the compaction summary.

**Anti-pattern (2026-05-22):** Retro ran but only found 3 Layer 1 items. User had to ask "any lessons?" twice to surface 6 more Layer 2/3 items.

**Anti-pattern (2026-05-23):** `/close-session` arrived during mid-commit. Jumped from git check → commit → checkpoint → "done", skipping retro entirely. This happened 3 times across sessions. The reorder + hook gate prevents this mechanically.

**Anti-pattern (2026-05-27, 8th occurrence):** Retro passed quantitative gate (11 items) but extraction step was skipped entirely. Jumped from retro → checkpoint → "safe to /clear" without running Step 5a (client artifact extraction). User asked "are you sure that's all?" and second pass found 4 Lego blocks, 2 SOPs, 1 SaaSw stack template, 2 skill candidates, 2 automation candidates. **Root cause:** extraction has no mechanical gate like retro does. Fix: extraction depth gate added below.

### Step 3 — Capture progress + session activity

Invoke `/capture-progress` skill. This captures WHAT was done (decisions, problems, status) to che-brain. See `~/.claude/skills/capture-progress/SKILL.md` for full spec.

**Step 3a-qmd — qmd sync (per-project recall, mandatory for project/client work).** che-brain is captured above, but qmd (the per-project local search Anton queries) only indexes `.md` files in a collection's path — it does NOT auto-update. If this was project/client work AND any durable knowledge was written to the project's qmd-indexed path this session (per the session-retro qmd routing rule), re-index it:
```bash
~/.claude/scripts/qmd-sync.sh   # auto-detects the project's collection(s) from cwd; conductor-worktree aware; non-blocking
```
If it reports "no qmd collection matches this project", that's fine. If it warns you're in a worktree, durable project knowledge must be written under `~/projects/<proj>/...` (not the worktree) to be searchable. Report the synced collection(s) in the final summary.

**Step 3b — Session activity from observations**

Read today's PostToolUse observations JSONL for an objective activity summary:

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
        if ctx.get('file_path'): files.add(ctx['file_path'].split('/')[-1])
        if ctx.get('command'):
            c = ctx['command'][:60]
            if c not in cmds: cmds.append(c)
    except: continue
print(f'Session activity: {len(lines)} observations')
print(f'Tools: {dict(tools)}')
if files: print(f'Files: {\", \".join(sorted(files)[:12])}')
if cmds: print(f'Commands: {\"; \".join(cmds[:5])}')
" "$OBS_FILE"
fi
```

Also detect and report the session's experience type (sales/engineering/content/dealflow/default):
```bash
python3 ~/projects/che-brain/scripts/brain-recall.py --query "session close" --cwd "$PWD" --json --limit 1 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Experience: {d.get(\"experience\", \"default\")}')" 2>/dev/null
```

Include both in the final summary block. Non-blocking: if observations file is empty, note "no observations captured."

### Step 3 — Work-style signal (reliable replacement for SessionEnd hook)

Append a raw signal line to `~/.claude/work-style-profile.md` — same format as `work-style-session-stop.sh` but guaranteed to fire (SessionEnd hook is unreliable). This costs ~0 and feeds the weekly `/work-style learn` synthesis.

```bash
PROFILE="$HOME/.claude/work-style-profile.md"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
PROJECT=$(basename "$PWD")
ENTRY="- $TIMESTAMP | project: $PROJECT | cwd: $PWD | signals: {FILL_BEHAVIORAL_SIGNALS}"

if [ -f "$PROFILE" ]; then
    if ! grep -q "^## Raw Signals Buffer" "$PROFILE"; then
        printf "\n## Raw Signals Buffer\n<!-- Auto-appended by SessionStop hook. Not for direct reading. Consumed by /work-style learn. -->\n" >> "$PROFILE"
    fi
    echo "$ENTRY" >> "$PROFILE"
fi
```

Non-blocking: if the file doesn't exist or the write fails, continue to the next step.

### Step 4 — Automation opportunity check (conditional)

**(Retro is now Step 2. Old Step 4 moved up because it needs full context.)**

**Scan independently of retro output.** Do NOT gate on retro tagging `[automation-candidate]` — shallow retros miss obvious candidates (proven 2026-05-27: 2 n8n candidates missed because retro was shallow). Instead, scan the session directly:

- Was a manual data pipeline executed? (Excel parse → DB load → dashboard update) → n8n candidate
- Was a monitoring/alerting need identified? (stale data, broken queries) → n8n candidate
- Was a multi-step API workflow done manually? (login → create → wire → share) → skill candidate
- Was a scheduled check mentioned? ("weekly refresh", "monthly report") → **launchd/cron** candidate (unattended, survives crashes) — NOT `/loop`, which dies with the session
- Was a task iterated to convergence in-session? (fix-until-tests-pass, refine-until-QA-green) → **`/loop`** candidate (attended)

**Route every candidate via `~/.claude/AUTOMATION-CANDIDATE-ROUTING.md`** — the 6-part loop-anatomy check + the loop-vs-launchd-vs-n8n-vs-delegate-vs-skill decision table. Don't default to `/loop` or a new skill; the #1 error is routing unattended/scheduled work to `/loop` (it can't survive a crash).

If ANY signal present, generate proposals. If retro ALSO tagged candidates, include those too.

For each tagged candidate, produce:

```
Automation opportunity: {description}
Type: {skill | n8n | hook | loop | delegate}
Evidence: {what happened in this session — the manual pattern}
Proposal:
  - If skill → skill name, 3 sub-use-cases, trigger phrases
  - If n8n → trigger, steps, output destination
  - If hook → event (PostToolUse/SessionStart/etc), matcher, action
  - If loop → Hermes cron spec (schedule, model, task)
  - If delegate → /delegate task body (Objective, Instructions, Output, Verification)
→ Build now with {/skill-forge | /n8n-workflow-builder | /delegate}? [Y/N]
```

**Rules for this step:**
- Max 3 proposals per session (if more candidates, pick highest frequency/impact)
- Each proposal must name the specific builder skill that would create it
- If user says N to all, note "deferred — will resurface in /weekly-ops" and continue
- If user says Y, execute the builder skill inline, then continue to step 5
- Non-blocking: don't stop the close ritual if user declines

### Step 4c — SOP capture (conditional)

Scan the session for workflow signals:
- Multi-step process executed (>5 sequential tool calls toward one goal)
- Infrastructure setup or config change was performed
- Debugging session that resolved an issue (→ runbook candidate)
- A process was done that someone else might need to repeat (reporting, onboarding, deployment)

If ANY signal present:
> "This session executed a repeatable workflow: '{description}'. Capture as SOP? [Y/N/later]"
- **Y** → invoke `/sop-forge --from-session`
- **N** → skip
- **later** → append workflow title to `~/.claude/sop-backlog.md` for weekly batch

Skip if: session was purely exploratory, read-only, conversational, or a one-time fix with no repeatable pattern.

Non-blocking: don't stop the close ritual if user declines.

**SOP backlog review (runs after capture decision):**

If `~/.claude/sop-backlog.md` exists and has entries, scan each entry:
- Is the origin work now complete? (e.g., "analysis incomplete" → check if a later session finished it)
- Is the entry >2 weeks old? If yes, it's stale - either forge now or delete.

Display pending items in the summary. Don't block on them - just make them visible so they're addressed.

### Step 4d — Trajectory extraction (client work only)

If this session involved **client deliverable work** (check: cwd contains `clients/`, task lock name contains client name, or session produced files in a client directory):

1. Determine `trajectory_id`: `{client}-{phase}` (e.g., `Client A-audit`, `client-b-discovery`)
2. Query che-brain for all trajectory checkpoints + decisions for this trajectory:
   ```
   search_knowledge(query="TRAJECTORY:{trajectory_id}", project="gotomoney_io", limit=15)
   ```
3. **Arc complete?** — Check if the work reached a natural endpoint (audit delivered, onboarding done, report sent, contract signed). Signs: task marked Done, deliverable file exists, user said "done" about the client work.
4. **If arc complete** → extract full process SOP:
   - Gather all trajectory checkpoints chronologically
   - Synthesize into a process timeline: what steps, in what order, what tools, what decisions
   - Save to `GTM/_playbooks/sop-{client}-{phase}.md`
   - Register in Playbooks Registry (Notion DB `YOUR-NOTION-DB-ID`):
     - Status: "Tested (1 client)" if first time, bump to "Proven (2+ clients)" if template already exists
   - Report: "Trajectory complete: {trajectory_id} → SOP extracted → Playbooks Registry updated"
5. **If arc still in progress** → just tag the current session's decisions:
   ```
   capture_thought(
     content="TRAJECTORY:{trajectory_id} | Session close: {1-sentence of what was done + next step}",
     project="gotomoney_io", source="trajectory_checkpoint"
   )
   ```
   - Report: "Trajectory in progress: {trajectory_id} — checkpoint saved, {N} total checkpoints"

**Skip if:** internal/infra work, my-agency tasks, no client context. This step is GoToMoney client work only.

Non-blocking: don't stop the close ritual if extraction fails.

### Step 5 — Skill Forge + Client Artifact Extraction

> **HOOK-ENFORCED (`close-extraction-gate.py`, Stop):** if the retro ran, you CANNOT end the turn until `/tmp/extraction-audit-{session_id}.json` answers ALL 7 categories — each a concrete artifact OR `"none - <reason>"`, never blank. Omission (not false-negation) is the failure mode: on 2026-07-03 content + process-learning were silently skipped until the user asked "sure all extracted?". Forced enumeration fixes it — same discipline as the retro convergence loop.

**5.0 — 7-category extraction self-check (run FIRST, min 2 passes).** For the WHOLE session, answer each with an artifact-or-`"none - reason"`, then ACT on real artifacts (capture content ideas to che-brain/Content Ideas DB, update the RIGHT existing skill, register Lego blocks) BEFORE writing the file — it records what you DID, not intent:
1. **sops** — reusable multi-step process → che-brain trajectory / SOP
2. **skill_candidates** — new packaged skill worth forging
3. **skill_updates** — which EXISTING skill should gain this (check it doesn't already cover it — grep the SKILL.md)
4. **lego_blocks** — reusable connector/processing/assembly → Lego Registry
5. **content** — a post/story angle → che-brain + Content Ideas DB (via che-linkedin-post-engine)
6. **strategic_assets** — deck/framework/presentation asset
7. **process_learnings** — what tool/approach should I have used (e.g. "should've used che-safe-batch-write")

Then write the audit:
```bash
python3 -c "import json; json.dump({'session_id':'$SESSION_ID','passes':2,'categories':{'sops':'...','skill_candidates':'...','skill_updates':'...','lego_blocks':'...','content':'...','strategic_assets':'...','process_learnings':'...'}}, open('/tmp/extraction-audit-$SESSION_ID.json','w'))"
```
Any category = `none` on a session with real deliverables → do a 2nd pass; the first is ALWAYS incomplete.

**5a. Client artifact extraction (GoToMoney client sessions — MANDATORY)**

If cwd contains `clients/` OR session produced files in a client directory, run the full extraction checklist. **Do NOT use "not recurring yet" as a reason to skip.** First client = the template for all future clients.

Extraction checklist — for each, ask "could another client use this?":
1. **Scripts written?** → Lego Registry as processing block + template copy to `GTM/_playbooks/`
2. **Infrastructure setup / stack deployed?** → SOP playbook + if multi-tool stack, document as stack template in `GTM/_playbooks/sop-saasw-*.md`
3. **Tool configured?** → Document setup steps as playbook (include gotchas like Metabase Site URL fix)
4. **Research extracted?** → Tag domain-general portions, consider Playbooks Registry
5. **Notion tracking pattern?** → Document the structure used
6. **Decision framework?** → Capture tool/approach selection criteria
7. **Data pipeline executed?** → n8n automation candidate (Telegram trigger → parse → DB load)
8. **Monitoring need identified?** → n8n automation candidate (scheduled check → alert)

Every extracted artifact → 3 surfaces: local file (`GTM/_playbooks/`), Lego Registry (Notion), Playbooks Registry (DB `YOUR-NOTION-DB-ID`).

**EXTRACTION DEPTH GATE (mandatory self-check):**

After extraction scan, count artifacts. If client session AND artifacts < 4, force a second scan — you missed something. This gate exists because extraction was skipped entirely on 2026-05-27 (8th shallow close-session) despite producing 4 Lego blocks, 2 SOPs, 1 stack template, 2 skill candidates, and 2 automation candidates.

| Artifact type | Minimum for client session | If below → |
|---|---|---|
| Lego blocks | >=2 | Re-scan: any script, API pattern, or config trick reusable? |
| SOPs/playbooks | >=1 | Re-scan: was a multi-step process executed? |
| Stack templates | Check: was infra deployed? | If yes and not captured → write `sop-saasw-*.md` |
| Skill candidates | >=1 if tool workflow was >5 steps | Name it or confirm none |
| Automation candidates | >=1 if manual pipeline was executed | Name it or confirm none |

Present findings: "This session produced {N} reusable artifacts: {list}. Registering now." Then register without asking (the extraction is mandatory, not optional).

**5b. Skill forge (general sessions)**

Invoke `/skill-forge`. Observe what was done this session and ask: was there a reusable pattern? Write SKILL.md, test 3 cases (happy/edge/error), score it. Save only if quality ≥ 0.8.

**Run after step 4 (retro)** so patterns surfaced by the retro feed directly into forging. **Run before step 8 (git commit)** so any newly created skill files are included in the session commit.

Skip if: the session was purely exploratory, read-only, or conversational with no tool-driven deliverables.

Non-blocking: if skill-forge produces nothing (score < 0.8 or no reusable pattern), continue to next step.

### Step 5b — SOT Registry sync + asset wiring (HOOK-ENFORCED)

**Invoke `/close-asset-audit`.** This skill independently checks git for new components, queries Lego Registry for gaps, and verifies a Notion task exists. It writes `/tmp/asset-audit-{session_id}.json` on pass. The `close-asset-audit-gate.py` Stop hook blocks session close if this hasn't run and the session has >=2 commits.

**Do NOT skip this step or do it inline.** The recurring failure (9+ times, 2026-05-27 through 2026-06-19) was always the same: "wrap up" momentum caused rationalization of N/A entries in the asset table. The skill runs the check independently — it reads git and Notion directly, not your summary.

After `/close-asset-audit` passes, continue with the registry sync below for any additional registries (Chains, Workflows, Brand, Glossary) that the audit doesn't cover.

Scan what was **produced AND acquired** this session. "Acquired" includes: installed tools, imported workflows/playbooks, cloned repos for use, templates received from others. These are just as important as things you built — they need the same registration treatment.

**Registry check — update ONLY if relevant work happened:**

| Registry | Notion ID | Update when |
|---|---|---|
| Skills Registry | `YOUR-NOTION-DB-ID` | Auto-synced by PostToolUse hook ✓ — no action needed |
| Lego Registry | `YOUR-NOTION-DB-ID` | A reusable block was built OR acquired (installed tool, imported playbook, received template) AND `/track done` wasn't run |
| Chains Registry | `YOUR-NOTION-DB-ID` | A new skill chain was assembled or an existing chain was modified |
| Workflows Registry | `YOUR-NOTION-DB-ID` | A workflow was built, modified, imported, or acquired this session (n8n, AirOps, or any automation platform) |
| Brand Asset Registry | `YOUR-NOTION-DB-ID` | A new brand asset was created: handle, domain, tagline, logo, pillar |
| Glossary SOT | `YOUR-NOTION-DB-ID` | A new metric or term was defined or redefined |

**For each triggered registry:**
1. State what was produced/acquired: "Built/Acquired X → qualifies for {Registry}"
2. Ask: "Add to {Registry} now?" — single yes/no, no preamble
3. If yes: append the entry. If no: note "skipped by user" and continue

**Chains Registry update** (most likely to trigger after skill-forge):
- Update `~/.claude/CHAINS.md` locally (runtime SOT)
- Append/update Notion DB entry with: Name, Steps (ordered skill list), Trigger phrases, Status=Active, Lego cross-refs if applicable

**Workflows Registry update format:**
- Workflow name, instance (n8n/AirOps/other), workflow ID, trigger type, status (Active/Draft/Paused), last modified

**Discoverability wiring (runs after registries):**

For every asset produced or acquired, verify these 3 surfaces:

1. **Project CLAUDE.md** — if a tool/workflow was installed or acquired for a specific project (client work, phase deliverable), does that project's CLAUDE.md reference it? A future session in that directory must find the asset without reading session history.
   - Check: `grep -l "<asset_name>" $(find . -name CLAUDE.md -maxdepth 3)`
   - If missing: propose the specific CLAUDE.md edit

2. **che-brain** — was the asset captured as a knowledge item? Future sessions across ALL projects should find it via search.
   - Check: `mcp__che-brain__search_knowledge` with asset name
   - If missing: capture via `mcp__che-brain__capture_thought`

3. **Notion task body completeness** — scan every Notion task created this session. Each must have structured body blocks (What/Why/Action Steps/Links/Limitations per global CLAUDE.md rule). A title + Description-only task is incomplete.
   - For each task created: fetch page blocks, check for heading_2/heading_3 structure
   - If body is thin: enrich inline before closing

**Output format:**
```
Asset wiring:
  {asset_1}: Registry ✓ | CLAUDE.md ✓ | che-brain ✓
  {asset_2}: Registry ✓ | CLAUDE.md MISSING → {proposed edit} | che-brain ✓
  Notion tasks: {N} created, {M} with full bodies, {P} enriched now
```

Non-blocking: if all registries are skipped and all surfaces are wired, note "no registry/wiring updates needed" and continue.

**ASSET WIRING GATE (mandatory self-check — mirrors the extraction-depth gate).**

Step 5b is the most-skipped step: under "wrap up" momentum the ritual jumps from retro → summary and silently drops registry wiring. This has now recurred (2026-05-27 extraction skip; 2026-06-01 Lego Registry only added because the user asked "have it been added to lego blocks?"). Unlike retro/extraction, 5b had no gate. It does now:

Before printing the Step 10 final summary, you MUST enumerate **every asset built OR acquired this session** (new script, tool, workflow, skill, installed package, imported playbook, configured integration) and produce this table — no asset may reach the summary with an unchecked cell:

| Asset | Lego/Workflows Registry | project CLAUDE.md | che-brain |
|---|---|---|---|
| {asset} | ✓ / N/A+reason | ✓ / N/A+reason | ✓ / N/A+reason |

Rules:
- A built/acquired reusable asset (tool, connector, processing block, assembly) defaults to **Registry = required** — "N/A" must carry an explicit reason (e.g., "one-off, not reusable"), never a blank.
- If any cell is unchecked → wire it NOW (append to the registry page, edit the project CLAUDE.md, capture to che-brain) before continuing. Do not ask permission for the wiring itself — registration is mandatory, same as extraction.
- The final summary (Step 10) MUST include this table. If you cannot produce it, you have not finished Step 5b.
- **Every ✓ requires a fetch-back PROOF command, not self-assertion** (C3(d)). A registry ✓ = the `GET /children` (paginated to the tail) that shows the row; a commit ✓ = the `git status --short <file>` showing it clean; a Supabase ✓ = the `select` that returns the rows. On 2026-07-03 "committed by autosave" was asserted for 5 files without proof, and a Notion append falsely read "not found" (unpaginated). Run the proof; paste nothing you didn't verify live.

This is a procedural gate (no hook enforces it) — treat it with the same non-negotiability as the retro convergence loop.

### Step 6 — Notion task (MANDATORY when work was done — hook-enforced)

> **HOOK-ENFORCED (`close-track-gate.py`, Stop):** if this session made **>=1 commit** and no Notion task was touched, turn-end is BLOCKED. "No task in session context" is a **TRIGGER to search + find-or-create**, NEVER a reason to skip (2026-07-02 miss: a full HeyReach campaign, 1 commit, logged nothing — the >=2-commit asset-audit gate didn't catch it). Prior gates missed this because Step 6 was gated on "If found."

**6.0 — Find-or-create (run FIRST, unconditionally, if the session did real work):**
1. Is a task already linked in session context / STATE.md / checkpoint? → use it.
2. If NOT: **search the Tasks DB before concluding none exists** — `notion-che api -X POST /v1/search -d '{"query":"<keywords>"}'`, or query the my-agency Tasks DB (`YOUR-NOTION-DB-ID`). 3. Log this session's work to the matched task: append a dated **toggle** ("YYYY-MM-DD · what — state") with bullet children (funnel/IDs/next-action/files), full structured body per C4. Fetch-back verify (`GET /v1/blocks/{id}/children`).
4. If genuinely no matching task, **create** one (sub-task under the right parent) with the full body — do not defer.
5. **Pending human step (e.g. "Anton must launch") = Doing / To Do, NEVER Done.**
6. **After logging/creating, write the gate marker:** `touch /tmp/notion-task-linked-{session_id}` (this satisfies `close-track-gate.py`). If the work was genuinely trivial with no deliverable, acknowledge instead: `echo trivial > /tmp/notion-task-linked-{session_id}` — a logged decision, not a silent skip.

Then, if a task is now linked:

**5a. Agent task check** — Fetch the task and check `🤖 Agent` checkbox. If true:
- Verify `Agent Context` property is populated (rich_text, not empty). If empty: "⚠️ Agent task missing Agent Context — add one-liner before closing?"
- Verify task body has the structured Agent Task Body format (Objective, Instructions, Output, Verification sections). If missing: "⚠️ Agent task body has no structured prompt — Rebel/poller can't execute. Add it now?"
- When marking Done on an agent task: set `Agent Status = Review` (not Approved), set `Reviewed = false`. Human reviews later.
- When leaving Doing on an agent task: set `Agent Status = Executing` if this session was actively working on it.

**5b. Status choice** — Ask:

```
Active Notion task: [Title] {🤖 if agent task}
  (a) mark Done — full deliverable section {+ Agent Status → Review if agent}
  (b) leave Doing — will resume {+ Agent Status → Executing if agent}
  (c) leave as-is
Choice:
```

Default to (b) if unclear. If (a), invoke `/track done`.

### Step 7 — GSD pause-work (conditional)

Check if current cwd is a GSD project (`.planning/PROJECT.md` exists). If YES:

- Invoke `/gsd:pause-work` skill to create `.planning/phases/XX/.continue-here.md`
- This captures: current state, completed work, remaining work, decisions, blockers, next action
- Next session can use `/gsd:resume-work` to pick up with full context

After `/gsd:pause-work` completes, **append a toggle block to the active Notion task** (if linked). Header: `CW{week} {YYYYMMDD}` in bold. Body: Next action, decisions, `claude --resume` deep link, local context path:

```python
import re, subprocess, datetime, json

# Read STATE.md ## Tracking for Notion URL
state_path = ".planning/STATE.md"
notion_url = None
try:
    with open(state_path) as f:
        content = f.read()
    m = re.search(r"active_notion_task_url: (https://[^\n]+)", content)
    if m and "none" not in m.group(1).lower():
        notion_url = m.group(1).strip()
except FileNotFoundError:
    pass

if notion_url:
    # Extract page ID from URL (last path segment, strip hyphens)
    page_id = notion_url.rstrip("/").split("/")[-1].split("?")[0]
    # Remove slug prefix (last 32 chars are the UUID)
    if len(page_id) > 32:
        page_id = page_id[-32:]
    # Format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    page_id = f"{page_id[0:8]}-{page_id[8:12]}-{page_id[12:16]}-{page_id[16:20]}-{page_id[20:32]}"

    # Read .continue-here.md for next_action and decisions
    continue_path = None  # GSD pause-work creates this — find most recently modified
    import glob, os
    files = glob.glob(".planning/phases/**/.continue-here.md", recursive=True)
    if files:
        continue_path = max(files, key=os.path.getmtime)

    next_action = "see .continue-here.md"
    decisions_snippet = ""
    if continue_path:
        with open(continue_path) as f:
            ch = f.read()
        m = re.search(r"<next_action>\n(.*?)\n</next_action>", ch, re.DOTALL)
        if m:
            next_action = m.group(1).strip()[:200]
        m = re.search(r"<decisions_made>(.*?)</decisions_made>", ch, re.DOTALL)
        if m:
            lines = [l.strip() for l in m.group(1).strip().splitlines() if l.strip().startswith("-")]
            decisions_snippet = " | ".join(lines[:3])  # max 3 decisions

    # Get session_id for resume link
    import glob as g
    session_markers = g.glob("/tmp/claude-sessions/session-*.json")
    resume_session_id = ""
    if session_markers:
        latest_marker = max(session_markers, key=os.path.getmtime)
        try:
            with open(latest_marker) as mf:
                marker_data = json.load(mf)
            if marker_data.get("cwd") == os.getcwd():
                resume_session_id = marker_data.get("session_id", "")
        except Exception:
            pass

    detail_text = f"Next: {next_action}"
    if decisions_snippet:
        detail_text += f"\nDecisions: {decisions_snippet}"
    if resume_session_id:
        detail_text += f"\nSession: claude --resume {resume_session_id}"
    detail_text += f"\nLocal context: {continue_path or '.planning/'}"

    # Build toggle header with calendar week and date
    today = datetime.date.today()
    cw = f"CW{today.isocalendar()[1]:02d}"
    datestamp = today.strftime("%Y%m%d")

    # Append to Notion page
    NOTION_KEY = subprocess.check_output(
        ["doppler", "secrets", "get", "NOTION__CLAUDE_CODE_CLI", "--config", "dev", "--project", "che-all", "--plain"],
        text=True
    ).strip()

    import json, urllib.request
    payload = {
        "children": [
            {
                "type": "toggle",
                "toggle": {
                    "rich_text": [
                        {"type": "text", "text": {"content": f"{cw} {datestamp}"}, "annotations": {"bold": True}}
                    ],
                    "color": "default",
                    "children": [
                        {
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [
                                    {"type": "text", "text": {"content": detail_text}}
                                ]
                            }
                        }
                    ]
                }
            }
        ]
    }
    req = urllib.request.Request(
        f"https://api.notion.com/v1/blocks/{page_id}/children",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {NOTION_KEY}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"},
        method="PATCH"
    )
    try:
        urllib.request.urlopen(req)
        print(f"  ↳ Notion paused log appended: {notion_url}")
        # Write dedup marker so brain-capture.sh SessionEnd hook skips its own append
        session_id = os.environ.get("CLAUDE_SESSION_ID", "")
        if not session_id:
            import glob as g
            markers = g.glob("/tmp/claude-sessions/session-*.json")
            if markers:
                latest = max(markers, key=os.path.getmtime)
                session_id = os.path.basename(latest).replace("session-", "").replace(".json", "")
        if session_id:
            with open(f"/tmp/brain-notion-appended-{session_id}", "w") as mf:
                mf.write(datetime.datetime.utcnow().isoformat())
    except Exception as e:
        print(f"  ↳ Notion append failed (non-blocking): {e}")
```

If NOT a GSD project → skip entirely.

### Step 8 — Git commit (if pending from step 1)

Now execute the commit proposed in step 1. Commit message format follows project convention (check recent `git log --oneline -5` if unsure).

### Step 9 — Release task locks

Release task locks claimed by THIS session only. Releasing must be scoped by `session_id`, NOT by `cwd` — multiple parallel sessions often share a cwd (same repo), and a cwd-only release sweeps OTHER sessions' active locks, freeing their tasks for a third session to grab. (Incident 2026-06-01: a close-session over-released `transcribe-local-diarization`, a parallel HeavyPope lock.) This signals to parallel sessions that only the tasks WE owned are free. Idempotent.

```bash
# Implementation — scoped to THIS session_id (falls back to cwd ONLY if our id is unknowable)
python3 <<PYEOF
import json, os, glob
locks_dir = os.path.expanduser("~/.claude/task-locks")
cwd = os.getcwd()

# Determine THIS session's id (env first, then the most-recent session marker matching cwd)
my_sid = os.environ.get("CLAUDE_SESSION_ID", "")
if not my_sid:
    markers = glob.glob("/tmp/claude-sessions/session-*.json")
    markers = sorted(markers, key=os.path.getmtime, reverse=True)
    for m in markers:
        try:
            md = json.load(open(m))
            if md.get("cwd") == cwd:
                my_sid = md.get("session_id", ""); break
        except Exception:
            pass

released, skipped_other = [], []
for lock in glob.glob(os.path.join(locks_dir, "*.lock")):
    try:
        with open(lock) as f:
            d = json.load(f)
        if d.get("cwd") != cwd:
            continue
        lock_sid = d.get("session_id", "")
        # Release only if this lock is OURS by session_id.
        # If we couldn't determine our own id, fall back to cwd-match (legacy) but
        # NEVER remove a lock whose session_id differs from a known other-session id.
        if my_sid and lock_sid == my_sid:
            os.remove(lock); released.append(d.get("slug", os.path.basename(lock)))
        elif not my_sid:
            os.remove(lock); released.append(d.get("slug", os.path.basename(lock)))  # legacy fallback
        else:
            skipped_other.append(d.get("slug", os.path.basename(lock)))
    except Exception:
        pass

for slug in released:
    print(f"🔓 Released: {slug}")
for slug in skipped_other:
    print(f"⏭️  Left alone (another session's lock): {slug}")
if not released:
    print("(no task locks owned by this session to release)")
PYEOF
```

**If no locks were released AND significant work was done this session** (commits made, files edited, tools called >3 times): offer to create a retroactive entry:

> "No task lock was claimed this session (common in context-resumption). Create a retroactive entry for audit trail? Suggest slug: `{project}-{short-description}`"
>
> If yes: `/claim "{slug}"` then immediately `/release "{slug}"` — this writes a timestamped record to `~/.claude/task-locks/` history without blocking anything.

This ensures every session with real work has a traceable record, even when `/claim` was missed at the start.

Report released slugs (or retroactive entry) in the final summary.

### Step 10 — Final summary

**Gate cleanup FIRST** — remove the close-pending marker so `close-retro-stop-gate.py` releases this session (the convergence marker has been written by `/session-retro` by now). Leaving it would block this turn from ending:
```bash
SESSION_ID=$(python3 -c "
import json, glob, os
markers = glob.glob('/tmp/claude-sessions/session-*.json')
if markers:
    latest = max(markers, key=os.path.getmtime)
    d = json.load(open(latest))
    if d.get('cwd') == os.getcwd():
        print(d.get('session_id', ''))
" 2>/dev/null)
if [ -n "$SESSION_ID" ]; then
    rm -f "$HOME/.claude/close-pending-$SESSION_ID"
fi
```
(Do NOT remove it before the retro converged — that would defeat the gate. Only here, at true completion.)

Then print a single block:

```
✓ Session closed — {timestamp}

Captured:
  - che-brain: [N knowledge items + status summary]
  - {/session-retro outcome: N learnings encoded into M files | no retro needed}

Activity:
  - Observations: {N} actions | Experience: {type}
  - Files: {list of files touched}
  - Commands: {notable commands}

Notion:
  - Task: [title] → [Done | still Doing | left as-is]

Git:
  - Committed {N files}: {hash} — {message first line}
  - OR: no uncommitted changes

Task locks:
  - Released: {list of slugs} — parallel sessions can now claim these
  - OR: none active

GSD:
  - Phase: [XX-name]
  - Handoff: .planning/phases/XX/.continue-here.md
  - Resume next session: /gsd:resume-work

Safe to /clear or end session.
```

Then capture the closing summary to che-brain via `mcp__che-brain__capture_thought`:
- `source`: `"session_close"`
- `project`: mapped project from cwd
- `content`: the same block printed above (verbatim), prefixed with `## Session Closed — {timestamp}`

Non-blocking: if the capture fails, note it and continue.

## Rules

- **NEVER skip step 1 (git check)** — uncommitted work is the biggest loss risk. If the user says "just close it, skip git", push back: "Uncommitted changes will be lost on /clear. Confirm you want to discard them."
- **Single approval gate** — after step 1 confirmation, run steps 2-7 without further prompts unless an error occurs.
- **If any step fails**, stop and report — don't silently continue. User should know exactly which ritual step failed.
- **Report, don't assume** — the final summary MUST reflect actual outcomes, not expected outcomes. If `/session-retro` was skipped, say "skipped — no retro-worthy events", not "completed".
- **Parallel-session aware** — this skill runs per-session. If multiple Claude sessions are open, each one should close itself. Global state (Notion, git) is shared; session-specific state (context monitor, che-brain capture) is per-session.

## Multi-session awareness

Anton often runs 10-20 parallel Claude Code sessions across projects. Each session must close itself without stepping on others. Key rules:

**Shared state (coordinate):**
- Git repo — explicit file lists only, never `git add .`
- Notion tasks — use `/track` skill's state machine (Doing/Done), don't force-update tasks another session owns
- Che-brain — every session can append, no conflicts

**Session-specific state (isolated):**
- Context monitor (per session_id via `/tmp/claude-ctx-{session_id}.json`)
- Che-brain capture (append-only, no conflict)
- Session-start marker (`/tmp/claude-sessions/session-{session_id}.json` — written by `session-start-marker.sh` SessionStart hook)

**When two sessions truly conflict** (same branch, overlapping files):
- Use `/using-git-worktrees` to create isolated worktrees PER session
- Each worktree is an independent checkout — zero shared state
- Only merge when both sessions close cleanly
- This is the nuclear option — only needed when editing the same files

**Detection order for "is this MINE or EXTERNAL":**
1. Read session-start marker (`/tmp/claude-sessions/session-{session_id}.json`) → get `head_sha`
2. `git diff --name-only <head_sha> HEAD` → files changed during my lifetime
3. Intersect with `git status --short` → precise "MINE" set
4. If no marker exists, fall back to tool-call history (harder — ask user if unclear)

**What to do with EXTERNAL files at close time:**
- NEVER stage them
- Report them in the final summary: "External modifications present but not included: {list}"
- Let the session that owns them commit them
- If they've been sitting uncommitted for a while and no session owns them, note it and optionally flag for next session

## Anti-patterns

- ❌ Running steps in parallel — ordering matters (capture BEFORE work-style signal BEFORE retro so progress is locked even if retro is interrupted)
- ❌ Using `git add .` — always explicit file list
- ❌ Silently skipping steps without reporting
- ❌ Asking multiple questions — one approval gate only
- ❌ Auto-committing without user confirmation in step 1

## Integration with existing hooks

Current hook setup (as of 2026-04-08):
- `gsd-context-monitor.js` fires WARNING at 35% remaining, CRITICAL at 25% remaining
- `brain-capture.sh` runs on SessionEnd + PreCompact (known unreliable)

**Proposed wiring:**
- Extend `gsd-context-monitor.js` to auto-invoke `/close-session` at CRITICAL threshold (25% remaining)
- Keep `/capture-progress` auto-run at WARNING threshold (35% remaining) — lightweight, already in CLAUDE.md line 101
- Add 50% remaining as SOFT NUDGE in statusline (no auto-action, just a visible reminder)

Hook wiring is a follow-up task — ship the manual skill first, automate after validation.

## Example invocation

```
User: /close-session
Claude: [runs step 1]
  Uncommitted tracked changes:
    M workflows/03-discovery-call-pipeline.json
    M scripts/test-pipeline.py

  Propose commit: "feat(03): add test webhook + automation script"
  Proceed? (yes/no)

User: yes
Claude: [runs steps 2-9, no further prompts]

  ✓ Session closed — 2026-04-08 20:42 UTC

  Captured:
    - che-brain: 5 knowledge items + status summary
    - /session-retro: 4 learnings encoded into 2 files

  Notion:
    - Task: "Sales coach in Pipedrive" → Done

  Git:
    - Committed 2 files: cb288dd — feat(03): add test webhook + automation script

  GSD:
    - Phase: 01-minimal-discovery-pipeline
    - Handoff: .planning/phases/01-minimal-discovery-pipeline/.continue-here.md
    - Resume next session: /gsd:resume-work

  Safe to /clear or end session.
```

## Client artifact extraction (migrated from ~/.claude/CLAUDE.md, 2026-05-30)

- **Client session artifact extraction is AGGRESSIVE, not conservative** (UP incident 2026-05-21). After ANY GoToMoney client session, extract reusable artifacts BEFORE closing — "wait for recurrence" is WRONG for first-client work; the first client IS the template. The skill-forge step must NOT use "not recurring yet" as a reason to skip.
  - Checklist: (1) Scripts → Lego Registry as processing block, (2) Infrastructure setup → SOP playbook, (3) Tool configs → setup playbook, (4) Research → tag domain-general portions for reuse, (5) Notion patterns → document tracking structure, (6) Decision frameworks → capture selection criteria.
  - Every extracted artifact hits 3 surfaces: local file (`GTM/_playbooks/`), Lego Registry (Notion), Playbooks Registry (Notion DB `YOUR-NOTION-DB-ID`).
