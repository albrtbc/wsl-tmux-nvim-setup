#!/bin/sh
set -u
set -e
set -x

# Clone wsl-tmux-nvim-setup
git clone https://github.com/albrtbc/wsl-tmux-nvim-setup.git /tmp/wsl-tmux-nvim-setup

# Move tmux config files
cp /tmp/wsl-tmux-nvim-setup/.tmux.conf ~/.tmux.conf

# Install Tmux TPM
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
source ~/. tmux. conf
~/.tmux/plugins/tpm/scripts/install_plugins.sh

# Clean up
rm -rf /tmp/wsl-tmux-nvim-setup
