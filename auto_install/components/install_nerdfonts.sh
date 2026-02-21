#!/bin/sh
set -u
set -e
set -x

REPO_DIR="${REPO_DIR:-/tmp/wsl-tmux-nvim-setup}"

# Install NERDFont FiraCode using local script
bash "$REPO_DIR/bin/nerdfont-install.sh"
