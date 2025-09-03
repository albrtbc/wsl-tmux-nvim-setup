# WSL Tmux Neovim Development Environment

A complete development environment setup for WSL (Windows Subsystem for Linux) featuring tmux, Neovim (Kickstart.nvim), Yazi file manager, LazyGit, and optimized shell configurations.

## Quick Installation

```bash
curl -O https://raw.githubusercontent.com/albrtbc/wsl-tmux-nvim-setup/main/bin/install.sh
chmod +x install.sh
./install.sh
rm -rf install.sh && reset
```

## Features

- **Shell**: Optimized Bash with custom functions and aliases
- **Terminal Multiplexer**: tmux with Nova theme and vim-like keybindings
- **Editor**: Neovim with Kickstart.nvim configuration
- **File Manager**: Yazi with custom themes and shell integration
- **Git UI**: LazyGit with custom commands and workflows
- **Version Control**: Git with delta diff viewer and custom scripts
- **Auto-Update System**: Keep configurations synchronized across machines

## Documentation

- **[Auto-Update Guide](./Auto-Update-Guide.md)** - Complete auto-update system setup
- **[Yazi File Manager Guide](./Yazi-File-Manager-Guide.md)** - Comprehensive Yazi documentation

## Key Components

### Shell Configuration
- Custom aliases and functions
- Yazi integration with directory changing
- Git performance optimization for WSL
- Windows integration (Explorer, git.exe)

### Tmux Setup
- Prefix: `Ctrl-a`
- Vim-style pane navigation
- Nova theme with nerdfonts
- Session persistence

### Neovim (Kickstart.nvim)
- Leader key: `,` (comma)
- LSP integration
- Telescope fuzzy finder
- Git integration (Fugitive, Gitsigns)
- GitHub Copilot support

### File Management
- Yazi terminal file manager
- Shell integration (`ya` command)
- Rich preview support
- Custom themes and keybindings

## Auto-Update System

Keep your configurations automatically updated:

```bash
# Manual update
./bin/update.sh

# Check for updates
./bin/check-updates.sh

# Update from releases
./bin/update-from-release.sh
```

See [Auto-Update-Guide.md](./Auto-Update-Guide.md) for complete setup instructions.

## Quick Start

After installation, use these commands to get started:

```bash
# Launch file manager (changes directory on exit)
ya

# Open LazyGit
lg  

# Start tmux session
tmux new -s dev

# Open Neovim
vim  # (aliased to nvim)
```

---

*This environment is optimized for WSL2 development with Windows integration.*
