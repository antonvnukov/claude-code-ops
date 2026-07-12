---
name: che-safe-batch-write
version: 1.0.0
description: Safe execution pattern for any batch write from a source dataset into a live CRM/production system (Pipedrive, Notion, HeyReach, Supabase, etc.) — dry-run preview, human sign-off on ambiguity, checkpointed execution, and live fetch-back verification.
author: Anton Vnukov / Claude
tags: [crm, batch-write, pipedrive, dedup, verification, production-safety]
tested: true
quality_score: 0.87
inputs:
  - source_rows: iterable of records to write (e.g. sheet rows, CSV, JSON export)
  - target_system: a live system with a create/read/update API (Pipedrive, Notion, HeyReach, Supabase...)
  - dedup_key_fn: ONE canonical function that normalizes a record into a lookup key, imported (not reimplemented) by every script that touches this batch
  - field_map: mapping from source_rows fields to target_system fields, with enum/option-id resolution where applicable
outputs:
  - dry_run_preview.json: every proposed create/update, zero writes made
  - execution_log.json: per-row/per-field checkpoint, written after EVERY write (not just at the end)
  - verification_report: live fetch-back diff (not the local log) confirming final state matches intent
metadata:
  summary: "Dry-run → sign-off → checkpointed batch writes into live CRMs with fetch-back verify"
---

# Safe Batch Write to a Live System

Forged 2026-07-01 from the Shoptalk Europe 2026 Pipedrive lead-creation + enrichment work
(32 leads, 3 sequential batch operations in one session). Two real incidents in that session
motivate every rule below — cited inline so the "why" survives, not just the "what."

## The 5 steps (do not skip or reorder)

### 1. Dry-run preview — zero writes
Build the full preview of what would be created/changed, **cross-referencing dedup against the
live target system**, not just the local source. Search the target for existing matches (by
email/URL/name or whatever the natural key is) before proposing "create." Output a preview file;
make no writes yet.

**Verify the dedup search itself works** before trusting a "0 matches" result — test it against a
record you KNOW exists in the target system. A silently-broken search returns "0 existing" for
every row, which looks identical to "genuinely all new."

**Source coverage before "new"/"absent", and never infer (Twenty/GoToMoney 2026-07-09).** Deciding
a record is NEW (create) or a field is ABSENT is only as good as the sources you checked. A
sub-agent's "NOT FOUND" is scoped ONLY to the sources it read — check ALL of them (local
`clients/*` files + transcripts, not just Notion/che-brain) before you create or delete. And NEVER
write an inferred attribute (a guessed title/role/surname/email): **source-or-nothing.** Cost of
skipping this: a fabricated "Sergey (technical)" contact, then a REAL "Sergiy (content)" deleted as
"fabricated" because the check only covered Notion + che-brain and missed the meeting transcript.
See memory `feedback_crm_source_coverage`.

### 2. Surface ambiguity — don't silently resolve it
When mapping between two systems' schemas (e.g. a sheet's `$1-3K` budget band vs a CRM's
`$1-2.5K`/`$2.5-5K` split), there is often no clean 1:1 map. Show the proposed value AND flag it
as a judgment call rather than picking one silently. The user approves or corrects; the system
never guesses on your behalf where the schemas genuinely diverge.

### 3. Checkpointed execution — per-row AND per-field
Write to a local execution log **after every individual field/entity write succeeds**, not just
at the end of a row or the end of the batch. A batch that fails partway through (one bad field,
one API rate limit) must be resumable without re-creating what already succeeded.

**Incident that motivates this:** a batch created Org+Person+Lead+Note+Activity per row; the
Activity step failed for all 32 rows (wrong field name), but Org/Person/Lead/Note had already
been written to the live system. The naive fix — re-run the whole script — would have created a
second full set for every row, because the local log only recorded success at the END of a row's
try-block, so a mid-row failure looked identical to "never started."

**The dedup key used to resume MUST be the exact same function as the key used to create.** Do
not reimplement or "improve" the normalization when rebuilding a log from live state — import the
original. Two different scripts using two different normalizations of the same name (one
deaccenting, one not) is invisible until a name has an accent or a space discrepancy, and then it
silently creates a full duplicate for exactly that one row.

### 4. Fetch-back verify against LIVE state — never trust the local log alone
After execution, re-read the actual target system and confirm what you intended is what's really
there. The local execution log can be wrong (see incident above) — only the live system is ground
truth. Verify EVERY field you claimed to have written, not a representative subset.

**Incident that motivates this:** a verification pass checked 4 of ~10 proposed fields and
reported "success." The other 3 fields had silently failed to populate on all 32 records — same
root cause as above (a second script's dedup lookup used a different normalization than the
first, so a downstream join silently matched nothing) — and it went unnoticed for a full session
turn because the verification scope was narrower than the write scope.

**Watch for type mismatches in verification itself**: an enum field written as the string `"454"`
may read back as the int `454`. A naive `==` comparison across types produces false "missing"
reports even when the write succeeded. Cast both sides consistently before comparing.

### 5. Diagnose with ONE row before batch-fixing
When fetch-back verification finds a discrepancy, don't immediately re-run the whole batch with a
guessed fix. Isolate to a single record, make the real API call directly, and read the actual
error body (not just the status code) before writing a fix. This finds the true root cause in one
call instead of guessing across 32.

## Known false positives / traps

- **"0 existing matches" on dedup search** — could mean genuinely all new, OR a broken search.
  Always validate the search mechanism against a known record first.
- **A field that "looks populated" via a generic non-null check** — some systems return a
  non-empty wrapper around an empty value by default (e.g. `[{"value": "", "primary": true}]`
  for an unset email/phone field). Check the actual inner value, not just "is the field truthy."
- **A source column that "looks like one type" from sample rows** — mixed-type columns (e.g. a
  sheet Date column that's text for most rows but a real date-serial-number for rows entered a
  different way) won't show up unless you check the specific rows you're about to use, not just
  the first few.

## When NOT to use this pattern

- One-off single-record writes with no batch/dedup risk — this is overhead for a single API call.
- Read-only audits — no write path, so steps 3-5 don't apply (though the "verify against live,
  not a subset" discipline from step 4 still generalizes to any audit).
