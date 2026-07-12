---
name: che-usage-stats
description: "Report how often you actually use each skill, slash command, CLI, MCP server, and subagent — plus an installed-but-never-used dead-weight report and a 7-day trend with token cost. Parses local Claude Code session transcripts (~/.claude/projects/*.jsonl). Use when asked 'how many times have I used X', 'what skills/CLIs/tools do I use most', 'what's installed but never used', 'usage stats', 'which MCP servers are dead weight', or 'what is Claude Code costing me'."
metadata:
  summary: "Real usage counts for skills, CLIs, MCP, agents + dead-weight report and token cost"
---

# che-usage-stats

Read-only analytics over your Claude Code session transcripts. Answers what you actually invoke, what's installed but dead, and what it costs.

## Run it

```bash
python3 ~/.claude/scripts/che-usage-stats.py            # full human-readable report
python3 ~/.claude/scripts/che-usage-stats.py --since 7  # last 7 days only
python3 ~/.claude/scripts/che-usage-stats.py --project my-agency   # one project
python3 ~/.claude/scripts/che-usage-stats.py --top 50   # deeper ranking
python3 ~/.claude/scripts/che-usage-stats.py --json     # machine-readable (for work-style)
python3 ~/.claude/scripts/che-usage-stats.py --md        # markdown summary block
```

A full scan of the whole transcript corpus (~1.6GB) takes ~60s. `--since` only filters records, not files, so it is not faster — it just narrows the output.

## What it reports

1. **Invocations** — skills (model-invoked), slash commands (user-typed), CLIs *with subcommands* (`gws sheets`, `gh pr`, `doppler secrets` — the layer hidden inside Bash), MCP tools + per-server rollup, subagent types, built-in tool mix, top API hosts.
2. **Dead weight** — installed-but-never-used: skills (used / installed), configured MCP servers with zero calls, registry CLIs never invoked, launchd job inventory.
3. **Trend + cost** — last-7d vs prior-7d deltas, estimated token spend by model and by project.

## Notes

- Source of truth = `~/.claude/projects/*/*.jsonl` (counts real `tool_use` invocations, not string occurrences).
- Cost is an **estimate** from public list pricing (Opus/Sonnet/Haiku) including cache tokens — directional, not a bill.
- Shell keywords (`cd`, `echo`, `export`…) are stoplisted from the CLI ranking so real tools surface.
- "MCP used" counts only servers declared in `settings.json` / `.claude.json`; plugin-provided MCPs (claude-in-chrome, discord) appear in the tool ranking but not the configured-server dead-weight check.
- Crons are inventory-only — headless cron runs are not in transcripts.
