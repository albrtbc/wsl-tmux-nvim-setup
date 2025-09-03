#!/usr/bin/env python3
"""
Install Command for WSL-Tmux-Nvim-Setup CLI

Handles installation of specific versions or latest release.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import click
    from rich.console import Console
    from rich.table import Table
except ImportError as e:
    print(f"Error: Required packages not found: {e}", file=sys.stderr)
    sys.exit(1)

# Add parent directories to path for imports
CLI_DIR = Path(__file__).parent.parent
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

from config import ConfigManager
from utils.backup import BackupError, BackupManager
from utils.download import DownloadError, DownloadManager
from utils.extract import ExtractionError, ExtractManager
from utils.github import GitHubAPIError, GitHubClient


class InstallManager:
    """Manages the installation process"""

    def __init__(self, config_manager: ConfigManager, console: Console):
        self.config = config_manager.config
        self.config_manager = config_manager
        self.console = console

        # Initialize utility managers
        self.github_client = None
        self.download_manager = DownloadManager(
            timeout=self.config.network_timeout,
            max_retries=self.config.max_retries,
            show_progress=self.config.show_progress and not self.config.verbose,
        )
        self.extract_manager = ExtractManager(show_progress=self.config.show_progress)
        self.backup_manager = BackupManager(
            backup_dir=self.config_manager.get_backup_directory(),
            retention_count=self.config.backup_retention,
            show_progress=self.config.show_progress,
        )

    def get_github_client(self) -> GitHubClient:
        """Get GitHub client instance"""
        if not self.github_client:
            try:
                self.github_client = GitHubClient(token=self.config.github_token)
            except GitHubAPIError as e:
                raise click.ClickException(f"GitHub API error: {e}")
        return self.github_client

    def list_available_versions(self, include_prerelease: bool = False) -> List[Dict[str, Any]]:
        """List available versions for installation"""
        client = self.get_github_client()

        try:
            releases = client.list_releases(
                include_prerelease=include_prerelease, include_draft=False, limit=50
            )

            return releases

        except GitHubAPIError as e:
            raise click.ClickException(f"Failed to fetch releases: {e}")

    def get_latest_version(self, include_prerelease: bool = False) -> Optional[Dict[str, Any]]:
        """Get latest available version"""
        client = self.get_github_client()

        try:
            return client.get_latest_release(include_prerelease=include_prerelease)
        except GitHubAPIError as e:
            raise click.ClickException(f"Failed to get latest release: {e}")

    def get_version_info(self, version_tag: str) -> Optional[Dict[str, Any]]:
        """Get information about specific version"""
        client = self.get_github_client()

        try:
            return client.get_release_by_tag(version_tag)
        except GitHubAPIError:
            return None

    def create_backup(self, description: str = "Pre-installation backup") -> Optional[Path]:
        """Create backup before installation"""
        if not self.config.backup_retention or self.config.backup_retention <= 0:
            return None

        # Determine what to backup
        backup_paths = []
        installation_path = self.config_manager.get_expanded_installation_path()

        # Backup existing installation if it exists
        if installation_path.exists():
            backup_paths.append(installation_path)

        # Backup important config files
        home_dir = Path.home()
        important_configs = [
            home_dir / ".bashrc",
            home_dir / ".zshrc",
            home_dir / ".tmux.con",
            home_dir / ".config" / "nvim",
            home_dir / ".config" / "yazi",
            home_dir / ".config" / "kitty",
        ]

        for config_path in important_configs:
            if config_path.exists():
                backup_paths.append(config_path)

        if not backup_paths:
            self.console.print("[dim]No existing files to backup[/dim]")
            return None

        try:
            backup_name = f"pre_install_{self.config_manager.status.version}"
            exclude_patterns = ["*.log", "*.tmp", "__pycache__/*", "*.pyc", ".git/*"]

            return self.backup_manager.create_backup(
                source_paths=backup_paths,
                backup_name=backup_name,
                description=description,
                exclude_patterns=exclude_patterns,
            )

        except BackupError as e:
            self.console.print(f"[yellow]Warning: Backup failed: {e}[/yellow]")
            return None

    def download_release_assets(
        self, release_info: Dict[str, Any], download_dir: Path
    ) -> Dict[str, Path]:
        """Download release assets"""
        assets_to_download = {}

        # Find main archive asset
        main_asset = None
        checksums_asset = None

        for asset in release_info["assets"]:
            asset_name = asset["name"].lower()

            # Look for main archive (tar.gz, zip, etc.)
            if any(asset_name.endswith(ext) for ext in [".tar.gz", ".zip", ".tar.xz"]):
                if not main_asset or "full" in asset_name or "complete" in asset_name:
                    main_asset = asset

            # Look for checksums file
            elif "checksum" in asset_name and asset_name.endswith(".txt"):
                checksums_asset = asset

        if not main_asset:
            raise click.ClickException("No installation archive found in release assets")

        # Add assets to download
        assets_to_download["main_archive"] = {
            "url": main_asset["download_url"],
            "output_path": download_dir / main_asset["name"],
        }

        if checksums_asset:
            assets_to_download["checksums"] = {
                "url": checksums_asset["download_url"],
                "output_path": download_dir / checksums_asset["name"],
            }

        # Download assets
        try:
            if self.config.parallel_downloads and len(assets_to_download) > 1:
                # Download multiple assets in parallel
                downloaded_files = self.download_manager.download_multiple(
                    assets_to_download,
                    max_concurrent=self.config.max_concurrent_downloads,
                )
            else:
                # Download assets sequentially
                downloaded_files = {}
                for name, download_config in assets_to_download.items():
                    downloaded_files[name] = self.download_manager.download_file(**download_config)

            return downloaded_files

        except DownloadError as e:
            raise click.ClickException(f"Download failed: {e}")

    def verify_downloads(self, downloaded_files: Dict[str, Path]) -> bool:
        """Verify downloaded files using checksums"""
        if not self.config.verify_checksums:
            return True

        checksums_file = downloaded_files.get("checksums")
        if not checksums_file:
            self.console.print("[yellow]No checksums file available for verification[/yellow]")
            return True

        main_archive = downloaded_files.get("main_archive")
        if not main_archive:
            return True

        try:
            # Parse checksums file
            checksums = {}
            with open(checksums_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = line.split(None, 1)
                        if len(parts) == 2:
                            checksums[parts[1]] = parts[0]

            # Verify main archive
            archive_name = main_archive.name
            if archive_name in checksums:
                expected_hash = checksums[archive_name]

                if self.download_manager.verify_file_hash(main_archive, expected_hash, "sha256"):
                    self.console.print("[green]✓ File verification successful[/green]")
                    return True
                else:
                    self.console.print("[red]✗ File verification failed[/red]")
                    return False
            else:
                self.console.print("[yellow]No checksum found for downloaded file[/yellow]")
                return True

        except Exception as e:
            self.console.print(f"[yellow]Verification error: {e}[/yellow]")
            return True  # Don't fail installation for verification errors

    def extract_and_install(self, archive_path: Path, version_info: Dict[str, Any]) -> bool:
        """Extract archive and run installation"""
        installation_path = self.config_manager.get_expanded_installation_path()

        # Create temporary extraction directory
        with tempfile.TemporaryDirectory(prefix="wsm_install_") as temp_dir:
            temp_path = Path(temp_dir)

            try:
                # Extract archive
                self.console.print("[blue]Extracting archive...[/blue]")
                extracted_path = self.extract_manager.extract_archive(
                    archive_path, temp_path, strip_components=1
                )

                # Look for installation script
                install_script = None
                possible_scripts = [
                    "install.sh",
                    "setup.sh",
                    "bootstrap.sh",
                    "auto_install.sh",
                    "auto_install/install.sh",
                ]

                for script_name in possible_scripts:
                    script_path = extracted_path / script_name
                    if script_path.exists() and script_path.is_file():
                        install_script = script_path
                        break

                if not install_script:
                    # Look in subdirectories
                    for item in extracted_path.iterdir():
                        if item.is_dir():
                            for script_name in possible_scripts:
                                script_path = item / script_name
                                if script_path.exists() and script_path.is_file():
                                    install_script = script_path
                                    break
                        if install_script:
                            break

                if not install_script:
                    raise click.ClickException("No installation script found in archive")

                # Make script executable
                install_script.chmod(0o755)

                # Run installation script
                self.console.print(
                    f"[blue]Running installation script: {install_script.name}[/blue]"
                )

                env = os.environ.copy()
                env["WSM_INSTALLATION_PATH"] = str(installation_path)
                env["WSM_VERSION"] = version_info["tag_name"]
                env["WSM_AUTOMATED"] = "1"

                result = subprocess.run(
                    [str(install_script)],
                    cwd=extracted_path,
                    env=env,
                    capture_output=not self.config.verbose,
                    text=True,
                )

                if result.returncode != 0:
                    if result.stderr:
                        self.console.print(f"[red]Installation error: {result.stderr}[/red]")
                    raise click.ClickException(
                        f"Installation script failed (exit code: {result.returncode})"
                    )

                return True

            except ExtractionError as e:
                raise click.ClickException(f"Extraction failed: {e}")
            except subprocess.TimeoutExpired:
                raise click.ClickException("Installation script timed out")
            except Exception as e:
                raise click.ClickException(f"Installation failed: {e}")

    def update_installation_status(
        self, version_info: Dict[str, Any], components: List[str] = None
    ) -> None:
        """Update installation status after successful installation"""
        from datetime import datetime

        # Determine installed components
        if components is None:
            # Try to detect from version info or use defaults
            components = [
                "tmux",
                "neovim",
                "yazi",
                "lazygit",
                "synth-shell",
                "nerdfonts",
                "kitty",
            ]

        # Update status
        self.config_manager.update_status(
            version=version_info["tag_name"].lstrip("v"),
            installed_components=components,
            installation_date=datetime.now().isoformat(),
            last_update=datetime.now().isoformat(),
        )

    def install_version(
        self,
        version: Optional[str] = None,
        prerelease: bool = False,
        force: bool = False,
        skip_backup: bool = False,
        components: Optional[List[str]] = None,
    ) -> bool:
        """
        Install specified version or latest

        Args:
            version: Specific version to install (None for latest)
            prerelease: Allow prerelease versions
            force: Force installation even if same version is installed
            skip_backup: Skip creating backup before installation
            components: Specific components to install (None for all)

        Returns:
            True if installation successful
        """

        # Determine version to install
        if version:
            # Install specific version
            if not version.startswith("v"):
                version = f"v{version}"

            version_info = self.get_version_info(version)
            if not version_info:
                raise click.ClickException(f"Version {version} not found")

            self.console.print(f"[blue]Installing {version_info['name']}...[/blue]")

        else:
            # Install latest version
            version_info = self.get_latest_version(include_prerelease=prerelease)
            if not version_info:
                raise click.ClickException("No releases available")

            self.console.print(f"[blue]Installing latest: {version_info['name']}...[/blue]")

        # Check if already installed
        current_version = self.config_manager.status.version
        target_version = version_info["tag_name"].lstrip("v")

        if not force and current_version == target_version:
            self.console.print(f"[yellow]Version {target_version} is already installed[/yellow]")
            self.console.print("Use --force to reinstall")
            return False

        # Show version information
        self.console.print(f"\n[bold]Version:[/bold] {version_info['tag_name']}")
        self.console.print(f"[bold]Published:[/bold] {version_info['published_at'][:10]}")
        if version_info["assets"]:
            asset_size = sum(asset["size"] for asset in version_info["assets"])
            size_mb = asset_size / 1024 / 1024
            self.console.print(f"[bold]Download Size:[/bold] {size_mb:.1f} MB")

        if version_info["prerelease"]:
            self.console.print("[yellow]⚠ This is a prerelease version[/yellow]")

        # Confirm installation
        if not force and not click.confirm("\nProceed with installation?"):
            self.console.print("Installation cancelled")
            return False

        try:
            # Create backup if not skipped
            if not skip_backup:
                self.console.print("\n[blue]Creating backup...[/blue]")
                backup_path = self.create_backup("Pre-installation backup")
                if backup_path:
                    self.console.print(f"[green]✓ Backup created: {backup_path.name}[/green]")

            # Create temporary download directory
            with tempfile.TemporaryDirectory(prefix="wsm_download_") as temp_dir:
                download_dir = Path(temp_dir)

                # Download release assets
                self.console.print("\n[blue]Downloading release assets...[/blue]")
                downloaded_files = self.download_release_assets(version_info, download_dir)

                # Verify downloads
                if not self.verify_downloads(downloaded_files):
                    raise click.ClickException("File verification failed")

                # Extract and install
                self.console.print("\n[blue]Installing...[/blue]")
                main_archive = downloaded_files["main_archive"]

                if self.extract_and_install(main_archive, version_info):
                    # Update installation status
                    self.update_installation_status(version_info, components)

                    self.console.print("\n[green]✓ Installation completed successfully![/green]")
                    self.console.print(f"[green]Version {target_version} is now installed[/green]")

                    # Show post-installation notes
                    self.show_post_install_notes(version_info)

                    return True
                else:
                    raise click.ClickException("Installation process failed")

        except Exception as e:
            self.console.print(f"\n[red]✗ Installation failed: {e}[/red]")
            return False

    def show_post_install_notes(self, version_info: Dict[str, Any]) -> None:
        """Show post-installation notes and recommendations"""
        self.console.print("\n[bold blue]📝 Post-Installation Notes:[/bold blue]")

        notes = [
            "Restart your terminal or run 'source ~/.bashrc' to apply changes",
            "Run 'tmux' to start a new tmux session",
            "Use 'nvim' to open Neovim text editor",
            "Type 'yazi' to launch the file manager",
            "Use 'lazygit' for an enhanced Git experience",
        ]

        for note in notes:
            self.console.print(f"[blue]•[/blue] {note}")

        # Show release notes if available
        if version_info.get("body") and len(version_info["body"].strip()) > 0:
            self.console.print("\n[bold]Release Notes:[/bold]")
            # Truncate long release notes
            body = version_info["body"][:500]
            if len(version_info["body"]) > 500:
                body += "..."
            self.console.print(f"[dim]{body}[/dim]")

        self.console.print(f"\n[dim]For more information: {version_info['html_url']}[/dim]")


@click.command()
@click.argument("version", required=False)
@click.option("--prerelease", is_flag=True, help="Allow prerelease versions")
@click.option("--force", is_flag=True, help="Force installation even if same version is installed")
@click.option("--skip-backup", is_flag=True, help="Skip creating backup before installation")
@click.option("--components", help="Comma-separated list of components to install")
@click.option("--list-versions", is_flag=True, help="List available versions and exit")
@click.option("--interactive", is_flag=True, help="Run interactive installation wizard")
@click.option(
    "--ui-mode",
    type=click.Choice(["rich", "curses", "textual", "auto"], case_sensitive=False),
    default="auto",
    help="UI mode for interactive installation",
)
@click.pass_obj
def install(
    ctx_obj,
    version,
    prerelease,
    force,
    skip_backup,
    components,
    list_versions,
    interactive,
    ui_mode,
):
    """
    Install WSL development environment setup

    \b
    Examples:
        wsm install                    # Run interactive installation wizard
        wsm install --interactive      # Explicitly run interactive wizard
        wsm install --ui-mode textual  # Use advanced textual UI
        wsm install v1.2.0             # Install specific version
        wsm install --prerelease       # Install latest including prereleases
        wsm install --force            # Force reinstall current version
        wsm install --components tmux,neovim  # Install specific components

    \b
    Interactive Installation:
    When run without arguments, an interactive wizard will guide you through:
    • Component selection with descriptions and size information
    • Installation path configuration
    • Network and backup preferences
    • Real-time installation progress

    \b
    UI Modes:
    • auto: Automatically detect best UI (default)
    • rich: Modern terminal interface with colors and formatting
    • curses: Classic terminal interface for maximum compatibility
    • textual: Advanced TUI with mouse support (requires textual package)

    The installation will:
    1. Create a backup of existing configuration (unless --skip-backup)
    2. Download the specified version from GitHub releases
    3. Extract and run the installation script
    4. Update your shell configuration and environment
    """

    console = ctx_obj.console

    try:
        install_manager = InstallManager(ctx_obj.config_manager, console)

        # Handle interactive installation wizard
        if interactive or (not version and not components and not list_versions):
            from interactive.textual_installer import (
                create_textual_installer,
                textual_available,
            )
            from interactive.wizard import InteractiveWizard, UIMode

            # Run interactive wizard
            console.print("[blue]Starting interactive installation wizard...[/blue]\n")

            try:
                if ui_mode == "textual" and textual_available:
                    # Use textual UI
                    wizard = InteractiveWizard(ctx_obj.config_manager, console)
                    textual_installer = create_textual_installer(wizard.components)
                    result = textual_installer.run()

                    if result:
                        components = ",".join(result["components"])
                        # Apply configuration settings
                        config = result["config"]
                        if config.get("installation_path"):
                            ctx_obj.config_manager.update_config(
                                installation_path=config["installation_path"]
                            )
                    else:
                        console.print("[yellow]Interactive installation cancelled[/yellow]")
                        return
                else:
                    # Use rich/curses wizard
                    ui_mode_enum = UIMode.AUTO
                    if ui_mode == "rich":
                        ui_mode_enum = UIMode.RICH
                    elif ui_mode == "curses":
                        ui_mode_enum = UIMode.CURSES

                    wizard = InteractiveWizard(ctx_obj.config_manager, console)
                    settings = wizard.run_wizard(ui_mode_enum)

                    if settings:
                        components = ",".join(settings.components)
                        # Apply configuration settings
                        ctx_obj.config_manager.update_config(
                            installation_path=settings.installation_path,
                            backup_retention=10 if settings.backup_enabled else 0,
                            auto_update=settings.auto_update,
                            github_token=settings.github_token,
                            parallel_downloads=settings.parallel_downloads,
                            verify_checksums=settings.verify_checksums,
                        )
                    else:
                        console.print("[yellow]Interactive installation cancelled[/yellow]")
                        return

            except Exception as e:
                console.print(f"[red]Interactive wizard error: {e}[/red]")
                console.print("[yellow]Falling back to standard installation...[/yellow]")

        # Handle list versions option
        if list_versions:
            console.print("[bold]Available Versions:[/bold]\n")

            releases = install_manager.list_available_versions(include_prerelease=prerelease)

            if not releases:
                console.print("[yellow]No releases found[/yellow]")
                return

            # Create table of versions
            table = Table()
            table.add_column("Version", style="cyan")
            table.add_column("Published", style="green")
            table.add_column("Type", style="yellow")
            table.add_column("Assets", style="dim")

            for release in releases[:20]:  # Show latest 20
                version_type = "Pre-release" if release["prerelease"] else "Release"
                asset_count = len(release["assets"])

                table.add_row(
                    release["tag_name"],
                    release["published_at"][:10],
                    version_type,
                    f"{asset_count} files",
                )

            console.print(table)
            return

        # Parse components list
        component_list = None
        if components:
            component_list = [c.strip() for c in components.split(",")]

        # Perform installation
        success = install_manager.install_version(
            version=version,
            prerelease=prerelease,
            force=force,
            skip_backup=skip_backup,
            components=component_list,
        )

        if not success:
            sys.exit(1)

    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Installation failed: {e}")


if __name__ == "__main__":
    install()
