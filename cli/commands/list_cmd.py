#!/usr/bin/env python3
"""
List Command for WSL-Tmux-Nvim-Setup CLI

Lists available releases and versions.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

try:
    import click
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

from config import ConfigManager
from utils.github import GitHubAPIError, GitHubClient
from utils.version_utils import VersionComparator


class ListManager:
    """Manages listing of releases and versions"""

    def __init__(self, config_manager: ConfigManager, console: Console):
        self.config = config_manager.config
        self.config_manager = config_manager
        self.console = console

        # Initialize GitHub client
        self.github_client = None

    def get_github_client(self) -> GitHubClient:
        """Get GitHub client instance"""
        if not self.github_client:
            try:
                self.github_client = GitHubClient(token=self.config.github_token)
            except GitHubAPIError as e:
                raise click.ClickException(f"GitHub API error: {e}")
        return self.github_client

    def list_releases(
        self,
        include_prerelease: bool = False,
        include_draft: bool = False,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """List available releases"""
        client = self.get_github_client()

        try:
            releases = client.list_releases(
                include_prerelease=include_prerelease,
                include_draft=include_draft,
                limit=limit,
            )
            return releases

        except GitHubAPIError as e:
            raise click.ClickException(f"Failed to fetch releases: {e}")

    def search_releases(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search releases by query"""
        client = self.get_github_client()

        try:
            return client.search_releases(query, limit=limit)
        except GitHubAPIError as e:
            raise click.ClickException(f"Search failed: {e}")

    def get_release_details(self, tag: str) -> Dict[str, Any]:
        """Get detailed information about a specific release"""
        client = self.get_github_client()

        try:
            release = client.get_release_by_tag(tag)
            if not release:
                raise click.ClickException(f"Release {tag} not found")
            return release
        except GitHubAPIError as e:
            raise click.ClickException(f"Failed to get release details: {e}")

    def show_releases_table(self, releases: List[Dict[str, Any]], detailed: bool = False) -> None:
        """Display releases in a formatted table"""
        if not releases:
            self.console.print("[yellow]No releases found[/yellow]")
            return

        # Create table
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Version", style="cyan", min_width=12)
        table.add_column("Published", style="green", min_width=12)
        table.add_column("Type", style="yellow", min_width=10)

        if detailed:
            table.add_column("Size", style="dim", min_width=8)
            table.add_column("Assets", style="dim", min_width=6)

        table.add_column("Description", style="white", max_width=50)

        # Get current version for highlighting
        current_version = self.config_manager.status.version

        for release in releases:
            # Version column with highlighting
            version = release["tag_name"]
            if version.lstrip("v") == current_version:
                version_display = f"[bold green]{version}[/bold green] ⭐"
            else:
                version_display = version

            # Published date
            published = release["published_at"][:10] if release["published_at"] else "Unknown"

            # Release type
            if release["draft"]:
                release_type = "[dim]Draft[/dim]"
            elif release["prerelease"]:
                release_type = "[yellow]Pre-release[/yellow]"
            else:
                release_type = "Release"

            # Description (truncated)
            description = release.get("body", "").strip()
            if description:
                # Extract first line or summary
                first_line = description.split("\n")[0]
                if len(first_line) > 50:
                    first_line = first_line[:47] + "..."
                description_display = first_line
            else:
                description_display = "[dim]No description[/dim]"

            # Build row
            row = [version_display, published, release_type]

            if detailed:
                # Calculate total size
                total_size = sum(asset["size"] for asset in release.get("assets", []))
                size_mb = total_size / 1024 / 1024 if total_size > 0 else 0
                size_display = f"{size_mb:.1f} MB" if size_mb > 0 else "[dim]N/A[/dim]"

                # Asset count
                asset_count = len(release.get("assets", []))
                asset_display = str(asset_count) if asset_count > 0 else "[dim]0[/dim]"

                row.extend([size_display, asset_display])

            row.append(description_display)
            table.add_row(*row)

        self.console.print(table)

        # Show legend
        if any(release["tag_name"].lstrip("v") == current_version for release in releases):
            self.console.print("\n[dim]⭐ = Currently installed[/dim]")

    def show_release_details(self, release: Dict[str, Any]) -> None:
        """Show detailed information about a single release"""
        # Header
        title = f"{release['name']} ({release['tag_name']})"
        self.console.print(f"\n[bold cyan]{title}[/bold cyan]")

        # Basic info
        info_table = Table(show_header=False, box=None, padding=(0, 2))
        info_table.add_row("Published:", f"[green]{release['published_at'][:10]}[/green]")

        if release["prerelease"]:
            info_table.add_row("Type:", "[yellow]Pre-release[/yellow]")
        elif release["draft"]:
            info_table.add_row("Type:", "[dim]Draft[/dim]")
        else:
            info_table.add_row("Type:", "Release")

        info_table.add_row("URL:", f"[link]{release['html_url']}[/link]")

        # Check if this is current version
        current_version = self.config_manager.status.version
        if release["tag_name"].lstrip("v") == current_version:
            info_table.add_row("Status:", "[bold green]Currently Installed ⭐[/bold green]")

        self.console.print(info_table)

        # Assets
        if release.get("assets"):
            self.console.print(f"\n[bold]Assets ({len(release['assets'])}):[/bold]")

            asset_table = Table()
            asset_table.add_column("Name", style="cyan")
            asset_table.add_column("Size", style="yellow")
            asset_table.add_column("Downloads", style="green")
            asset_table.add_column("Updated", style="dim")

            total_size = 0
            for asset in release["assets"]:
                size_mb = asset["size"] / 1024 / 1024
                total_size += asset["size"]

                # Try to get download count (may not be available)
                download_count = asset.get("download_count", "N/A")

                asset_table.add_row(
                    asset["name"],
                    f"{size_mb:.1f} MB",
                    str(download_count),
                    asset["updated_at"][:10],
                )

            self.console.print(asset_table)

            total_mb = total_size / 1024 / 1024
            self.console.print(f"\n[dim]Total Size: {total_mb:.1f} MB[/dim]")

        # Description/Release Notes
        if release.get("body") and release["body"].strip():
            self.console.print("\n[bold]Release Notes:[/bold]")

            # Format release notes
            body = release["body"].strip()

            # Create a panel for the release notes
            release_panel = Panel(
                body,
                title="📝 Release Notes",
                title_align="left",
                border_style="dim",
                padding=(1, 2),
            )
            self.console.print(release_panel)

        else:
            self.console.print("\n[dim]No release notes available[/dim]")

    def show_version_comparison(self, releases: List[Dict[str, Any]]) -> None:
        """Show version comparison with current installation"""
        current_version = self.config_manager.status.version

        if current_version == "unknown":
            self.console.print("[yellow]No current installation to compare[/yellow]")
            return

        self.console.print(f"\n[bold]Version Comparison (Current: {current_version})[/bold]")

        # Sort releases by version
        try:
            sorted_releases = sorted(
                releases,
                key=lambda r: VersionComparator.parse_version(r["tag_name"]),
                reverse=True,
            )
        except Exception:
            # Fallback to sorting by published date
            sorted_releases = sorted(releases, key=lambda r: r["published_at"] or "", reverse=True)

        comparison_table = Table()
        comparison_table.add_column("Version", style="cyan")
        comparison_table.add_column("Status", style="white")
        comparison_table.add_column("Update Type", style="yellow")
        comparison_table.add_column("Published", style="green")

        try:
            current_sem = VersionComparator.parse_version(current_version)

            for release in sorted_releases[:10]:  # Show top 10
                version = release["tag_name"]

                try:
                    release_sem = VersionComparator.parse_version(version)
                    comparison = VersionComparator.compare_versions(current_sem, release_sem)

                    if comparison == 0:
                        status = "[bold green]Current[/bold green]"
                        update_type = "N/A"
                    elif comparison < 0:
                        status = "[green]Newer[/green]"
                        update_type = VersionComparator.get_update_type(current_sem, release_sem)
                        if VersionComparator.check_breaking_change(current_sem, release_sem):
                            update_type += " (Breaking)"
                    else:
                        status = "[dim]Older[/dim]"
                        update_type = "Downgrade"

                except Exception:
                    status = "[yellow]Unknown[/yellow]"
                    update_type = "Unknown"

                published = release["published_at"][:10] if release["published_at"] else "Unknown"

                comparison_table.add_row(version, status, update_type, published)

            self.console.print(comparison_table)

        except Exception as e:
            self.console.print(f"[yellow]Could not compare versions: {e}[/yellow]")


@click.command(name="list")
@click.option("--prerelease", is_flag=True, help="Include prerelease versions")
@click.option("--draft", is_flag=True, help="Include draft releases (if you have access)")
@click.option("--limit", "-l", default=20, type=int, help="Maximum number of releases to show")
@click.option(
    "--detailed",
    "-d",
    is_flag=True,
    help="Show detailed information including file sizes",
)
@click.option("--search", "-s", type=str, help="Search releases by query string")
@click.option("--version", "-v", type=str, help="Show details for specific version")
@click.option("--compare", is_flag=True, help="Show version comparison with current installation")
@click.pass_obj
def list_releases(ctx_obj, prerelease, draft, limit, detailed, search, version, compare):
    """
    List available releases and versions

    \b
    Examples:
        wsm list                    # List latest releases
        wsm list --prerelease       # Include prerelease versions
        wsm list --detailed         # Show detailed information
        wsm list --search "v1.2"    # Search for specific versions
        wsm list --version v1.2.0   # Show details for specific version
        wsm list --compare          # Compare with current version

    This command fetches release information from GitHub and displays
    it in a formatted table. You can filter results and get detailed
    information about specific releases.
    """

    console = ctx_obj.console

    try:
        list_manager = ListManager(ctx_obj.config_manager, console)

        # Handle specific version details
        if version:
            console.print(f"[blue]Fetching details for {version}...[/blue]")
            release = list_manager.get_release_details(version)
            list_manager.show_release_details(release)
            return

        # Handle search
        if search:
            console.print(f"[blue]Searching releases for '{search}'...[/blue]")
            releases = list_manager.search_releases(search, limit=limit)
        else:
            console.print("[blue]Fetching available releases...[/blue]")
            releases = list_manager.list_releases(
                include_prerelease=prerelease, include_draft=draft, limit=limit
            )

        if not releases:
            console.print("[yellow]No releases found[/yellow]")
            return

        # Show results
        console.print(f"\n[bold]Found {len(releases)} releases:[/bold]")
        list_manager.show_releases_table(releases, detailed=detailed)

        # Show comparison if requested
        if compare:
            list_manager.show_version_comparison(releases)

        # Show helpful tips
        console.print("\n[dim]💡 Use 'wsm list --version <tag>' for detailed information")
        console.print("💡 Use 'wsm install <version>' to install a specific version[/dim]")

    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Failed to list releases: {e}")


if __name__ == "__main__":
    list_releases()
