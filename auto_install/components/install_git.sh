#!/bin/sh
set -u
set -e
set -x

# Clone wsl-tmux-nvim-setup
git clone https://github.com/albrtbc/wsl-tmux-nvim-setup.git /tmp/wsl-tmux-nvim-setup

# Move git config files
cp /tmp/wsl-tmux-nvim-setup/.gitconfig ~/.gitconfig

# Move git scripts
mkdir -p ~/.git-scripts/
cp /tmp/wsl-tmux-nvim-setup/.git-scripts/* ~/.git-scripts/
chmod -R +x ~/.git-scripts/

# Clean up
rm -rf /tmp/wsl-tmux-nvim-setup
