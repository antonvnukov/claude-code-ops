---
name: che-conductor-handoff
description: Produce a complete, crash-proof handoff so the CURRENT session's in-flight work can be picked up by a fresh zero-memory agent (Conductor workspace, Ekko, or a future resumed session). Commits only the files this session touched, enumerates ALL out-of-repo and external-state changes, writes _context/handoff.md, and SELF-TESTS that a blind agent could finish from it alone. Use when the user says "move this to Conductor", "hand this off", "make a handoff", "pause this for a fresh agent", or before parking a substantive session.
metadata:
  summary: "Crash-proof handoff so a zero-memory agent can finish this session's in-flight work"
---

# che-conductor-handoff

Move the current session's work to a fresh, zero-memory agent (Conductor worktree,
Ekko, or a later resume) **without losing anything**.

## Why a naive handoff is insufficient

A Conductor workspace = a fresh agent in its own git worktree branched from a commit
**in one repo**, with no conversation memory. Three things a "commit + handoff.md"
miss, and this skill closes:

1. **Out-of-repo changes** — `~/.claude/{skills,scripts,hooks}`, dotfiles, OTHER
   repos. A single project branch never carries these. Must be committed to THEIR
   repos (dotfiles-claude, che-harness, …) or listed with absolute paths + state.
2. **MINE vs EXTERNAL** — never `git add -A` (Anton's rule; repos carry 100+
   untracked AI-tool dotfolders + parallel-session files). Commit ONLY files this
   session edited, named explicitly.
3. **External side-effects** — Notion / n8n / VPS / CRM / sent messages aren't in
   git. Enumerate what was changed or left mid-flight so the next agent doesn't
   redo or corrupt it.

## Run this in the session being handed off

Paste / run this against the live session (it has the context):

```
Hand this session to a fresh agent with ZERO memory of this chat. Build a complete handoff:

1. COMMIT — only the files I actually edited this session, listed explicitly (NEVER git add -A;
   this repo has untracked noise + maybe parallel-session files). Branch `handoff/<short-topic>`.
   Report branch + SHA + the exact file list. Push only if the repo has a remote.
2. OUT-OF-REPO — list every change outside this repo: other repos (path + committed-SHA or
   uncommitted), ~/.claude skills/hooks/scripts, dotfiles, /tmp artifacts. For each: committed
   where, or still uncommitted at <abs path>. Commit the ones that belong to a repo (e.g.
   dotfiles-claude, che-harness) on their own branch and report SHAs.
3. EXTERNAL STATE — list Notion pages, n8n workflows, VPS/systemd, CRM writes, sent/queued
   messages I changed or left mid-flight, with IDs/links, so the next agent doesn't redo them.
4. _context/handoff.md — write it: Objective (what+why) · DONE (with paths) vs LEFT · branch to
   check out · ordered next steps · Verification commands (exit 0 = correct) per step · settled
   decisions & dead-ends (so they're not re-litigated). Assume the reader never saw this chat.
5. SELF-TEST — re-read ONLY handoff.md (ignore everything you remember) and answer honestly:
   could a blind agent finish the task from it alone? Name every gap, then fill it. Repeat until
   no gaps.
6. CONDUCTOR SETUP — output the base branch + the one-paragraph kickoff prompt to paste into the
   new workspace.
```

## Auto-surfacing (you don't have to remember the handoff exists)

A global `SessionStart` hook (`~/.claude/hooks/handoff-surface.sh`, verified to fire inside
Conductor) detects live handoffs in any new session of the repo and prints a banner:
- On a `handoff/*` branch with `_context/handoff.md` → "read it before any work."
- On the base branch while an unmerged `handoff/*` branch exists → "checkout `<branch>` first."

So the kickoff prompt from Step 6 is now a convenience, not a dependency — even if you forget,
the next session in that repo shouts the handoff at you. The branch + `handoff.md` carry the
state; the hook is the pointer.

**Harness-on-main caveat (dogfooded 2026-06-30):** the auto-surface fires on `handoff/*`
branches that are AHEAD of base (unmerged). In a harness session you commit to `main`, so if you
then create the handoff branch AT `main`'s HEAD it counts as merged and will NOT surface. For a
harness handoff to self-surface, commit `handoff.md` ONLY on the `handoff/*` branch (branched
from `main` BEFORE the handoff commit), leaving `main` behind it. If you already committed to
`main`, the `handoff.md` is still durable and findable — it just won't trip the banner; rely on
the committed doc + a direct pointer instead.

## Completing a handoff (this is what clears the banner)

The banner keys off **unmerged** `handoff/*` branches, so finishing the work is what silences it
— there is no manual "dismiss." When the handoff is done:

1. Merge the `handoff/<topic>` branch into the base branch (PR or local merge).
2. That's it — the next session sees the branch as merged and stays silent (self-cleaning).

Do NOT just delete `_context/handoff.md` to quiet the banner: the file can ride into `main` on
merge, and the hook ignores file existence by design precisely so a stale file never cries wolf.
A handoff is "done" when its branch is merged, not when its file is gone.

## Routing — not every session should go to Conductor

- **In-repo code session** → Conductor handoff (above). Worktree isolation is the win.
- **Harness / `~/.claude` / dotfile session** → commit to its real repo (dotfiles-claude,
  che-harness); Conductor worktrees are for PROJECT repos, not the harness. Don't force it.
- **External-state-heavy session** (Notion/n8n/CRM/VPS) → finish in place; fragmenting external
  ops across a worktree handoff invites double-writes.
- **Already in a Conductor worktree** (`~/conductor/workspaces/...`) → it's already there;
  just continue or commit + write handoff.md for durability.

## Relationship to /delegate (not a duplicate — the other half)

Same DNA (a self-contained, verification-backed spec for a zero-memory reader), opposite job:

- **/delegate** → hands NEW, well-scoped, non-interactive work to an AUTONOMOUS bot
  (Ekko/HeavyPope/Hermes) as a Notion task. Its rules forbid delegating interactive work or
  uncommitted local deps.
- **/che-conductor-handoff** → relocates IN-FLIGHT, possibly-interactive work (with uncommitted +
  out-of-repo + external state) to an agent YOU drive (Conductor) or a future resume, as a git
  branch + handoff.md. This is precisely the case /delegate refuses.

Reuse delegate's body-contract for the handoff.md spec quality: **Objective · Instructions ·
Output · Verification (runnable, exit 0 = pass)**. Decision rule: *autonomous + scopable +
committable →* `/delegate`. *Interactive / in-flight / uncommitted →* this skill.

## The real sufficiency test

Step 5 (self-test) IS the sufficiency guarantee — the session proves the handoff is complete by
trying to act from it blind. Without that step, "sufficient" is an assumption; with it, it's
verified. Pair with `/che-session-recover` to find what still needs a handoff. See
[[claudecode-nested-guard-vscode-resume]].
