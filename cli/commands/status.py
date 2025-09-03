#!/usr/bin/env python3
"""
Status Command for WSL-Tmux-Nvim-Setup CLI

Shows current installation status and system information.
"""

import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

try:
    import click
    import psutil
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
except ImportError as e:
    print(f"Error: Required packages not found: {e}", file=sys.stderr)
    sys.exit(1)

# Add parent directories to path for imports
CLI_DIR = Path(__file__).parent.parent
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

from commands.update import UpdateManager
from config import ConfigManager
from utils.version_utils import ComponentVersionManager


class StatusManager:
    """Manages status reporting and system information"""

    def __init__(self, config_manager: ConfigManager, console: Console):
        self.config = config_manager.config
        self.config_manager = config_manager
        self.console = console
        self.version_manager = ComponentVersionManager()

    def get_installation_status(self) -> Dict[str, Any]:
        """Get current installation status"""
        status = self.config_manager.status

        return {
            "version": status.version,
            "installed_components": status.installed_components or [],
            "installation_date": status.installation_date,
            "last_update": status.last_update,
            "last_update_check": status.last_update_check,
            "installation_path": str(self.config_manager.get_expanded_installation_path()),
        }

    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        system_info = {
            "os": platform.system(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
            "shell": Path(os.environ.get("SHELL", "")).name,
            "terminal": os.environ.get("TERM", "unknown"),
            "wsl_detected": False,
            "wsl_version": None,
            "ubuntu_version": None,
        }

        # Detect WSL
        try:
            with open("/proc/version", "r") as f:
                version_info = f.read().lower()
                if "microsoft" in version_info or "wsl" in version_info:
                    system_info["wsl_detected"] = True

                    # Try to determine WSL version
                    if "wsl2" in version_info or "microsoft-standard-wsl2" in version_info:
                        system_info["wsl_version"] = "2"
                    else:
                        system_info["wsl_version"] = "1"
        except FileNotFoundError:
            pass

        # Get Ubuntu version if available
        try:
            result = subprocess.run(
                ["lsb_release", "-rs"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                system_info["ubuntu_version"] = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Memory information
        try:
            memory = psutil.virtual_memory()
            system_info["memory_total"] = memory.total
            system_info["memory_available"] = memory.available
            system_info["memory_percent"] = memory.percent
        except Exception:
            pass

        # Disk space
        try:
            disk = psutil.disk_usage(str(Path.home()))
            system_info["disk_total"] = disk.total
            system_info["disk_free"] = disk.free
            system_info["disk_percent"] = (disk.used / disk.total) * 100
        except Exception:
            pass

        return system_info

    def get_component_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of individual components"""
        component_status = {}

        components = {
            "tmux": {"command": "tmux -V", "version_pattern": r"tmux (\d+\.\d+)", "expected": True},
            "nvim": {
                "command": "nvim --version",
                "version_pattern": r"NVIM v(\d+\.\d+\.\d+)",
                "expected": True,
            },
            "yazi": {
                "command": "yazi --version",
                "version_pattern": r"Yazi (\d+\.\d+\.\d+)",
                "expected": True,
            },
            "lazygit": {
                "command": "lazygit --version",
                "version_pattern": r"version=(\d+\.\d+\.\d+)",
                "expected": True,
            },
            "git": {
                "command": "git --version",
                "version_pattern": r"git version (\d+\.\d+\.\d+)",
                "expected": True,
            },
            "kitty": {
                "command": "kitty --version",
                "version_pattern": r"kitty (\d+\.\d+\.\d+)",
                "expected": False,  # Optional component
            },
        }

        for component, config in components.items():
            status = {
                "installed": False,
                "version": None,
                "expected": config["expected"],
                "working": False,
            }

            try:
                result = subprocess.run(
                    config["command"].split(), capture_output=True, text=True, timeout=5
                )

                if result.returncode == 0:
                    status["installed"] = True
                    status["working"] = True

                    # Extract version
                    import re

                    output = result.stdout + result.stderr
                    match = re.search(config["version_pattern"], output)
                    if match:
                        status["version"] = match.group(1)

            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

            component_status[component] = status

        return component_status

    def check_configuration(self) -> Dict[str, Any]:
        """Check configuration files and settings"""
        config_checks = {}

        # Check important config files
        home = Path.home()
        config_files = {
            ".bashrc": home / ".bashrc",
            ".zshrc": home / ".zshrc",
            ".tmux.con": home / ".tmux.con",
            "nvim config": home / ".config" / "nvim" / "init.lua",
            "yazi config": home / ".config" / "yazi" / "yazi.toml",
            "kitty config": home / ".config" / "kitty" / "kitty.conf",
        }

        for name, path in config_files.items():
            config_checks[name] = {
                "exists": path.exists(),
                "path": str(path),
                "size": path.stat().st_size if path.exists() else 0,
                "modified": path.stat().st_mtime if path.exists() else None,
            }

        # Check WSM configuration
        config_checks["wsm_config"] = {
            "exists": self.config_manager.config_file.exists(),
            "path": str(self.config_manager.config_file),
            "valid": True,  # We wouldn't get here if config was invalid
            "auto_update": self.config.auto_update,
            "backup_retention": self.config.backup_retention,
        }

        return config_checks

    def get_update_status(self) -> Dict[str, Any]:
        """Get update status information"""
        try:
            update_manager = UpdateManager(self.config_manager, self.console)
            update_info = update_manager.check_for_updates()
            return update_info
        except Exception as e:
            return {
                "error": str(e),
                "update_available": False,
                "current_version": self.config_manager.status.version,
                "message": f"Could not check for updates: {e}",
            }

    def show_installation_status(self, detailed: bool = False) -> None:
        """Display installation status"""
        status = self.get_installation_status()

        # Main status panel
        if status["version"] != "unknown":
            title = f"🚀 WSL-Tmux-Nvim-Setup v{status['version']}"
            status_color = "green"

            status_lines = [
                f"Version: [bold]{status['version']}[/bold]",
            ]

            if status["installation_date"]:
                from datetime import datetime

                try:
                    install_date = datetime.fromisoformat(
                        status["installation_date"].replace("Z", "+00:00")
                    )
                    status_lines.append(f"Installed: {install_date.strftime('%Y-%m-%d %H:%M')}")
                except Exception:
                    status_lines.append(f"Installed: {status['installation_date']}")

            if status["last_update"]:
                try:
                    update_date = datetime.fromisoformat(
                        status["last_update"].replace("Z", "+00:00")
                    )
                    status_lines.append(f"Last Updated: {update_date.strftime('%Y-%m-%d %H:%M')}")
                except Exception:
                    status_lines.append(f"Last Updated: {status['last_update']}")

            if status["installed_components"]:
                components = ", ".join(status["installed_components"])
                status_lines.append(f"Components: {components}")

        else:
            title = "❌ WSL-Tmux-Nvim-Setup - Not Installed"
            status_color = "red"
            status_lines = ["No installation detected", "Run 'wsm install' to get started"]

        status_panel = Panel(
            "\n".join(status_lines), title=title, title_align="left", border_style=status_color
        )
        self.console.print(status_panel)

        if detailed and status["installation_path"]:
            self.console.print(f"\n[dim]Installation Path: {status['installation_path']}[/dim]")

    def show_system_info(self) -> None:
        """Display system information"""
        system = self.get_system_info()

        self.console.print("\n[bold blue]💻 System Information[/bold blue]")

        table = Table(show_header=False, box=None, padding=(0, 2))

        table.add_row("OS:", f"{system['os']} {system.get('os_release', '')}")
        table.add_row("Architecture:", system["architecture"])
        table.add_row("Hostname:", system["hostname"])
        table.add_row("Shell:", system["shell"] or "unknown")
        table.add_row("Terminal:", system["terminal"])
        table.add_row("Python:", system["python_version"])

        if system["wsl_detected"]:
            wsl_info = f"WSL {system.get('wsl_version', 'unknown')}"
            if system.get("ubuntu_version"):
                wsl_info += f" (Ubuntu {system['ubuntu_version']})"
            table.add_row("Environment:", f"[green]{wsl_info}[/green]")
        else:
            table.add_row("Environment:", "[yellow]Not WSL[/yellow]")

        # Memory info
        if "memory_total" in system:
            total_gb = system["memory_total"] / (1024**3)
            available_gb = system["memory_available"] / (1024**3)
            memory_info = f"{available_gb:.1f}GB available / {total_gb:.1f}GB total"
            table.add_row("Memory:", memory_info)

        # Disk space
        if "disk_total" in system:
            total_gb = system["disk_total"] / (1024**3)
            free_gb = system["disk_free"] / (1024**3)
            disk_info = f"{free_gb:.1f}GB free / {total_gb:.1f}GB total"
            table.add_row("Disk Space:", disk_info)

        self.console.print(table)

    def show_component_status(self) -> None:
        """Display component status"""
        components = self.get_component_status()

        self.console.print("\n[bold blue]🔧 Components[/bold blue]")

        table = Table()
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("Version", style="green")
        table.add_column("Notes", style="dim")

        for name, status in components.items():
            # Status display
            if status["installed"] and status["working"]:
                status_display = "[green]✓ Installed[/green]"
            elif status["installed"]:
                status_display = "[yellow]⚠ Issues[/yellow]"
            elif status["expected"]:
                status_display = "[red]✗ Missing[/red]"
            else:
                status_display = "[dim]- Not installed[/dim]"

            # Version display
            version_display = status.get("version", "[dim]N/A[/dim]")

            # Notes
            notes = []
            if not status["installed"] and status["expected"]:
                notes.append("Required component")
            elif not status["expected"]:
                notes.append("Optional")

            notes_display = ", ".join(notes) if notes else ""

            table.add_row(name.title(), status_display, version_display, notes_display)

        self.console.print(table)

    def show_configuration_status(self) -> None:
        """Display configuration status"""
        config_checks = self.check_configuration()

        self.console.print("\n[bold blue]⚙️ Configuration[/bold blue]")

        table = Table()
        table.add_column("File", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("Size", style="yellow")
        table.add_column("Path", style="dim")

        for name, info in config_checks.items():
            if name == "wsm_config":
                # Special handling for WSM config
                status_display = (
                    "[green]✓ Valid[/green]" if info.get("valid") else "[red]✗ Invalid[/red]"
                )
                size_display = ""
                table.add_row("WSM Config", status_display, size_display, info["path"])
                continue

            # Regular config files
            if info["exists"]:
                status_display = "[green]✓ Present[/green]"
                size_kb = info["size"] / 1024
                size_display = f"{size_kb:.1f} KB" if size_kb > 0 else "0 KB"
            else:
                status_display = "[dim]- Missing[/dim]"
                size_display = ""

            table.add_row(name, status_display, size_display, info["path"])

        self.console.print(table)

        # WSM-specific settings
        self.console.print("\n[bold]WSM Settings:[/bold]")
        settings_table = Table(show_header=False, box=None, padding=(0, 2))
        settings_table.add_row(
            "Auto Update:", "✓ Enabled" if self.config.auto_update else "✗ Disabled"
        )
        settings_table.add_row("Backup Retention:", f"{self.config.backup_retention} backups")
        settings_table.add_row(
            "GitHub Token:", "✓ Set" if self.config.github_token else "✗ Not set"
        )

        self.console.print(settings_table)

    def show_update_status(self) -> None:
        """Display update status"""
        update_info = self.get_update_status()

        self.console.print("\n[bold blue]🔄 Updates[/bold blue]")

        if "error" in update_info:
            self.console.print(f"[red]Error checking for updates: {update_info['error']}[/red]")
            return

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_row("Current Version:", f"[blue]{update_info['current_version']}[/blue]")

        if update_info["update_available"]:
            table.add_row("Latest Version:", f"[green]{update_info['latest_version']}[/green]")
            update_type = update_info.get("update_type", "unknown")
            table.add_row("Update Type:", f"[yellow]{update_type.title()}[/yellow]")

            if update_info.get("breaking_change"):
                table.add_row("Breaking Changes:", "[red]Yes[/red]")

            self.console.print(table)
            self.console.print("\n[green]💡 Run 'wsm update' to install the latest version[/green]")
        else:
            table.add_row("Status:", "[green]✓ Up to date[/green]")
            self.console.print(table)

        # Show last update check
        status = self.config_manager.status
        if status.last_update_check:
            try:
                from datetime import datetime

                check_date = datetime.fromisoformat(status.last_update_check.replace("Z", "+00:00"))
                self.console.print(
                    f"\n[dim]Last checked: {check_date.strftime('%Y-%m-%d %H:%M')}[/dim]"
                )
            except Exception:
                self.console.print(f"\n[dim]Last checked: {status.last_update_check}[/dim]")


@click.command()
@click.option("--detailed", "-d", is_flag=True, help="Show detailed system information")
@click.option("--components", "-c", is_flag=True, help="Show component status")
@click.option("--config", is_flag=True, help="Show configuration status")
@click.option("--updates", "-u", is_flag=True, help="Check update status")
@click.option(
    "--all", "-a", is_flag=True, help="Show all information (equivalent to -d -c --config -u)"
)
@click.pass_obj
def status(ctx_obj, detailed, components, config, updates, all):
    """
    Show current installation and system status

    \b
    Examples:
        wsm status              # Basic status information
        wsm status --detailed   # Include system information
        wsm status --components # Show component status
        wsm status --config     # Show configuration status
        wsm status --updates    # Check for available updates
        wsm status --all        # Show everything

    This command provides a comprehensive overview of your current
    WSL-Tmux-Nvim-Setup installation, system environment, and
    configuration status.
    """

    console = ctx_obj.console

    try:
        status_manager = StatusManager(ctx_obj.config_manager, console)

        # Determine what to show
        if all:
            detailed = components = config = updates = True

        # Always show basic installation status
        status_manager.show_installation_status(detailed=detailed)

        # Show system info if requested or detailed
        if detailed:
            status_manager.show_system_info()

        # Show component status if requested
        if components:
            status_manager.show_component_status()

        # Show configuration status if requested
        if config:
            status_manager.show_configuration_status()

        # Show update status if requested
        if updates:
            status_manager.show_update_status()

        # If no specific options, show helpful tips
        if not any([detailed, components, config, updates]):
            console.print("\n[dim]💡 Use --help to see all available options")
            console.print("💡 Use --all to show complete status information[/dim]")

    except Exception as e:
        raise click.ClickException(f"Failed to get status information: {e}")


if __name__ == "__main__":
    status()
