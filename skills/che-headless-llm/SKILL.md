---
name: che-headless-llm
description: 'Run batch LLM extraction/classification at $0 marginal cost via `claude -p` (headless Claude Code) under the Max subscription — no API key, no free-tier 429 walls. Use when a script needs to call an LLM per-item over a batch (enrich N files, classify N rows, extract JSON from N docs) and quality fits Haiku/Sonnet tier. Triggers: "batch LLM", "enrich these files", "classify this list with an LLM", "LLM per row without an API key", "Gemini keeps 429ing".'
metadata:
  summary: "$0 batch LLM calls via claude -p under the Max sub — the proven invocation block + batch harness rules"
uses:     []
requires: []
bets:     []
maturity: proven
---

# che-headless-llm

Batch LLM work billed to the **Max subscription** instead of API dollars or fragile free tiers. Proven 2026-07-01/02: 133 extraction calls (che-kb enrichment backfill), $0, 1 transient timeout, quality ≥ gemini-2.5-flash. Marginal-cost order for batch LLM: **Max-sub headless ($0) > paid API (cheap, reliable) > free API tier (429 walls = most expensive: aborted batches + rework)**.

## The invocation block (copy verbatim)

```python
import os, json, re, subprocess, time

def claude_extract(prompt: str, model: str = "claude-haiku-4-5", timeout: int = 300) -> dict:
    """One headless LLM call under the Max sub. Returns parsed JSON dict."""
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}   # 1
    cmd = ["claude", "-p", "--model", model, "--output-format", "json",
           "--setting-sources", "",                                     # 2
           "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}']  # 3
    last_err = None
    for attempt in range(2):                                            # 4
        r = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                           timeout=timeout, env=env, cwd="/tmp")        # 5
        try:
            txt = json.loads(r.stdout).get("result", "")
            m = re.search(r"\{.*\}", txt, re.S)                         # 6
            return json.loads(m.group(0))
        except Exception as e:
            last_err = e; time.sleep(5)
    raise RuntimeError(f"claude -p failed twice: {last_err}; stderr={r.stderr[:200]}")
```

Why each line exists (all bitten-once):
1. **`CLAUDECODE` env var must be stripped** — the nested-session guard blocks `claude -p` inside any Claude Code session otherwise.
2. **`--setting-sources ''`** — skips global CLAUDE.md/hooks: cuts ~48k → ~25k tokens overhead per call (the floor is the Claude Code system prompt) and halves wall time.
3. **Empty strict MCP** — without it, every call spins up ALL user MCP servers (12+): slow, wasteful.
4. **Validate + 1 retry** — no schema enforcement in `-p`; instruct "ONLY JSON, no fences", then parse defensively (fence-strip regex) and retry once.
5. **Prompt via stdin** — 20k-char prompts break argv; `cwd=/tmp` avoids loading a project's context.
6. Models tolerate fences/preamble despite instructions — always extract the outermost `{...}`.

## Batch harness rules (each prevented a real failure)

- **Per-item try/except — one bad item must NEVER abort the batch.** (A fail-fast raise killed an unattended 110-card run at card 15.)
- **Skip-guard = the output file's existence** — makes every run resumable/idempotent; crash recovery = just re-run.
- **Expect ~1 transient 300s timeout per ~125 calls** — the retry/re-run handles it; don't tune around it.
- **~80s/call wall** (harness startup + model) — a no-op run (all skips) must NOT sleep between items.
- **Usage-window exhaustion looks like empty `result`** — Max 5-hour windows can run dry near heavy interactive use (observed ~23:50 after a marathon); the SAME items succeed in a fresh window. Include stdout snippet in error messages; re-run later, don't debug the code.
- **Stamp metadata from the RUNTIME model choice**, never a module constant — a wrong `enriched_by` stamp made a grep-driven refresh pass re-run all 124 items.
- **Detach with `nohup python3 -u`** — without `-u`, python buffers stdout and the log sits at 0 bytes looking stalled; progress-check via output-file counts, not the log.
- **Cost telemetry:** the wrapper's `total_cost_usd` is *notional* under the sub (what API would have billed) — report it as such, actual marginal $0.
- **Convergence for drain-loops keys on the QUEUE metric** (pending/remaining), never a growable proxy (see global CLAUDE.md throughput rule).

## When NOT to use
- Interactive/latency-sensitive (80s/call floor) → paid API.
- Strict-schema-critical output → paid API with `output_config.format` / structured outputs.
- Volume that would dent the 5-hour quota windows during work hours → pace it overnight (`--sleep`, nohup) or paid API.
- Content that must not leave disk (client/private wings) → no LLM at all; respect privacy walls.

## Reference implementation
`~/projects/che-kb/bin/enrich.py` (dual-backend: haiku default, gemini fallback) + `bin/backfill-youtube.sh` (2-pass batch runner) + `bin/nightly-enrich.sh` (launchd incremental + heartbeat).
