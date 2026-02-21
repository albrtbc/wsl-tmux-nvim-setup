#!/bin/sh
set -u
set -e
set -x

REPO_DIR="${REPO_DIR:-/tmp/wsl-tmux-nvim-setup}"

# Install dependencies
# https://github.com/nvim-lua/kickstart.nvim#Install-Recipes
sudo add-apt-repository ppa:neovim-ppa/unstable -y
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt update
sudo apt install -y make gcc ripgrep unzip git tmux neovim nodejs

# Install ubuntu dependencies
if [ -z "${WSL_DISTRO_NAME:-}" ]; then
    sudo apt install -y kitty xclip
fi

# Install git-delta
curl -s -L https://api.github.com/repos/dandavison/delta/releases/latest | grep "browser_download_url.*amd64.deb" | cut -d : -f 2,3 | tr -d \" | wget -qi - -P /tmp
sudo dpkg -i /tmp/git-delta_*_amd64.deb
rm -f /tmp/git-delta_*_amd64.deb

# Move bash config files
cp "$REPO_DIR/.gitconfig" ~/.gitconfig
cp "$REPO_DIR/.gitignore_global" ~/.gitignore_global
cp "$REPO_DIR/.bashrc" ~/.bashrc
