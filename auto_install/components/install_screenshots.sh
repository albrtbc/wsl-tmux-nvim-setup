#!/bin/bash
set -euo pipefail

# Install Windows-to-WSL2 Screenshot Bridge
# Clones the repo and creates a Windows Scheduled Task to auto-start on login

INSTALL_DIR="$HOME/dev/windows-to-wsl2-screenshots"

# Clone repo (or update if already exists)
if [ -d "$INSTALL_DIR" ]; then
    echo "Repository already exists, pulling latest..."
    git -C "$INSTALL_DIR" pull
else
    mkdir -p "$HOME/dev"
    git clone https://github.com/jddev273/windows-to-wsl2-screenshots.git "$INSTALL_DIR"
fi

# Create screenshots directory
mkdir -p "$HOME/.screenshots"

# Create Windows Scheduled Task to start monitor on login
PS_SCRIPT=$(wslpath -w "$INSTALL_DIR/auto-clipboard-monitor.ps1")
powershell.exe -Command "
\$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument \"-WindowStyle Hidden -ExecutionPolicy Bypass -File $PS_SCRIPT\"
\$trigger = New-ScheduledTaskTrigger -AtLogOn
\$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName 'WSL2-Screenshot-Monitor' -Action \$action -Trigger \$trigger -Settings \$settings -Description 'Auto-save Windows screenshots to WSL2' -Force
"

# Add source to .bashrc for manual start/stop commands
SOURCE_LINE="source $INSTALL_DIR/screenshot-functions.sh"
grep -qxF "$SOURCE_LINE" ~/.bashrc || echo "$SOURCE_LINE" >> ~/.bashrc

echo "Windows-to-WSL2 Screenshot Bridge installed."
echo "Scheduled Task created - will auto-start on login."
echo "Commands available: start-screenshot-monitor, stop-screenshot-monitor, check-screenshot-monitor"
