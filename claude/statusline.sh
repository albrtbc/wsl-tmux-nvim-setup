#!/usr/bin/env bash
# Claude Code status line
# Format: ❯ path │  git:(branch) │ 🧠 [5h:XX% wk:XX% ctx:XX%]
# Usage API cached for 2 minutes.

set -euo pipefail

CREDENTIALS_FILE="$HOME/.claude/.credentials.json"
CACHE_FILE="/tmp/claude-usage-cache.json"
CACHE_MAX_AGE=120

# --- Colors ---
RST='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'
CYAN='\033[36m'
GREEN='\033[32m'
YELLOW='\033[33m'
ORANGE='\033[38;5;208m'
RED='\033[31m'
MAGENTA='\033[35m'
BLUE='\033[34m'
STEEL_BLUE='\033[38;5;67m'
LAVENDER='\033[38;5;140m'
TEAL='\033[38;5;73m'
PALE_ORANGE='\033[38;5;180m'
WHITE='\033[37m'

SEP="${DIM} │ ${RST}"

# Color by usage thresholds: <60 green, 61-74 yellow, 75-89 orange, 90-100 red
# Input is "used" percentage (higher = worse)
color_used() {
  local pct=$1
  if (( pct <= 60 )); then
    printf "${GREEN}%d%%${RST}" "$pct"
  elif (( pct <= 74 )); then
    printf "${YELLOW}%d%%${RST}" "$pct"
  elif (( pct <= 89 )); then
    printf "${ORANGE}%d%%${RST}" "$pct"
  else
    printf "${RED}%d%%${RST}" "$pct"
  fi
}

# For API windows: input is "remaining" %, so invert for color
# remaining 40% = used 60% → green boundary
color_remaining() {
  local remaining=$1
  local used=$(( 100 - remaining ))
  if (( used <= 60 )); then
    printf "${GREEN}%d%%${RST}" "$remaining"
  elif (( used <= 74 )); then
    printf "${YELLOW}%d%%${RST}" "$remaining"
  elif (( used <= 89 )); then
    printf "${ORANGE}%d%%${RST}" "$remaining"
  else
    printf "${RED}%d%%${RST}" "$remaining"
  fi
}

# --- Read stdin JSON (session data from Claude Code) ---
input=$(cat)

cwd=$(printf '%s' "$input" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('workspace', {}).get('current_dir', '') or d.get('cwd', ''))
except: print('')
" 2>/dev/null) || cwd=""
[[ -z "$cwd" ]] && cwd="$(pwd)"

ctx_pct=$(printf '%s' "$input" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(int(d.get('context_window', {}).get('used_percentage', 0) or 0))
except: print('0')
" 2>/dev/null) || ctx_pct="0"

# Shorten cwd: replace $HOME with ~
short_cwd="${cwd/#$HOME/\~}"

# --- Git branch + sync status ---
git_part=""
if branch=$(git -C "$cwd" rev-parse --abbrev-ref HEAD 2>/dev/null); then
  git_part="${SEP}${STEEL_BLUE}⎇ git:${RST}${LAVENDER}(${branch})${RST}"

  # Ahead/behind remote
  upstream=$(git -C "$cwd" rev-parse --abbrev-ref '@{upstream}' 2>/dev/null) || upstream=""
  if [[ -n "$upstream" ]]; then
    ahead=$(git -C "$cwd" rev-list --count '@{upstream}..HEAD' 2>/dev/null) || ahead=0
    behind=$(git -C "$cwd" rev-list --count 'HEAD..@{upstream}' 2>/dev/null) || behind=0
    sync=""
    [[ "$ahead" -gt 0 ]] && sync+=" ${PALE_ORANGE}↑${ahead}${RST}"
    [[ "$behind" -gt 0 ]] && sync+=" ${PALE_ORANGE}↓${behind}${RST}"
    git_part+="${sync}"
  fi

  # Dirty file count
  dirty=$(git -C "$cwd" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$dirty" -gt 0 ]]; then
    git_part+=" ${PALE_ORANGE}~${dirty}${RST}"
  fi
fi

# --- Usage API with 2-minute cache ---
fetch_usage() {
  [[ ! -f "$CREDENTIALS_FILE" ]] && return

  local token
  token=$(python3 -c "
import json, sys
try:
    print(json.load(open(sys.argv[1]))['claudeAiOauth']['accessToken'])
except: print('')
" "$CREDENTIALS_FILE" 2>/dev/null) || true
  [[ -z "$token" ]] && return

  local tmp
  tmp=$(mktemp)
  local code
  code=$(curl -s --max-time 5 -o "$tmp" -w "%{http_code}" \
    -H "Authorization: Bearer $token" \
    -H "anthropic-beta: oauth-2025-04-20" \
    -H "Content-Type: application/json" \
    "https://api.anthropic.com/api/oauth/usage" 2>/dev/null) || code="000"

  if [[ "$code" == "200" ]]; then
    cat "$tmp"
  elif [[ "$code" == "429" ]]; then
    echo '{"_rate_limited":true}'
  fi
  rm -f "$tmp" 2>/dev/null
}

# Check cache freshness
use_cache=false
if [[ -f "$CACHE_FILE" ]]; then
  now=$(date +%s)
  mtime=$(stat -c %Y "$CACHE_FILE" 2>/dev/null || echo 0)
  if (( now - mtime < CACHE_MAX_AGE )); then
    use_cache=true
  fi
fi

raw=""
if $use_cache; then
  raw=$(cat "$CACHE_FILE" 2>/dev/null)
else
  raw=$(fetch_usage)
  [[ -n "$raw" ]] && printf '%s' "$raw" > "$CACHE_FILE"
fi

# --- Parse usage ---
five_h=""
seven_d=""
if [[ -n "$raw" ]]; then
  read -r five_h seven_d < <(python3 -c "
import json, sys
try:
    d = json.loads(sys.argv[1])
except: sys.exit(0)

if d.get('_rate_limited'):
    print('')
    sys.exit(0)

fh = d.get('five_hour') or {}
sd = d.get('seven_day') or {}
fv = max(0, 100 - int(fh['utilization'])) if 'utilization' in fh else ''
sv = max(0, 100 - int(sd['utilization'])) if 'utilization' in sd else ''
print(f'{fv} {sv}')
" "$raw" 2>/dev/null) || true
fi

# --- Assemble: ❯ path │  git:(branch) │ 🧠 [5h:XX% wk:XX% ctx:XX%] ---
out=""
out+="${CYAN}${BOLD}❯${RST} ${YELLOW}${short_cwd}${RST}"
out+="${git_part}"

# Build bracket contents
bracket_items=""

if [[ -n "$five_h" && "$five_h" -gt 0 ]] 2>/dev/null; then
  bracket_items+="${TEAL}5h:${RST}$(color_remaining "$five_h")"
fi

if [[ -n "$seven_d" && "$seven_d" -gt 0 ]] 2>/dev/null; then
  [[ -n "$bracket_items" ]] && bracket_items+=" "
  bracket_items+="${TEAL}wk:${RST}$(color_remaining "$seven_d")"
fi

[[ -n "$bracket_items" ]] && bracket_items+=" "
bracket_items+="${TEAL}ctx:${RST}$(color_used "$ctx_pct")"

out+="${SEP}🧠 ${DIM}[${RST}${bracket_items}${DIM}]${RST}"

printf '%b\n' "$out"
