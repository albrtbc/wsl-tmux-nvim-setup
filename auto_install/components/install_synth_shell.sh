#!/bin/sh
set -u
set -e
set -x

REPO_DIR="${REPO_DIR:-/tmp/wsl-tmux-nvim-setup}"

# Install Synth Shell
rm -rf /tmp/synth-shell
git clone --recursive https://github.com/andresgongora/synth-shell.git /tmp/synth-shell
cd /tmp/synth-shell
./setup.sh
cd /tmp
rm -rf /tmp/synth-shell

# Move synth-shell config files
mkdir -p ~/.config/synth-shell/
cp "$REPO_DIR/synth-shell/"* ~/.config/synth-shell/
