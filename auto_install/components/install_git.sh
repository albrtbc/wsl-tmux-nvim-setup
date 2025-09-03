#!/bin/sh
set -u
set -e
set -x

# Parse command line arguments
DRY_RUN=false
for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--dry-run] [--help]"
            echo "  --dry-run: Show what would be configured without actually configuring"
            echo "  --help: Show this help message"
            exit 0
            ;;
    esac
done

# Clean up
cleanup() {
    echo "Cleaning up..."
    if [ "$DRY_RUN" = false ]; then
        rm -rf /tmp/wsl-tmux-nvim-setup
    fi
}

trap cleanup EXIT INT TERM

if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN] Would clone repository and configure git settings"
    echo "[DRY RUN] Would copy .gitconfig and .gitignore_global"
    exit 0
fi

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
