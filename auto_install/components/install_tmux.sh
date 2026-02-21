#!/bin/sh
set -u
set -e
set -x

REPO_DIR="${REPO_DIR:-/tmp/wsl-tmux-nvim-setup}"

# Move tmux config files
cp "$REPO_DIR/.tmux.conf" ~/.tmux.conf

# Install Tmux TPM
mkdir -p ~/.tmux/plugins
rm -rf ~/.tmux/plugins/tpm
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
~/.tmux/plugins/tpm/scripts/install_plugins.sh
