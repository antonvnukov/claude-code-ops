# Skill Chains
Multi-step pipelines composed from individual skills. The flagship chain — and the reason
this repo exists — is `/close-session`: a session can't end without capturing its learnings,
and hooks (not instructions) enforce it.

### /close-session
**Trigger:** "wrap up", "close session", "done for the day", before /clear
**Steps:**
1. `/git-status` — classify MINE vs EXTERNAL files
2. `/capture-progress` — capture decisions/progress to che-brain
3. `/session-retro` — extract process learnings → encode into CLAUDE.md/memory
4. **Trajectory check** — if session involved client work: query che-brain for all decisions on this project/client → assess if an arc completed (audit done, onboarding done, report delivered) → if yes, extract full process SOP → save to `GTM/_playbooks/` → register in Playbooks Registry (`YOUR-NOTION-DB-ID`). If arc is still in progress, tag decisions with trajectory_id for later stitching. Skip for internal/infra tasks.
5. **Extraction + `/skill-forge`** — client sessions: run extraction depth gate (Lego >=2, SOPs >=1, stack templates checked, automations >=1). Automation scan is INDEPENDENT of retro tags. Then skill-forge for reusable patterns (≥0.8 score).
6. `git commit` — stage + commit MINE files (includes any skills forged in step 5)
7. `/track done` — mark Notion task Done, add deliverable
8. `/gsd:pause-work` — write .continue-here.md handoff


> My full harness runs 7 active chains (weekly ops, blog, SEO, event outreach...). Only the
> session-lifecycle chain ships here because its skills are the ones in this repo — the
> pattern (skills declare `chain:` metadata; a CHAINS.md is the runtime SOT) transfers as-is.
