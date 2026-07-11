---
name: sop-forge
description: "Create gold-standard SOPs, runbooks, and playbooks from session work or on demand. Outputs to Notion Notes DB with full structured body. Use when a repeatable workflow was executed, a process needs documenting, or at session close when a delegatable procedure was established."
uses: []
requires: []
bets:     []
maturity: proven
---

# SOP Forge — Create delegatable SOPs, runbooks, and playbooks

Create end-to-end procedural documentation that any person or AI agent can follow to reproduce a workflow with zero prior context. Outputs directly to the Notion Notes DB as a structured page with all fields populated.

## When to use

**Explicit triggers:**
- User says `/sop-forge`, "document this process", "create an SOP", "make a playbook"
- After completing a multi-step workflow that should be repeatable
- During `/close-session` step 4c when a workflow pattern is detected

**Auto-suggest triggers (during close-session):**
- Session executed >5 sequential tool calls toward one goal
- Infrastructure setup or config change was performed
- Debugging session resolved an issue (→ runbook candidate)
- A process was done that someone else might need to repeat

## Entry points

1. **`/sop-forge`** — interactive: ask what to document, build from conversation
2. **`/sop-forge "<title>"`** — direct: create SOP for named workflow
3. **`/sop-forge --from-session`** — extract from current session's tool calls (most accurate)
4. **`/sop-forge --from-skill <skill-name>`** — convert a Claude skill into human-readable SOP
5. **Auto-prompt at close-session** — offer when workflow pattern detected

## Process

### Step 1 — Classify the document type

Ask (or infer from context):

| Type | When | Signal |
|---|---|---|
| **SOP** | Routine, repeatable, same steps every time | "How to run weekly report", "How to deploy workflow" |
| **Runbook** | Triggered by alert/incident, includes diagnosis | "Hermes not claiming tasks", "VPS disk full" |
| **Playbook** | Strategic, requires judgment, multiple paths | "New competitor response", "Client escalation" |

Default to **SOP** if unclear.

### Step 2 — Gather information

**Mode A: From current session (--from-session, most accurate)**
Scan the current session's tool calls (Edit, Write, Bash, etc.) and reconstruct:
- What was the trigger/goal?
- What commands were run, in what order?
- What files were read/written?
- What decisions were made and why?
- What failed and how was it recovered?
- What was the verification that it worked?

**Mode B: Interactive (default)**
Ask the user ONE compound question:
> "What workflow are we documenting? Give me: (1) what triggers it, (2) who should be able to run it (you, contractor, agent, anyone), (3) roughly what the steps are."

Then fill gaps by reading relevant files, skills, and memory.

**Mode C: From skill (--from-skill)**
Read `~/.claude/skills/<name>/SKILL.md` and translate:
- Skill steps → human-readable procedure steps
- Skill rules → prerequisite checks and edge cases
- Skill verification → runnable verification commands
- Add environment setup that skills assume but humans need

### Step 3 — Draft the SOP

Write the full SOP body following the Gold Standard Template (below). Every section is mandatory — do not skip any.

### Step 4 — Quality gate (pre-flight)

Before publishing, verify ALL of these. Fix any failures inline:

| # | Check | Fail signal | Fix | Severity |
|---|---|---|---|---|
| 1 | **Zero-context test** — could someone with NO prior knowledge follow this? | References internal tools without explaining them ("Run /weekly-report"), "the usual way", "as discussed", "you know where" | Replace skill/tool references with the actual underlying commands, paths, URLs. If a Claude skill is the only way, document: what it is, how to install it, what it does under the hood | BLOCKER |
| 2 | **One action per step** — no compound steps | "Deploy and verify", "Create and configure", "Pull and analyze" | Split into separate steps. Each step = one verb + one object | BLOCKER |
| 3 | **Every decision point has explicit criteria** | "If it looks right", "check the output", "verify correct" | Add measurable conditions: `status_code == 200`, `file_size > 0`, `row_count >= N`, "dashboard shows green status for all items" | BLOCKER |
| 4 | **Commands are executable, not descriptive** | "Run the report tool", "Use the API", "Pull the data". Internal tool/skill names without commands. | Every Command field MUST be one of: (a) shell command copy-pasteable into terminal, (b) full API call with curl/python, (c) UI click-path with exact URLs and button names. Test: could you paste this into a terminal or follow these clicks without guessing? | BLOCKER |
| 5 | **Verification is executable + cross-method** | Descriptive checks: "count reports", "check it matches". Same method as steps. | Each verification MUST be a runnable command (exit 0 = pass) or a URL + specific expected content. At least one check MUST use a different method than the steps (API→UI, CLI→browser, etc.) | BLOCKER |
| 6 | **Prerequisites are checkable** | "Have access to X", "Ensure Y is set up" | Each prerequisite needs: (a) verify command/action, (b) how to obtain if missing. Example: "GSC access — verify: open https://search.google.com/search-console, confirm property {{url}} visible — get access: ask SEO lead to add your Google account" | WARNING |
| 7 | **Failure branches exist** at critical steps | Step has no "If fails:" section, or "If fails: contact support" | Add: (a) diagnosis command to identify root cause, (b) specific recovery steps, (c) escalation path if recovery fails | WARNING |
| 8 | **No [BRACKETS] placeholders** remain in final output | `[YOUR_NAME]`, `[INSERT URL]`, `<placeholder>` | Fill with actual values or mark as `{{parameter}}` with entry in Parameters section | BLOCKER |
| 9 | **Estimated Duration section exists and is realistic** | Missing, or just "varies", or clearly wrong | Add "Estimated Duration" section with time breakdown. Formula: count steps, estimate 2-5 min per simple step, 10-15 min per complex step. Split human vs agent time if Executor=Either | WARNING |
| 10 | **Trigger is unambiguous** | "When needed", "periodically", "regularly" | Specific event with time/condition: "Every Monday at 09:00 Kyiv", "When Notion task status changes to Queued", "When alert fires in #alerts channel" | WARNING |
| 11 | **Tools Required section exists** | Missing, or just tool names without access verification | List every tool/platform/credential. Each with: verify command, how to get access if missing | WARNING |
| 12 | **All {{parameters}} documented** | `{{param}}` used in steps but not in Parameters section | Every `{{variable}}` in the SOP must have an entry in Parameters: description + where to find the value + example | BLOCKER |

**Scoring:** Count BLOCKER fails and WARNING fails separately.
- **0 BLOCKER + 0-2 WARNING = PASS** → publish as Active
- **0 BLOCKER + 3+ WARNING = CONDITIONAL** → publish as Draft, note gaps
- **Any BLOCKER = FAIL** → fix before publishing. Do NOT publish with any BLOCKER.

### Step 5 — Publish to Notion

Create the page in the Notes DB with ALL fields populated. Use the Notion API calls below.

### Step 6 — Confirm to user

```
SOP created:
  Title: {title}
  Type: {SOP|Runbook|Playbook}
  Project: {project name}
  Executor: {Human|Agent|Either}
  SOP Status: Active
  Notion: {url from API response}

  Steps: {N steps}
  Estimated duration: {Xm}

  Review in 90 days (by {date}).
```

---

## Gold Standard Template

This is the exact structure written into the Notion page body. Every heading is a `heading_2` block. Every step is a numbered item with sub-fields. The template produces SOPs that pass the "naive executor test" — a person with zero context can follow it without asking a single question.

### Mandatory sections (skip none)

```
## Purpose
{One sentence: what outcome this produces + why it matters. Not "this documents how to X" but "Ensures X happens consistently, preventing Y."}

## Trigger
{Exact event, schedule, or condition that initiates this procedure.}
{Examples: "Every Monday at 09:00 Kyiv time", "When a new client signs contract in Pipedrive", "When Hermes stops claiming Notion tasks (alert in #alerts)"}

## Estimated Duration
{Time for a competent executor. Split by executor type if relevant.}
{Example: "~45 min total (30 min automated extraction, 15 min manual review). Agent-only steps: ~10 min."}

## Scope
Covers: {what's in scope}
Does NOT cover: {what's explicitly out, with cross-references to other SOPs if they exist}

## Tools Required
{Every tool, platform, and credential the executor needs. For each: what it is, how to verify access, how to get access if missing.}
1. {Tool/platform} — verify: {command or "login at URL, confirm dashboard loads"} — get access: {who to ask or where to sign up}
2. ...

## Prerequisites
Before starting, verify each condition is true. Do NOT proceed if any check fails.
1. {Checkable condition} — verify: {exact command that exits 0 on success, or specific UI check with URL}
2. {Access requirement} — verify: {command or action} — if missing: {how to obtain}
3. {Data/state requirement} — verify: {command or action}

## Steps

### Step 1: {Action verb + object}
Action: {What to do — one action only. No compound steps ("X and Y").}
Input: {What you need — from prior step, environment, or parameter. Be specific: file path, URL, field name.}
Command: {MUST be one of:
  - Exact shell command copy-pasteable into terminal
  - API call with full curl/python syntax
  - UI action with exact click path: "Open {{url}} → Click 'Settings' in left sidebar → Select 'Integrations' → Click 'Add new'"}
Expected: {Observable success state. One of:
  - Command output: "Returns JSON with {\"active\": true}"
  - File state: "File {{path}} exists and contains N lines"
  - UI state: "Green checkmark appears next to workflow name"
  - Measurable: "Response status 200, body contains 'success'"}
If fails: {Specific diagnosis + recovery:
  - "If 401: Token expired. Run: doppler secrets get YOUR_SECRET --plain | wc -c — if 0, re-add key via doppler secrets set"
  - "If file not found: Check path spelling. Run: ls {{parent_dir}} to see available files"
  - "If timeout: Service may be down. Check: systemctl is-active {{service}} — if inactive, run: sudo systemctl start {{service}}"}

### Step 2: {Action verb + object}
Action: ...
Input: ...
Command: ...
Expected: ...
If fails: ...

{Continue for all steps. Each step MUST have all 5 fields (Action, Input, Command, Expected, If fails). The only optional addition is Note: for gotchas or context.}

## Verification
Run EVERY check below after completing all steps. Each check MUST be executable — either a command that exits 0 on success, a URL to open with specific expected content, or a measurable UI state.
1. {What this checks}: {exact command or action} — expected: {specific output or state}
2. {What this checks}: {exact command or action} — expected: {specific output or state}
{Minimum 2 verification checks. At least one MUST be a different method than the steps used (e.g., if steps used API, verify via UI; if steps used UI, verify via API/command).}

## Rollback
{How to undo what this procedure did. MUST include exact commands/steps, not just "undo the changes".}
{If truly not applicable (read-only procedures), state: "Not applicable — this procedure is read-only and produces no side effects." For procedures that create/modify: always provide rollback steps.}

## Edge Cases
{Known situations where the standard steps don't apply. For each:}
{Situation: specific, recognizable condition} → {Exact response: what to do differently, which step to modify or skip}

## Parameters
{Every {{variable}} used in this SOP. For each: description, where to find the actual value, example value.}
{{parameter_name}}: {what it is} — find it: {where/how to look up} — example: {concrete example value}

## Post-Execution Review
After completing this SOP:
- Did all steps match reality? If not, note the discrepancy and update the SOP.
- Update the Review Date in Notion to today.
- If any step was wrong, fix it now — stale SOPs are worse than no SOPs.

## Change Log
v1.0 ({today's date}): Initial creation — {brief context of why this was documented}
```

### Adaptation by type

**For Runbooks**, replace the Steps section header structure with:

```
## Symptoms
{What the alert/error looks like. Exact error messages, log patterns, dashboard indicators.}

## Diagnosis
### Check 1: {What to check}
Command: {diagnostic command}
If normal: {expected output} — skip to Check 2
If abnormal: {what it means} — go to Resolution A

### Check 2: ...

## Resolution A: {Root cause description}
### Step 1: ...

## Resolution B: {Alternative root cause}
### Step 1: ...
```

**For Playbooks**, replace Steps with:

```
## Situation Assessment
{What questions to answer before choosing a path}

## Option A: {Strategy name}
When to use: {conditions}
Steps: {high-level actions}
Expected outcome: {what success looks like}
Risks: {what could go wrong}

## Option B: {Strategy name}
...

## Decision Framework
{How to choose between options — criteria table or decision tree}
```

---

## Notion API — Create SOP Page

### Setup

```bash
NOTION_KEY=$(doppler secrets get YOUR_SECRET --config dev --project che-all --plain 2>/dev/null)
NOTES_DB="YOUR-NOTION-DB-ID"
```

### Pick the right Project ID

Query the Projects DB to find the project ID:

```bash
curl -s -X POST "https://api.notion.com/v1/databases/YOUR-NOTION-DB-ID/query" \
  -H "Authorization: Bearer $NOTION_KEY" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d '{"filter": {"property": "Name", "title": {"equals": "my-agency"}}, "page_size": 1}'
```

Common project IDs (cache these — they don't change):
- Look up once per session, then reuse.

### Create the page with properties

Use `python3` for reliable JSON construction (no shell escaping issues):

```python
import json, urllib.request, datetime

NOTION_KEY = "{{from_doppler}}"
NOTES_DB = "YOUR-NOTION-DB-ID"

# All properties
properties = {
    "Name": {"title": [{"text": {"content": "{{SOP_TITLE}}"}}]},
    "Type": {"select": {"name": "{{SOP|Runbook|Playbook}}"}},
    "Executor": {"select": {"name": "{{Human|Agent|Either}}"}},
    "SOP Status": {"select": {"name": "Active"}},
    "Review Date": {"date": {"start": "{{REVIEW_DATE_90_DAYS_FROM_NOW}}"}},
    "Project": {"relation": [{"id": "{{PROJECT_PAGE_ID}}"}]},
    "URL": {"url": "{{GIT_PATH_OR_EMPTY}}"}
}

# Optional: People relation for Verified By
# "People": {"relation": [{"id": "{{PERSON_ID}}"}]}

# Optional: Tag relation
# "Tag": {"relation": [{"id": "{{TAG_ID}}"}]}

payload = {
    "parent": {"database_id": NOTES_DB},
    "properties": properties
}

req = urllib.request.Request(
    "https://api.notion.com/v1/pages",
    data=json.dumps(payload).encode(),
    headers={
        "Authorization": f"Bearer {NOTION_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    },
    method="POST"
)
result = json.loads(urllib.request.urlopen(req).read())
page_id = result["id"]
page_url = result["url"]
print(f"Created: {page_url}")
```

### Append structured body

Build the body as Notion blocks. Use `heading_2` for sections, `paragraph` for content, `numbered_list_item` for steps and prerequisites, `divider` between major sections.

**CRITICAL:** Notion API limits block text to 2000 characters per rich_text element. For long content, split into multiple paragraph blocks.

```python
# Build children blocks from the Gold Standard Template sections
children = []

def h2(text):
    return {"type": "heading_2", "heading_2": {"rich_text": [{"text": {"content": text}}]}}

def para(text):
    # Split into 2000-char chunks if needed
    blocks = []
    while text:
        chunk = text[:2000]
        text = text[2000:]
        blocks.append({"type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": chunk}}]}})
    return blocks

def numbered(text):
    return {"type": "numbered_list_item", "numbered_list_item": {"rich_text": [{"text": {"content": text[:2000]}}]}}

def divider():
    return {"type": "divider", "divider": {}}

def callout(text, emoji="💡"):
    return {"type": "callout", "callout": {"rich_text": [{"text": {"content": text[:2000]}}], "icon": {"type": "emoji", "emoji": emoji}}}

# === Build the body ===

# Purpose
children.append(h2("Purpose"))
children.extend(para("{{PURPOSE}}"))

# Trigger
children.append(h2("Trigger"))
children.extend(para("{{TRIGGER}}"))

# Estimated Duration
children.append(h2("Estimated Duration"))
children.extend(para("{{ESTIMATED_DURATION}}"))

# Scope
children.append(h2("Scope"))
children.extend(para("Covers: {{IN_SCOPE}}\nDoes NOT cover: {{OUT_OF_SCOPE}}"))

# Tools Required
children.append(h2("Tools Required"))
# For each tool:
children.append(numbered("{{TOOL_1}} — verify: {{VERIFY_ACCESS_1}} — get access: {{HOW_TO_GET_1}}"))
# ... repeat for each tool

# Prerequisites
children.append(h2("Prerequisites"))
children.append(callout("Verify each prerequisite before starting. Do not skip.", "⚠️"))
# For each prerequisite:
children.append(numbered("{{PREREQ_1}} — verify: {{VERIFY_CMD_1}}"))
# ... repeat for each

children.append(divider())

# Steps
children.append(h2("Steps"))
# For each step, create a heading_3 + paragraphs:
# children.append({"type": "heading_3", "heading_3": {"rich_text": [{"text": {"content": "Step 1: {{ACTION}}"}}]}})
# children.extend(para("Action: {{ACTION_DETAIL}}\nInput: {{INPUT}}\nCommand: {{COMMAND}}\nExpected: {{EXPECTED}}\nIf fails: {{FAILURE_BRANCH}}"))

children.append(divider())

# Verification
children.append(h2("Verification"))
children.append(callout("Run ALL checks below. Every check must pass.", "✅"))
children.append(numbered("{{CHECK_1}}: {{COMMAND_1}} — expected: {{OUTPUT_1}}"))
# ... repeat

# Rollback
children.append(h2("Rollback"))
children.extend(para("{{ROLLBACK_OR_NOT_APPLICABLE}}"))

# Edge Cases
children.append(h2("Edge Cases"))
children.extend(para("{{EDGE_CASE_1}} → {{RESPONSE_1}}"))

# Parameters (if any {{params}} exist in the SOP)
children.append(h2("Parameters"))
children.extend(para("{{PARAM_NAME}}: {{DESCRIPTION}}"))

# Post-Execution Review
children.append(h2("Post-Execution Review"))
children.append({"type": "to_do", "to_do": {"rich_text": [{"text": {"content": "All steps matched reality? If not, note discrepancy and update this SOP."}}]}})
children.append({"type": "to_do", "to_do": {"rich_text": [{"text": {"content": "Update Review Date in Notion to today."}}]}})
children.append({"type": "to_do", "to_do": {"rich_text": [{"text": {"content": "If any step was wrong, fix it now."}}]}})

# Change Log
children.append(h2("Change Log"))
children.extend(para(f"v1.0 ({datetime.date.today().isoformat()}): Initial creation — {{CONTEXT}}"))

# === Append to page ===
# Notion API limits to 100 blocks per request. Batch if needed.
batch_size = 100
for i in range(0, len(children), batch_size):
    batch = children[i:i+batch_size]
    req = urllib.request.Request(
        f"https://api.notion.com/v1/blocks/{page_id}/children",
        data=json.dumps({"children": batch}).encode(),
        headers={
            "Authorization": f"Bearer {NOTION_KEY}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        },
        method="PATCH"
    )
    urllib.request.urlopen(req)

print(f"Body appended: {len(children)} blocks")
```

---

## Field mapping reference

| SOP concept | Notion field | Type | How to populate |
|---|---|---|---|
| Title | `Name` | title | Action verb + Object: "Deploy n8n Workflow", "Run Weekly SEO Report" |
| Document type | `Type` | select | `SOP`, `Runbook`, or `Playbook` |
| Who runs it | `Executor` | select | `Human` (only people), `Agent` (only AI), or `Either` (both can run it) |
| Lifecycle | `SOP Status` | select | `Active` (passed quality gate), `Draft` (WIP or has BLOCKER fails), `Deprecated` (superseded) |
| Next review | `Review Date` | date | Today + 90 days (default). Adjust: high-change = 30d, stable = 180d |
| Project | `Project` | relation | Link to Projects DB entry (my-agency, GoToMoney, CheAgents, etc.) |
| Git file | `URL` | url | Optional — link to git-tracked markdown if dual-stored |
| Category tags | `Tag` | relation | Link to Tags DB entries (ops, sales, content, outbound, infra) |
| Verified by | `People` | relation | Link to People DB entry after first successful end-to-end execution |
| Full procedure | Page body | blocks | Gold Standard Template rendered as Notion blocks (14 mandatory sections) |

### Review Date calculation

| Process change velocity | Review cycle | Example |
|---|---|---|
| Weekly changes | 30 days | CI/CD, deployment SOPs |
| Monthly changes | 90 days (default) | Reporting, onboarding |
| Stable process | 180 days | Legal, compliance |

---

## Integration with /close-session (Step 4c)

When invoked from close-session, use `--from-session` mode automatically:

1. Scan session tool calls for multi-step workflow patterns
2. If found: "This session executed a repeatable workflow: '{description}'. Capture as SOP? [Y/N/later]"
   - **Y** → run /sop-forge --from-session with the detected workflow
   - **N** → skip
   - **later** → append workflow title to `~/.claude/sop-backlog.md` for weekly batch
3. Use session context to auto-fill: trigger, steps (from actual commands), verification (from what was checked), project (from cwd)

---

## Rules

- **NEVER publish a Draft to Active without passing the quality gate (Step 4)**
- **NEVER skip the Prerequisites section** — this is where most SOPs fail. "Have access" is not checkable. "Run `doppler secrets get YOUR_SECRET --plain | wc -c` returns >10" is checkable.
- **NEVER use relative paths** — all file paths must be absolute from repo root or system root
- **NEVER reference session context** — "as we discussed" is forbidden. The SOP must stand alone.
- **ALWAYS set Review Date** — 90 days from today by default. An SOP without a review date decays silently.
- **ALWAYS include at least one verification command** — even if it's just `echo "Manual check: verify X in the UI"`
- **ALWAYS use RFC 2119 keywords** for agent-executable SOPs — MUST (mandatory), SHOULD (recommended), MAY (optional)
- **One SOP = one outcome** — not "How to manage Hermes" but "How to deploy a Hermes config change" and "How to add a new Hermes cron job" separately
- **Parameters over hardcoding** — use `{{parameter_name}}` for values that change between executions. Document each parameter in the Parameters section.
- **Write while doing, not from memory** — session-based mode (`--from-session`) produces the most accurate SOPs because it captures real commands, real paths, real outputs. Prefer it over retrospective documentation.

## Examples of good SOP titles

**my-agency:**
- "Generate Weekly SEO Performance Report"
- "Onboard New Client into Pipedrive + HeyReach"
- "Run LinkedIn Outbound Sequence for Event Follow-up"
- "Create Content Brief from Keyword Research"
- "Set Up n8n Workflow with Telegram Alerting"

**GoToMoney:**
- "Publish LinkedIn Post from Draft to Scheduled"
- "Create LinkedIn Carousel from Blog Post"

**CheAgents (infra):**
- "Deploy Hermes Configuration Change to VPS"
- "Add New Cron Job to Hermes"
- "Debug Ekko Task Execution Failure" (runbook)
- "Handle VPS Disk Full Alert" (runbook)

## Anti-patterns

- "How to do SEO" — too broad, not actionable
- "Hermes" — not a procedure, it's a system
- "Fix bugs" — not specific, no repeatable steps
- "Weekly tasks" — a list, not a procedure. Break into individual SOPs.
- Steps without verification — "deploy the config" with no check that it worked
- Prerequisites that say "access to the system" — which system? which credentials? how to verify?
