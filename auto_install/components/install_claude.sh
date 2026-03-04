#!/bin/bash
set -euo pipefail

# Install Claude Code statusline configuration
# Deploys statusline.sh and merges statusLine config into settings.json

CLAUDE_DIR="$HOME/.claude"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"

mkdir -p "$CLAUDE_DIR"

# Copy statusline script
cp "$REPO_DIR/claude/statusline.sh" "$CLAUDE_DIR/statusline.sh"
chmod +x "$CLAUDE_DIR/statusline.sh"

# Merge statusLine config into settings.json (preserve existing settings)
python3 -c "
import json, os, sys

settings_file = sys.argv[1]

try:
    with open(settings_file) as f:
        settings = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    settings = {}

settings['statusLine'] = {
    'type': 'command',
    'command': 'bash ~/.claude/statusline.sh'
}

with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)
    f.write('\n')
" "$SETTINGS_FILE"

echo "Claude Code statusline installed."
