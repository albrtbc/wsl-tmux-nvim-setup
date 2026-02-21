#!/bin/sh
set -u
set -e
set -x

REPO_DIR="${REPO_DIR:-/tmp/wsl-tmux-nvim-setup}"

# Install yazi
sudo apt update
sudo apt install -y build-essential
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
. "$HOME/.cargo/env"
cargo install --locked yazi-fm yazi-cli

# Move yazi config files
mkdir -p ~/.config/yazi/
cp -r "$REPO_DIR/yazi/"* ~/.config/yazi/
