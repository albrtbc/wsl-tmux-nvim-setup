#!/bin/bash
# Automatic update checker for WSL-Tmux-Nvim-Setup
# Can be run via cron for periodic checks

REPO_URL="https://github.com/albrtbc/wsl-tmux-nvim-setup.git"
UPDATE_SCRIPT="$HOME/dev/wsl-tmux-nvim-setup/bin/update.sh"
LAST_CHECK_FILE="$HOME/.config/wsl-tmux-nvim-setup/last-update-check"
LOG_FILE="$HOME/.config/wsl-tmux-nvim-setup/update.log"

# Create config directory if it doesn't exist
mkdir -p "$(dirname "$LAST_CHECK_FILE")"

log_with_timestamp() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

check_for_updates() {
    log_with_timestamp "Checking for updates..."
    
    # Get remote commit hash
    REMOTE_COMMIT=$(git ls-remote "$REPO_URL" HEAD 2>/dev/null | cut -f1)
    
    if [ -z "$REMOTE_COMMIT" ]; then
        log_with_timestamp "ERROR: Could not fetch remote commit hash"
        return 1
    fi
    
    # Check if we have a record of the last update
    if [ -f "$LAST_CHECK_FILE" ]; then
        LAST_COMMIT=$(cat "$LAST_CHECK_FILE")
        if [ "$REMOTE_COMMIT" = "$LAST_COMMIT" ]; then
            log_with_timestamp "No updates available"
            return 1
        fi
    fi
    
    log_with_timestamp "Updates available! Remote commit: $REMOTE_COMMIT"
    return 0
}

notify_user() {
    # Create notification file
    cat > "$HOME/.config/wsl-tmux-nvim-setup/update-available" << EOF
Updates available for WSL-Tmux-Nvim-Setup!

Run the following command to update:
  $(realpath "$UPDATE_SCRIPT")

Or add to your .bashrc for easy access:
  alias update-configs="$(realpath "$UPDATE_SCRIPT")"

Last check: $(date)
EOF
    
    log_with_timestamp "Update notification created"
    
    # Show notification if running interactively
    if [ -t 1 ]; then
        echo "🔄 WSL-Tmux-Nvim-Setup updates are available!"
        echo "Run: $UPDATE_SCRIPT"
    fi
}

auto_update() {
    if [ "$AUTO_UPDATE" = "true" ]; then
        log_with_timestamp "Auto-update enabled, applying updates..."
        "$UPDATE_SCRIPT"
        
        if [ $? -eq 0 ]; then
            # Record successful update
            echo "$REMOTE_COMMIT" > "$LAST_CHECK_FILE"
            rm -f "$HOME/.config/wsl-tmux-nvim-setup/update-available"
            log_with_timestamp "Auto-update completed successfully"
        else
            log_with_timestamp "Auto-update failed"
        fi
    else
        notify_user
    fi
}

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --auto-update)
                AUTO_UPDATE="true"
                shift
                ;;
            --silent)
                exec > /dev/null 2>&1
                shift
                ;;
            *)
                echo "Usage: $0 [--auto-update] [--silent]"
                echo "  --auto-update  Automatically apply updates if available"
                echo "  --silent       Run silently (useful for cron)"
                exit 1
                ;;
        esac
    done
    
    if check_for_updates; then
        auto_update
    fi
}

main "$@"