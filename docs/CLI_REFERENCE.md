# WSL-Tmux-Nvim-Setup CLI Reference

Complete reference guide for the WSL-Tmux-Nvim-Setup Manager (`wsm`) command-line interface.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Global Options](#global-options)
- [Commands](#commands)
  - [install](#install)
  - [update](#update)
  - [list](#list)
  - [status](#status)
  - [config](#config)
  - [rollback](#rollback)
  - [doctor](#doctor)
  - [version-info](#version-info)
- [Configuration](#configuration)
- [Environment Variables](#environment-variables)
- [Examples](#examples)
- [Exit Codes](#exit-codes)

## Overview

The WSL-Tmux-Nvim-Setup Manager (`wsm`) is a comprehensive command-line tool for managing your WSL development environment setup. It provides automated installation, updates, and maintenance of development tools and configurations.

### Key Features

- **Automated Installation**: Install complete WSL development environment
- **Version Management**: Install specific versions or latest releases
- **Interactive Mode**: Guided setup with component selection
- **Backup & Rollback**: Safe operations with automatic backups
- **Update Management**: Check for and apply updates
- **Configuration Management**: Centralized configuration system
- **System Diagnostics**: Health checks and compatibility validation

## Installation

### From Release

```bash
# Download and install latest release
curl -sSL https://github.com/albrtbc/wsl-tmux-nvim-setup/releases/latest/download/install.sh | bash
```

### From Source

```bash
# Clone repository
git clone https://github.com/albrtbc/wsl-tmux-nvim-setup.git
cd wsl-tmux-nvim-setup

# Install with pip
pip install -e .

# Or install dependencies and run directly
pip install -r requirements.txt
python cli/wsm.py --help
```

### Verify Installation

```bash
wsm --version
wsm doctor
```

## Global Options

Global options can be used with any command:

| Option | Short | Description |
|--------|-------|-------------|
| `--help` | `-h` | Show help message and exit |
| `--version` |  | Show version information |
| `--verbose` | `-v` | Enable verbose output |
| `--quiet` | `-q` | Suppress non-error output |
| `--config-dir PATH` | `-c` | Use custom configuration directory |

### Examples

```bash
# Verbose mode
wsm -v install

# Quiet mode
wsm -q status

# Custom config directory
wsm -c /custom/config install
```

## Commands

### install

Install a specific version or the latest release of the WSL development environment.

#### Syntax

```bash
wsm install [VERSION] [OPTIONS]
```

#### Options

| Option | Description |
|--------|-------------|
| `--interactive` | Enable interactive installation mode |
| `--force` | Force installation even if already installed |
| `--dry-run` | Show what would be done without making changes |
| `--components COMPONENTS` | Comma-separated list of components to install |
| `--skip-components COMPONENTS` | Comma-separated list of components to skip |
| `--backup` | Create backup before installation (default: true) |
| `--no-backup` | Skip backup creation |

#### Examples

```bash
# Install latest version
wsm install

# Install specific version
wsm install v1.2.0

# Interactive installation with component selection
wsm install --interactive

# Install only specific components
wsm install --components tmux,neovim,git

# Dry run to see what would be installed
wsm install --dry-run

# Force reinstall over existing installation
wsm install --force

# Install without creating backup
wsm install --no-backup
```

#### Interactive Mode

Interactive mode provides a guided installation experience:

1. **System Check**: Validates system compatibility
2. **Component Selection**: Choose which components to install
3. **Configuration**: Customize installation settings
4. **Preview**: Review installation plan
5. **Installation**: Execute with progress tracking

```bash
wsm install --interactive
```

**Interactive Features:**
- Visual component selection with descriptions
- Real-time configuration validation
- Progress bars with time estimation
- Error recovery with user guidance

### update

Check for and install updates to the WSL development environment.

#### Syntax

```bash
wsm update [OPTIONS]
```

#### Options

| Option | Description |
|--------|-------------|
| `--check` | Check for updates without installing |
| `--pre-release` | Include pre-release versions |
| `--force` | Force update even if current version is latest |
| `--backup` | Create backup before update (default: true) |
| `--no-backup` | Skip backup creation |
| `--components COMPONENTS` | Update only specific components |

#### Examples

```bash
# Check for updates
wsm update --check

# Update to latest version
wsm update

# Include pre-release versions
wsm update --pre-release

# Update specific components only
wsm update --components tmux,neovim

# Force update
wsm update --force
```

#### Update Process

1. **Check**: Compare current version with latest available
2. **Backup**: Create backup of current installation
3. **Download**: Download new version and verify checksums
4. **Install**: Apply updates with rollback capability
5. **Verify**: Validate successful update

### list

List available versions and releases.

#### Syntax

```bash
wsm list [OPTIONS]
```

#### Options

| Option | Description |
|--------|-------------|
| `--pre-release` | Include pre-release versions |
| `--limit N` | Limit number of results (default: 20) |
| `--format FORMAT` | Output format: table, json, simple |

#### Examples

```bash
# List latest releases
wsm list

# Include pre-releases
wsm list --pre-release

# Show first 10 releases
wsm list --limit 10

# JSON output
wsm list --format json

# Simple format for scripting
wsm list --format simple
```

#### Output Formats

**Table Format (default):**
```
Version    Released     Size     Status
v1.2.0     2025-09-01   2.1 MB   ✓ Available
v1.1.0     2025-08-15   2.0 MB   Current
v1.0.0     2025-08-01   1.9 MB   Available
```

**JSON Format:**
```json
[
  {
    "version": "v1.2.0",
    "published_at": "2025-09-01T00:00:00Z",
    "size": 2097152,
    "is_current": false,
    "is_latest": true
  }
]
```

### status

Show current installation status and system information.

#### Syntax

```bash
wsm status [OPTIONS]
```

#### Options

| Option | Description |
|--------|-------------|
| `--detailed` | Show detailed component information |
| `--check-updates` | Include update availability check |
| `--format FORMAT` | Output format: table, json, simple |

#### Examples

```bash
# Basic status
wsm status

# Detailed status with component versions
wsm status --detailed

# Include update check
wsm status --check-updates

# JSON format
wsm status --format json
```

#### Status Information

- **Version**: Currently installed version
- **Components**: Installed components and versions
- **Installation**: Installation path and date
- **Updates**: Last update check and available updates
- **Backups**: Number of backups and retention policy
- **Health**: System health and compatibility status

### config

Manage configuration settings.

#### Syntax

```bash
wsm config SUBCOMMAND [OPTIONS]
```

#### Subcommands

| Subcommand | Description |
|------------|-------------|
| `show` | Display current configuration |
| `list` | List all configuration options |
| `get KEY` | Get specific configuration value |
| `set KEY VALUE` | Set configuration value |
| `unset KEY` | Remove configuration value |
| `reset` | Reset to default configuration |
| `validate` | Validate configuration |

#### Examples

```bash
# Show current configuration
wsm config show

# List all available options
wsm config list

# Get specific value
wsm config get auto_update

# Set configuration value
wsm config set auto_update true
wsm config set github_token ghp_your_token_here

# Remove configuration value
wsm config unset github_token

# Reset to defaults
wsm config reset

# Validate configuration
wsm config validate
```

#### Configuration Options

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `auto_update` | boolean | `false` | Enable automatic updates |
| `backup_retention` | integer | `5` | Number of backups to keep |
| `github_token` | string | `null` | GitHub API token for higher rate limits |
| `preferred_components` | array | `[]` | Default components for installation |
| `installation_path` | string | `~/.wsl-setup` | Installation directory |
| `download_timeout` | integer | `300` | Download timeout in seconds |
| `max_retries` | integer | `3` | Maximum download retry attempts |
| `verbose` | boolean | `false` | Enable verbose output by default |

### rollback

Rollback to a previous version or backup.

#### Syntax

```bash
wsm rollback [VERSION] [OPTIONS]
```

#### Options

| Option | Description |
|--------|-------------|
| `--list-backups` | List available backups |
| `--backup-id ID` | Rollback to specific backup |
| `--dry-run` | Show what would be restored |
| `--force` | Force rollback without confirmation |

#### Examples

```bash
# List available backups
wsm rollback --list-backups

# Rollback to previous version
wsm rollback

# Rollback to specific version
wsm rollback v1.0.0

# Rollback to specific backup
wsm rollback --backup-id backup-20250901-120000

# Dry run rollback
wsm rollback --dry-run
```

#### Rollback Process

1. **List Options**: Show available backups and versions
2. **Select Target**: Choose version or backup to restore
3. **Validate**: Verify backup integrity
4. **Backup Current**: Save current state before rollback
5. **Restore**: Restore selected version
6. **Verify**: Validate successful rollback

### doctor

Run system diagnostics and health checks.

#### Syntax

```bash
wsm doctor [OPTIONS]
```

#### Options

| Option | Description |
|--------|-------------|
| `--fix` | Attempt to fix detected issues |
| `--check CHECK` | Run specific diagnostic check |
| `--format FORMAT` | Output format: table, json, simple |

#### Examples

```bash
# Run all diagnostics
wsm doctor

# Attempt to fix issues
wsm doctor --fix

# Run specific check
wsm doctor --check dependencies

# JSON output
wsm doctor --format json
```

#### Diagnostic Checks

- **System Information**: OS, architecture, environment
- **Dependencies**: Required packages and tools
- **Configuration**: Configuration file validation
- **Permissions**: File and directory permissions
- **Network**: Connectivity and API access
- **Storage**: Disk space and file system
- **Compatibility**: WSL version and feature support

### version-info

Show detailed version and component information.

#### Syntax

```bash
wsm version-info [OPTIONS]
```

#### Options

| Option | Description |
|--------|-------------|
| `--components` | Show component versions |
| `--compatibility` | Show compatibility information |
| `--format FORMAT` | Output format: table, json, simple |

#### Examples

```bash
# Show version information
wsm version-info

# Include component versions
wsm version-info --components

# Include compatibility info
wsm version-info --compatibility

# JSON output
wsm version-info --format json
```

## Configuration

WSM uses a hierarchical configuration system with the following precedence:

1. Command-line options (highest priority)
2. Environment variables
3. User configuration file
4. System configuration file
5. Default values (lowest priority)

### Configuration Files

**User Configuration:**
- Location: `~/.config/wsm/config.json` or `$WSM_CONFIG_DIR/config.json`
- Format: JSON

**System Configuration:**
- Location: `/etc/wsm/config.json`
- Format: JSON

**Example Configuration:**

```json
{
  "installation_path": "~/.wsl-setup",
  "auto_update": false,
  "backup_retention": 5,
  "github_token": null,
  "preferred_components": [
    "tmux",
    "neovim", 
    "git",
    "zsh"
  ],
  "download": {
    "timeout": 300,
    "max_retries": 3,
    "parallel": true,
    "mirrors": [
      "https://github.com",
      "https://mirror.example.com"
    ]
  },
  "logging": {
    "level": "INFO",
    "file": "~/.config/wsm/logs/wsm.log"
  }
}
```

## Environment Variables

Environment variables can be used to override configuration:

| Variable | Description | Example |
|----------|-------------|---------|
| `WSM_CONFIG_DIR` | Configuration directory | `/custom/config` |
| `WSM_INSTALL_DIR` | Installation directory | `/opt/wsl-setup` |
| `WSM_GITHUB_TOKEN` | GitHub API token | `ghp_token123` |
| `WSM_VERBOSE` | Enable verbose output | `1` or `true` |
| `WSM_QUIET` | Enable quiet mode | `1` or `true` |
| `WSM_LOG_LEVEL` | Logging level | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Examples

```bash
# Use custom config directory
export WSM_CONFIG_DIR=/custom/config
wsm status

# Enable verbose mode
WSM_VERBOSE=1 wsm install

# Use GitHub token
WSM_GITHUB_TOKEN=ghp_token123 wsm update --check
```

## Examples

### Quick Start

```bash
# First installation
wsm install --interactive

# Check status
wsm status

# Update to latest
wsm update

# Check for issues
wsm doctor
```

### Advanced Usage

```bash
# Install specific version with custom components
wsm install v1.2.0 --components tmux,neovim --force

# Update with pre-release and backup
wsm update --pre-release --backup

# Rollback if something goes wrong
wsm rollback --list-backups
wsm rollback --backup-id backup-20250901-120000

# Configure for automatic updates
wsm config set auto_update true
wsm config set backup_retention 10
```

### Scripting

```bash
#!/bin/bash
# Automated setup script

# Check if wsm is available
if ! command -v wsm &> /dev/null; then
    echo "Installing WSM..."
    curl -sSL https://install.wsl-setup.com | bash
fi

# Install latest version
wsm install --force --no-interactive

# Configure
wsm config set auto_update true
wsm config set preferred_components tmux,neovim,git,zsh

# Verify installation
wsm doctor || exit 1
echo "Setup complete!"
```

### JSON Output Processing

```bash
# Get version information as JSON
wsm status --format json | jq '.version'

# List updates
wsm list --format json | jq '.[] | select(.is_latest) | .version'

# Check component status
wsm status --detailed --format json | jq '.components'
```

## Exit Codes

WSM uses standard exit codes to indicate operation results:

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error |
| `2` | Command line usage error |
| `3` | Configuration error |
| `4` | Network error |
| `5` | File system error |
| `6` | Permission error |
| `7` | Version not found |
| `8` | Installation error |
| `9` | Update error |
| `10` | Rollback error |
| `130` | Interrupted (Ctrl+C) |

### Examples

```bash
# Check exit code
wsm install
echo "Exit code: $?"

# Script usage
if wsm update --check; then
    echo "Updates available"
else
    case $? in
        4) echo "Network error - check connection" ;;
        7) echo "No updates available" ;;
        *) echo "Unknown error" ;;
    esac
fi
```

---

*For more information, visit the [project repository](https://github.com/albrtbc/wsl-tmux-nvim-setup) or run `wsm --help` for quick reference.*