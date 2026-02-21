#!/bin/sh
set -u
set -e
set -x

REPO_DIR="${REPO_DIR:-/tmp/wsl-tmux-nvim-setup}"

# Install Kitty (only on native Linux, not WSL)
if [ -z "${WSL_DISTRO_NAME:-}" ]; then
    mkdir -p ~/.config/kitty/
    cp "$REPO_DIR/kitty.conf" ~/.config/kitty/kitty.conf
    # Set as default terminal if gsettings is available (GNOME)
    if command -v gsettings > /dev/null 2>&1; then
        gsettings set org.gnome.desktop.default-applications.terminal exec 'kitty'
    fi
fi
