# Migration Guide

Complete guide for migrating from the existing auto_install system to the new WSL-Tmux-Nvim-Setup Manager (WSM).

## Table of Contents

- [Overview](#overview)
- [Pre-Migration Assessment](#pre-migration-assessment)
- [Migration Strategies](#migration-strategies)
- [Step-by-Step Migration](#step-by-step-migration)
- [Data Preservation](#data-preservation)
- [Configuration Migration](#configuration-migration)
- [Testing and Validation](#testing-and-validation)
- [Rollback Plan](#rollback-plan)
- [Post-Migration Tasks](#post-migration-tasks)
- [Troubleshooting](#troubleshooting)

## Overview

The WSL-Tmux-Nvim-Setup Manager (WSM) represents a significant evolution from the original `auto_install` system. This migration provides:

- **Enhanced CLI Interface**: Comprehensive command-line tool
- **Automated Updates**: Built-in update mechanism
- **Backup & Rollback**: Safe operations with recovery options
- **Configuration Management**: Centralized configuration system
- **Interactive Installation**: Guided setup process
- **Performance Improvements**: Faster operations and better caching

### Key Differences

| Feature | Old System | New System (WSM) |
|---------|------------|------------------|
| **Installation** | Manual script execution | `wsm install` command |
| **Updates** | Manual git pull + script | `wsm update` command |
| **Configuration** | Scattered config files | Centralized config management |
| **Backup** | Manual backup required | Automatic backup system |
| **Rollback** | Manual restoration | `wsm rollback` command |
| **Components** | All-or-nothing install | Selective component installation |
| **Validation** | Manual verification | Built-in health checks |

## Pre-Migration Assessment

Before starting migration, assess your current setup:

### 1. Current Installation Analysis

```bash
# Check current installation
cd ~/wsl-tmux-nvim-setup  # or your installation directory
ls -la

# Check installed components
which tmux nvim git zsh

# Check configuration files
ls -la ~/.config/ | grep -E "(tmux|nvim|git|zsh)"
ls -la ~/.* | grep -E "(tmux|nvim|git|zsh)"
```

### 2. Backup Current Setup

```bash
#!/bin/bash
# Create comprehensive backup

BACKUP_DIR="$HOME/wsl-setup-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Creating backup in: $BACKUP_DIR"

# Backup installation directory
if [ -d ~/wsl-tmux-nvim-setup ]; then
    cp -r ~/wsl-tmux-nvim-setup "$BACKUP_DIR/installation"
fi

# Backup configuration files
mkdir -p "$BACKUP_DIR/configs"
cp ~/.bashrc "$BACKUP_DIR/configs/" 2>/dev/null || true
cp ~/.zshrc "$BACKUP_DIR/configs/" 2>/dev/null || true
cp ~/.tmux.conf "$BACKUP_DIR/configs/" 2>/dev/null || true
cp -r ~/.config/nvim "$BACKUP_DIR/configs/" 2>/dev/null || true
cp ~/.gitconfig "$BACKUP_DIR/configs/" 2>/dev/null || true

# Backup custom modifications
find ~ -maxdepth 1 -name ".*" -type f | while read file; do
    if grep -q "wsl-tmux-nvim" "$file" 2>/dev/null; then
        cp "$file" "$BACKUP_DIR/configs/"
    fi
done

echo "Backup completed: $BACKUP_DIR"
echo "Backup size: $(du -sh $BACKUP_DIR | cut -f1)"
```

### 3. Document Current Configuration

```bash
# Document current setup
cat > ~/current-setup-info.txt << EOF
=== Current WSL-Tmux-Nvim Setup ===
Date: $(date)

Installation Directory: $(pwd)
Git Status: $(git status --porcelain 2>/dev/null || echo "Not a git repository")
Last Modified: $(find . -name "*.sh" -exec ls -lt {} + | head -5)

Installed Versions:
- Tmux: $(tmux -V 2>/dev/null || echo "Not installed")
- Neovim: $(nvim --version | head -1 2>/dev/null || echo "Not installed")
- Git: $(git --version 2>/dev/null || echo "Not installed")
- Zsh: $(zsh --version 2>/dev/null || echo "Not installed")

Custom Modifications:
$(grep -r "# CUSTOM" . 2>/dev/null || echo "No custom modifications found")

Active Shell: $SHELL
Current User: $USER
Home Directory: $HOME
EOF

cat ~/current-setup-info.txt
```

## Migration Strategies

Choose the migration approach that best fits your needs:

### Strategy 1: Clean Migration (Recommended)

**Best for:** Users who want a fresh start and can recreate customizations

**Process:**
1. Backup current setup
2. Uninstall old system
3. Install WSM
4. Migrate configurations
5. Restore customizations

**Pros:**
- Clean, predictable state
- Latest features and optimizations
- No legacy conflicts

**Cons:**
- Requires manual customization restoration
- Temporary loss of environment during migration

### Strategy 2: In-Place Migration

**Best for:** Users with extensive customizations who prefer minimal disruption

**Process:**
1. Install WSM alongside existing system
2. Migrate configurations gradually
3. Test new system
4. Switch over when ready
5. Clean up old system

**Pros:**
- Minimal downtime
- Gradual transition
- Easy rollback

**Cons:**
- More complex process
- Potential conflicts
- Requires more disk space

### Strategy 3: Parallel Installation

**Best for:** Users who want to test extensively before switching

**Process:**
1. Install WSM in separate directory
2. Configure WSM with existing settings
3. Run both systems in parallel
4. Switch when confident
5. Remove old system

**Pros:**
- Zero downtime
- Extensive testing possible
- Easy comparison

**Cons:**
- Highest disk usage
- Most complex setup
- Potential confusion

## Step-by-Step Migration

### Phase 1: Preparation

#### 1.1 Install WSM

```bash
# Install WSM (choose one method)

# Method 1: From release
curl -sSL https://install.wsl-setup.com | bash

# Method 2: From source
git clone https://github.com/user/wsl-tmux-nvim-setup.git wsm-new
cd wsm-new
pip install -e .

# Method 3: With pip
pip install wsl-tmux-nvim-setup
```

#### 1.2 Verify Installation

```bash
# Check WSM installation
wsm --version
wsm doctor
```

#### 1.3 Initial Configuration

```bash
# Configure installation directory
wsm config set installation_path ~/.wsl-setup-new

# Set other preferences
wsm config set backup_retention 10
wsm config set auto_update false  # Disable during migration
```

### Phase 2: Configuration Migration

#### 2.1 Analyze Current Configuration

```bash
# Create configuration mapping
cat > ~/config-migration-map.txt << EOF
=== Configuration Migration Map ===

Current Files -> WSM Configuration:
~/.bashrc -> wsm config (shell integration)
~/.tmux.conf -> wsm config (tmux settings)
~/.config/nvim -> wsm config (neovim settings)
~/.gitconfig -> wsm config (git settings)

Custom Settings to Preserve:
$(grep -h "# CUSTOM\|# Personal" ~/.bashrc ~/.zshrc ~/.tmux.conf 2>/dev/null || echo "None found")
EOF
```

#### 2.2 Extract Configuration Settings

```bash
#!/bin/bash
# Extract current configuration

# Create WSM configuration template
mkdir -p ~/.config/wsm
cat > ~/.config/wsm/config.json << 'EOF'
{
  "installation_path": "~/.wsl-setup",
  "auto_update": false,
  "backup_retention": 5,
  "preferred_components": [],
  "custom_settings": {
    "preserve_existing_configs": true,
    "merge_shell_configs": true
  }
}
EOF

# Extract component preferences from current installation
if [ -f ~/wsl-tmux-nvim-setup/auto_install/main.py ]; then
    echo "Detecting currently installed components..."
    
    # Check what's currently installed
    components=()
    [ -x "$(command -v tmux)" ] && components+=("tmux")
    [ -x "$(command -v nvim)" ] && components+=("neovim")
    [ -x "$(command -v git)" ] && components+=("git")
    [ -x "$(command -v zsh)" ] && components+=("zsh")
    
    # Update WSM config with detected components
    if [ ${#components[@]} -gt 0 ]; then
        component_list=$(printf '"%s",' "${components[@]}")
        component_list="[${component_list%,}]"
        
        wsm config set preferred_components "$component_list"
        echo "Detected components: ${components[*]}"
    fi
fi
```

#### 2.3 Custom Configuration Preservation

```bash
#!/bin/bash
# Preserve custom configurations

CUSTOM_CONFIG_DIR="$HOME/.config/wsm/custom"
mkdir -p "$CUSTOM_CONFIG_DIR"

# Extract custom bashrc additions
if grep -q "wsl-tmux-nvim" ~/.bashrc 2>/dev/null; then
    echo "Extracting custom bashrc settings..."
    
    # Extract WSL setup related lines
    grep -A 50 -B 50 "wsl-tmux-nvim" ~/.bashrc > "$CUSTOM_CONFIG_DIR/bashrc-custom.sh"
    
    # Extract other custom lines (marked with # CUSTOM)
    grep -A 1 -B 1 "# CUSTOM" ~/.bashrc >> "$CUSTOM_CONFIG_DIR/bashrc-custom.sh" || true
fi

# Extract custom tmux settings
if [ -f ~/.tmux.conf ]; then
    echo "Backing up tmux configuration..."
    cp ~/.tmux.conf "$CUSTOM_CONFIG_DIR/tmux.conf.backup"
    
    # Extract custom bindings and settings
    grep -E "^(bind|set)" ~/.tmux.conf > "$CUSTOM_CONFIG_DIR/tmux-custom.conf" || true
fi

# Extract custom nvim settings
if [ -d ~/.config/nvim ]; then
    echo "Backing up neovim configuration..."
    cp -r ~/.config/nvim "$CUSTOM_CONFIG_DIR/nvim.backup"
fi

echo "Custom configurations saved to: $CUSTOM_CONFIG_DIR"
```

### Phase 3: Migration Execution

#### 3.1 Test Installation

```bash
# Test WSM installation without affecting current setup
wsm install --dry-run --components tmux,neovim

# Test with limited components first
wsm install --dry-run --components git
```

#### 3.2 Incremental Migration

```bash
#!/bin/bash
# Incremental migration script

set -e

echo "=== WSM Migration Script ==="
echo "Phase: Incremental Migration"
echo "Date: $(date)"

# Step 1: Install core components
echo "Step 1: Installing core components..."
wsm install --components git --backup

# Verify git installation
if wsm status | grep -q "git"; then
    echo "✓ Git installation successful"
else
    echo "✗ Git installation failed"
    exit 1
fi

# Step 2: Install tmux
echo "Step 2: Installing tmux..."
wsm install --components tmux --backup

# Verify tmux installation
if wsm status | grep -q "tmux"; then
    echo "✓ Tmux installation successful"
else
    echo "✗ Tmux installation failed"
    exit 1
fi

# Step 3: Install neovim
echo "Step 3: Installing neovim..."
wsm install --components neovim --backup

# Verify neovim installation
if wsm status | grep -q "neovim"; then
    echo "✓ Neovim installation successful"
else
    echo "✗ Neovim installation failed"
    exit 1
fi

echo "=== Migration Phase Complete ==="
wsm status --detailed
```

#### 3.3 Configuration Application

```bash
#!/bin/bash
# Apply migrated configurations

echo "Applying migrated configurations..."

# Apply custom shell configurations
if [ -f ~/.config/wsm/custom/bashrc-custom.sh ]; then
    echo "Applying custom bashrc settings..."
    
    # Add WSM integration to bashrc
    if ! grep -q "WSM Integration" ~/.bashrc; then
        cat >> ~/.bashrc << 'EOF'

# WSM Integration
if [ -f ~/.wsl-setup/shell/integration.sh ]; then
    source ~/.wsl-setup/shell/integration.sh
fi

EOF
    fi
    
    # Add custom settings
    echo "# Custom settings from migration" >> ~/.bashrc
    cat ~/.config/wsm/custom/bashrc-custom.sh >> ~/.bashrc
fi

# Apply tmux configurations
if [ -f ~/.config/wsm/custom/tmux-custom.conf ]; then
    echo "Applying custom tmux settings..."
    
    # Ensure WSM tmux config is loaded first
    cat > ~/.tmux.conf << 'EOF'
# WSM Base Configuration
if '[ -f ~/.wsl-setup/configs/tmux.conf ]' 'source ~/.wsl-setup/configs/tmux.conf'

# Custom configurations from migration
EOF
    cat ~/.config/wsm/custom/tmux-custom.conf >> ~/.tmux.conf
fi

echo "Configuration application complete."
```

### Phase 4: Validation and Testing

#### 4.1 Comprehensive Testing

```bash
#!/bin/bash
# Migration validation script

echo "=== Migration Validation ==="

# Test WSM functionality
echo "Testing WSM commands..."
wsm --version || { echo "✗ WSM version check failed"; exit 1; }
wsm status || { echo "✗ WSM status check failed"; exit 1; }
wsm doctor || { echo "✗ WSM doctor check failed"; exit 1; }

# Test component functionality
echo "Testing installed components..."

# Test Git
if command -v git &> /dev/null; then
    git --version && echo "✓ Git functional"
else
    echo "✗ Git not found"
fi

# Test Tmux
if command -v tmux &> /dev/null; then
    tmux -V && echo "✓ Tmux functional"
    
    # Test tmux session creation
    tmux new-session -d -s test-session
    tmux list-sessions | grep test-session && echo "✓ Tmux sessions working"
    tmux kill-session -t test-session
else
    echo "✗ Tmux not found"
fi

# Test Neovim
if command -v nvim &> /dev/null; then
    nvim --version | head -1 && echo "✓ Neovim functional"
    
    # Test basic nvim functionality
    echo "print('hello')" | nvim --headless -c 'q' && echo "✓ Neovim basic functionality working"
else
    echo "✗ Neovim not found"
fi

# Test shell integration
echo "Testing shell integration..."
if [ -f ~/.wsl-setup/shell/integration.sh ]; then
    source ~/.wsl-setup/shell/integration.sh && echo "✓ Shell integration loaded"
else
    echo "⚠ Shell integration file not found"
fi

echo "=== Validation Complete ==="
```

#### 4.2 Performance Validation

```bash
# Test performance improvements
echo "=== Performance Validation ==="

# Test command response times
start_time=$(date +%s.%N)
wsm status > /dev/null
end_time=$(date +%s.%N)
status_time=$(echo "$end_time - $start_time" | bc)
echo "WSM status command time: ${status_time}s"

# Test update check performance
start_time=$(date +%s.%N)
wsm update --check > /dev/null
end_time=$(date +%s.%N)
update_time=$(echo "$end_time - $start_time" | bc)
echo "WSM update check time: ${update_time}s"

# Compare with old system (if available)
if [ -d ~/wsl-tmux-nvim-setup ]; then
    echo "Comparing with old system performance..."
    
    start_time=$(date +%s.%N)
    cd ~/wsl-tmux-nvim-setup && python3 scripts/check-updates.py > /dev/null 2>&1
    end_time=$(date +%s.%N)
    old_update_time=$(echo "$end_time - $start_time" | bc)
    echo "Old update check time: ${old_update_time}s"
    
    # Calculate improvement
    improvement=$(echo "scale=2; (($old_update_time - $update_time) / $old_update_time) * 100" | bc)
    echo "Performance improvement: ${improvement}%"
fi
```

## Data Preservation

### User Data and Customizations

```bash
#!/bin/bash
# Preserve user data and customizations

PRESERVATION_DIR="$HOME/.config/wsm/preserved"
mkdir -p "$PRESERVATION_DIR"

echo "Preserving user data and customizations..."

# Preserve custom aliases
if grep -q "alias" ~/.bashrc; then
    echo "Preserving custom aliases..."
    grep "^alias" ~/.bashrc > "$PRESERVATION_DIR/aliases.sh"
fi

# Preserve custom functions
if grep -q "function\|() {" ~/.bashrc; then
    echo "Preserving custom functions..."
    grep -A 10 -B 1 "function\|() {" ~/.bashrc > "$PRESERVATION_DIR/functions.sh"
fi

# Preserve environment variables
if grep -q "^export" ~/.bashrc; then
    echo "Preserving custom environment variables..."
    grep "^export" ~/.bashrc > "$PRESERVATION_DIR/exports.sh"
fi

# Preserve SSH configurations
if [ -d ~/.ssh ]; then
    echo "Preserving SSH configurations..."
    cp -r ~/.ssh "$PRESERVATION_DIR/"
    chmod -R 600 "$PRESERVATION_DIR/.ssh"
fi

# Preserve Git configurations
if [ -f ~/.gitconfig ]; then
    echo "Preserving Git global configuration..."
    cp ~/.gitconfig "$PRESERVATION_DIR/"
fi

echo "User data preservation complete."
echo "Preserved items location: $PRESERVATION_DIR"
```

### Development Environment State

```bash
#!/bin/bash
# Preserve development environment state

echo "Preserving development environment state..."

# Document current projects and their states
find ~ -name ".git" -type d 2>/dev/null | while read gitdir; do
    project_dir=$(dirname "$gitdir")
    project_name=$(basename "$project_dir")
    
    echo "Project: $project_name" >> ~/.config/wsm/preserved/projects.txt
    echo "Path: $project_dir" >> ~/.config/wsm/preserved/projects.txt
    echo "Status:" >> ~/.config/wsm/preserved/projects.txt
    cd "$project_dir" && git status --short >> ~/.config/wsm/preserved/projects.txt 2>/dev/null
    echo "---" >> ~/.config/wsm/preserved/projects.txt
done

# Preserve virtual environments
if [ -d ~/venv ] || [ -d ~/.virtualenvs ]; then
    echo "Documenting Python virtual environments..."
    ls -la ~/venv ~/.virtualenvs 2>/dev/null >> ~/.config/wsm/preserved/virtualenvs.txt
fi

# Preserve package lists
if command -v pip &> /dev/null; then
    echo "Preserving Python packages..."
    pip list > ~/.config/wsm/preserved/pip-packages.txt
fi

if command -v npm &> /dev/null; then
    echo "Preserving npm global packages..."
    npm list -g --depth=0 > ~/.config/wsm/preserved/npm-packages.txt
fi

echo "Development environment state preserved."
```

## Configuration Migration

### Automated Configuration Mapping

```bash
#!/bin/bash
# Automated configuration mapping

echo "=== Automated Configuration Migration ==="

# Create mapping configuration
cat > ~/.config/wsm/migration-mapping.json << 'EOF'
{
  "file_mappings": {
    "~/.bashrc": {
      "target": "shell/bashrc.d/custom.sh",
      "patterns": [
        "alias.*",
        "export.*",
        "function.*"
      ],
      "exclude_patterns": [
        "# WSM managed",
        "# Auto-generated"
      ]
    },
    "~/.tmux.conf": {
      "target": "configs/tmux/custom.conf",
      "patterns": [
        "bind.*",
        "set.*",
        "run-shell.*"
      ]
    },
    "~/.gitconfig": {
      "target": "configs/git/custom.gitconfig",
      "merge_strategy": "preserve_user_settings"
    }
  },
  "component_preferences": {
    "detect_from_current": true,
    "preserve_versions": false,
    "upgrade_to_latest": true
  }
}
EOF

# Execute automated migration
python3 << 'EOF'
import json
import os
import re
import shutil
from pathlib import Path

# Load migration mapping
with open(os.path.expanduser('~/.config/wsm/migration-mapping.json')) as f:
    mapping = json.load(f)

print("Executing automated configuration migration...")

for source_file, config in mapping['file_mappings'].items():
    source_path = Path(os.path.expanduser(source_file))
    
    if not source_path.exists():
        continue
        
    print(f"Processing {source_file}...")
    
    # Read source file
    with open(source_path, 'r') as f:
        content = f.read()
    
    # Extract matching patterns
    extracted_lines = []
    for pattern in config['patterns']:
        matches = re.findall(f'^{pattern}.*$', content, re.MULTILINE)
        extracted_lines.extend(matches)
    
    # Filter out excluded patterns
    if 'exclude_patterns' in config:
        for exclude_pattern in config['exclude_patterns']:
            extracted_lines = [line for line in extracted_lines 
                             if not re.search(exclude_pattern, line)]
    
    if extracted_lines:
        # Write to target file
        target_path = Path(os.path.expanduser(f'~/.wsl-setup/{config["target"]}'))
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(target_path, 'w') as f:
            f.write(f"# Migrated from {source_file}\n")
            f.write(f"# Migration date: {os.popen('date').read().strip()}\n\n")
            f.write('\n'.join(extracted_lines))
        
        print(f"  → Migrated {len(extracted_lines)} lines to {target_path}")

print("Automated migration complete.")
EOF
```

### Manual Configuration Review

```bash
# Create manual review checklist
cat > ~/wsm-migration-checklist.txt << 'EOF'
=== WSM Migration Checklist ===

□ Backup created and verified
□ WSM installed and functional
□ Core components migrated (git, tmux, neovim)
□ Shell integration working
□ Custom aliases preserved
□ Custom functions preserved
□ Environment variables preserved
□ SSH configuration preserved
□ Git configuration preserved
□ Tmux key bindings preserved
□ Neovim plugins working
□ Development projects accessible
□ Performance validated
□ Old system cleanly removed

Manual Review Items:
□ Review ~/.bashrc for missed customizations
□ Review ~/.tmux.conf for missed settings
□ Test all custom key bindings
□ Verify all development tools work
□ Check environment variable exports
□ Validate PATH modifications
□ Test terminal color schemes
□ Verify font configurations

Post-Migration Tasks:
□ Enable auto-updates: wsm config set auto_update true
□ Configure backup retention: wsm config set backup_retention 10
□ Set up GitHub token: wsm config set github_token <token>
□ Test update mechanism: wsm update --check
□ Document any remaining manual steps
□ Share feedback with WSM project

Notes:
_________________________________
_________________________________
_________________________________
EOF

echo "Migration checklist created: ~/wsm-migration-checklist.txt"
```

## Testing and Validation

### Comprehensive Test Suite

```bash
#!/bin/bash
# Comprehensive migration test suite

test_count=0
passed_count=0

run_test() {
    local test_name="$1"
    local test_command="$2"
    
    ((test_count++))
    echo "Test $test_count: $test_name"
    
    if eval "$test_command" >/dev/null 2>&1; then
        echo "  ✓ PASSED"
        ((passed_count++))
    else
        echo "  ✗ FAILED"
        echo "    Command: $test_command"
    fi
}

echo "=== WSM Migration Test Suite ==="

# WSM Core Functionality Tests
run_test "WSM Installation" "wsm --version"
run_test "WSM Status Command" "wsm status"
run_test "WSM Configuration" "wsm config show"
run_test "WSM Doctor Check" "wsm doctor"

# Component Tests
run_test "Git Installation" "command -v git"
run_test "Git Configuration" "git config --get user.name"
run_test "Tmux Installation" "command -v tmux"
run_test "Tmux Configuration" "tmux show-options -g"
run_test "Neovim Installation" "command -v nvim"
run_test "Neovim Basic Function" "nvim --version"

# Integration Tests
run_test "Shell Integration" "[ -f ~/.wsl-setup/shell/integration.sh ]"
run_test "Custom Aliases" "alias | grep -q 'custom'"
run_test "Custom Functions" "declare -F | grep -q 'custom'"

# Performance Tests
run_test "WSM Status Performance" "timeout 5 wsm status"
run_test "Update Check Performance" "timeout 10 wsm update --check"

# Configuration Preservation Tests
run_test "SSH Config Preserved" "[ -f ~/.ssh/config ]"
run_test "Git Config Preserved" "[ -f ~/.gitconfig ]"
run_test "Custom Bashrc Preserved" "grep -q 'custom' ~/.bashrc"

echo ""
echo "=== Test Results ==="
echo "Total Tests: $test_count"
echo "Passed: $passed_count"
echo "Failed: $((test_count - passed_count))"
echo "Success Rate: $(( (passed_count * 100) / test_count ))%"

if [ $passed_count -eq $test_count ]; then
    echo "🎉 All tests passed! Migration successful."
    exit 0
else
    echo "⚠️  Some tests failed. Review and fix issues before completing migration."
    exit 1
fi
```

## Rollback Plan

### Automated Rollback

```bash
#!/bin/bash
# Automated rollback script

echo "=== WSM Migration Rollback ==="
echo "This will restore your system to the pre-migration state."

read -p "Are you sure you want to rollback? (y/N): " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "Rollback cancelled."
    exit 0
fi

BACKUP_DIR=$(find ~ -name "wsl-setup-backup-*" -type d | sort | tail -1)

if [ -z "$BACKUP_DIR" ] || [ ! -d "$BACKUP_DIR" ]; then
    echo "Error: Backup directory not found."
    echo "Please ensure you have a backup before rollback."
    exit 1
fi

echo "Using backup: $BACKUP_DIR"

# Stop any WSM processes
pkill -f wsm || true

# Remove WSM installation
echo "Removing WSM installation..."
pip uninstall -y wsl-tmux-nvim-setup 2>/dev/null || true
rm -rf ~/.wsl-setup
rm -rf ~/.config/wsm
rm -rf ~/.cache/wsm

# Restore configuration files
echo "Restoring configuration files..."
if [ -d "$BACKUP_DIR/configs" ]; then
    cp -r "$BACKUP_DIR/configs/"* ~/ 2>/dev/null || true
fi

# Restore old installation
echo "Restoring old installation..."
if [ -d "$BACKUP_DIR/installation" ]; then
    cp -r "$BACKUP_DIR/installation" ~/wsl-tmux-nvim-setup
fi

# Restore shell configuration
if [ -f "$BACKUP_DIR/configs/.bashrc" ]; then
    cp "$BACKUP_DIR/configs/.bashrc" ~/.bashrc
fi

if [ -f "$BACKUP_DIR/configs/.zshrc" ]; then
    cp "$BACKUP_DIR/configs/.zshrc" ~/.zshrc
fi

echo "Rollback complete."
echo "Please restart your shell or run 'source ~/.bashrc' to apply changes."
```

### Manual Rollback Steps

1. **Remove WSM:**
   ```bash
   pip uninstall wsl-tmux-nvim-setup
   rm -rf ~/.wsl-setup ~/.config/wsm ~/.cache/wsm
   ```

2. **Restore configurations:**
   ```bash
   # Restore from backup
   cp ~/wsl-setup-backup-*/configs/.bashrc ~/.bashrc
   cp ~/wsl-setup-backup-*/configs/.tmux.conf ~/.tmux.conf
   ```

3. **Restore old installation:**
   ```bash
   cp -r ~/wsl-setup-backup-*/installation ~/wsl-tmux-nvim-setup
   ```

## Post-Migration Tasks

### Optimization and Cleanup

```bash
#!/bin/bash
# Post-migration optimization

echo "=== Post-Migration Optimization ==="

# Enable auto-updates
echo "Enabling auto-updates..."
wsm config set auto_update true

# Configure optimal backup retention
echo "Configuring backup retention..."
wsm config set backup_retention 5

# Set up GitHub token for better API limits
if [ -n "$GITHUB_TOKEN" ]; then
    echo "Configuring GitHub token..."
    wsm config set github_token "$GITHUB_TOKEN"
fi

# Optimize performance settings
echo "Optimizing performance settings..."
wsm config set download.parallel true
wsm config set download.connections 4

# Clean up migration artifacts
echo "Cleaning up migration artifacts..."
rm -f ~/current-setup-info.txt
rm -f ~/config-migration-map.txt
rm -f ~/wsm-migration-checklist.txt

# Remove old backup after confirmation
if [ -d ~/wsl-setup-backup-* ]; then
    echo "Old backups found:"
    ls -d ~/wsl-setup-backup-*
    
    read -p "Remove old backups? (y/N): " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        rm -rf ~/wsl-setup-backup-*
        echo "Old backups removed."
    fi
fi

echo "Post-migration optimization complete."
```

### Documentation Update

```bash
# Create personal documentation
cat > ~/.config/wsm/migration-summary.md << 'EOF'
# WSM Migration Summary

## Migration Details
- Date: $(date)
- Previous System: auto_install
- New System: WSM (WSL-Tmux-Nvim-Setup Manager)
- Migration Strategy: [Clean/In-Place/Parallel]

## Migrated Components
- [ ] Git
- [ ] Tmux  
- [ ] Neovim
- [ ] Zsh
- [ ] Custom configurations

## Custom Configurations Preserved
- Aliases: ~/.wsl-setup/shell/bashrc.d/custom.sh
- Functions: ~/.wsl-setup/shell/bashrc.d/custom.sh
- Tmux settings: ~/.wsl-setup/configs/tmux/custom.conf
- Git settings: ~/.gitconfig

## New Features Available
- Interactive installation: `wsm install --interactive`
- Automated updates: `wsm update`
- System diagnostics: `wsm doctor`
- Backup management: `wsm rollback --list-backups`
- Configuration management: `wsm config`

## Useful Commands
- Check status: `wsm status`
- Update system: `wsm update`
- Check health: `wsm doctor`
- Manage config: `wsm config show`
- View backups: `wsm rollback --list-backups`

## Notes
- Auto-updates: Enabled
- Backup retention: 5 versions
- Installation path: ~/.wsl-setup
EOF

echo "Migration summary created: ~/.config/wsm/migration-summary.md"
```

## Troubleshooting

### Common Migration Issues

#### Issue: Configuration Not Applied

**Symptoms:**
- Custom aliases not working
- Shell integration missing
- Settings not preserved

**Solutions:**
```bash
# Check shell integration
source ~/.bashrc
source ~/.wsl-setup/shell/integration.sh

# Verify custom configurations
ls -la ~/.wsl-setup/shell/bashrc.d/
cat ~/.wsl-setup/shell/bashrc.d/custom.sh

# Manually apply if needed
echo "source ~/.wsl-setup/shell/integration.sh" >> ~/.bashrc
```

#### Issue: Component Conflicts

**Symptoms:**
- Duplicate installations
- Version conflicts
- Command path issues

**Solutions:**
```bash
# Check what's installed
which tmux nvim git
whereis tmux nvim git

# Remove duplicates
sudo apt remove tmux neovim git  # Remove system versions if needed
hash -r  # Clear command cache

# Reinstall with WSM
wsm install --force
```

#### Issue: Performance Regression

**Symptoms:**
- Slower command execution
- Increased memory usage
- Longer startup times

**Solutions:**
```bash
# Check WSM performance
wsm doctor --check performance

# Optimize configuration
wsm config set download.parallel true
wsm config set cache.enabled true

# Profile shell startup
bash -x ~/.bashrc 2>&1 | head -50
```

### Getting Migration Help

1. **Check migration status:**
   ```bash
   wsm status --detailed
   wsm doctor
   ```

2. **Create migration report:**
   ```bash
   wsm status --format json > migration-report.json
   cat ~/.config/wsm/migration-summary.md
   ```

3. **Contact support:**
   - GitHub Issues: Include migration report
   - Community Forum: Share specific problems
   - Documentation: Check latest migration guides

---

*Migration complete! Welcome to the new WSL-Tmux-Nvim-Setup Manager experience. For ongoing support, visit our [documentation](./CLI_REFERENCE.md) or [troubleshooting guide](./TROUBLESHOOTING.md).*