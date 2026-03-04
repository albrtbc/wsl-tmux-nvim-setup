#!/usr/bin/env bash
# Claude Code status line (Linux/WSL)
# Format: ❯ path │ ⎇ git:(branch) ↑N ↓N ~N │ 🧠 [5h:XX% wk:XX% ctx:XX%]
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
STEEL_BLUE='\033[38;5;67m'
LAVENDER='\033[38;5;140m'
TEAL='\033[38;5;73m'
PALE_ORANGE='\033[38;5;180m'

SEP="${DIM} │ ${RST}"

# Color a percentage by usage level: <=60 green, 61-74 yellow, 75-89 orange, 90+ red
# Args: <display_value> <used_pct>
color_pct() {
  local val=$1 used=$2
  if   (( used <= 60 )); then printf "${GREEN}%d%%${RST}"  "$val"
  elif (( used <= 74 )); then printf "${YELLOW}%d%%${RST}" "$val"
  elif (( used <= 89 )); then printf "${ORANGE}%d%%${RST}" "$val"
  else                        printf "${RED}%d%%${RST}"    "$val"
  fi
}

# --- Read stdin JSON (session data from Claude Code) ---
input=$(cat)

read -r cwd ctx_pct < <(printf '%s' "$input" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    cwd = d.get('workspace', {}).get('current_dir', '') or d.get('cwd', '')
    ctx = int(d.get('context_window', {}).get('used_percentage', 0) or 0)
    print(f'{cwd} {ctx}')
except:
    print('. 0')
" 2>/dev/null) || { cwd=""; ctx_pct="0"; }
[[ -z "$cwd" || "$cwd" == "." ]] && cwd="$(pwd)"

# Shorten cwd: replace $HOME with ~
short_cwd="${cwd/#$HOME/\~}"

# --- Git branch + sync status ---
git_part=""
if branch=$(git -C "$cwd" rev-parse --abbrev-ref HEAD 2>/dev/null); then
  git_part="${SEP}${STEEL_BLUE}⎇ git:${RST}${LAVENDER}(${branch})${RST}"

  # Ahead/behind remote (single git call)
  upstream=$(git -C "$cwd" rev-parse --abbrev-ref '@{upstream}' 2>/dev/null) || upstream=""
  if [[ -n "$upstream" ]]; then
    lr=$(git -C "$cwd" rev-list --count --left-right '@{upstream}...HEAD' 2>/dev/null) || lr=""
    if [[ -n "$lr" ]]; then
      behind=${lr%%$'\t'*}
      ahead=${lr##*$'\t'}
      [[ "$ahead" -gt 0 ]] && git_part+=" ${PALE_ORANGE}↑${ahead}${RST}"
      [[ "$behind" -gt 0 ]] && git_part+=" ${PALE_ORANGE}↓${behind}${RST}"
    fi
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
except:
    print('')
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
  now=${EPOCHSECONDS:-$(date +%s)}
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
except:
    sys.exit(0)

if d.get('_rate_limited'):
    print('')
    sys.exit(0)

fh = d.get('five_hour') or {}
sd = d.get('seven_day') or {}
fv = round(fh['utilization']) if 'utilization' in fh else ''
sv = round(sd['utilization']) if 'utilization' in sd else ''
print(f'{fv} {sv}')
" "$raw" 2>/dev/null) || true
fi

# --- Assemble output ---
out=""
out+="${CYAN}${BOLD}❯${RST} ${YELLOW}${short_cwd}${RST}"
out+="${git_part}"

# Build bracket contents
bracket_items=""

if [[ -n "$five_h" && "$five_h" -gt 0 ]] 2>/dev/null; then
  bracket_items+="${TEAL}5h:${RST}$(color_pct "$five_h" "$five_h")"
fi

if [[ -n "$seven_d" && "$seven_d" -gt 0 ]] 2>/dev/null; then
  [[ -n "$bracket_items" ]] && bracket_items+=" "
  bracket_items+="${TEAL}wk:${RST}$(color_pct "$seven_d" "$seven_d")"
fi

[[ -n "$bracket_items" ]] && bracket_items+=" "
bracket_items+="${TEAL}ctx:${RST}$(color_pct "$ctx_pct" "$ctx_pct")"

out+="${SEP}🧠 ${DIM}[${RST}${bracket_items}${DIM}]${RST}"

printf '%b\n' "$out"
