#!/usr/bin/env python3
"""
WSL-Tmux-Nvim-Setup GitHub Release Upload Script

Handles GitHub API integration for creating releases and uploading assets.
Supports authentication, retry logic, and comprehensive error handling.
"""

import os
import sys
import json
import argparse
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass
class ReleaseAsset:
    """Release asset information"""

    name: str
    path: Path
    content_type: str
    size: int

    @classmethod
    def from_file(cls, file_path: Path) -> "ReleaseAsset":
        """Create asset from file path"""
        if not file_path.exists():
            raise FileNotFoundError(f"Asset file not found: {file_path}")

        # Determine content type based on extension
        content_types = {
            ".tar.gz": "application/gzip",
            ".zip": "application/zip",
            ".tar.xz": "application/x-xz",
            ".tar.bz2": "application/x-bzip2",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".json": "application/json",
            ".sh": "application/x-sh",
            ".py": "text/x-python",
        }

        # Get file extension
        if file_path.name.endswith(".tar.gz"):
            ext = ".tar.gz"
        else:
            ext = file_path.suffix

        content_type = content_types.get(ext, "application/octet-stream")

        return cls(
            name=file_path.name,
            path=file_path,
            content_type=content_type,
            size=file_path.stat().st_size,
        )


@dataclass
class GitHubRelease:
    """GitHub release information"""

    tag_name: str
    name: str
    body: str
    draft: bool = False
    prerelease: bool = False
    target_commitish: str = "main"


class GitHubAPIError(Exception):
    """GitHub API related errors"""

    pass


class GitHubReleaseClient:
    """GitHub API client for release management"""

    def __init__(self, token: str, repository: str, timeout: int = 30):
        self.token = token
        self.repository = repository  # Format: "owner/repo"
        self.timeout = timeout
        self.base_url = "https://api.github.com"

        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"],
            backoff_factor=1,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        self.session.headers.update(
            {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "wsl-tmux-nvim-setup-release-tool/1.0",
            }
        )

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make authenticated request with error handling"""
        try:
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                print(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                return self._make_request(method, url, **kwargs)

            response.raise_for_status()
            return response

        except requests.exceptions.RequestException as e:
            raise GitHubAPIError(f"GitHub API request failed: {e}")

    def get_release_by_tag(self, tag: str) -> Optional[Dict]:
        """Get existing release by tag"""
        url = f"{self.base_url}/repos/{self.repository}/releases/tags/{tag}"

        try:
            response = self._make_request("GET", url)
            return response.json()
        except GitHubAPIError:
            return None

    def create_release(self, release: GitHubRelease) -> Dict:
        """Create a new GitHub release"""
        url = f"{self.base_url}/repos/{self.repository}/releases"

        data = {
            "tag_name": release.tag_name,
            "target_commitish": release.target_commitish,
            "name": release.name,
            "body": release.body,
            "draft": release.draft,
            "prerelease": release.prerelease,
        }

        response = self._make_request("POST", url, json=data)
        return response.json()

    def update_release(self, release_id: int, release: GitHubRelease) -> Dict:
        """Update an existing release"""
        url = f"{self.base_url}/repos/{self.repository}/releases/{release_id}"

        data = {
            "tag_name": release.tag_name,
            "target_commitish": release.target_commitish,
            "name": release.name,
            "body": release.body,
            "draft": release.draft,
            "prerelease": release.prerelease,
        }

        response = self._make_request("PATCH", url, json=data)
        return response.json()

    def upload_asset(
        self, release_id: int, asset: ReleaseAsset, progress_callback=None
    ) -> Dict:
        """Upload an asset to a release"""
        # Get upload URL
        upload_url_template = f"https://uploads.github.com/repos/{self.repository}/releases/{release_id}/assets"
        upload_url = f"{upload_url_template}?name={asset.name}"

        # Prepare headers for upload
        headers = {
            "Content-Type": asset.content_type,
            "Content-Length": str(asset.size),
        }

        print(f"Uploading {asset.name} ({self._format_size(asset.size)})...")

        # Read and upload file
        with open(asset.path, "rb") as f:
            if progress_callback:
                # Upload with progress tracking
                data = self._upload_with_progress(f, asset.size, progress_callback)
                response = self._make_request(
                    "POST", upload_url, data=data, headers=headers
                )
            else:
                # Simple upload
                response = self._make_request(
                    "POST", upload_url, data=f, headers=headers
                )

        print(f"✓ Uploaded {asset.name}")
        return response.json()

    def _upload_with_progress(self, file_obj, total_size: int, callback):
        """Upload file with progress tracking"""
        chunk_size = 8192
        uploaded = 0

        def read_with_progress():
            nonlocal uploaded
            while True:
                chunk = file_obj.read(chunk_size)
                if not chunk:
                    break
                uploaded += len(chunk)
                callback(uploaded, total_size)
                yield chunk

        return b"".join(read_with_progress())

    def list_release_assets(self, release_id: int) -> List[Dict]:
        """List assets for a release"""
        url = f"{self.base_url}/repos/{self.repository}/releases/{release_id}/assets"
        response = self._make_request("GET", url)
        return response.json()

    def delete_asset(self, asset_id: int) -> None:
        """Delete a release asset"""
        url = f"{self.base_url}/repos/{self.repository}/releases/assets/{asset_id}"
        self._make_request("DELETE", url)

    @staticmethod
    def _format_size(size: int) -> str:
        """Format file size in human readable format"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}TB"


class ReleaseUploader:
    """Main release upload orchestrator"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.version_file = self.project_root / "version.json"
        self.changelog_file = self.project_root / "CHANGELOG.md"

    def load_version_info(self) -> Dict:
        """Load version information from version.json"""
        try:
            with open(self.version_file, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Error loading version info: {e}")

    def extract_release_notes(self, version: str) -> str:
        """Extract release notes from CHANGELOG.md"""
        if not self.changelog_file.exists():
            return f"Release {version}\n\nNo changelog available."

        try:
            with open(self.changelog_file, "r") as f:
                content = f.read()

            # Find the release section
            import re

            pattern = rf"## \[{re.escape(version)}\].*?(?=## \[|\Z)"
            match = re.search(pattern, content, re.DOTALL)

            if match:
                # Clean up the release notes
                release_notes = match.group(0)
                # Remove the version header line
                lines = release_notes.split("\n")[1:]
                return "\n".join(lines).strip()
            else:
                return f"Release {version}\n\nNo release notes found in changelog."

        except Exception as e:
            print(f"Warning: Could not extract release notes: {e}")
            return f"Release {version}"

    def find_release_assets(self, assets_dir: Path) -> List[ReleaseAsset]:
        """Find all release assets in directory"""
        if not assets_dir.exists():
            raise FileNotFoundError(f"Assets directory not found: {assets_dir}")

        asset_patterns = [
            "*.tar.gz",
            "*.zip",
            "checksums.txt",
            "checksums-*.txt",
        ]

        assets = []
        for pattern in asset_patterns:
            for file_path in assets_dir.glob(pattern):
                if file_path.is_file():
                    try:
                        asset = ReleaseAsset.from_file(file_path)
                        assets.append(asset)
                    except Exception as e:
                        print(f"Warning: Could not process asset {file_path}: {e}")

        return sorted(assets, key=lambda a: a.name)

    def create_or_update_release(
        self,
        client: GitHubReleaseClient,
        version: str,
        prerelease: bool = False,
        draft: bool = False,
    ) -> Dict:
        """Create or update a GitHub release"""
        tag_name = f"v{version}"

        # Check if release already exists
        existing_release = client.get_release_by_tag(tag_name)

        # Prepare release notes
        release_notes = self.extract_release_notes(version)

        # Create release object
        release = GitHubRelease(
            tag_name=tag_name,
            name=f"WSL-Tmux-Nvim-Setup v{version}",
            body=release_notes,
            draft=draft,
            prerelease=prerelease,
        )

        if existing_release:
            print(f"Updating existing release: {tag_name}")
            return client.update_release(existing_release["id"], release)
        else:
            print(f"Creating new release: {tag_name}")
            return client.create_release(release)

    def upload_assets_to_release(
        self,
        client: GitHubReleaseClient,
        release_id: int,
        assets: List[ReleaseAsset],
        replace_existing: bool = True,
    ) -> List[Dict]:
        """Upload assets to a GitHub release"""
        uploaded_assets = []

        # Get existing assets if we need to replace them
        existing_assets = {}
        if replace_existing:
            for asset in client.list_release_assets(release_id):
                existing_assets[asset["name"]] = asset

        for asset in assets:
            try:
                # Delete existing asset if it exists and we're replacing
                if replace_existing and asset.name in existing_assets:
                    existing_asset = existing_assets[asset.name]
                    print(f"Deleting existing asset: {asset.name}")
                    client.delete_asset(existing_asset["id"])

                # Upload new asset with progress
                def progress_callback(uploaded: int, total: int):
                    percent = (uploaded / total) * 100
                    print(
                        f"\r  Progress: {percent:.1f%} ({uploaded}/{total} bytes)",
                        end="",
                    )

                result = client.upload_asset(release_id, asset, progress_callback)
                print()  # New line after progress
                uploaded_assets.append(result)

            except Exception as e:
                print(f"Error uploading {asset.name}: {e}")
                continue

        return uploaded_assets

    def verify_assets(
        self, assets: List[ReleaseAsset], checksums_file: Optional[Path] = None
    ) -> bool:
        """Verify asset integrity before upload"""
        if not checksums_file or not checksums_file.exists():
            print("No checksums file found, skipping verification")
            return True

        print("Verifying asset checksums...")

        # Parse checksums file
        checksums = {}
        with open(checksums_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        checksums[parts[1]] = parts[0]

        # Verify each asset
        verification_failed = False
        for asset in assets:
            if asset.name in checksums:
                expected_hash = checksums[asset.name]

                # Calculate SHA256 hash
                hash_obj = hashlib.sha256()
                with open(asset.path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_obj.update(chunk)

                actual_hash = hash_obj.hexdigest()

                if actual_hash == expected_hash:
                    print(f"✓ {asset.name}")
                else:
                    print(f"✗ {asset.name} - checksum mismatch!")
                    verification_failed = True
            else:
                print(f"? {asset.name} - no checksum found")

        return not verification_failed


def get_github_token() -> str:
    """Get GitHub token from environment or prompt user"""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        token = os.environ.get("GH_TOKEN")

    if not token:
        print("GitHub token not found in environment variables.")
        print("Please set GITHUB_TOKEN or GH_TOKEN environment variable.")
        print("Or pass token using --token argument.")
        sys.exit(1)

    return token


def parse_repository_from_git() -> str:
    """Extract repository information from git remote"""
    try:
        import subprocess

        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            check=True,
        )

        remote_url = result.stdout.strip()

        # Parse GitHub repository from URL
        import re

        patterns = [
            r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?/?$",
            r"github\.com/([^/]+/[^/]+?)/?$",
        ]

        for pattern in patterns:
            match = re.search(pattern, remote_url)
            if match:
                return match.group(1)

        raise ValueError(f"Could not parse GitHub repository from: {remote_url}")

    except subprocess.CalledProcessError:
        raise RuntimeError("Could not get git remote URL")


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(
        description="Upload release assets to GitHub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Auto-detect version and assets
  %(prog)s --version 1.2.3 --prerelease      # Create prerelease
  %(prog)s --assets-dir /path/to/assets       # Custom assets directory
  %(prog)s --repository owner/repo            # Override repository
  %(prog)s --draft                            # Create draft release

Environment Variables:
  GITHUB_TOKEN or GH_TOKEN    GitHub personal access token
        """,
    )

    parser.add_argument(
        "--project-root",
        "-p",
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "--version",
        "-v",
        help="Release version (default: auto-detect from version.json)",
    )
    parser.add_argument(
        "--assets-dir", "-a", help="Assets directory (default: ./release-assets)"
    )
    parser.add_argument(
        "--repository",
        "-r",
        help="GitHub repository (owner/repo, default: auto-detect)",
    )
    parser.add_argument(
        "--token", "-t", help="GitHub token (default: from environment)"
    )
    parser.add_argument("--prerelease", action="store_true", help="Mark as prerelease")
    parser.add_argument("--draft", action="store_true", help="Create as draft")
    parser.add_argument(
        "--no-verify", action="store_true", help="Skip asset verification"
    )
    parser.add_argument(
        "--replace-assets",
        action="store_true",
        help="Replace existing assets (default: true)",
        default=True,
    )

    args = parser.parse_args()

    try:
        # Initialize uploader
        uploader = ReleaseUploader(args.project_root)

        # Get version
        if args.version:
            version = args.version
        else:
            version_info = uploader.load_version_info()
            version = version_info["version"]

        print(f"Preparing release for version: {version}")

        # Get GitHub token
        token = args.token or get_github_token()

        # Get repository
        repository = args.repository or parse_repository_from_git()
        print(f"Target repository: {repository}")

        # Initialize GitHub client
        client = GitHubReleaseClient(token, repository)

        # Find assets
        assets_dir = Path(args.assets_dir or "release-assets")
        if not assets_dir.is_absolute():
            assets_dir = uploader.project_root / assets_dir

        assets = uploader.find_release_assets(assets_dir)

        if not assets:
            print("No release assets found!")
            return 1

        print(f"Found {len(assets)} assets:")
        for asset in assets:
            print(f"  - {asset.name} ({client._format_size(asset.size)})")

        # Verify assets if requested
        if not args.no_verify:
            checksums_file = assets_dir / "checksums.txt"
            if not uploader.verify_assets(assets, checksums_file):
                print("Asset verification failed!")
                return 1

        # Create or update release
        release_data = uploader.create_or_update_release(
            client, version, args.prerelease, args.draft
        )

        print(f"Release created/updated: {release_data['html_url']}")

        # Upload assets
        uploaded_assets = uploader.upload_assets_to_release(
            client, release_data["id"], assets, args.replace_assets
        )

        print(f"\nUpload completed!")
        print(f"Release URL: {release_data['html_url']}")
        print(f"Assets uploaded: {len(uploaded_assets)}")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
