# claude-code-ops

**How I run 10–20 parallel Claude Code sessions a day without losing work.**

I'm [Anton Vnukov](https://www.linkedin.com/in/antonvnukov/) — 20+ years in sales, now building
revenue systems at [gotomoney.io](https://gotomoney.io). Claude Code is my execution layer:
on a normal day, 10–20 sessions run in parallel across five project contexts. At that scale the
failure mode isn't bad code — it's **lost work**: sessions crash mid-task, two sessions grab the
same task, learnings evaporate at session end, and "I'll remember it" never survives to tomorrow.

This repo is the operating system I built around that problem: **15 skills + 6 enforcement
hooks** that make sessions claim their work, checkpoint it, capture what they learned, and
refuse to close until they've done so.

## The core idea: instructions don't survive — hooks do

Every skill here started as an instruction Claude kept skipping under "wrap-up momentum."
The fix each time was mechanical enforcement:

- `/session-retro` runs a **convergence loop** (min 2 passes, until <3 new items per pass),
  because single-pass retros consistently found ~40–50% of the real learnings.
- A **Stop hook** (`close-retro-stop-gate.py`) blocks the session from ending while the retro
  gate is armed but unconverged. You cannot politely talk your way past it.
- A **PreToolUse hook** (`claim-gate.py`) hard-blocks writes after 3 unclaimed mutating calls,
  so parallel sessions can't silently collide.

The pattern generalizes: *if a discipline matters, encode it as a gate the harness enforces,
not a paragraph the model reads.*

## The session lifecycle

```
session-open ──► claim ──► [work] ──► mid-sess-check (35% context) ──► close-session
                                              │                            │
                                       checkpoint + capture         8-step chain, hook-gated:
                                                                    git classify → retro loop →
                                                                    capture → automation scan →
                                                                    asset audit → commit →
                                                                    release locks → handoff
```

See [`CHAINS.md`](CHAINS.md) for the full close-session chain — the flagship of this repo.

## Skills

### Session lifecycle (11)

| Skill | What it does |
|---|---|
| [`session-open`](skills/session-open/SKILL.md) | Startup orchestrator: resume context, task queue, lock scan |
| [`claim`](skills/claim/SKILL.md) / [`release`](skills/release/SKILL.md) | File-based task locks so parallel sessions never grab the same work |
| [`checkpoint`](skills/checkpoint/SKILL.md) | Resumable work-state snapshot, auto-injected into the next session |
| [`capture-progress`](skills/capture-progress/SKILL.md) | Extract decisions/insights to a knowledge store before they evaporate |
| [`mid-sess-check`](skills/mid-sess-check/SKILL.md) | Safety checkpoint at 35% context; `--subtask` mode for multi-tab worktrees |
| [`session-retro`](skills/session-retro/SKILL.md) | Convergence-loop retro: friction → strategy → trajectory, hook-enforced |
| [`close-session`](skills/close-session/SKILL.md) | The 8-step closing chain — a session can't end without capturing its work |
| [`close-asset-audit`](skills/close-asset-audit/SKILL.md) | Independent audit: did every built asset get registered? |
| [`skill-forge`](skills/skill-forge/SKILL.md) | Turn a session's repeated pattern into a new skill (score-gated) |
| [`sop-forge`](skills/sop-forge/SKILL.md) | Turn a session's workflow into a runnable SOP |

### AI-ops tools (4)

| Skill | What it does |
|---|---|
| [`che-session-recover`](skills/che-session-recover/SKILL.md) | Post-crash triage: every session classified UNFINISHED/DONE/EMPTY with paste-ready resume commands |
| [`che-conductor-handoff`](skills/che-conductor-handoff/SKILL.md) | Crash-proof handoff a zero-memory agent can finish from alone — self-tested |
| [`che-context-optimize`](skills/che-context-optimize/SKILL.md) | Shrink an oversized always-loaded context file without dropping a single rule |
| [`che-headless-llm`](skills/che-headless-llm/SKILL.md) | $0-marginal-cost batch LLM calls via headless `claude -p` under a Max subscription |

### Hooks (6)

`retro-gate.py` · `close-retro-stop-gate.py` · `claim-gate.py` · `close-asset-audit-gate.py` ·
`session-start-marker.sh` · `auto-release-session.sh` — the mechanical spine. Wire them in
`settings.json` (PreToolUse / Stop / SessionStart) per each file's header comment.

## Install

```bash
git clone <this repo>
cp -R skills/* ~/.claude/skills/
cp hooks/*   ~/.claude/hooks/     # then register in ~/.claude/settings.json
```

## Adapt to your stack

These skills come from a living harness and reference a few pieces of **my** infrastructure by
name. Swap them for your equivalents:

| Reference in the skills | What it is | Swap in |
|---|---|---|
| `che-brain` / `capture_thought` | my personal knowledge-base MCP | any KB / notes MCP, or a plain append-to-file |
| `/track`, Notion DB IDs | my Notion task tracker | your task tracker (IDs are `YOUR-NOTION-DB-ID` placeholders) |
| `/gsd:pause-work` | the GSD project-management system | skip, or your planning tool |
| `qmd-sync` | my local markdown search index | skip, or your local search |

Skills degrade gracefully: every external call is wrapped in "if unavailable, skip and note it."

## Provenance

These aren't theoretical. Each rule carries the incident that created it — dates and
post-mortems included ("the 8th shallow close-session", "the retro that found 3 items until the
user asked *is that all?* twice"). The system exists because every one of those failures
happened at least twice.

## License

MIT
