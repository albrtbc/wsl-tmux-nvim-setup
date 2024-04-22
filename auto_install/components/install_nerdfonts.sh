#!/bin/sh
set -u
set -e
set -x

# Install NERDFont FiraCode
curl https://raw.githubusercontent.com/albrtbc/wsl-tmux-nvim-setup/main/bin/nerdfont-install.sh -sSf | sh
