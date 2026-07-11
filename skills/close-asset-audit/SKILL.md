---
name: close-asset-audit
description: "Close Asset Audit"
uses: []
requires: []
bets:     []
maturity: proven
chain:
  consumes: "session deliverables"
  produces: "registry + tracking audit"
  chains: ["close-session"]
  position: 6
---

# Close Asset Audit

Independent audit of session deliverables — checks that reusable components are registered in the Lego Registry and work is tracked in Notion. Invoked by `/close-session` Step 5b; enforced by `close-asset-audit-gate.py` Stop hook.

## When to run

- Automatically during `/close-session` (Step 5b)
- The Stop hook blocks session close if this hasn't run and the session has >=2 commits

## Instructions

### Step 1: Identify session commits

Read the session-start marker to find `head_sha`, then enumerate all commits and new/modified files:

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

# Get start SHA
START_SHA=$(python3 -c "
import json
d = json.load(open('/tmp/claude-sessions/session-$SESSION_ID.json'))
print(d.get('head_sha', ''))
" 2>/dev/null)

# If nogit or missing, fall back to checking last N commits by date
if [ "$START_SHA" = "nogit" ] || [ -z "$START_SHA" ]; then
    echo "No session SHA — using git log from today"
    git log --oneline --since="12 hours ago" --name-only
else
    echo "Session commits ($START_SHA..HEAD):"
    git log --oneline "$START_SHA..HEAD"
    echo ""
    echo "Files changed:"
    git diff --name-only "$START_SHA" HEAD
    echo ""
    echo "New files:"
    git diff --name-only --diff-filter=A "$START_SHA" HEAD
fi
```

### Step 2: Classify deliverables

For each new or significantly modified file, classify:

| File | Type | Lego candidate? | Why |
|---|---|---|---|
| `scripts/*.sh` (new) | Script/Library | YES if reusable function/pattern | Connectors, processing blocks |
| `scripts/*.sh` (modified) | Extension | MAYBE if new capability added | New deploy targets, new functions |
| `config/*.sh` | Config | NO unless new reusable pattern | Infrastructure |
| `systemd/*.service` | Infrastructure | NO | One-off deployment |
| `hooks/*.sh` | Hook | YES if the pattern is reusable | Discriminator, injection, gate patterns |

**Classification rules:**
- A script with exported functions sourced by other scripts = Connector or Processing block
- A script that combines multiple components end-to-end = Assembly
- A pattern that applies across agents/projects = Processing block (even if the script is specific)
- Infrastructure (systemd units, plists, drop-ins) = NOT Lego unless the pattern itself is novel

### Step 3: Check Lego Registry for gaps

For each Lego candidate from Step 2, search the Lego Registry:

```bash
NOTION_KEY=$(doppler secrets get YOUR_SECRET --project che-all --config dev --plain 2>/dev/null)
LEGO_PAGE="YOUR-NOTION-DB-ID"

# Get current Lego blocks
curl -s "https://api.notion.com/v1/blocks/$LEGO_PAGE/children?page_size=100" \
  -H "Authorization: Bearer $NOTION_KEY" \
  -H "Notion-Version: 2022-06-28" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for r in data.get('results', []):
    if r.get('type') == 'toggle':
        text = ''.join(t.get('plain_text','') for t in r['toggle'].get('rich_text',[]))
        print(text)
"
```

Compare the list of Lego candidates against existing entries. Report:
```
Lego audit:
  ✓ {component} — already registered
  ✗ {component} — MISSING, should be: {Connector|Processing|Assembly}
  - {component} — not a Lego candidate (reason)
```

### Step 4: Check Notion task exists

Search Che Tasks DB for a task matching this session's work:

```bash
NOTION_KEY=$(doppler secrets get YOUR_SECRET --project che-all --config dev --plain 2>/dev/null)
DB_ID="YOUR-NOTION-DB-ID"

# Search by keywords from commit messages
KEYWORDS=$(git log --oneline "$START_SHA..HEAD" 2>/dev/null | head -3 | sed 's/^[a-f0-9]* //')
echo "Searching tasks for: $KEYWORDS"
```

If no matching task found AND the session has >=2 commits:
```
⚠️ No Notion task tracks this work.
   Commits: {N}
   Suggest: "{task title from commit messages}" → Create as Done?
```

### Step 5: Check MEMORY.md updated

If new components were deployed or new gotchas discovered, verify MEMORY.md has a corresponding entry:

```bash
# For each new script/component, check if MEMORY.md mentions it
for file in $(git diff --name-only --diff-filter=A "$START_SHA" HEAD 2>/dev/null); do
    base=$(basename "$file")
    if grep -q "$base" ~/.claude/projects/*/memory/MEMORY.md 2>/dev/null; then
        echo "✓ $base — in MEMORY.md"
    else
        echo "✗ $base — NOT in MEMORY.md"
    fi
done
```

### Step 6: Produce verdict

Print a summary table:

```
Asset Audit Results:
| Asset | Lego Registry | Notion Task | MEMORY.md |
|---|---|---|---|
| {component} | ✓ / ✗ MISSING | ✓ / ✗ MISSING | ✓ / ✗ MISSING |

Verdict: PASS / FAIL ({N} gaps found)
```

**If PASS:** Write the audit marker and report.

```bash
python3 << PYEOF
import json, datetime
marker = {
    "session_id": "SESSION_ID_HERE",
    "assets_checked": 0,       # FILL
    "lego_entries_added": 0,    # FILL
    "notion_task_exists": True, # FILL
    "memory_updated": True,     # FILL
    "audited_at": datetime.datetime.now(datetime.UTC).isoformat() + "Z"
}
with open("/tmp/asset-audit-SESSION_ID_HERE.json", "w") as f:
    json.dump(marker, f, indent=2)
print("Asset audit marker written — gate satisfied.")
PYEOF
```

**If FAIL:** List the specific gaps. The caller (close-session) should fix them before writing the marker. Do NOT write the marker on fail — the Stop hook will block until the gaps are closed and the audit re-run.

## Rules

- **Independent check** — this skill reads git and Notion directly. It does not trust the caller's summary of what was built.
- **No rationalizing N/A** — if a script has exported functions sourced by other scripts, it IS a Lego block. "Internal library" is not a valid reason to skip registration.
- **Notion task is mandatory for >=2 commits** — significant work must be tracked. Offer to create retroactively if missing.
- **MEMORY.md check is advisory** — report gaps but don't block on them (some components don't need memory entries).
- **Write marker ONLY on pass** — the Stop hook checks for this file. A premature marker defeats the gate.
