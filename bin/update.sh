#!/bin/bash
# WSL-Tmux-Nvim-Setup Auto Update Script
# Updates configuration files from GitHub repository

set -e

REPO_URL="https://github.com/albrtbc/wsl-tmux-nvim-setup.git"
TEMP_DIR="/tmp/wsl-tmux-nvim-update"
CONFIG_DIR="$HOME/.config/wsl-tmux-nvim-setup"
BACKUP_DIR="$HOME/.config/wsl-tmux-nvim-setup/backups/$(date +%Y%m%d_%H%M%S)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

cleanup() {
    log_info "Cleaning up temporary files..."
    rm -rf "$TEMP_DIR"
}

trap cleanup EXIT INT TERM

check_git_updates() {
    log_info "Checking for updates from GitHub..."
    
    # Get current commit hash if we're in a git repo
    if [ -d ".git" ]; then
        LOCAL_COMMIT=$(git rev-parse HEAD)
        REMOTE_COMMIT=$(git ls-remote origin HEAD | cut -f1)
        
        if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
            log_info "Already up to date!"
            return 1
        fi
    fi
    
    return 0
}

backup_current_configs() {
    log_info "Creating backup of current configurations..."
    mkdir -p "$BACKUP_DIR"
    
    # Backup key config files
    [ -f "$HOME/.bashrc" ] && cp "$HOME/.bashrc" "$BACKUP_DIR/"
    [ -f "$HOME/.tmux.conf" ] && cp "$HOME/.tmux.conf" "$BACKUP_DIR/"
    [ -f "$HOME/.gitconfig" ] && cp "$HOME/.gitconfig" "$BACKUP_DIR/"
    [ -d "$HOME/.config/nvim" ] && cp -r "$HOME/.config/nvim" "$BACKUP_DIR/"
    [ -d "$HOME/.config/yazi" ] && cp -r "$HOME/.config/yazi" "$BACKUP_DIR/"
    [ -d "$HOME/.config/lazygit" ] && cp -r "$HOME/.config/lazygit" "$BACKUP_DIR/"
    [ -d "$HOME/.aws-scripts" ] && cp -r "$HOME/.aws-scripts" "$BACKUP_DIR/"
    
    log_success "Backup created at: $BACKUP_DIR"
}

download_latest() {
    log_info "Downloading latest version from GitHub..."
    rm -rf "$TEMP_DIR"
    git clone "$REPO_URL" "$TEMP_DIR"
    log_success "Downloaded latest version"
}

update_configs() {
    log_info "Updating configuration files..."
    
    cd "$TEMP_DIR"
    
    # Update .bashrc (preserve existing, append new functions)
    if [ -f ".bashrc" ]; then
        log_info "Updating .bashrc..."
        # Extract and update specific functions rather than overwrite
        update_bashrc_functions
    fi
    
    # Update .tmux.conf
    if [ -f ".tmux.conf" ]; then
        log_info "Updating .tmux.conf..."
        cp ".tmux.conf" "$HOME/.tmux.conf"
    fi
    
    # Update Neovim config (be careful not to overwrite user customizations)
    if [ -d ".config/nvim" ] && [ ! -d "$HOME/.config/nvim/lua/custom" ]; then
        log_info "Updating Neovim configuration..."
        cp -r ".config/nvim" "$HOME/.config/"
    elif [ -d ".config/nvim" ]; then
        log_warning "Neovim custom config detected, skipping automatic update"
        log_warning "You may need to manually merge changes"
    fi
    
    # Update Yazi config
    if [ -d "yazi" ]; then
        log_info "Updating Yazi configuration..."
        mkdir -p "$HOME/.config/yazi"
        cp -r yazi/* "$HOME/.config/yazi/"
    fi
    
    # Update LazyGit config
    if [ -d "lazygit" ]; then
        log_info "Updating LazyGit configuration..."
        mkdir -p "$HOME/.config/lazygit"
        cp -r lazygit/* "$HOME/.config/lazygit/"
    fi
    
    # Update AWS scripts
    if [ -d "aws-scripts" ]; then
        log_info "Updating AWS scripts..."
        cp -r aws-scripts "$HOME/.aws-scripts"
        chmod +x "$HOME/.aws-scripts"/*.sh
    fi
    
    # Update Synth-shell config
    if [ -d "synth-shell" ]; then
        log_info "Updating Synth-shell configuration..."
        mkdir -p "$HOME/.config/synth-shell"
        cp -r synth-shell/* "$HOME/.config/synth-shell/"
    fi
}

update_bashrc_functions() {
    local temp_bashrc="$HOME/.bashrc.new"
    local current_bashrc="$HOME/.bashrc"
    
    # Create a new .bashrc with updated functions
    cp "$current_bashrc" "$temp_bashrc"
    
    # Update specific functions (ya, git, git_tably)
    # This is a simplified approach - in practice, you'd want more sophisticated merging
    if grep -q "function ya()" "$temp_bashrc"; then
        log_info "Updating ya() function..."
        # Replace the ya function
        sed -i '/^function ya()/,/^}$/c\
# Updated ya function\
function ya() {\
    local tmp="$(mktemp -t "yazi-cwd.XXXXXX")"\
    yazi "$@" --cwd-file="$tmp"\
    if cwd="$(cat -- "$tmp")" && [ -n "$cwd" ] && [ "$cwd" != "$PWD" ]; then\
        cd -- "$cwd"\
    fi\
    rm -f -- "$tmp"\
}' "$temp_bashrc"
    else
        # Append the function if it doesn't exist
        log_info "Adding ya() function..."
        cat >> "$temp_bashrc" << 'EOF'

# Yazi wrapper to cd on exit
function ya() {
    local tmp="$(mktemp -t "yazi-cwd.XXXXXX")"
    yazi "$@" --cwd-file="$tmp"
    if cwd="$(cat -- "$tmp")" && [ -n "$cwd" ] && [ "$cwd" != "$PWD" ]; then
        cd -- "$cwd"
    fi
    rm -f -- "$tmp"
}
EOF
    fi
    
    # Update git function
    if grep -q "function git()" "$temp_bashrc"; then
        log_info "Git function already exists, keeping current version"
    else
        log_info "Adding git performance wrapper..."
        cat >> "$temp_bashrc" << 'EOF'

# Git wrapper for WSL performance
function isWinDir {
  case $PWD/ in
    /mnt/*) return $(true);;
    *) return $(false);;
  esac
}

function git {
  if isWinDir
  then
    git.exe "$@"
  else
    /usr/bin/git "$@"
  fi
}
EOF
    fi
    
    # Replace the original .bashrc
    mv "$temp_bashrc" "$current_bashrc"
}

reload_configs() {
    log_info "Reloading configurations..."
    
    # Source .bashrc
    source "$HOME/.bashrc" 2>/dev/null || log_warning "Could not source .bashrc"
    
    # Reload tmux config if tmux is running
    if command -v tmux >/dev/null 2>&1 && tmux list-sessions >/dev/null 2>&1; then
        tmux source-file "$HOME/.tmux.conf" 2>/dev/null || log_warning "Could not reload tmux config"
        log_success "Tmux configuration reloaded"
    fi
}

show_changes() {
    log_info "Update completed! Here's what was updated:"
    echo ""
    echo "Updated configurations:"
    echo "  • Shell configuration (.bashrc)"
    echo "  • Tmux configuration (.tmux.conf)" 
    echo "  • Yazi file manager config"
    echo "  • LazyGit configuration"
    echo "  • AWS scripts"
    echo ""
    echo "Backup location: $BACKUP_DIR"
    echo ""
    log_info "Restart your terminal or run 'source ~/.bashrc' to apply changes"
}

main() {
    log_info "WSL-Tmux-Nvim-Setup Updater v1.0"
    log_info "=================================="
    
    # Check if we need updates
    if ! check_git_updates; then
        exit 0
    fi
    
    # Create backup
    backup_current_configs
    
    # Download and update
    download_latest
    update_configs
    
    # Reload configurations
    reload_configs
    
    # Show summary
    show_changes
    
    log_success "Update completed successfully!"
}

# Parse command line arguments
case "${1:-}" in
    --check-only)
        check_git_updates
        exit $?
        ;;
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo "Options:"
        echo "  --check-only    Check for updates without applying them"
        echo "  --help, -h      Show this help message"
        exit 0
        ;;
    *)
        main
        ;;
esac