# Auto-Update System Guide

## Overview
This repository includes several mechanisms to keep your WSL development environment automatically updated when you push changes to GitHub or create releases.

## Available Update Methods

### 1. Manual Update Script (Recommended)
**File**: `bin/update.sh`

A comprehensive update script that safely updates your configurations with automatic backups.

#### Features
- ✅ Automatic backup of current configurations
- ✅ Smart merging of shell functions (preserves customizations)
- ✅ Selective config updates (skips user-customized files)
- ✅ Automatic reload of configurations
- ✅ Detailed logging and error handling

#### Usage
```bash
# Run update
./bin/update.sh

# Check for updates only
./bin/update.sh --check-only

# Get help
./bin/update.sh --help
```

#### What Gets Updated
- `.bashrc` (shell functions and aliases)
- `.tmux.conf` (tmux configuration)
- Yazi configuration (`~/.config/yazi/`)
- LazyGit configuration (`~/.config/lazygit/`)
- AWS scripts (`~/.aws-scripts/`)
- Synth-shell configuration (`~/.config/synth-shell/`)
- Neovim config (only if no custom modifications detected)

### 2. Automatic Update Checker
**File**: `bin/check-updates.sh`

A lightweight script for periodic update checking, ideal for cron jobs.

#### Features
- ✅ Checks GitHub for new commits
- ✅ Can run silently in background
- ✅ Optional auto-update mode
- ✅ Creates notification files when updates available
- ✅ Detailed logging

#### Usage
```bash
# Check for updates (interactive)
./bin/check-updates.sh

# Check and auto-update if available
./bin/check-updates.sh --auto-update

# Run silently (for cron)
./bin/check-updates.sh --silent
```

#### Setting Up Automatic Checks
Add to your crontab for daily checks:
```bash
# Edit crontab
crontab -e

# Add line for daily check at 9 AM
0 9 * * * /path/to/wsl-tmux-nvim-setup/bin/check-updates.sh --silent
```

For auto-update (use with caution):
```bash
# Auto-update daily at 2 AM
0 2 * * * /path/to/wsl-tmux-nvim-setup/bin/check-updates.sh --auto-update --silent
```

### 3. GitHub Release-Based Updates
**File**: `bin/update-from-release.sh`

Updates from official GitHub releases rather than latest commits.

#### Features
- ✅ Updates from tagged releases only
- ✅ Shows changelog/release notes
- ✅ Version tracking
- ✅ Works with or without GitHub CLI

#### Usage
```bash
# Update from latest release
./bin/update-from-release.sh

# Check latest release version
./bin/update-from-release.sh --check

# Update without confirmation
./bin/update-from-release.sh --yes
```

## Setup Instructions

### 1. Initial Setup
Make the scripts executable and add to your PATH:
```bash
# Make scripts executable
chmod +x bin/update.sh
chmod +x bin/check-updates.sh  
chmod +x bin/update-from-release.sh

# Add to PATH (add to .bashrc)
export PATH="$HOME/dev/wsl-tmux-nvim-setup/bin:$PATH"

# Create convenient aliases (add to .bashrc)
alias update-configs="$HOME/dev/wsl-tmux-nvim-setup/bin/update.sh"
alias check-updates="$HOME/dev/wsl-tmux-nvim-setup/bin/check-updates.sh"
alias update-release="$HOME/dev/wsl-tmux-nvim-setup/bin/update-from-release.sh"
```

### 2. Enable Update Notifications
Add to your `.bashrc` to check for updates on shell startup:
```bash
# Check for config updates on shell start (silent, non-blocking)
if [ -f "$HOME/dev/wsl-tmux-nvim-setup/bin/check-updates.sh" ]; then
    "$HOME/dev/wsl-tmux-nvim-setup/bin/check-updates.sh" --silent &
fi

# Show update notification if available
if [ -f "$HOME/.config/wsl-tmux-nvim-setup/update-available" ]; then
    cat "$HOME/.config/wsl-tmux-nvim-setup/update-available"
    echo ""
fi
```

### 3. Advanced: GitHub Actions Integration
For automatic deployment to multiple machines, you can use GitHub Actions:

Create `.github/workflows/auto-deploy.yml`:
```yaml
name: Auto Deploy Configs

on:
  push:
    branches: [ main ]
  release:
    types: [ published ]

jobs:
  notify-update:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger update notification
        run: |
          # This could send notifications to your machines
          # via webhook, Slack, email, etc.
          echo "New version available: ${{ github.sha }}"
```

## Best Practices

### For Development
1. **Test changes locally** before pushing to main branch
2. **Use feature branches** for experimental changes  
3. **Create releases** for stable versions
4. **Document breaking changes** in commit messages

### For Updates
1. **Always backup** before major updates (done automatically)
2. **Review changes** before applying auto-updates
3. **Test critical functions** after updates (tmux, nvim, etc.)
4. **Keep a recovery plan** (know how to restore from backups)

### Security Considerations
1. **Review scripts** before running (especially with auto-update)
2. **Use HTTPS** for GitHub cloning (avoid SSH in automated scripts)
3. **Limit auto-update scope** (don't auto-update critical system files)
4. **Monitor update logs** for suspicious activity

## Troubleshooting

### Update Script Issues
```bash
# Check update logs
tail -f ~/.config/wsl-tmux-nvim-setup/update.log

# Restore from backup
cp ~/.config/wsl-tmux-nvim-setup/backups/YYYYMMDD_HHMMSS/.bashrc ~/.bashrc

# Reset to clean state
./bin/install.sh  # Re-run initial install
```

### Permission Issues
```bash
# Fix script permissions
find bin/ -name "*.sh" -exec chmod +x {} \;

# Fix config directory permissions
chmod -R u+rw ~/.config/wsl-tmux-nvim-setup/
```

### Network Issues
```bash
# Test GitHub connectivity
curl -I https://api.github.com/repos/albrtbc/wsl-tmux-nvim-setup/releases/latest

# Use different update method if GitHub is blocked
# (manually download and run update.sh)
```

## File Structure
```
bin/
├── update.sh              # Main update script
├── check-updates.sh       # Periodic update checker  
└── update-from-release.sh # Release-based updates

~/.config/wsl-tmux-nvim-setup/
├── backups/               # Automatic backups
├── current-version        # Current release version
├── last-update-check      # Last commit hash checked
├── update-available       # Update notification file
└── update.log            # Update operation logs
```

## Integration Examples

### Shell Integration
```bash
# Add to .bashrc
update-check() {
    if check-updates --silent; then
        echo "🔄 Config updates available! Run 'update-configs' to apply."
    fi
}

# Check on cd to project directories
cd() {
    builtin cd "$@" && {
        [[ "$PWD" =~ "dev" ]] && update-check
    }
}
```

### Tmux Integration
```bash
# Add to .tmux.conf
# Show update status in tmux status bar
set -g status-right '#[fg=yellow]#{?#{e|>:#{l:#{b:update-available}},0}, 🔄 Updates Available,}#[default] | %Y-%m-%d %H:%M'
```

### Neovim Integration
```lua
-- Add to init.lua
vim.api.nvim_create_autocmd("VimEnter", {
  callback = function()
    local update_file = vim.fn.expand("~/.config/wsl-tmux-nvim-setup/update-available")
    if vim.fn.filereadable(update_file) == 1 then
      vim.notify("Config updates available! Run update-configs", vim.log.levels.INFO)
    end
  end
})
```

## Workflow Recommendations

### Daily Development Workflow
1. **Morning**: Automatic check shows available updates
2. **Review**: Check what changed (`git log` or release notes)  
3. **Update**: Run `update-configs` when convenient
4. **Test**: Verify key functions work after update

### Release Workflow
1. **Development** on feature branches
2. **Testing** with manual update script
3. **Create release** when stable
4. **Deploy** using release-based updater

This system provides flexible, safe, and automated ways to keep your development environment synchronized across all your machines!

---

*Choose the update method that best fits your workflow and risk tolerance.*