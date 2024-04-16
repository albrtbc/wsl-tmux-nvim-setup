#!/bin/sh
set -u
set -e
set -x

# Install dependencies
sudo apt-get update
sudo apt-get install -y neovim git tmux unzip kitty

# Install Synth Shell
wget https://github.com/andresgongora/synth-shell/raw/master/setup.sh
chmod +x setup.sh
./setup.sh

# Clone vim-complex-sensible
git clone https://github.com/albrtbc/vim-complex-sensible.git ~/vim-complex-sensible

# Move neovim / bash / tmux / git / kitty / synth-shell config files
mv ~/vim-complex-sensible/.gitconfig ~/.gitconfig
mv ~/vim-complex-sensible/.bashrc ~/.bashrc
mv ~/vim-complex-sensible/.tmux.conf ~/.tmux.conf
mkdir -p ~/.conf/kitty/
mv ~/vim-complex-sensible/kitty.conf ~/.conf/kitty/kitty.conf
mv ~/vim-complex-sensible/synth-shell/* ~/.conf/synth-shell/*

# Move git scripts
mkdir -p ~/.git-scripts/
mv ~/vim-complex-sensible/.git-scripts/* ~/.git-scripts/
chmod -R +x ~/.git-scripts/

# Install neovim plugins
mkdir ~/.nvim/undodir
mkdir ~/.config/nvim
mv ~/vim-complex-sensible/nvim/* ~/.config/nvim/
echo "Syncing neovim packages! PackerSync:"
nvim +"PackerSync" +qall

# Clean up
rm -rf ~/vim-complex-sensible

