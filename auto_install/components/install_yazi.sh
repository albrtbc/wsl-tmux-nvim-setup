#!/bin/sh
set -u
set -e
set -x

# Clean up
cleanup() {
    echo "Cleaning up..."
    rm -rf /tmp/wsl-tmux-nvim-setup
}

trap cleanup EXIT INT TERM

# Install yazi
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
sudo apt install -y cargo
cargo install --locked yazi-fm

git clone https://github.com/albrtbc/wsl-tmux-nvim-setup.git /tmp/wsl-tmux-nvim-setup
cp -r /tmp/wsl-tmux-nvim-setup/yazi/* ~/.config/yazi/
