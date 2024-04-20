#!/bin/sh
set -u
set -e
set -x

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

# Install lazygit
LAZYGIT_VERSION=$(curl -s "https://api.github.com/repos/jesseduffield/lazygit/releases/latest" | grep -Po '"tag_name": "v\K[^"]*')
curl -Lo lazygit.tar.gz "https://github.com/jesseduffield/lazygit/releases/latest/download/lazygit_${LAZYGIT_VERSION}_Linux_x86_64.tar.gz"
tar xf lazygit.tar.gz lazygit
sudo install lazygit /usr/local/bin
rm -rf lazygit lazygit.tar.gz

# Install yazi
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
sudo apt install -y cargo
cargo install --locked yazi-fm

# Install NERDFonts
./nerdfont-install.sh

# Install Synth Shell
git clone --recursive https://github.com/andresgongora/synth-shell.git
cd synth-shell
./setup.sh
cd ..
rm -rf synth-shell

# Clone wsl-tmux-nvim-setup
git clone https://github.com/albrtbc/wsl-tmux-nvim-setup.git ~/wsl-tmux-nvim-setup

# Move bash / tmux / git / kitty / synth-shell config files
cp ~/wsl-tmux-nvim-setup/.gitconfig ~/.gitconfig
cp ~/wsl-tmux-nvim-setup/.bashrc ~/.bashrc
cp ~/wsl-tmux-nvim-setup/.tmux.conf ~/.tmux.conf
cp ~/wsl-tmux-nvim-setup/synth-shell/* ~/.config/synth-shell/
if [ -z "$WSL_DISTRO_NAME" ]; then
    mkdir -p ~/.config/kitty/
    cp ~/wsl-tmux-nvim-setup/kitty.conf ~/.config/kitty/kitty.conf
    gsettings set org.gnome.desktop.default-applications.terminal exec 'kitty'
fi

# Install NERDFont FiraCode
curl -sSfL https://raw.githubusercontent.com/ryanoasis/nerd-fonts/master/install.sh | bash -s -- FiraCode

# Install Tmux TPM
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
source ~/. tmux. conf
~/.tmux/plugins/tpm/scripts/install_plugins.sh

# Move git scripts
mkdir -p ~/.git-scripts/
cp ~/wsl-tmux-nvim-setup/.git-scripts/* ~/.git-scripts/
chmod -R +x ~/.git-scripts/

# Install kickstart nvim
#mkdir ~/.nvim/undodir
mkdir ~/.config/nvim
#mv ~/wsl-tmux-nvim-setup/nvim/* ~/.config/nvim/
#echo "Syncing neovim packages! PackerSync:"
#nvim +"PackerSync" +qall
git clone https://github.com/albrtbc/kickstart.nvim.git "${XDG_CONFIG_HOME:-$HOME/.config}"/nvim
nvim

# Clean up
rm -rf ~/wsl-tmux-nvim-setup
