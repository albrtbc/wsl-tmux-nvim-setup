#!/usr/bin/env python3
"""
WSL-Tmux-Nvim-Setup Manager (wsm) - Main CLI Application

A comprehensive command-line interface for managing WSL development environment
setup, updates, and configuration.
"""

import os
import sys
from pathlib import Path

# Ensure the CLI directory is in the Python path
CLI_DIR = Path(__file__).parent
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

try:
    import click
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
except ImportError as e:
    print(f"Error: Required packages not found: {e}", file=sys.stderr)
    print("Install dependencies with: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

from commands import config_cmd, install, list_cmd, rollback, status, update
from config import ConfigManager, get_default_config_manager


class WSMContext:
    """Shared context for WSM CLI commands"""

    def __init__(self):
        self.console = Console()
        self.config_manager = None
        self.verbose = False
        self.quiet = False

    def initialize(self, config_dir: Path = None, verbose: bool = False, quiet: bool = False):
        """Initialize the WSM context"""
        self.verbose = verbose
        self.quiet = quiet

        try:
            if config_dir:
                self.config_manager = ConfigManager(str(config_dir))
            else:
                self.config_manager = get_default_config_manager()

            # Update config with CLI preferences
            if verbose:
                self.config_manager.update_config(verbose=True)

        except Exception as e:
            self.console.print(f"[red]Error initializing configuration: {e}[/red]")
            sys.exit(1)

    def print_info(self, message: str):
        """Print info message unless in quiet mode"""
        if not self.quiet:
            self.console.print(f"[blue]ℹ {message}[/blue]")

    def print_success(self, message: str):
        """Print success message"""
        if not self.quiet:
            self.console.print(f"[green]✓ {message}[/green]")

    def print_warning(self, message: str):
        """Print warning message"""
        if not self.quiet:
            self.console.print(f"[yellow]⚠ {message}[/yellow]")

    def print_error(self, message: str):
        """Print error message"""
        self.console.print(f"[red]✗ {message}[/red]")

    def print_verbose(self, message: str):
        """Print message only in verbose mode"""
        if self.verbose and not self.quiet:
            self.console.print(f"[dim]{message}[/dim]")


# Global context object
ctx = WSMContext()


@click.group(invoke_without_command=True)
@click.option("--config-dir", "-c", type=click.Path(), help="Configuration directory path")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-error output")
@click.option("--version", is_flag=True, help="Show version and exit")
@click.pass_context
def cli(click_ctx, config_dir, verbose, quiet, version):
    """
    WSL-Tmux-Nvim-Setup Manager (wsm)

    A comprehensive CLI tool for managing your WSL development environment.

    \b
    Common Commands:
      wsm install [version]     Install specific version or latest
      wsm update [--check]      Update to latest release
      wsm list                  List available releases
      wsm status                Show current version and status
      wsm config                Manage configuration preferences
      wsm rollback [version]    Rollback to previous version

    \b
    Examples:
      wsm install               # Install latest release
      wsm install v1.2.0        # Install specific version
      wsm update --check        # Check for updates without installing
      wsm status                # Show installation status
      wsm config set auto_update true  # Enable auto-updates
      wsm rollback              # Rollback to previous version

    For more help on specific commands, use: wsm <command> --help
    """

    # Handle version flag
    if version:
        from utils.version_utils import ComponentVersionManager

        try:
            version_manager = ComponentVersionManager()
            current_version = version_manager.version_manager.get_current_version()
            click.echo(f"WSL-Tmux-Nvim-Setup Manager v{current_version}")
            ctx.cleanup()
            return
        except Exception:
            click.echo("WSL-Tmux-Nvim-Setup Manager v1.0.0")
            ctx.cleanup()
            return

    # Initialize context
    config_path = Path(config_dir) if config_dir else None
    ctx.initialize(config_path, verbose, quiet)

    # Store context for subcommands
    click_ctx.obj = ctx

    # If no command specified, show help
    if click_ctx.invoked_subcommand is None:
        show_welcome_screen()


def show_welcome_screen():
    """Show welcome screen with basic information"""
    console = Console()

    # Create welcome panel
    welcome_text = Text()
    welcome_text.append("WSL-Tmux-Nvim-Setup Manager", style="bold blue")
    welcome_text.append(
        "\n\nA comprehensive CLI tool for managing your WSL development environment."
    )
    welcome_text.append("\n\nGet started with: ")
    welcome_text.append("wsm install", style="bold green")
    welcome_text.append(" or ")
    welcome_text.append("wsm --help", style="bold green")
    welcome_text.append(" for more options.")

    panel = Panel(welcome_text, title="🚀 Welcome", title_align="left", border_style="blue")
    console.print(panel)

    # Show current status if available
    try:
        config_manager = get_default_config_manager()
        status = config_manager.status

        if status.version != "unknown" or status.installed_components:
            console.print("\n[bold]Current Installation:[/bold]")

            # Create status table
            table = Table(show_header=False, box=None, padding=(0, 2))

            table.add_row("Version:", f"[green]{status.version}[/green]")

            if status.installed_components:
                components_str = ", ".join(status.installed_components)
                table.add_row("Components:", f"[blue]{components_str}[/blue]")

            if status.installation_date:
                table.add_row("Installed:", f"[dim]{status.installation_date}[/dim]")

            console.print(table)

            # Check for updates
            if config_manager.should_check_for_updates():
                console.print("\n[yellow]💡 Run 'wsm update --check' to check for updates[/yellow]")

    except Exception:
        # Don't fail if we can't show status
        pass


# Register command modules
cli.add_command(install.install)
cli.add_command(update.update)
cli.add_command(list_cmd.list_releases)
cli.add_command(status.status)
cli.add_command(config_cmd.config)
cli.add_command(rollback.rollback)


# Add some utility commands
@cli.command()
@click.pass_obj
def doctor(ctx_obj):
    """Run diagnostics to check system health and compatibility"""
    import platform

    from utils.version_utils import ComponentVersionManager

    console = ctx_obj.console

    console.print("[bold blue]🔍 WSM Doctor - System Diagnostics[/bold blue]\n")

    # Check system information
    console.print("[bold]System Information:[/bold]")
    table = Table(show_header=False, box=None, padding=(0, 2))

    table.add_row("OS:", platform.system())
    table.add_row("Architecture:", platform.machine())
    table.add_row("Python:", f"{platform.python_version()}")

    # Check if we're in WSL
    try:
        with open("/proc/version", "r") as f:
            version_info = f.read()
            if "microsoft" in version_info.lower() or "wsl" in version_info.lower():
                table.add_row("Environment:", "[green]WSL[/green]")
            else:
                table.add_row("Environment:", "[yellow]Not WSL[/yellow]")
    except Exception:
        table.add_row("Environment:", "[dim]Unknown[/dim]")

    console.print(table)
    console.print()

    # Check dependencies
    console.print("[bold]Dependencies:[/bold]")
    dep_table = Table(show_header=True)
    dep_table.add_column("Package", style="cyan")
    dep_table.add_column("Status", style="green")
    dep_table.add_column("Version", style="dim")

    dependencies = [
        ("click", "click"),
        ("rich", "rich"),
        ("requests", "requests"),
        ("pydantic", "pydantic"),
        ("yaml", "pyyaml"),
        ("tqdm", "tqdm"),
        ("psutil", "psutil"),
    ]

    for import_name, package_name in dependencies:
        try:
            module = __import__(import_name)
            version = getattr(module, "__version__", "Unknown")
            dep_table.add_row(package_name, "✓ Installed", version)
        except ImportError:
            dep_table.add_row(package_name, "✗ Missing", "")

    console.print(dep_table)
    console.print()

    # Check configuration
    console.print("[bold]Configuration:[/bold]")
    config_table = Table(show_header=False, box=None, padding=(0, 2))

    try:
        config = ctx_obj.config_manager.config
        status = ctx_obj.config_manager.status

        config_table.add_row("Config Directory:", str(ctx_obj.config_manager.config_dir))
        config_table.add_row("Installation Path:", config.installation_path)
        config_table.add_row("Current Version:", status.version)
        config_table.add_row("Auto Update:", "✓ Enabled" if config.auto_update else "✗ Disabled")
        config_table.add_row("Backup Retention:", str(config.backup_retention))

    except Exception as e:
        config_table.add_row("Configuration:", f"[red]Error: {e}[/red]")

    console.print(config_table)
    console.print()

    # Check compatibility
    console.print("[bold]Compatibility:[/bold]")
    try:
        version_manager = ComponentVersionManager()
        compatibility = version_manager.check_system_compatibility()

        compat_table = Table(show_header=False, box=None, padding=(0, 2))

        for check, result in compatibility.items():
            if result is True:
                status_icon = "[green]✓[/green]"
            elif result is False:
                status_icon = "[red]✗[/red]"
            else:
                status_icon = "[yellow]?[/yellow]"

            check_name = check.replace("_", " ").title()
            compat_table.add_row(f"{check_name}:", status_icon)

        console.print(compat_table)

    except Exception as e:
        console.print(f"[red]Error checking compatibility: {e}[/red]")

    console.print()

    # Recommendations
    console.print("[bold]Recommendations:[/bold]")
    recommendations = []

    try:
        if not ctx_obj.config_manager.config.auto_update:
            recommendations.append("Enable auto-updates with: wsm config set auto_update true")

        if ctx_obj.config_manager.status.version == "unknown":
            recommendations.append("Install WSL setup with: wsm install")

        if not ctx_obj.config_manager.config.github_token:
            recommendations.append(
                "Set GitHub token for higher API limits: wsm config set github_token <token>"
            )

    except Exception:
        pass

    if recommendations:
        for rec in recommendations:
            console.print(f"[yellow]💡 {rec}[/yellow]")
    else:
        console.print("[green]✓ No issues found![/green]")


@cli.command()
@click.pass_obj
def version_info(ctx_obj):
    """Show detailed version information"""
    from utils.version_utils import ComponentVersionManager

    console = ctx_obj.console

    try:
        version_manager = ComponentVersionManager()
        current_version = version_manager.version_manager.get_current_version()
        components = version_manager.get_component_versions()
        compatibility = version_manager.get_compatibility_info()

        console.print(f"[bold blue]WSL-Tmux-Nvim-Setup v{current_version}[/bold blue]\n")

        if components:
            console.print("[bold]Component Versions:[/bold]")
            comp_table = Table(show_header=True)
            comp_table.add_column("Component", style="cyan")
            comp_table.add_column("Version", style="green")

            for component, version in components.items():
                comp_table.add_row(component.title(), version)

            console.print(comp_table)
            console.print()

        if compatibility:
            console.print("[bold]Compatibility:[/bold]")
            compat_table = Table(show_header=False, box=None, padding=(0, 2))

            for key, value in compatibility.items():
                key_formatted = key.replace("_", " ").title()
                if isinstance(value, list):
                    value_formatted = ", ".join(str(v) for v in value)
                else:
                    value_formatted = str(value)

                compat_table.add_row(f"{key_formatted}:", value_formatted)

            console.print(compat_table)

    except Exception as e:
        console.print(f"[red]Error getting version information: {e}[/red]")


def main():
    """Main entry point for the CLI"""
    try:
        cli()
    except KeyboardInterrupt:
        console = Console()
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console = Console()
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        if os.environ.get("WSM_DEBUG"):
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    main()
