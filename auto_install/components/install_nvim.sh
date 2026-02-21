#!/bin/sh
set -u
set -e
set -x

# Install kickstart nvim
mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}"
rm -rf "${XDG_CONFIG_HOME:-$HOME/.config}"/nvim
git clone https://github.com/albrtbc/kickstart.nvim.git "${XDG_CONFIG_HOME:-$HOME/.config}"/nvim
nvim --headless "+Lazy! sync" +qa
