#!/bin/bash
set -u
set -e
set -x

# Clean up
cleanup() {
    echo "Cleaning up..."
    rm -rf /tmp/wsl-tmux-nvim-setup
}

trap cleanup EXIT INT TERM

sudo apt install git python3

# Clone wsl-tmux-nvim-setup
git clone https://github.com/albrtbc/wsl-tmux-nvim-setup.git /tmp/wsl-tmux-nvim-setup

# Move files
mkdir -p ~/bin/auto_install/
cp ~/wsl-tmux-nvim-setup/auto_install/main.py ~/bin/auto_install/
chmod +x ~/bin/auto_install/main.py
mkdir -p ~/.config/auto_install/
cp -r ~/wsl-tmux-nvim-setup/auto_install/components/ ~/.config/auto_install/
cp ~/wsl-tmux-nvim-setup/auto_install/components.json ~/.config/auto_install/

# Add to PATH
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
echo 'alias gasbo="python3 ~/bin/auto_install/main.py"' >> ~/.bashrc

# Source .bashrc
. ~/.bashrc

python3 ~/bin/auto_install/main.py
