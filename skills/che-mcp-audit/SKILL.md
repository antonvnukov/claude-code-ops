---
name: che-mcp-audit
description: Audit and clean up a Claude Code MCP server surface — inventory all config layers, kill dead/duplicate servers, convert MCP→CLI where a CLI exists (CLI-first), Doppler-wrap kept servers to remove plaintext secrets, and verify nothing breaks. Use when asked to "audit my MCP setup", "clean up MCP servers", "which MCP should I keep", "too many MCP servers", "convert MCP to CLI", or to harden MCP config on a new machine/VPS. Proven 2026-06-27 (Mac: 37→12 servers).
metadata:
  summary: "Inventory and prune the MCP surface — kill dead servers, convert to CLI-first, Doppler-wrap secrets"
---

# che-mcp-audit

Reduce an MCP surface to the minimum that earns its keep, CLI-first, with no plaintext secrets — without breaking any skill.

## Core principle
**CLI-first whenever a CLI exists.** A CLI call is ~17x cheaper/call, model-native, no schema tax. MCP only for integrations with no CLI that need structured/OAuth/audit. **MCP Tool Search (Claude Code v2.1.7+) auto-defers tool schemas >~10% context** — so raw server count is NOT the problem; dead servers, duplicates, and plaintext secrets are.

## Interaction style (enforced)
Anton wants this driven **one tool at a time** with **per-item evidence + explicit approval** — never batch-execute even "safe" changes. Use `AskUserQuestion` per tool, and include a one-line "what it is" so he can decide. (See memory `feedback_interactive_change_approval`.)

## Process

### 1. Inventory all config layers (they STACK — total = union)
```bash
claude mcp list                                   # health + all servers (incl. claude.ai connectors + plugins)
python3 -c "import json,os;print(list(json.load(open(os.path.expanduser('~/.claude.json')))['mcpServers']))"
python3 -c "import json,os;print(list(json.load(open(os.path.expanduser('~/.claude/settings.json')))['mcpServers']))"
```
Layers: `~/.claude.json` mcpServers + `~/.claude/settings.json` mcpServers + claude.ai connectors (account-side) + enabled plugins. Note per-project `disabledMcpServers` overrides in `~/.claude.json` `projects`.

### 2. Classify each server
dead (failed/401) · duplicate (same capability N ways) · plaintext-secret (inline token in args/env) · used-by-skills · core-keep.

### 3. Per tool, one at a time — verify BEFORE dropping
1. **Blast radius:** `grep -rlI 'mcp__<server>__' ~/.claude/skills | wc -l` — how many skills call its MCP tools.
2. **CLI exists + works?** `command -v <cli>`; verify auth with a **direct API call** (`curl … → HTTP 200`), NOT the CLI's own `auth-status`/`whoami` (those lie/noise).
3. **Migrate dependent skills** to the CLI + **live-test** each.
4. **Then drop** the MCP (`python3` edit of the config file — never the Edit tool on settings.json while a daemon runs; use `jq`/`python3`).

"Failed to connect" in `claude mcp list` ≠ dead — npx cold-start times out the health check; verify creds/endpoint before deleting.

### 4. Doppler-wrap kept MCPs that carry inline secrets
Repoint config to `~/.claude/scripts/<svc>-mcp.sh`:
```bash
#!/bin/bash
set -e
exec env KEY="$(doppler secrets get <YOUR_SECRET> --config dev --project che-all --plain 2>/dev/null)" npx -y <package>
```
(Pattern: notion-che-server.sh.) Removes plaintext from config.

### 5. Update surfaces (one pass)
global `CLAUDE.md` (tool-precedence), `INSTRUCTIONS.md`, `CAPABILITY-REGISTRY.md` (Local CLIs surface), memory `reference_mcp_cli_topology`, an audit doc in the project `_context/`.

### 6. Verify parity (multi-machine)
If skills sync to other machines (VPS vault-sync), confirm the CLIs exist there: `ssh root@<vps> 'command -v <cli>'`. A migrated skill that calls a CLI the VPS lacks degrades there.

## Gotchas (hard-won)
- `gh` prioritizes `YOUR_SECRET` env over its keyring → a dead token in Doppler (injected by `doppler run`) breaks `gh` everywhere. The same var is shared with the last30days engine (collision inherent).
- Inline MCP secrets usually live in untracked `~/.claude.json`, not tracked `settings.json` — verify which file before assuming a git-history leak.
- Per-tool `/last30days` surfaces SWITCH candidates (e.g. Clay→Default/Bitscale) — those are business decisions orthogonal to MCP-vs-CLI; flag, don't block.

## References
- che-brain SOP id 10434 · memory `reference_mcp_cli_topology` · example audit `che-agents/_context/mcp-cli-audit-2026-06-27.md`
