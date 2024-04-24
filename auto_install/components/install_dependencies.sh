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

# Install dependencies
# https://github.com/nvim-lua/kickstart.nvim#Install-Recipes
sudo add-apt-repository ppa:neovim-ppa/unstable -y
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt update
sudo apt install -y make gcc ripgrep unzip git tmux unzip neovim nodejs

# Install ubuntu dependencies
if [ -z "$WSL_DISTRO_NAME" ]; then
    sudo apt install -y kitty xclip 
fi

# Install git-delta
curl -s -L https://api.github.com/repos/dandavison/delta/releases/latest | grep "browser_download_url.*amd64.deb" | cut -d : -f 2,3 | tr -d \" | wget -qi -
sudo dpkg -i git-delta_*_amd64.deb
rm *.deb

# Clone wsl-tmux-nvim-setup
git clone https://github.com/albrtbc/wsl-tmux-nvim-setup.git /tmp/wsl-tmux-nvim-setup

# Move bash config files
cp /tmp/wsl-tmux-nvim-setup/.gitconfig ~/.gitconfig
cp /tmp/wsl-tmux-nvim-setup/.bashrc ~/.bashrc
