# wsl-tmux-nvim-setup

Interactive installer for my WSL/Linux dev environment. Select which components to install from a curses TUI, and the installer handles dependencies, ordering, and idempotency automatically.

## Quick start

```bash
curl -O https://raw.githubusercontent.com/albrtbc/wsl-tmux-nvim-setup/main/bin/install.sh
chmod +x install.sh
./install.sh
rm -rf install.sh && reset
```

## Components

| Component | Description |
|-----------|-------------|
| Dependencies | Base packages: neovim, ripgrep, node, build tools |
| Lazygit | Terminal UI for git |
| Yazi | Terminal file manager |
| NERDFonts | FiraCode Nerd Font |
| Synth Shell | Fancy shell prompt |
| Tmux | Terminal multiplexer + TPM plugins |
| Neovim | Neovim config with Lazy plugin manager |
| Kitty | Kitty terminal config |
| Git | Git global config |

Dependencies between components are declared in `components.json` and resolved automatically. For example, selecting Neovim will auto-include Dependencies and NERDFonts.

## Usage

After installation, re-run the installer anytime with:

```bash
python3 ~/bin/auto_install/main.py
```

Already-installed components are skipped. Use `--force` to reinstall everything:

```bash
python3 ~/bin/auto_install/main.py --force
```

## Project structure

```
bin/install.sh              # Bootstrap script (curl entry point)
auto_install/
  main.py                   # Curses TUI + install orchestration
  components.json           # Component registry with dependencies
  components/               # Standalone bash install scripts
    install_dependencies.sh
    install_lazygit.sh
    install_yazi.sh
    ...
```
