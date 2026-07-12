#!/usr/bin/env bash
# Installs the skills + hooks into ~/.claude and prints the settings fragment to merge.
set -euo pipefail
DEST="${CLAUDE_DIR:-$HOME/.claude}"
mkdir -p "$DEST/skills" "$DEST/hooks"
cp -R skills/* "$DEST/skills/"
cp hooks/*     "$DEST/hooks/"
chmod +x "$DEST"/hooks/*.sh "$DEST"/hooks/*.py 2>/dev/null || true
echo "✓ skills → $DEST/skills   ✓ hooks → $DEST/hooks"
echo
echo "Now merge this into $DEST/settings.json (hooks block):"
echo "──────────────────────────────────────────────────────"
cat examples/settings-example.json
