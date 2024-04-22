#!/bin/sh
set -u
set -e
set -x

# Install Synth Shell
git clone --recursive https://github.com/andresgongora/synth-shell.git
cd synth-shell
./setup.sh
cd ..
rm -rf synth-shell

# Clone wsl-tmux-nvim-setup
git clone https://github.com/albrtbc/wsl-tmux-nvim-setup.git /tmp/wsl-tmux-nvim-setup

cp /tmp/wsl-tmux-nvim-setup/synth-shell/* ~/.config/synth-shell/

# Clean up
rm -rf /tmp/wsl-tmux-nvim-setup
