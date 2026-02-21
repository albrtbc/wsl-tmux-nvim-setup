#!/bin/sh
set -u
set -e
set -x

REPO_DIR="${REPO_DIR:-/tmp/wsl-tmux-nvim-setup}"

# Install github cli
sudo apt update
sudo apt install -y curl gnupg
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null
sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install -y gh

# Copy gitconfig and scripts to WSL home
cp "$REPO_DIR/.gitconfig" ~/.gitconfig
mkdir -p ~/.git-scripts/
cp "$REPO_DIR/.git-scripts/"* ~/.git-scripts/
chmod -R +x ~/.git-scripts/

# Copy gitconfig and scripts to Windows home (for git.exe in /mnt/ paths)
WIN_HOME=$(wslpath "$(cmd.exe /c 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r')") || true
if [ -n "$WIN_HOME" ] && [ -d "$WIN_HOME" ]; then
    cp "$REPO_DIR/.gitconfig" "$WIN_HOME/.gitconfig"
    mkdir -p "$WIN_HOME/.git-scripts/"
    cp "$REPO_DIR/.git-scripts/"* "$WIN_HOME/.git-scripts/"
fi
