#!/bin/sh
set -u
set -e
set -x

# Install yazi
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
sudo apt install -y cargo
cargo install --locked yazi-fm

git clone https://github.com/albrtbc/wsl-tmux-nvim-setup.git /tmp/wsl-tmux-nvim-setup
cp -r /tmp/wsl-tmux-nvim-setup/yazi/* ~/.config/yazi/

# Clean up
rm -rf /tmp/wsl-tmux-nvim-setup
