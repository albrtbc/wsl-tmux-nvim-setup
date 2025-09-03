#!/usr/bin/env python3
"""
Rollback Command for WSL-Tmux-Nvim-Setup CLI

Handles rollback to previous versions using backups.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import click
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm
    from rich.table import Table
except ImportError as e:
    print(f"Error: Required packages not found: {e}", file=sys.stderr)
    sys.exit(1)

# Add parent directories to path for imports
CLI_DIR = Path(__file__).parent.parent
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

from commands.install import InstallManager
from config import ConfigManager
from utils.backup import BackupError, BackupManager
from utils.version_utils import ComponentVersionManager, VersionComparator


class RollbackManager:
    """Manages rollback operations"""

    def __init__(self, config_manager: ConfigManager, console: Console):
        self.config = config_manager.config
        self.config_manager = config_manager
        self.console = console

        # Initialize managers
        self.backup_manager = BackupManager(
            backup_dir=self.config_manager.get_backup_directory(),
            retention_count=self.config.backup_retention,
            show_progress=self.config.show_progress,
        )
        self.install_manager = InstallManager(config_manager, console)
        self.version_manager = ComponentVersionManager()

    def list_available_rollbacks(self) -> List[Dict[str, Any]]:
        """List available rollback options"""
        rollback_options = []

        # Get backup-based rollbacks
        try:
            backups = self.backup_manager.list_backups()

            for backup in backups:
                # Try to extract version info from backup name or description
                version = "unknown"
                backup_type = "backup"

                # Parse version from backup name (e.g., "pre_install_1.0.0")
                if backup["name"].startswith("pre_install_"):
                    version = backup["name"].replace("pre_install_", "")
                    backup_type = "pre-installation"
                elif backup["name"].startswith("pre_update_"):
                    version = backup["name"].replace("pre_update_", "")
                    backup_type = "pre-update"

                rollback_options.append(
                    {
                        "type": "backup",
                        "version": version,
                        "backup_name": backup["name"],
                        "backup_type": backup_type,
                        "date": backup["date"],
                        "timestamp": backup["timestamp"],
                        "size": backup["size"],
                        "description": backup.get("description", ""),
                    }
                )

        except BackupError:
            pass  # No backups available

        # Get version-based rollbacks (GitHub releases)
        try:
            releases = self.install_manager.list_available_versions(include_prerelease=False)
            current_version = self.config_manager.status.version

            if current_version != "unknown":
                for release in releases:
                    release_version = release["tag_name"].lstrip("v")

                    # Only show older versions as rollback options
                    try:
                        if VersionComparator.compare_versions(release_version, current_version) < 0:
                            rollback_options.append(
                                {
                                    "type": "version",
                                    "version": release_version,
                                    "tag_name": release["tag_name"],
                                    "name": release["name"],
                                    "published_at": release["published_at"],
                                    "prerelease": release["prerelease"],
                                    "assets": release["assets"],
                                }
                            )
                    except Exception:
                        # Skip if version comparison fails
                        continue

        except Exception:
            pass  # GitHub access failed

        # Sort by date/timestamp (newest first)
        def sort_key(item):
            if item["type"] == "backup":
                return item["timestamp"]
            else:
                return item["published_at"] or ""

        rollback_options.sort(key=sort_key, reverse=True)
        return rollback_options

    def show_rollback_options(self, options: List[Dict[str, Any]]) -> None:
        """Display available rollback options"""
        if not options:
            self.console.print("[yellow]No rollback options available[/yellow]")
            self.console.print("To create rollback points:")
            self.console.print("  • Backups are created automatically before installations/updates")
            self.console.print("  • You can install older versions from GitHub releases")
            return

        self.console.print("[bold blue]📦 Available Rollback Options[/bold blue]\n")

        # Group by type
        backup_options = [opt for opt in options if opt["type"] == "backup"]
        version_options = [opt for opt in options if opt["type"] == "version"]

        if backup_options:
            self.console.print("[bold]From Backups:[/bold]")
            backup_table = Table()
            backup_table.add_column("Backup Name", style="cyan")
            backup_table.add_column("Version", style="yellow")
            backup_table.add_column("Date", style="green")
            backup_table.add_column("Size", style="dim")
            backup_table.add_column("Type", style="blue")

            for backup in backup_options:
                size_mb = backup["size"] / 1024 / 1024 if backup["size"] > 0 else 0
                size_str = f"{size_mb:.1f} MB" if size_mb > 0 else "N/A"

                backup_table.add_row(
                    backup["backup_name"],
                    backup["version"],
                    backup["date"],
                    size_str,
                    backup["backup_type"],
                )

            self.console.print(backup_table)
            self.console.print()

        if version_options:
            self.console.print("[bold]From Releases:[/bold]")
            version_table = Table()
            version_table.add_column("Version", style="cyan")
            version_table.add_column("Name", style="white")
            version_table.add_column("Published", style="green")
            version_table.add_column("Assets", style="dim")

            for version in version_options:
                asset_count = len(version.get("assets", []))
                version_table.add_row(
                    version["tag_name"],
                    version.get("name", ""),
                    version["published_at"][:10] if version["published_at"] else "Unknown",
                    f"{asset_count} files",
                )

            self.console.print(version_table)

    def rollback_from_backup(self, backup_name: str, restore_path: Optional[Path] = None) -> bool:
        """Rollback from a backup"""
        try:
            # Get backup info
            backups = self.backup_manager.list_backups()
            backup_info = None

            for backup in backups:
                if backup["name"] == backup_name:
                    backup_info = backup
                    break

            if not backup_info:
                raise click.ClickException(f"Backup '{backup_name}' not found")

            self.console.print(f"[blue]Rolling back from backup: {backup_name}[/blue]")
            self.console.print(f"Backup date: {backup_info['date']}")
            self.console.print(f"Size: {backup_info['size'] / 1024 / 1024:.1f} MB")

            if backup_info.get("description"):
                self.console.print(f"Description: {backup_info['description']}")

            # Confirm rollback
            if not Confirm.ask("\nRestore from this backup?", default=False):
                self.console.print("Rollback cancelled")
                return False

            # Create backup of current state before rollback
            current_backup = None
            try:
                self.console.print("[blue]Creating backup of current state...[/blue]")
                current_backup = self.backup_manager.create_backup(
                    source_paths=[self.config_manager.get_expanded_installation_path()],
                    backup_name=f"pre_rollback_{self.config_manager.status.version}",
                    description="Backup created before rollback operation",
                )
                if current_backup:
                    self.console.print("[green]✓ Current state backed up[/green]")
            except BackupError as e:
                self.console.print(f"[yellow]Warning: Could not backup current state: {e}[/yellow]")

            # Restore from backup
            restored_path = self.backup_manager.restore_backup(
                backup_name=backup_name, restore_to=restore_path
            )

            # Update installation status
            # Try to determine version from backup name
            version = backup_info.get("version", "unknown")
            if version != "unknown":
                self.config_manager.update_status(
                    version=version, last_update=datetime.now().isoformat()
                )

            self.console.print("\n[green]✓ Rollback completed successfully![/green]")
            self.console.print(f"[green]Restored to: {restored_path}[/green]")

            # Show post-rollback instructions
            self.show_post_rollback_instructions()

            return True

        except BackupError as e:
            raise click.ClickException(f"Rollback failed: {e}")

    def rollback_to_version(self, version: str, force: bool = False) -> bool:
        """Rollback by installing a specific older version"""
        current_version = self.config_manager.status.version

        if current_version == "unknown":
            raise click.ClickException("No current installation to rollback from")

        # Validate that target version is older
        try:
            if not force and VersionComparator.compare_versions(version, current_version) >= 0:
                raise click.ClickException(
                    f"Version {version} is not older than current version {current_version}. "
                    "Use --force to install anyway."
                )
        except Exception:
            if not force:
                self.console.print(
                    "[yellow]Warning: Could not compare versions. Use --force to proceed.[/yellow]"
                )
                return False

        self.console.print(f"[blue]Rolling back from {current_version} to {version}[/blue]")

        # Show rollback information
        rollback_panel = Panel(
            f"Current Version: [red]{current_version}[/red]\n"
            f"Target Version:  [green]{version}[/green]\n"
            "Operation:       [yellow]Version Rollback[/yellow]",
            title="🔄 Rollback Operation",
            title_align="left",
            border_style="yellow",
        )
        self.console.print(rollback_panel)

        # Confirm rollback
        if not force and not Confirm.ask(f"\nRollback to version {version}?", default=False):
            self.console.print("Rollback cancelled")
            return False

        # Use install manager to install the older version
        try:
            success = self.install_manager.install_version(
                version=version,
                force=True,  # Force installation
                skip_backup=False,  # Create backup before rollback
            )

            if success:
                self.console.print(
                    f"\n[green]✓ Rollback to {version} completed successfully![/green]"
                )
                self.show_post_rollback_instructions()
                return True
            else:
                self.console.print(f"\n[red]✗ Rollback to {version} failed[/red]")
                return False

        except Exception as e:
            raise click.ClickException(f"Rollback failed: {e}")

    def show_post_rollback_instructions(self) -> None:
        """Show instructions after successful rollback"""
        self.console.print("\n[bold blue]📝 Post-Rollback Instructions:[/bold blue]")

        instructions = [
            "Restart your terminal or run 'source ~/.bashrc' to apply changes",
            "Verify that all components are working correctly",
            "Run 'wsm status --all' to check the installation status",
            "If you encounter issues, you can rollback again or reinstall",
        ]

        for instruction in instructions:
            self.console.print(f"[blue]•[/blue] {instruction}")

        self.console.print("\n[dim]💡 Use 'wsm status' to verify the rollback was successful[/dim]")


@click.command()
@click.argument("target", required=False)
@click.option("--list", "-l", is_flag=True, help="List available rollback options")
@click.option("--backup", "-b", type=str, help="Rollback from specific backup name")
@click.option("--version", "-v", type=str, help="Rollback to specific version")
@click.option("--force", is_flag=True, help="Force rollback without version checks")
@click.option("--restore-to", type=click.Path(), help="Custom restore location for backup rollback")
@click.pass_obj
def rollback(ctx_obj, target, list, backup, version, force, restore_to):
    """
    Rollback to a previous version or backup

    \b
    Examples:
        wsm rollback                    # Show available rollback options
        wsm rollback --list             # List all rollback options
        wsm rollback --backup pre_install_1.0.0  # Restore from backup
        wsm rollback --version v1.0.0   # Rollback to specific version
        wsm rollback v1.0.0             # Rollback to version (shorthand)

    Rollback options include:
    • Restoring from automatic backups created before installations/updates
    • Installing an older version from GitHub releases

    A backup of the current state is created before rollback operations.
    """

    console = ctx_obj.console

    try:
        rollback_manager = RollbackManager(ctx_obj.config_manager, console)

        # Handle list option or no arguments
        if list or (not target and not backup and not version):
            console.print("[blue]Finding available rollback options...[/blue]")
            options = rollback_manager.list_available_rollbacks()
            rollback_manager.show_rollback_options(options)

            if not list and options:
                console.print("\n[dim]💡 Use specific options to perform rollback:")
                console.print("   wsm rollback --backup <backup_name>")
                console.print("   wsm rollback --version <version>")
                console.print("   wsm rollback <version>[/dim]")

            return

        # Handle backup rollback
        if backup:
            restore_path = Path(restore_to) if restore_to else None
            success = rollback_manager.rollback_from_backup(backup, restore_path)
            if not success:
                sys.exit(1)
            return

        # Handle version rollback
        rollback_version = version or target
        if rollback_version:
            # Ensure version has 'v' prefix for consistency
            if not rollback_version.startswith("v"):
                rollback_version = f"v{rollback_version}"

            success = rollback_manager.rollback_to_version(rollback_version, force=force)
            if not success:
                sys.exit(1)
            return

        # If we get here, no valid option was provided
        console.print("[red]No rollback option specified[/red]")
        console.print("Use --help to see available options")
        sys.exit(1)

    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Rollback operation failed: {e}")


if __name__ == "__main__":
    rollback()
