#!/bin/sh
set -u
set -e
set -x

# Install Kitty
if [ -z "$WSL_DISTRO_NAME" ]; then
    # Clone wsl-tmux-nvim-setup
    git clone https://github.com/albrtbc/wsl-tmux-nvim-setup.git /tmp/wsl-tmux-nvim-setup

    mkdir -p ~/.config/kitty/
    cp /tmp/wsl-tmux-nvim-setup/kitty.conf ~/.config/kitty/kitty.conf
    gsettings set org.gnome.desktop.default-applications.terminal exec 'kitty'
    
    # Clean up
    rm -rf /tmp/wsl-tmux-nvim-setup
fi
