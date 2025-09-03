# Troubleshooting Guide

Comprehensive troubleshooting guide for common issues with WSL-Tmux-Nvim-Setup.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Common Issues](#common-issues)
- [Installation Problems](#installation-problems)
- [Update Issues](#update-issues)
- [Configuration Problems](#configuration-problems)
- [Performance Issues](#performance-issues)
- [Network Problems](#network-problems)
- [Permission Issues](#permission-issues)
- [Platform-Specific Issues](#platform-specific-issues)
- [Getting Help](#getting-help)

## Quick Diagnostics

Always start with the built-in diagnostic tool:

```bash
# Run comprehensive system check
wsm doctor

# Run with automatic fixes
wsm doctor --fix

# Check specific component
wsm doctor --check dependencies
```

### Basic Health Check

```bash
# Check version and status
wsm --version
wsm status

# Verify installation
wsm status --detailed

# Check configuration
wsm config validate
```

## Common Issues

### Issue: Command Not Found

**Symptoms:**
```bash
$ wsm --version
bash: wsm: command not found
```

**Solutions:**

1. **Check installation:**
   ```bash
   # Verify wsm is installed
   which wsm
   pip list | grep wsl-tmux-nvim-setup
   ```

2. **Install or reinstall:**
   ```bash
   # Install from release
   curl -sSL https://install.wsl-setup.com | bash
   
   # Or install with pip
   pip install wsl-tmux-nvim-setup
   ```

3. **Check PATH:**
   ```bash
   # Add to PATH if needed
   export PATH="$HOME/.local/bin:$PATH"
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc
   ```

### Issue: Permission Denied

**Symptoms:**
```bash
$ wsm install
Error: Permission denied accessing /opt/wsl-setup
```

**Solutions:**

1. **Change installation directory:**
   ```bash
   # Use user directory
   wsm config set installation_path ~/.wsl-setup
   wsm install
   ```

2. **Fix permissions:**
   ```bash
   # Create directory with correct permissions
   sudo mkdir -p /opt/wsl-setup
   sudo chown $USER:$USER /opt/wsl-setup
   ```

3. **Use sudo (not recommended):**
   ```bash
   # Only if necessary
   sudo wsm install
   ```

### Issue: Network Connection Failed

**Symptoms:**
```bash
$ wsm update --check
Error: Failed to connect to GitHub API
```

**Solutions:**

1. **Check network connectivity:**
   ```bash
   # Test GitHub connectivity
   curl -I https://api.github.com
   ping github.com
   ```

2. **Configure proxy if needed:**
   ```bash
   # Set proxy environment variables
   export http_proxy=http://proxy.example.com:8080
   export https_proxy=https://proxy.example.com:8080
   wsm update --check
   ```

3. **Use GitHub token for rate limits:**
   ```bash
   # Set GitHub token
   wsm config set github_token ghp_your_token_here
   ```

### Issue: Checksum Verification Failed

**Symptoms:**
```bash
$ wsm install
Error: Checksum verification failed for downloaded file
```

**Solutions:**

1. **Clear cache and retry:**
   ```bash
   # Clear download cache
   rm -rf ~/.cache/wsm/downloads/*
   wsm install
   ```

2. **Check network stability:**
   ```bash
   # Test download manually
   curl -L https://github.com/user/repo/releases/download/v1.0.0/file.tar.gz -o test.tar.gz
   sha256sum test.tar.gz
   ```

3. **Use different mirror:**
   ```bash
   # Configure alternative mirror
   wsm config set download.mirrors '["https://mirror.example.com", "https://github.com"]'
   ```

## Installation Problems

### Issue: Installation Hangs

**Symptoms:**
- Installation process appears to freeze
- No progress updates for extended period

**Diagnosis:**
```bash
# Run with verbose output
wsm install -v

# Check system resources
top
df -h
```

**Solutions:**

1. **Increase timeouts:**
   ```bash
   wsm config set download_timeout 600
   wsm config set max_retries 5
   ```

2. **Check disk space:**
   ```bash
   # Ensure sufficient space
   df -h
   # Clean up if needed
   sudo apt clean
   docker system prune -f
   ```

3. **Use dry run first:**
   ```bash
   # Test without actual installation
   wsm install --dry-run
   ```

### Issue: Component Installation Failed

**Symptoms:**
```bash
Installing tmux...
Error: Failed to install tmux - package not found
```

**Solutions:**

1. **Update package lists:**
   ```bash
   # Update system packages
   sudo apt update
   sudo apt upgrade
   ```

2. **Check component availability:**
   ```bash
   # Verify package exists
   apt search tmux
   apt show tmux
   ```

3. **Install dependencies manually:**
   ```bash
   # Install required dependencies
   sudo apt install build-essential cmake git
   ```

4. **Skip problematic components:**
   ```bash
   # Install without failing component
   wsm install --skip-components tmux
   ```

### Issue: Backup Creation Failed

**Symptoms:**
```bash
Creating backup...
Error: Failed to create backup - insufficient permissions
```

**Solutions:**

1. **Check backup directory permissions:**
   ```bash
   # Check backup location
   wsm config get backup_dir
   ls -la ~/.config/wsm/backups/
   ```

2. **Create backup directory:**
   ```bash
   # Ensure backup directory exists
   mkdir -p ~/.config/wsm/backups
   chmod 755 ~/.config/wsm/backups
   ```

3. **Change backup location:**
   ```bash
   # Use different backup location
   wsm config set backup_dir ~/wsm-backups
   ```

## Update Issues

### Issue: Update Check Failed

**Symptoms:**
```bash
$ wsm update --check
Error: Unable to fetch latest release information
```

**Solutions:**

1. **Check API rate limits:**
   ```bash
   # Check rate limit status
   curl -I https://api.github.com/rate_limit
   ```

2. **Use GitHub token:**
   ```bash
   # Set token for higher limits
   wsm config set github_token ghp_your_token_here
   ```

3. **Manual version check:**
   ```bash
   # Check manually
   curl -s https://api.github.com/repos/user/wsl-tmux-nvim-setup/releases/latest | jq -r '.tag_name'
   ```

### Issue: Update Download Failed

**Symptoms:**
```bash
$ wsm update
Downloading v1.2.0...
Error: Download interrupted or corrupted
```

**Solutions:**

1. **Retry with resume:**
   ```bash
   # Clear partial downloads
   rm -rf ~/.cache/wsm/downloads/*.partial
   wsm update
   ```

2. **Use alternative download method:**
   ```bash
   # Manual download and install
   wget https://github.com/user/repo/releases/download/v1.2.0/release.tar.gz
   wsm install --local release.tar.gz
   ```

3. **Check connection stability:**
   ```bash
   # Test sustained download
   wget --progress=bar https://github.com/user/repo/releases/download/v1.2.0/release.tar.gz
   ```

## Configuration Problems

### Issue: Configuration File Corrupted

**Symptoms:**
```bash
$ wsm status
Error: Invalid configuration file format
```

**Solutions:**

1. **Validate configuration:**
   ```bash
   # Check configuration syntax
   wsm config validate
   cat ~/.config/wsm/config.json | jq .
   ```

2. **Backup and reset:**
   ```bash
   # Backup current config
   cp ~/.config/wsm/config.json ~/.config/wsm/config.json.backup
   
   # Reset to defaults
   wsm config reset
   ```

3. **Manually fix JSON:**
   ```bash
   # Edit configuration file
   nano ~/.config/wsm/config.json
   
   # Validate JSON syntax
   python3 -m json.tool ~/.config/wsm/config.json
   ```

### Issue: Invalid Configuration Values

**Symptoms:**
```bash
$ wsm config set timeout invalid
Error: Invalid value 'invalid' for timeout (must be integer)
```

**Solutions:**

1. **Check valid values:**
   ```bash
   # List configuration options
   wsm config list
   
   # Get specific help
   wsm config help timeout
   ```

2. **Use correct types:**
   ```bash
   # Correct value types
   wsm config set timeout 300          # integer
   wsm config set auto_update true     # boolean
   wsm config set components '["tmux", "vim"]'  # array
   ```

## Performance Issues

### Issue: Slow Downloads

**Symptoms:**
- Very slow download speeds
- Timeouts during downloads

**Solutions:**

1. **Check network speed:**
   ```bash
   # Test download speed
   wget --progress=bar https://speedtest.wdc01.softlayer.com/downloads/test100.zip
   ```

2. **Use parallel downloads:**
   ```bash
   # Enable parallel downloads
   wsm config set download.parallel true
   wsm config set download.connections 4
   ```

3. **Configure mirrors:**
   ```bash
   # Add faster mirrors
   wsm config set download.mirrors '[
     "https://mirror1.example.com",
     "https://mirror2.example.com",
     "https://github.com"
   ]'
   ```

### Issue: High Memory Usage

**Symptoms:**
- System becomes slow during operations
- Out of memory errors

**Solutions:**

1. **Monitor memory usage:**
   ```bash
   # Check memory while running
   htop
   
   # Check wsm memory usage
   ps aux | grep wsm
   ```

2. **Reduce concurrent operations:**
   ```bash
   # Limit parallel downloads
   wsm config set download.connections 2
   
   # Process components sequentially
   wsm config set install.parallel false
   ```

3. **Increase swap space:**
   ```bash
   # Add swap file
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

## Network Problems

### Issue: Proxy Configuration

**Symptoms:**
```bash
$ wsm update --check
Error: Connection refused - check proxy settings
```

**Solutions:**

1. **Configure system proxy:**
   ```bash
   # Set environment variables
   export http_proxy=http://proxy.company.com:8080
   export https_proxy=https://proxy.company.com:8080
   export no_proxy=localhost,127.0.0.1
   ```

2. **Configure WSM proxy:**
   ```bash
   # Set WSM-specific proxy
   wsm config set proxy.http http://proxy.company.com:8080
   wsm config set proxy.https https://proxy.company.com:8080
   ```

3. **Test proxy connectivity:**
   ```bash
   # Test proxy connection
   curl -x http://proxy.company.com:8080 https://api.github.com
   ```

### Issue: DNS Resolution Failed

**Symptoms:**
```bash
Error: Could not resolve hostname github.com
```

**Solutions:**

1. **Check DNS configuration:**
   ```bash
   # Test DNS resolution
   nslookup github.com
   dig github.com
   
   # Check DNS servers
   cat /etc/resolv.conf
   ```

2. **Use alternative DNS:**
   ```bash
   # Temporarily use Google DNS
   sudo sed -i 's/^nameserver.*/nameserver 8.8.8.8/' /etc/resolv.conf
   ```

3. **Flush DNS cache:**
   ```bash
   # Flush system DNS cache
   sudo systemctl restart systemd-resolved
   
   # Or for older systems
   sudo service networking restart
   ```

## Permission Issues

### Issue: Script Execution Permission

**Symptoms:**
```bash
bash: ./install.sh: Permission denied
```

**Solutions:**

1. **Make scripts executable:**
   ```bash
   # Fix single script
   chmod +x install.sh
   
   # Fix all scripts
   find . -name "*.sh" -type f -exec chmod +x {} \;
   ```

2. **Check file system permissions:**
   ```bash
   # Check if filesystem supports execution
   mount | grep "$(df . | tail -1 | awk '{print $1}')"
   ```

### Issue: Configuration Directory Access

**Symptoms:**
```bash
Error: Cannot write to configuration directory
```

**Solutions:**

1. **Create configuration directory:**
   ```bash
   # Create with correct permissions
   mkdir -p ~/.config/wsm
   chmod 755 ~/.config/wsm
   ```

2. **Fix ownership:**
   ```bash
   # Fix ownership recursively
   sudo chown -R $USER:$USER ~/.config/wsm
   ```

## Platform-Specific Issues

### WSL1 Issues

**Common Problems:**
- File permission issues
- Performance degradation
- Limited system call support

**Solutions:**

1. **Enable WSL1 compatibility mode:**
   ```bash
   wsm config set wsl.version 1
   wsm config set wsl.compatibility_mode true
   ```

2. **Use WSL1-specific workarounds:**
   ```bash
   # Avoid symlinks in WSL1
   wsm config set filesystem.use_symlinks false
   ```

### WSL2 Issues

**Common Problems:**
- Network connectivity issues
- Docker integration problems
- Memory usage

**Solutions:**

1. **Configure WSL2 settings:**
   ```bash
   # Create or edit .wslconfig
   cat > ~/.wslconfig << EOF
   [wsl2]
   memory=4GB
   processors=2
   swap=2GB
   EOF
   ```

2. **Restart WSL2:**
   ```bash
   # From PowerShell/CMD
   wsl --shutdown
   wsl
   ```

### Native Linux Issues

**Common Problems:**
- Package manager differences
- System service integration
- Path differences

**Solutions:**

1. **Detect Linux distribution:**
   ```bash
   # Check distribution
   cat /etc/os-release
   
   # Configure for specific distro
   wsm config set system.distro $(lsb_release -si)
   ```

2. **Use distribution-specific packages:**
   ```bash
   # Configure package manager
   wsm config set package_manager.type apt  # or yum, dnf, etc.
   ```

## Getting Help

### Log Files

**Default locations:**
- **System logs:** `~/.config/wsm/logs/wsm.log`
- **Installation logs:** `~/.config/wsm/logs/install.log`
- **Update logs:** `~/.config/wsm/logs/update.log`

**Enable verbose logging:**
```bash
# Temporary verbose mode
wsm -v install

# Permanent verbose mode
wsm config set logging.level DEBUG
```

### Collect Diagnostic Information

```bash
#!/bin/bash
# Create diagnostic report

echo "=== WSM Diagnostic Report ===" > wsm-diagnostic.txt
echo "Date: $(date)" >> wsm-diagnostic.txt
echo "" >> wsm-diagnostic.txt

echo "=== System Information ===" >> wsm-diagnostic.txt
uname -a >> wsm-diagnostic.txt
cat /etc/os-release >> wsm-diagnostic.txt
echo "" >> wsm-diagnostic.txt

echo "=== WSM Status ===" >> wsm-diagnostic.txt
wsm --version >> wsm-diagnostic.txt 2>&1
wsm status --detailed >> wsm-diagnostic.txt 2>&1
echo "" >> wsm-diagnostic.txt

echo "=== Configuration ===" >> wsm-diagnostic.txt
wsm config show >> wsm-diagnostic.txt 2>&1
echo "" >> wsm-diagnostic.txt

echo "=== Doctor Report ===" >> wsm-diagnostic.txt
wsm doctor >> wsm-diagnostic.txt 2>&1
echo "" >> wsm-diagnostic.txt

echo "=== Recent Logs ===" >> wsm-diagnostic.txt
tail -50 ~/.config/wsm/logs/wsm.log >> wsm-diagnostic.txt 2>&1

echo "Diagnostic report saved to: wsm-diagnostic.txt"
```

### Community Support

1. **GitHub Issues:** [Report bugs and request features](https://github.com/user/wsl-tmux-nvim-setup/issues)
2. **Discussions:** [Ask questions and share tips](https://github.com/user/wsl-tmux-nvim-setup/discussions)
3. **Wiki:** [Community documentation](https://github.com/user/wsl-tmux-nvim-setup/wiki)

### Bug Reports

When reporting issues, include:

1. **System information:**
   - OS version and architecture
   - WSL version (if applicable)
   - Python version

2. **WSM information:**
   - WSM version (`wsm --version`)
   - Configuration (`wsm config show`)
   - Doctor report (`wsm doctor`)

3. **Error details:**
   - Full error message
   - Steps to reproduce
   - Expected vs actual behavior
   - Log files (if relevant)

4. **Environment:**
   - Network configuration (proxy, firewall)
   - Security software
   - Other development tools

### Emergency Recovery

If WSM becomes completely unusable:

1. **Manual cleanup:**
   ```bash
   # Remove WSM completely
   pip uninstall wsl-tmux-nvim-setup
   rm -rf ~/.config/wsm
   rm -rf ~/.cache/wsm
   ```

2. **Fresh installation:**
   ```bash
   # Reinstall from scratch
   curl -sSL https://install.wsl-setup.com | bash
   ```

3. **Restore from backup:**
   ```bash
   # If you have backups
   wsm rollback --list-backups
   wsm rollback --backup-id latest
   ```

---

*For additional help, please visit our [support page](https://github.com/user/wsl-tmux-nvim-setup/blob/main/SUPPORT.md) or create an issue on GitHub.*