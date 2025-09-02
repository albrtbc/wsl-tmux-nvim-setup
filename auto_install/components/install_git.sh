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

# Clone wsl-tmux-nvim-setup
git clone https://github.com/albrtbc/wsl-tmux-nvim-setup.git /tmp/wsl-tmux-nvim-setup

# Move git config files
cp /tmp/wsl-tmux-nvim-setup/.gitconfig ~/.gitconfig

# Install github cli
sudo apt update
sudo apt install -y curl gnupg
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null
sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install -y gh
#(type -p wget >/dev/null || (sudo apt update && sudo apt install wget -y)) \
	#&& sudo mkdir -p -m 755 /etc/apt/keyrings \
	#&& out=$(mktemp) && wget -nv -O$out https://cli.github.com/packages/githubcli-archive-keyring.gpg \
	#&& cat $out | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
	#&& sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
	#&& sudo mkdir -p -m 755 /etc/apt/sources.list.d \
	#&& echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
	#&& sudo apt update \
	#&& sudo apt install gh -y

# Move git scripts
mkdir -p ~/.git-scripts/
cp /tmp/wsl-tmux-nvim-setup/.git-scripts/* ~/.git-scripts/
chmod -R +x ~/.git-scripts/
