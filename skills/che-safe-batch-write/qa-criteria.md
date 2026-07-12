# QA Criteria — che-safe-batch-write

## Expected output structure
Applying this pattern to a task should produce, in order:
1. A dry-run preview file (or equivalent inline preview) listing every proposed create/update,
   with an explicit CREATE-vs-LINK-existing marker per row — before any write.
2. At least one explicit ambiguity flagged to the user (if the schema mapping has any non-1:1
   translation) with the proposed value shown, not silently resolved.
3. A per-row execution log/report that updates incrementally (verifiable by checking it contains
   partial state after an interrupted run, not only after a full run completes).
4. A verification pass that queries the LIVE target system fresh (not the local log) and checks
   EVERY field that was proposed for write, not a subset.

## Correctness checks
- [ ] Dedup search was validated against a known-existing record before trusting "0 matches"
- [ ] The SAME dedup-key function is used by every script/step touching this batch (no
      reimplementation — verify by checking for a shared import, not two separate `def norm()`)
- [ ] Execution log is written after each field/entity write, not batched at row-end or batch-end
- [ ] Verification re-fetches the live system per record (not from the local execution log)
- [ ] Verification checks the FULL set of fields proposed in the dry-run, not a hand-picked subset
- [ ] Type consistency in verification comparisons (e.g. Pipedrive enum int-vs-string) is handled
- [ ] "Is field populated" checks the actual inner value for wrapped types (arrays-of-dicts with
      an empty value), not just "is the field non-null/non-empty-list"
- [ ] On any discrepancy, a single-record diagnostic call (with full error body) precedes any
      batch-wide fix attempt

## Known false positives
- Dry-run reporting 0 existing matches when the dedup search mechanism itself is broken (looks
  identical to "everything is genuinely new")
- A "found"/"populated" flag that's true only because a wrapper structure is non-empty, while the
  actual value inside is blank
- A verification pass reporting success because it only checked a subset of the intended fields
- Silent duplicate creation on a resumed/rerun batch when the resume log's dedup key doesn't
  exactly match the original creation key (accents, spaces, case — any normalization drift)

## Severity / quality threshold
- **Must fix before shipping any batch write**: no dedup-search validation, no per-field
  checkpointing, verification that checks fewer fields than were written, or two different
  normalization functions for the same dedup key across scripts.
- **Acceptable to flag-and-defer**: a genuinely un-mappable enum/schema mismatch (present it to
  the user, don't force a guess) — this is a judgment call, not a bug.
- Minimum bar: every write claimed as "done" must be independently re-confirmed by re-querying
  the live system, not asserted from the execution log or from memory of "it returned 200 OK."
