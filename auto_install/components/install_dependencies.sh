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
            echo "  --dry-run: Show what would be installed without actually installing"
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
    echo "[DRY RUN] Would install system dependencies"
    echo "[DRY RUN] Would add neovim PPA"
    echo "[DRY RUN] Would add NodeJS repository"
    echo "[DRY RUN] Would install: make gcc ripgrep unzip git tmux neovim nodejs"
    echo "[DRY RUN] Would install git-delta"
    exit 0
fi

# Install dependencies
# https://github.com/nvim-lua/kickstart.nvim#Install-Recipes
sudo apt update
sudo apt install -y software-properties-common
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
cp /tmp/wsl-tmux-nvim-setup/.gitignore_global ~/.gitignore_global
cp /tmp/wsl-tmux-nvim-setup/.bashrc ~/.bashrc
