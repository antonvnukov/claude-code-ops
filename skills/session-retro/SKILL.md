---
name: session-retro
description: "Extract PROCESS learnings from the current session — friction, strategic discoveries, methodological patterns, and trajectory insights. Compounds the system: each session makes the next one better. Different from /capture-progress (which captures decisions and progress) — this captures HOW we worked and WHAT patterns emerged."
uses: []
requires: []
bets:     []
maturity: proven
chain:
  produces: "encoded rules in CLAUDE.md, memory files, skill updates, trajectory checkpoints, recurring pattern alerts"
  consumes: "session context with friction/corrections/discoveries"
  chains: ["close-session", "weekly-ops"]
  position: 4
  feeds: ["weekly-system-improvement"]
---

# Session Retro

Extract reusable **process learnings** from the current Claude Code session and encode them into the right files so the next session is smarter.

This is the meta-skill that compounds the system. Different from `/capture-progress`:

| Skill | Captures | Lives in |
|---|---|---|
| `/capture-progress` | WHAT was done — decisions, problems, status | che-brain |
| `/session-retro` | HOW we worked — friction, missed tools, patterns | global CLAUDE.md, MEMORY.md, project CLAUDE.md, new skills |

Run both at session end. They're complementary, not redundant.

---

## When to Run

Run `/session-retro` at the end of any session that included **at least one** of:

**Layer 1 — Explicit friction (easy to spot):**
- A user correction ("no, do X instead")
- User pointing out a missed tool ("you could have used Y")
- Repeated iterations to get something right (3+ tries)
- User pushback on a suggestion
- A manual workaround for something that should be automated
- A new convention being established (filenames, formatting, sequencing)
- A new gotcha discovered (API quirk, tool limitation, edge case)

**Layer 2 — Strategic reframes (harder to spot, often MORE valuable):**
- User reframed your output at a higher level ("this isn't X, it's Y") — e.g., "content gaps" reframed as "product expansion opportunities"
- User connected your finding to a business outcome you didn't see — e.g., linking audit data to upsell funnel
- User pointed you to existing context you should have read first — e.g., engagement model, Observations Doc, prior session artifacts
- User asked "is that all?" or "go deeper" — signals you stopped at the surface
- User provided business intel (call notes, voice memos, screenshots) that changed the interpretation of data you already had

**Layer 3 — Trajectory / arc patterns (client work OR any multi-step/multi-session build — NOT client-only):**
- A reusable multi-step process was executed (applies to future clients OR future infra/migrations/builds — infra counts)
- A client engagement OR build pattern crystallized (e.g. data→findings→framing→hook; or migrate→cutover→self-heal→document)
- A tool/skill/component combination proved effective and should be templated as a PROCESS, not just captured as parts

If none of these happened across all three layers — skip it. A clean session has nothing to retro.

---

## Instructions

### Step 0: Context load (MANDATORY — before writing ANY retro items)

The shallow retro failure mode (7+ occurrences, 2026-05-22 through 2026-05-27) happens because retro is written from session memory alone. Layers 2-3 require external context to surface strategic connections and trajectory patterns. Load this context BEFORE scanning:

1. **Read MEMORY.md project section** — scan active trajectories, skill backlog, recent session learnings. Ask: "does this session advance any of these?"
2. **Read project CLAUDE.md pillars/positioning** — scan content pillars, service tracks, engagement model. Ask: "does this session's output connect to a pillar or service I didn't explicitly think about?"
3. **`ls GTM/_playbooks/`** (or equivalent project playbooks dir) — scan existing SOPs. Ask: "did I execute a multi-step process that should update or create an SOP?"
4. **Self-application check** — Ask: "does this session's output apply to MY OWN properties (gotomoney.io, LinkedIn, my-startup) and not just the immediate task?"

Spend 30 seconds per item (2 minutes total). This is NOT optional overhead — it's the forcing function that prevents the "Layer 1 only" shallow retro. The items you discover here become Layer 2/3 candidates.

**Output of Step 0:** A scratchpad list of potential connections found. These feed directly into the Layer 2 and Layer 3 scans below. If Step 0 finds zero connections, that's fine — proceed with the scan. But the scan must still check all layers.

### Convergence Loop Protocol

**Problem:** First-pass retro consistently finds 40-50% of actual items (9 sessions, 2026-05-22 to 2026-05-28). Self-check checklists don't work. Quantitative gates don't work. The only fix is multiple passes until convergence.

**Mechanism:** Run the three-layer scan (Step 1) as Pass 1, then automatically run additional passes focusing on categories that Pass 1 consistently misses. Stop when `delta < 3` new items per pass OR `pass >= 5`. Minimum 2 passes always.

**Pass focus:**

| Pass | Focus | What to scan |
|---|---|---|
| 1 | Standard 3-layer scan | Step 1 below - friction, strategic insights, trajectory |
| 2 | Missed categories | SOPs (>5-step processes), skill candidates, automation candidates, work-style signals |
| 3 | Strategic depth | Cross-project reuse, existing material gaps, architectural decisions |
| 4 | Sweep | "Scan the full session one more time. What patterns did I miss?" |
| 5 | Safety cap | Same as 4. Stop regardless. |

**Execution rules:**
- **ALWAYS run at least 2 passes.** Pass 2 is unconditional. The `delta < 3` exit only applies from Pass 2 onward.
- Each pass explicitly excludes items already found (no double-counting).
- Present ALL passes merged as one retro. Never present Pass 1 alone.
- Track items per pass for the convergence marker.

**TRAJECTORY GATE (mandatory — mechanical, not a checklist).** Convergence CANNOT complete until this is resolved. Count the session's reusable artifacts (Lego blocks, scripts, che-brain captures, deployed components) and distinct build phases. **If >=3 artifacts OR >=3 phases OR the work spanned multiple sessions → you MUST do ONE of:**
  (a) extract the connecting **PROCESS** as a trajectory/SOP (the ordered sequence of steps that produced those artifacts — capture to che-brain `source=session_retro_trajectory` + MEMORY pointer), OR
  (b) write one explicit line stating why the sequence is NOT reusable.
This fires REGARDLESS of client-vs-infra — a multi-day/multi-step build always has a process worth extracting; Layer 3 is NOT client-only. **The 2026-06-02 miss:** captured 5+ components (Lego + che-brain + runbook) but never the migration PROCESS, because the session was mis-framed as "infra, no trajectory." The user's "is that all?" caught it. This gate makes the artifact count — not the framing — force the trajectory extraction.

**HOOK-ENFORCED (not just instruction):** `close-retro-stop-gate.py` reads `/tmp/retro-items-{session_id}.jsonl`, counts items whose `category` ∈ {lego, sop, script, component, automation, stack, workflow, skill, playbook}, and BLOCKS turn-end if that count >=3 AND no item has `"layer":"L3"` or `"category":"trajectory"`. To satisfy it: log artifacts with their real category, AND when the count hits 3+, append EITHER a real trajectory item (`{"layer":"L3","category":"trajectory","item":"<the process>"}`) OR an explicit `{"category":"trajectory","item":"not reusable: <why>"}`. The hook keys off the logged items, so honest logging is the only way through — you can't suppress it by mis-framing.
- Each item gets appended to `/tmp/retro-items-{session_id}.jsonl`:
  ```json
  {"pass": 2, "layer": "L2", "category": "sop", "item": "Clay enrichment workflow is a 7-step SOP", "destination": "MEMORY.md"}
  ```

**After convergence, write the marker** `/tmp/retro-converged-{session_id}.json`:

```bash
SESSION_ID=$(python3 -c "
import json, glob, os
markers = glob.glob('/tmp/claude-sessions/session-*.json')
if markers:
    latest = max(markers, key=os.path.getmtime)
    print(json.load(open(latest)).get('session_id', ''))
" 2>/dev/null)

if [ -n "$SESSION_ID" ]; then
python3 << 'PYEOF'
import json, datetime
marker = {
    "session_id": "FILL_SESSION_ID",
    "passes": 0,           # FILL: actual pass count
    "items_per_pass": [],   # FILL: [count_pass1, count_pass2, ...]
    "total_items": 0,       # FILL: sum of all items
    "final_delta": 0,       # FILL: items found in last pass
    "categories_covered": [],  # FILL: list of category strings scanned
    "converged_at": datetime.datetime.utcnow().isoformat() + "Z"
}
with open(f"/tmp/retro-converged-FILL_SESSION_ID.json", "w") as f:
    json.dump(marker, f, indent=2)
print(f"Convergence marker written: /tmp/retro-converged-FILL_SESSION_ID.json")
PYEOF
fi
```

Replace all `FILL_*` with actual values from the loop. The `retro-gate.py` hook blocks checkpoint.md if this marker is missing or shows `passes < 2`.

### Step 1: Three-layer scan (Pass 1)

Scan the full session (including pre-compaction summary if context was compressed) across ALL three layers. Do not stop after Layer 1. **Use the Step 0 scratchpad to seed Layer 2 and Layer 3 — don't scan those layers cold.**

> **COMPACTION-SCOPE RULE (2026-06-05, root cause of the 9th shallow-retro):** When the session was compacted, the compaction **summary is the PRIMARY scan input** — ~90% of the session's work lives there, not in the live post-compaction slice. Retro'ing only the last N turns produces a loop that *converges* (passes the gate) yet is shallow, because it converged on a narrow input. Re-read the entire compaction summary's "All user messages" + "Files/Errors/Problem Solving" sections and log an artifact/trajectory item for EACH distinct build phase before checking convergence. This also closes a hole in `close-retro-stop-gate.py`: that gate counts artifacts logged to the jsonl, so an under-scoped retro that logs few artifacts silently defeats it — scanning the full (pre-compaction) session is what makes the artifact-count gate work. Trigger to re-scan: user asks "is that all?" after a compacted session = you scoped too narrowly, go back to the summary.

**Layer 1 — Friction scan (corrections, retries, missed tools):**

For each friction event, note:
- **What happened** — the actual exchange
- **Wrong assumption** — what did Claude assume incorrectly?
- **Prevention rule** — a concrete rule that prevents recurrence

**Layer 2 — Strategic & methodological discovery scan:**

Ask these questions about the session:
- Did I use a **technique** that worked well and would apply to other projects? (e.g., Brand Analytics price column comparison, DFS + Seller Central cross-reference)
- Did I discover a **data insight** that maps to the client's engagement model or sales motion? (e.g., door hinges as gateway product, PPC waste as kickoff talking point)
- Did the user reframe my output at a higher level? ("this isn't an SEO finding, it's a revenue opportunity")
- Did I skip a step in the plan, and the user caught it? (plan→execution discipline)
- Did I present something as "done" that wasn't deep enough? ("is that all?" / "go deeper")
- Was there a **reusable tool/API** used for the first time that should be registered as a Lego block?

**Severity filter:** Only produce output for a question if the answer is "yes AND this would change what I do next time." The questions are prompts to CHECK, not prompts to WRITE. Using pandas to read a CSV is not a "reusable technique." Discovering that Brand Analytics has price columns that diagnose positioning problems IS one — because next time you'd use it proactively instead of stumbling on it.

For each discovery that passes the filter, note:
- **What was discovered** — the technique, insight, or tool
- **Why it's reusable** — what future scenario would benefit from this
- **Where to encode** — MEMORY.md (project), CLAUDE.md (global), che-brain (cross-project), or Lego Registry (reusable block)
- **MEMORY.md writes are INDEX writes:** ONE line ≤~200 chars per entry (`- [Title](topic_file.md) — hook`); body/detail goes in the topic file, never inline. The index hard-truncates at ~24.4k — multi-line entries push the tail off the cliff (see `/che-context-optimize`).

**Layer 3 — Trajectory scan (client/project arc):**

If this session involved client work or a multi-session project:
- What **phase** of the engagement did this session advance? (setup → analysis → synthesis → delivery)
- Did a **reusable process** crystallize that applies to future clients? (e.g., "Amazon marketplace audit = DFS competitive landscape + Seller Central operational data")
- Should this be captured as a **trajectory checkpoint** in che-brain? (multi-session story arc)
- Do the findings **map to the engagement model**? (observations doc, proof-of-work, kickoff hooks)

**Severity filter:** Same as Layer 2 — only capture if the pattern would change how you approach the NEXT client engagement. "We advanced from setup to analysis" is a status update (belongs in /capture-progress). "Marketplace audits need both API competitive data AND seller's own operational data — neither alone tells the story" is a reusable pattern.

For each trajectory pattern that passes the filter, note:
- **Pattern name** — one phrase (e.g., "marketplace audit dual-source pattern")
- **Steps** — the sequence that worked
- **Reuse scope** — this client only, all e-commerce clients, or universal

**Note:** Step 1 is Pass 1 of the convergence loop. After completing this scan, proceed to Pass 2+ per the Convergence Loop Protocol above. Do NOT present results until all passes complete and converge (delta < 3 or pass >= 5, minimum 2 passes).

**CONFIDENCE TAGGING (prevents overcapture):**

Layer 1 items are always **verified** — the friction happened, the fix is concrete and testable.

Layer 2 and Layer 3 items from a single session are **hypothesis** until confirmed across 2+ sessions. When encoding:
- Tag in MEMORY.md: prefix with `[hypothesis]` — e.g., `[hypothesis] Brand Analytics price columns = price positioning diagnosis tool`
- Tag in che-brain: include `confidence: hypothesis` in the capture content

**Hypothesis lifecycle:**
- During `/weekly-ops` retro rollup: scan MEMORY.md for `[hypothesis]` items. If the pattern recurred in another session that week → promote to verified (remove tag). If 3+ weeks old with no recurrence → delete.
- Exception: items from first-client work (GoToMoney Track 2) get 6 weeks instead of 3, because the second client may not appear for a while.
- Layer 1 items NEVER get hypothesis tags — friction is verified by definition.

### Step 2: Classify each learning

For each ripe learning, place it in one of these buckets:

| Type | Where it belongs | Example |
|---|---|---|
| **Universal process default** | `~/.claude/CLAUDE.md` → Verify before acting | "ls inputs/ before writing any analysis report" |
| **Universal don't-do rule** | `~/.claude/CLAUDE.md` → Never Do | "Never claim Notion update is done without re-fetching" |
| **Technical gotcha** | `MEMORY.md` → relevant section | "Notion replace_all_matches is case-sensitive" |
| **Project-specific convention** | `{project}/CLAUDE.md` | "Client A deliverables use {Client}-{Type}-{YYYY-MM}.pdf" |
| **Reusable technique** | `MEMORY.md` + che-brain | "Brand Analytics price column comparison for price gap diagnosis" |
| **Reusable tool/API** | che-brain + Lego Registry | "DataForSEO Amazon Merchant API = $0.04 marketplace audit" |
| **Strategic insight** | che-brain (engagement model tag) | "Door hinges as gateway product for retargeting" |
| **Trajectory pattern** | che-brain (trajectory checkpoint) | "Amazon marketplace audit = DFS competitive + Seller Central operational" |
| **Reusable workflow** | New or extended skill | Client email patterns, proposal sequencing |
| **Automation candidate** | Tag in brain capture (see Step 5) | Manual steps done 3+ times, data entry that could be API-driven |
| **Audit SOP gap** | `GTM/_playbooks/sop-*.md` | "Add Amazon data sources to onboarding form" |
| **One-off, not recurring** | Don't encode — skip it | Anything that won't apply to a future session |

**Quality bar:** A learning that won't apply to a future session is not a learning. It's a fact about today. Skip it.

**qmd routing (per-project recall — the analogue of che-brain, but file-based).** che-brain has a push API so any learning reaches it directly. qmd does NOT — it only **indexes local `.md` files inside a collection's path**. So a **project-scoped** learning (a client/project gotcha, decision, SOP, shipped-state) only reaches qmd if you ALSO write it as a `.md` under that project's qmd-collection path (e.g. `~/projects/<proj>/...`), not only into `~/.claude/.../memory/` (which qmd does NOT index). Rule: when a learning's destination is **project-specific**, write/append it to the project's qmd-indexed path too; **global/cross-project** learnings stay in che-brain + `~/.claude` memory. Check the project has a collection: `qmd collection list` (path via `qmd collection show <name>`). If you're in a conductor worktree, the collection indexes the MAIN project (`~/projects/<proj>`), so write there, not the worktree. (Incident 2026-06-29: a session's project learnings landed only in `~/.claude` memory + che-brain and never reached qmd — the user reads qmd, so it was effectively invisible there.)

### Step 3: Propose the encoding plan

Before making any edits, present the plan to the user as a numbered list:

```
## Session Retro — N learnings to encode

1. [Learning] → [destination file] — [one-sentence rule to add]
2. [Learning] → [destination file] — [one-sentence rule to add]
...

Apply all? Or pick: (a)ll / (s)ome / (n)one
```

Wait for confirmation. If the user picks "some", ask which numbers.

### Step 4: Apply the encoding

For each approved learning:

1. **Read the destination file** (Edit tool requires Read first)
2. **Find the right insertion point** — match existing structure, don't dump at the bottom
3. **Write a concrete, actionable rule** — not a description of what happened. The rule should be something Claude can act on without re-reading the original session.
4. **Verify the edit landed** by re-reading the changed section

For new skills:
1. Create `~/.claude/skills/{skill-name}/SKILL.md`
2. Use YAML frontmatter: `name`, `description` (description should be specific enough for auto-discovery)
3. Mirror the structure of an existing simple skill like `capture-progress`

### Step 5: Capture meta-learning to che-brain

After file edits, capture ONE summary entry to che-brain via `mcp__che-brain__capture_thought`:

- `source`: `"session_retro"`
- `project`: mapped project (or omit for cross-project)
- `content`: formatted as:

```
## Session Retro — {YYYY-MM-DD HH:MM}

### Layer 1 — Friction
- (corrections, retries, missed tools — what went wrong and the prevention rule)

### Layer 2 — Strategic & Methodological Discoveries
- (reusable techniques, data insights mapping to engagement model, tools to register as Lego blocks)

### Layer 3 — Trajectory
- (client arc progress, reusable process patterns, engagement model hooks)

### Encoded into
- (file paths that were updated, one per line — MEMORY.md, CLAUDE.md, project CLAUDE.md, che-brain)

### New skills created
- (skill name + path, if any)

### Automation candidates
- (list any manual patterns that should become automated — tag each with type)
- Format: `[automation-candidate: skill|n8n|hook|loop|delegate]` — {description of the manual pattern}
- **Route via `~/.claude/AUTOMATION-CANDIDATE-ROUTING.md`** — pick loop vs launchd vs n8n vs delegate vs skill by the 6-part loop-anatomy check. `/loop` is IN-SESSION only (dies with the session); scheduled/unattended → launchd. Tag a real loop only if it has a Doer + a SEPARATE Verifier + an explicit stop rule.
- Only include if genuine repetition was observed (3+ times or cross-session pattern)
- Omit this section entirely if no candidates found
```

### Step 5b: Recurring pattern check (self-improving loop hook)

After capturing to che-brain, immediately check if any of this session's friction patterns have appeared before. This closes the self-improving loop in real-time instead of waiting for the weekly cron.

For each Layer 1 friction item captured above:
1. Extract the key phrase (root cause or category — e.g., "Notion polling preflight", "wrong agent routing")
2. Query che-brain: `search_knowledge({ query: "<key phrase>", limit: 10 })` filtered to source `session_retro` or `session_knowledge`
3. Count matches from DIFFERENT sessions (same content from this session doesn't count)

**If 2+ prior matches found for any pattern:**

```
⚠️ Recurring pattern detected: [summary]
  Appeared in [N] prior sessions: [dates]
  Brain item IDs: [id1, id2, ...]
  → Already encoded as rule? [grep target file for key phrase]
  → If NOT encoded: propose CLAUDE.md/MEMORY.md addition NOW (don't wait for weekly cron)
```

Present the proposed rule inline. If user approves, apply it in the same Step 4 batch. If user declines, the weekly `weekly-system-improvement` cron will pick it up on Monday.

**If 0-1 matches:** Skip silently. Single occurrence = not yet a pattern.

This step is lightweight (~3 che-brain queries, <10 seconds). It catches patterns the moment they recur rather than accumulating silently until Monday.

### Scope note

The convergence loop runs mechanically only when invoked via `/close-session` (Step 2). When `/session-retro` is called ad-hoc (user asks "any lessons?"), the loop must still be followed manually - run all passes, write the JSONL + convergence marker. The hook enforcement only gates checkpoint.md writes during close-session, but the multi-pass discipline applies regardless of invocation context.

### Step 5c: qmd sync (per-project recall)

If any **project-scoped** learning was written/appended to a project's qmd-indexed path this retro (per the qmd routing rule in Step 2), re-index it so it's searchable:

```bash
~/.claude/scripts/qmd-sync.sh   # auto-detects the project's collection(s) from cwd; worktree-aware; non-blocking
```

Skip if no project `.md` was touched (purely global/cross-project learnings → che-brain only). If `qmd-sync` reports "no qmd collection matches this project", that's fine — not every project has a qmd collection. Report the synced collection(s) in the confirmation.

### Step 6: Output confirmation

Print a single summary line:
```
Session retro complete: N learnings encoded into M files. Next session starts smarter.
```

If recurring patterns were found in Step 5b, append:
```
Recurring patterns flagged: N (applied: M, deferred to weekly: K)
```

If 0 learnings were ripe, print: `Session retro: nothing new to encode.` and stop.

---

## Rules

- **Process learnings only**, not work logs. Use `/capture-progress` for decisions/status.
- **No duplicates**: before adding a rule, search the destination file for an existing similar one. Extend if present, add new only if genuinely novel.
- **Be specific**: "Use the right tool" is not a rule. "Use gws-gmail-send when user mentions email" is a rule.
- **No questions during execution**: scan, propose, wait for one approval, execute, confirm. One decision point only.
- **Encode now, not 'later'**: if a learning is worth surfacing, it's worth writing the rule in the right place THIS session. "I'll remember it" is the failure mode.
- **Compound, don't bloat**: prefer extending an existing rule over adding a new bullet. Watch CLAUDE.md size — the goal is denser rules, not longer files.

---

## Anti-patterns

- ❌ Capturing what was done in this session (that's `/capture-progress`)
- ❌ Adding a rule that contradicts an existing rule without removing the old one
- ❌ Writing rules in the form "Try to..." or "Consider..." — be imperative
- ❌ Creating a new skill for a one-off pattern. Skills are for recurring workflows, not one-time wins.
- ❌ Appending `## Session Learning (date)` sections to CLAUDE.md. Place each learning in its proper section (Verify before acting, Never Do, Operational defaults, etc.) or in MEMORY.md for project-specific gotchas. Standalone "Session Learning" sections bloat the file without structural integration.
- ❌ Asking the user multiple questions. One approval gate, one execution.
- ❌ Skipping the verification re-read after edits. The cost of a missed edit is a learning that doesn't compound.

---

## Example

**Session friction:** User asked Claude to write an email; Claude wrote text in chat instead of using `gws-gmail-send`. User said "you could have done this yourself with gws".

**Wrong assumption:** Claude assumed "give me an email draft" meant "write text I can copy into Gmail".

**Prevention pattern:** Default to `gws-gmail-send` whenever email work is mentioned.

**Encoding:**
- Destination: `~/.claude/CLAUDE.md` → Default Behaviors
- Rule added: "Email work via gws-gmail-send — when Anton mentions sending an email, asks 'what should I write?', or shows a Gmail draft screenshot, OFFER to draft and send directly via the `gws-gmail-send` skill instead of letting him build the draft manually in the Gmail UI."

**Verification:** Re-read the Default Behaviors section, confirmed the rule appears in the right place, in the right voice, with the same imperative tone as surrounding rules.

**Done.** Next session that mentions email will trigger the rule automatically.
