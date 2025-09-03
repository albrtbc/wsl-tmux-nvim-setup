#!/usr/bin/env python3
"""
Update Command for WSL-Tmux-Nvim-Setup CLI

Handles checking for and installing updates.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import click
    from rich.console import Console
    from rich.panel import Panel
except ImportError as e:
    print(f"Error: Required packages not found: {e}", file=sys.stderr)
    sys.exit(1)

# Add parent directories to path for imports
CLI_DIR = Path(__file__).parent.parent
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

try:
    from commands.install import InstallManager
    from config import ConfigManager
    from utils.github import GitHubAPIError
    from utils.version_utils import ComponentVersionManager, VersionComparator
except ImportError as e:
    print(f"Error: CLI modules not found: {e}", file=sys.stderr)
    sys.exit(1)


class UpdateManager:
    """Manages update checking and installation"""

    def __init__(self, config_manager: ConfigManager, console: Console):
        self.config = config_manager.config
        self.config_manager = config_manager
        self.console = console

        # Initialize managers
        self.install_manager = InstallManager(config_manager, console)
        self.version_manager = ComponentVersionManager()

    def check_for_updates(self, include_prerelease: bool = False) -> Dict[str, Any]:
        """
        Check for available updates

        Returns:
            Dictionary with update information
        """
        current_version = self.config_manager.status.version

        if current_version == "unknown":
            return {
                "current_version": current_version,
                "latest_version": None,
                "update_available": False,
                "message": 'No installation detected. Use "wsm install" to install.',
                "update_type": None,
            }

        try:
            # Get latest release
            latest_release = self.install_manager.get_latest_version(
                include_prerelease=include_prerelease
            )

            if not latest_release:
                return {
                    "current_version": current_version,
                    "latest_version": None,
                    "update_available": False,
                    "message": "No releases found on GitHub",
                    "update_type": None,
                }

            latest_version = latest_release["tag_name"].lstrip("v")

            # Compare versions
            try:
                current_sem = VersionComparator.parse_version(current_version)
                latest_sem = VersionComparator.parse_version(latest_version)

                is_newer = VersionComparator.is_newer_version(current_sem, latest_sem)
                update_type = (
                    VersionComparator.get_update_type(current_sem, latest_sem) if is_newer else None
                )
                breaking_change = (
                    VersionComparator.check_breaking_change(current_sem, latest_sem)
                    if is_newer
                    else False
                )

                message = None
                if not is_newer:
                    if VersionComparator.compare_versions(current_sem, latest_sem) == 0:
                        message = "You are running the latest version"
                    else:
                        message = "Your version is newer than the latest release"

                return {
                    "current_version": current_version,
                    "latest_version": latest_version,
                    "latest_release": latest_release,
                    "update_available": is_newer,
                    "update_type": update_type,
                    "breaking_change": breaking_change,
                    "message": message,
                }

            except Exception:
                # If version comparison fails, assume update is available
                return {
                    "current_version": current_version,
                    "latest_version": latest_version,
                    "latest_release": latest_release,
                    "update_available": True,
                    "update_type": "unknown",
                    "breaking_change": False,
                    "message": "Version comparison failed, update recommended",
                }

        except GitHubAPIError as e:
            return {
                "current_version": current_version,
                "latest_version": None,
                "update_available": False,
                "message": f"Failed to check for updates: {e}",
                "update_type": None,
                "error": str(e),
            }

    def check_component_updates(self) -> Dict[str, Dict[str, Any]]:
        """Check for component-specific updates"""
        # This would integrate with component-specific version checking
        # For now, we'll return empty as component updates are handled
        # through the main release updates
        return {}

    def perform_update(
        self,
        include_prerelease: bool = False,
        force: bool = False,
        skip_backup: bool = False,
    ) -> bool:
        """
        Perform update to latest version

        Returns:
            True if update successful
        """
        # Check for updates first
        update_info = self.check_for_updates(include_prerelease=include_prerelease)

        if not update_info["update_available"]:
            self.console.print(f"[green]✓ {update_info['message']}[/green]")
            return True

        if "error" in update_info:
            self.console.print(f"[red]✗ {update_info['message']}[/red]")
            return False

        latest_release = update_info["latest_release"]

        # Show update information
        self.show_update_info(update_info)

        # Confirm update
        if not force:
            if update_info.get("breaking_change"):
                self.console.print(
                    "\n[red]⚠ WARNING: This is a major version update that may include breaking changes![/red]"
                )
                self.console.print("Please review the release notes before proceeding.")

            if not click.confirm(f"\nUpdate to {latest_release['name']}?"):
                self.console.print("Update cancelled")
                return False

        # Perform installation using install manager
        try:
            success = self.install_manager.install_version(
                version=latest_release["tag_name"],
                force=True,  # Force update even if "same" version
                skip_backup=skip_backup,
            )

            if success:
                # Mark update check timestamp
                self.config_manager.mark_update_check()
                self.console.print("\n[green]✓ Update completed successfully![/green]")

                return True
            else:
                self.console.print("\n[red]✗ Update failed[/red]")
                return False

        except Exception as e:
            self.console.print(f"\n[red]✗ Update failed: {e}[/red]")
            return False

    def show_update_info(self, update_info: Dict[str, Any]) -> None:
        """Display update information to user"""
        current = update_info["current_version"]
        latest = update_info["latest_version"]
        update_type = update_info.get("update_type", "unknown")

        # Create info panel
        info_lines = [
            f"Current Version: [blue]{current}[/blue]",
            f"Latest Version:  [green]{latest}[/green]",
            f"Update Type:     [yellow]{update_type.title()}[/yellow]",
        ]

        if update_info.get("breaking_change"):
            info_lines.append("[red]Breaking Changes: Yes[/red]")

        panel = Panel(
            "\n".join(info_lines),
            title="🔄 Update Available",
            title_align="left",
            border_style="blue",
        )

        self.console.print(panel)

        # Show release notes if available
        latest_release = update_info.get("latest_release")
        if latest_release and latest_release.get("body"):
            self.console.print("\n[bold]Release Notes:[/bold]")

            # Format and truncate release notes
            body = latest_release["body"].strip()
            if len(body) > 300:
                body = body[:300] + "..."

            # Split into lines and add indentation
            lines = body.split("\n")
            for line in lines:
                self.console.print(f"  {line}")

            self.console.print(f"\n[dim]Full release notes: {latest_release['html_url']}[/dim]")

    def auto_update_check(self) -> Optional[Dict[str, Any]]:
        """
        Check for updates if auto-update is enabled and it's time to check

        Returns:
            Update info if check was performed, None otherwise
        """
        if not self.config.auto_update:
            return None

        if not self.config_manager.should_check_for_updates():
            return None

        try:
            update_info = self.check_for_updates()
            self.config_manager.mark_update_check()

            return update_info

        except Exception:
            # Silently fail auto-update checks
            return None

    def show_update_summary(self, update_info: Dict[str, Any]) -> None:
        """Show a summary of update status"""
        if update_info["update_available"]:
            current = update_info["current_version"]
            latest = update_info["latest_version"]
            update_type = update_info.get("update_type", "unknown")

            self.console.print(
                f"[yellow]💡 Update available: {current} → {latest} ({update_type})[/yellow]"
            )
            self.console.print("[yellow]Run 'wsm update' to install the latest version[/yellow]")
        else:
            self.console.print("[green]✓ You are running the latest version[/green]")


@click.command()
@click.option("--check", "-c", is_flag=True, help="Only check for updates, do not install")
@click.option("--prerelease", is_flag=True, help="Include prerelease versions")
@click.option("--force", is_flag=True, help="Force update without confirmation")
@click.option("--skip-backup", is_flag=True, help="Skip creating backup before update")
@click.option(
    "--auto",
    is_flag=True,
    help="Perform automatic update if available (non-interactive)",
)
@click.pass_obj
def update(ctx_obj, check, prerelease, force, skip_backup, auto):
    """
    Check for and install updates

    \b
    Examples:
        wsm update              # Check and install latest update
        wsm update --check      # Only check for updates
        wsm update --prerelease # Include prerelease versions
        wsm update --force      # Update without confirmation
        wsm update --auto       # Automatic update (if available)

    The update process will:
    1. Check GitHub for the latest release
    2. Compare with your current version
    3. Download and install the update if available
    4. Create a backup before updating (unless --skip-backup)
    """

    console = ctx_obj.console

    try:
        update_manager = UpdateManager(ctx_obj.config_manager, console)

        if check:
            # Only check for updates
            console.print("[blue]Checking for updates...[/blue]")

            update_info = update_manager.check_for_updates(include_prerelease=prerelease)

            if update_info["update_available"]:
                update_manager.show_update_info(update_info)
                console.print("\n[green]Run 'wsm update' to install the update[/green]")
            else:
                if "error" in update_info:
                    console.print(f"[red]✗ {update_info['message']}[/red]")
                    sys.exit(1)
                else:
                    console.print(f"[green]✓ {update_info['message']}[/green]")

            return

        # Perform update
        console.print("[blue]Checking for updates...[/blue]")

        # Handle auto update
        if auto:
            update_info = update_manager.auto_update_check()
            if not update_info:
                console.print("[dim]Auto-update not needed at this time[/dim]")
                return

            if not update_info["update_available"]:
                console.print("[green]✓ You are running the latest version[/green]")
                return

            # Proceed with automatic update
            force = True

        # Perform the update
        success = update_manager.perform_update(
            include_prerelease=prerelease, force=force, skip_backup=skip_backup
        )

        if not success:
            sys.exit(1)

    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Update failed: {e}")


if __name__ == "__main__":
    update()
