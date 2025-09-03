#!/usr/bin/env python3
"""
GitHub API Client for WSL-Tmux-Nvim-Setup CLI

Handles GitHub API integration for release management and asset downloads.
Extends the existing upload-release.py functionality for CLI usage.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests
    from rich.console import Console
except ImportError as e:
    print(f"Error: Required package not found: {e}", file=sys.stderr)
    print("Install with: pip install requests rich", file=sys.stderr)
    sys.exit(1)

# Import existing GitHub client from scripts
sys.path.append(str(Path(__file__).parent.parent.parent / "scripts"))

try:
    from upload_release import GitHubAPIError, GitHubReleaseClient
except ImportError as e:
    print(f"Error: Could not import existing GitHub client: {e}", file=sys.stderr)
    print("Make sure scripts/upload-release.py exists.", file=sys.stderr)
    sys.exit(1)


class GitHubClient:
    """
    Enhanced GitHub API client for CLI operations
    Wraps the existing GitHubReleaseClient with additional functionality
    """

    def __init__(
        self,
        token: Optional[str] = None,
        repository: str = "albertodall/wsl-tmux-nvim-setup",
    ):
        self.console = Console()

        # Get token from environment if not provided
        if not token:
            token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

        if not token:
            raise GitHubAPIError(
                "GitHub token required. Set GITHUB_TOKEN environment variable "
                "or pass token parameter."
            )

        self.repository = repository
        self.client = GitHubReleaseClient(token, repository)

    def list_releases(
        self,
        include_prerelease: bool = False,
        include_draft: bool = False,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        List available releases

        Args:
            include_prerelease: Include prerelease versions
            include_draft: Include draft releases
            limit: Maximum number of releases to return

        Returns:
            List of release information dictionaries
        """
        url = f"{self.client.base_url}/repos/{self.repository}/releases"
        params = {"per_page": limit}

        try:
            response = self.client._make_request("GET", url, params=params)
            releases = response.json()

            # Filter releases based on parameters
            filtered_releases = []
            for release in releases:
                if not include_draft and release.get("draft", False):
                    continue
                if not include_prerelease and release.get("prerelease", False):
                    continue

                # Extract useful information
                release_info = {
                    "tag_name": release["tag_name"],
                    "name": release["name"],
                    "body": release["body"],
                    "published_at": release["published_at"],
                    "prerelease": release["prerelease"],
                    "draft": release["draft"],
                    "html_url": release["html_url"],
                    "assets": [
                        {
                            "name": asset["name"],
                            "download_url": asset["browser_download_url"],
                            "size": asset["size"],
                            "content_type": asset["content_type"],
                            "updated_at": asset["updated_at"],
                        }
                        for asset in release.get("assets", [])
                    ],
                }

                filtered_releases.append(release_info)

            return filtered_releases

        except requests.exceptions.RequestException as e:
            raise GitHubAPIError(f"Failed to list releases: {e}")

    def get_latest_release(self, include_prerelease: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get the latest release

        Args:
            include_prerelease: Whether to include prerelease versions

        Returns:
            Latest release information or None if no releases found
        """
        if include_prerelease:
            # Get all releases and find the latest (including prereleases)
            releases = self.list_releases(include_prerelease=True, limit=10)
            return releases[0] if releases else None
        else:
            # Use GitHub's latest release endpoint
            url = f"{self.client.base_url}/repos/{self.repository}/releases/latest"

            try:
                response = self.client._make_request("GET", url)
                release = response.json()

                return {
                    "tag_name": release["tag_name"],
                    "name": release["name"],
                    "body": release["body"],
                    "published_at": release["published_at"],
                    "prerelease": release["prerelease"],
                    "draft": release["draft"],
                    "html_url": release["html_url"],
                    "assets": [
                        {
                            "name": asset["name"],
                            "download_url": asset["browser_download_url"],
                            "size": asset["size"],
                            "content_type": asset["content_type"],
                            "updated_at": asset["updated_at"],
                        }
                        for asset in release.get("assets", [])
                    ],
                }

            except requests.exceptions.RequestException:
                return None

    def get_release_by_tag(self, tag: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific release by tag name

        Args:
            tag: Release tag (e.g., "v1.0.0")

        Returns:
            Release information or None if not found
        """
        try:
            release = self.client.get_release_by_tag(tag)
            if not release:
                return None

            return {
                "tag_name": release["tag_name"],
                "name": release["name"],
                "body": release["body"],
                "published_at": release["published_at"],
                "prerelease": release["prerelease"],
                "draft": release["draft"],
                "html_url": release["html_url"],
                "assets": [
                    {
                        "name": asset["name"],
                        "download_url": asset["browser_download_url"],
                        "size": asset["size"],
                        "content_type": asset["content_type"],
                        "updated_at": asset["updated_at"],
                    }
                    for asset in release.get("assets", [])
                ],
            }

        except GitHubAPIError:
            return None

    def download_release_asset(
        self,
        download_url: str,
        output_path: Path,
        progress_callback: Optional[callable] = None,
    ) -> Path:
        """
        Download a release asset

        Args:
            download_url: Asset download URL
            output_path: Where to save the downloaded file
            progress_callback: Optional progress callback

        Returns:
            Path to downloaded file
        """
        from .download import DownloadError, DownloadManager

        try:
            # Use the download manager for consistent downloading
            download_manager = DownloadManager(show_progress=True)
            return download_manager.download_file(
                url=download_url,
                output_path=output_path,
                progress_callback=progress_callback,
            )

        except DownloadError as e:
            raise GitHubAPIError(f"Failed to download asset: {e}")

    def get_repository_info(self) -> Dict[str, Any]:
        """Get repository information"""
        url = f"{self.client.base_url}/repos/{self.repository}"

        try:
            response = self.client._make_request("GET", url)
            repo = response.json()

            return {
                "name": repo["name"],
                "full_name": repo["full_name"],
                "description": repo["description"],
                "html_url": repo["html_url"],
                "clone_url": repo["clone_url"],
                "default_branch": repo["default_branch"],
                "created_at": repo["created_at"],
                "updated_at": repo["updated_at"],
                "language": repo["language"],
                "topics": repo.get("topics", []),
                "license": repo["license"]["name"] if repo["license"] else None,
            }

        except requests.exceptions.RequestException as e:
            raise GitHubAPIError(f"Failed to get repository info: {e}")

    def search_releases(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search releases by query string

        Args:
            query: Search query (searches in tag names and release names)
            limit: Maximum number of results

        Returns:
            List of matching releases
        """
        releases = self.list_releases(include_prerelease=True, limit=100)

        query_lower = query.lower()
        matching_releases = []

        for release in releases:
            if query_lower in release["tag_name"].lower() or query_lower in release["name"].lower():
                matching_releases.append(release)

                if len(matching_releases) >= limit:
                    break

        return matching_releases

    def check_rate_limit(self) -> Dict[str, Any]:
        """Check GitHub API rate limit status"""
        url = f"{self.client.base_url}/rate_limit"

        try:
            response = self.client._make_request("GET", url)
            return response.json()

        except requests.exceptions.RequestException as e:
            raise GitHubAPIError(f"Failed to check rate limit: {e}")

    def get_release_downloads_stats(self, tag: str) -> Dict[str, Any]:
        """
        Get download statistics for a release

        Args:
            tag: Release tag

        Returns:
            Dictionary with download statistics
        """
        release = self.get_release_by_tag(tag)
        if not release:
            raise GitHubAPIError(f"Release not found: {tag}")

        total_downloads = 0
        asset_stats = []

        for asset in release["assets"]:
            # Get detailed asset information
            asset_url = f"{self.client.base_url}/repos/{self.repository}/releases/assets/{asset.get('id', 0)}"

            try:
                response = self.client._make_request("GET", asset_url)
                asset_details = response.json()

                download_count = asset_details.get("download_count", 0)
                total_downloads += download_count

                asset_stats.append(
                    {
                        "name": asset["name"],
                        "size": asset["size"],
                        "download_count": download_count,
                        "created_at": asset_details.get("created_at"),
                        "updated_at": asset_details.get("updated_at"),
                    }
                )

            except requests.exceptions.RequestException:
                # If we can't get detailed stats, use basic info
                asset_stats.append(
                    {
                        "name": asset["name"],
                        "size": asset["size"],
                        "download_count": 0,
                        "created_at": None,
                        "updated_at": asset["updated_at"],
                    }
                )

        return {
            "tag": tag,
            "total_downloads": total_downloads,
            "assets": asset_stats,
            "published_at": release["published_at"],
        }

    def format_release_info(self, release: Dict[str, Any], detailed: bool = False) -> str:
        """Format release information for display"""
        from rich.markup import escape

        lines = []
        lines.append(
            f"[bold cyan]{escape(release['name'])}[/bold cyan] ([dim]{release['tag_name']}[/dim])"
        )
        lines.append(f"Published: [green]{release['published_at'][:10]}[/green]")

        if release["prerelease"]:
            lines.append("[yellow]⚠ Prerelease[/yellow]")
        if release["draft"]:
            lines.append("[red]📝 Draft[/red]")

        if release["assets"]:
            lines.append(f"Assets: {len(release['assets'])} files")
            if detailed:
                for asset in release["assets"]:
                    size_mb = asset["size"] / 1024 / 1024
                    lines.append(f"  • {escape(asset['name'])} ({size_mb:.1f} MB)")

        if detailed and release["body"]:
            lines.append("")
            lines.append("[dim]Description:[/dim]")
            # Truncate long descriptions
            body = release["body"][:500]
            if len(release["body"]) > 500:
                body += "..."
            lines.append(escape(body))

        lines.append(f"URL: [link]{release['html_url']}[/link]")

        return "\n".join(lines)


def get_default_github_client() -> GitHubClient:
    """Get default GitHub client instance"""
    return GitHubClient()


if __name__ == "__main__":
    # CLI for testing GitHub functionality
    import click

    @click.group()
    @click.option("--token", envvar="GITHUB_TOKEN", help="GitHub token")
    @click.option(
        "--repository",
        default="albertodall/wsl-tmux-nvim-setup",
        help="Repository (owner/name)",
    )
    @click.pass_context
    def cli(ctx, token, repository):
        """GitHub API client utilities"""
        ctx.ensure_object(dict)
        try:
            ctx.obj["client"] = GitHubClient(token, repository)
        except GitHubAPIError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    @cli.command()
    @click.option("--include-prerelease", is_flag=True, help="Include prereleases")
    @click.option("--limit", default=10, help="Maximum number of releases")
    @click.pass_context
    def list_releases(ctx, include_prerelease, limit):
        """List available releases"""
        try:
            client = ctx.obj["client"]
            releases = client.list_releases(include_prerelease=include_prerelease, limit=limit)

            console = Console()
            for release in releases:
                console.print(client.format_release_info(release))
                console.print()

        except GitHubAPIError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    @cli.command()
    @click.option("--include-prerelease", is_flag=True, help="Include prereleases")
    @click.pass_context
    def latest(ctx, include_prerelease):
        """Get latest release"""
        try:
            client = ctx.obj["client"]
            release = client.get_latest_release(include_prerelease=include_prerelease)

            if not release:
                click.echo("No releases found")
                return

            console = Console()
            console.print(client.format_release_info(release, detailed=True))

        except GitHubAPIError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    @cli.command()
    @click.argument("tag")
    @click.pass_context
    def get_release(ctx, tag):
        """Get specific release by tag"""
        try:
            client = ctx.obj["client"]
            release = client.get_release_by_tag(tag)

            if not release:
                click.echo(f"Release not found: {tag}")
                sys.exit(1)

            console = Console()
            console.print(client.format_release_info(release, detailed=True))

        except GitHubAPIError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    @cli.command()
    @click.pass_context
    def repo_info(ctx):
        """Get repository information"""
        try:
            client = ctx.obj["client"]
            info = client.get_repository_info()

            console = Console()
            console.print(f"[bold]{info['full_name']}[/bold]")
            console.print(f"Description: {info['description'] or 'N/A'}")
            console.print(f"Language: {info['language'] or 'N/A'}")
            console.print(f"License: {info['license'] or 'N/A'}")
            console.print(f"Created: {info['created_at'][:10]}")
            console.print(f"URL: [link]{info['html_url']}[/link]")

        except GitHubAPIError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    cli()
