#!/bin/sh
set -u
set -e
set -x

# Parse command line arguments
DRY_RUN=false
for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--dry-run] [--help]"
            echo "  --dry-run: Show what would be configured without actually configuring"
            echo "  --help: Show this help message"
            exit 0
            ;;
    esac
done

# Clean up
cleanup() {
    echo "Cleaning up..."
    if [ "$DRY_RUN" = false ]; then
        rm -rf /tmp/wsl-tmux-nvim-setup
    fi
}

trap cleanup EXIT INT TERM

if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN] Would configure tmux with custom settings"
    echo "[DRY RUN] Would copy .tmux.conf"
    exit 0
fi

# Clone wsl-tmux-nvim-setup
git clone https://github.com/albrtbc/wsl-tmux-nvim-setup.git /tmp/wsl-tmux-nvim-setup

# Move tmux config files
cp /tmp/wsl-tmux-nvim-setup/.tmux.conf ~/.tmux.conf

# Install Tmux TPM
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
# shellcheck source=/dev/null
. ~/.tmux.conf
~/.tmux/plugins/tpm/scripts/install_plugins.sh
