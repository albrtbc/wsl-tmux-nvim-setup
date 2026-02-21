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
cp /tmp/wsl-tmux-nvim-setup/auto_install/main.py ~/bin/auto_install/
chmod +x ~/bin/auto_install/main.py
mkdir -p ~/.config/auto_install/
cp -r /tmp/wsl-tmux-nvim-setup/auto_install/components/ ~/.config/auto_install/
cp /tmp/wsl-tmux-nvim-setup/auto_install/components.json ~/.config/auto_install/

# Add to PATH (append only if not already present)
grep -qxF 'export PATH="$HOME/bin:$PATH"' ~/.bashrc || echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
grep -qxF 'alias gasbo="python3 ~/bin/auto_install/main.py"' ~/.bashrc || echo 'alias gasbo="python3 ~/bin/auto_install/main.py"' >> ~/.bashrc

# Set PATH for current session (avoid sourcing .bashrc which exits on non-interactive shells)
export PATH="$HOME/bin:$PATH"

python3 ~/bin/auto_install/main.py
