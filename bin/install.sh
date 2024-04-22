#!/bin/sh
set -u
set -e
set -x

sudo apt install git python3

# Clone wsl-tmux-nvim-setup
git clone https://github.com/albrtbc/wsl-tmux-nvim-setup.git /tmp/wsl-tmux-nvim-setup

# Move files
mkdir -p ~/bin
cp -r ~/wsl-tmux-nvim-setup/auto_install ~/bin/
chmod +x ~/bin/auto_install/main.py

# Add to PATH
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
echo 'alias gasbo="python3 ~/bin/auto_install/main.py"' >> ~/.bashrc

# Clean up
echo "Cleaning up..."
rm -rf /tmp/wsl-tmux-nvim-setup

# Execute Install
echo "Installing..."
python3 ~/bin/auto_install/main.py
