---
name: che-context-optimize
description: Shrink an oversized always-loaded context file (global ~/.claude/CLAUDE.md, a project CLAUDE.md, or an auto-memory MEMORY.md index) WITHOUT dropping any rule. Use when the 40k warning fires, when the harness says "MEMORY.md is over the read limit / only part of it was loaded / compact it now", when docs-health reports an oversized context file, or when the user says "optimize CLAUDE.md", "context file too big", "shrink memory". Enforces per-item before→after reconciliation (not sampling) so nothing is silently lost.
metadata:
  summary: "Shrink an oversized always-loaded CLAUDE.md/MEMORY.md without dropping any rule"
uses:     []
requires: []
bets:     []
maturity: proven
---

# che-context-optimize

Optimize an oversized **always-loaded** context file. The size is the symptom; **dilution** is the real cost — too many irrelevant rules per session make the model apply the relevant one less reliably. Knowledge source: che-agents memory `reference_context_file_optimization.md`.

Core principle: **always-loaded context (CLAUDE.md, auto-memory index) is scarce; on-demand context (skills, topic files, referenced files) is free.** Content earns an always-loaded slot only if it fires across many session types.

## File classes — the bar is DIFFERENT per class (do not mix them up)

| File | Constraint | Trigger | Target |
|---|---|---|---|
| Global / project `CLAUDE.md` | soft 40k performance warning | ≥ ~38k chars | **32–34k** (headroom, not just under the line) |
| Auto-memory `MEMORY.md` index (`~/.claude/projects/*/memory/MEMORY.md`) | **HARD ~24.4k read cap — content beyond is SILENTLY DROPPED each session** | harness reminder ("over the read limit" / "only part was loaded") or ≥ ~20k | **≤17k**, every entry ONE line ≤ ~200 chars; detail lives in topic files |

Landing a MEMORY.md at 30k is still broken — it truncates. The index target is 17k, period.

## Routing — when NOT to run inline
If the nag fires mid-task or late in a long session: **queue it** (todo / first task of a fresh session). A lossless compaction needs a fresh head; a rushed one loses rules — the failure this skill exists to prevent.

## Step 0 — Baseline (always first)
```bash
F=<target file>
mkdir -p ~/.claude/.skill-backups
cp "$F" ~/.claude/.skill-backups/$(basename $F)-$(date +%Y%m%d-%H%M).bak   # NOT /tmp — survives reboot
wc -c "$F"; wc -l "$F"    # baseline bytes + LINE COUNT (the reconciliation anchor)
```

## Step 0.5 — Whole-budget scan (optimize the biggest offender, report the total)
```bash
for f in ~/.claude/CLAUDE.md ~/CLAUDE.md ./CLAUDE.md ~/.claude/projects/*/memory/MEMORY.md; do
  [ -f "$f" ] && printf "%7d  %s\n" "$(wc -c < "$f")" "$f"; done | sort -rn
```
The always-loaded budget is the SUM. If a bigger file than the requested one is over its bar, say so before starting.

## The five moves, in value order

**1. Consolidate (biggest win — improves firing, not just size).**
Cluster rules that are the *same action under different triggers* into one principle + an enumerated trigger sub-list (`(a)…(h)`). **Safety contract: the action merges, but EVERY distinct trigger phrase survives as a sub-bullet.** This is how `C1–C4` were built.

**2. Compress.**
Collapse multi-sentence rules whose detail is already enforced by a hook/skill or duplicated in a `feedback_*`/`reference_*` file — leave a one-line pointer.

**3. Demote to topic file (PRIMARY move for MEMORY.md indexes).**
An index entry is a *pointer*, not the content. Multi-line entries and whole inline sections (cron tables, gotcha lists, routing tables) → move body into the entry's topic file (create one if missing), keep ONE line ≤200 chars: `- [Title](file.md) — hook`. **Stale-entry collapse:** entries for dead/dropped/dormant things (product DROPPED, service stopped) shrink to one line with the terminal state; their history already lives in the topic file. Index safety contract: a line may be cut ONLY after verifying its content exists in the named topic file (fetch-back, not memory).

**4. Archive provenance.**
Move `Origin:`/incident narratives to a companion file (`~/.claude/RULES-PROVENANCE.md`). **Plain-reference it, NEVER `@`-import** — an `@`-import reloads into context and defeats the purpose.

**5. Migrate.**
Move workflow-scoped rules into that workflow's `SKILL.md` (loads when the work happens). Only migrate rules whose trigger is a **named workflow with a skill**; cross-cutting rules stay always-loaded.

## Step F — Verification = RECONCILIATION, not sampling (MANDATORY)
The 2026-05-30 pass dropped 1 rule + 2 dups; "size dropped + spot-checks pass" did NOT catch it.
1. **Per-item ledger:** enumerate every rule/bullet in the `.bak`; mark each **kept / merged-into-X / demoted-to-topic-Y (verified) / migrated-to-skill-Z / archived**. Zero items unaccounted.
2. **Mechanical anchor check** (runs the ledger for you; investigate every MISSING before accepting):
```bash
python3 - "$BAK" "$F" <<'EOF'
import re, sys
bak, new = open(sys.argv[1]).read(), open(sys.argv[2]).read().lower()
miss = 0
for line in bak.splitlines():
    line = line.strip()
    if not line.startswith(('-', '*')) or len(line) < 12: continue
    words = [w for w in re.findall(r"[A-Za-z0-9_./-]{5,}", line)][:4]   # anchor tokens per bullet
    if words and not any(w.lower() in new for w in words):
        print("MISSING anchors:", line[:110]); miss += 1
print(f"{'FAIL' if miss else 'OK'}: {miss} bullets with no surviving anchor")
sys.exit(1 if miss else 0)
EOF
```
   (Anchors moved to a topic/provenance file count as accounted — check THAT file before restoring anything.)
3. **Duplicate scan:** sort/uniq bullets; flag any rule now appearing twice.
4. **Save the ledger** (don't just print): append the summary to the run log (Step G).
5. For MEMORY.md: re-check `wc -c` ≤ 17k AND `awk 'length > 220' F` returns nothing (one-line contract).

If any item can't be accounted for, restore from the backup and redo that move.

## Step G — Regrowth defense (the fix must outlive the run)
1. **Run log** — append one line to `~/.claude/RULES-PROVENANCE.md` under `## Optimization runs`:
   `- 2026-07-02 | <file> | 48.1k→16.8k | ledger: kept N, merged N, demoted N, archived N | bak: <path>`
   (This is also how the next session answers "didn't we already run this?")
2. **Budget banner** — ensure the file's top comment states its budget, e.g. `<!-- BUDGET: index ≤17k, one line ≤200 chars per entry; detail goes in topic files -->`. Writers see it at every append.
3. **Writer check** — the appenders (session-retro, capture-progress, close-session, memory instructions) must state the one-line-per-entry contract; if one doesn't, patch it in the same pass (C3: all surfaces at once).
4. Re-run trigger stays automatic (harness reminder + docs-health) — but with 1–3 in place, re-runs should be rare and small.

## Output
- before/after bytes + % + line delta, per file AND for the whole always-loaded budget (Step 0.5)
- the reconciliation ledger summary (kept/merged/demoted/migrated/archived; any MISSING anchor = STOP)
- what moved where (topic files, provenance, skills) + run-log line + backup path

## Notes
- Global `~/.claude/CLAUDE.md` is the highest-stakes file — every session loads it. Bias toward consolidate/compress over deletion; never drop a trigger.
- MEMORY.md indexes are the opposite: deletion from the INDEX is fine once content is fetch-back-verified in a topic file — the index is a table of contents, not the book.
