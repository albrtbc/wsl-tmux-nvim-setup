#!/usr/bin/env python3
"""
Version Utilities for WSL-Tmux-Nvim-Setup CLI

Handles version comparison, parsing, and compatibility checking.
Integrates with existing version-manager.py functionality.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Import existing version manager
sys.path.append(str(Path(__file__).parent.parent.parent / "scripts"))

try:
    from version_manager import SemanticVersion, VersionManager, VersionManagerError
except ImportError as e:
    print(f"Error: Could not import existing version manager: {e}", file=sys.stderr)
    print("Make sure scripts/version-manager.py exists.", file=sys.stderr)
    sys.exit(1)


class VersionComparator:
    """Enhanced version comparison and compatibility utilities"""

    def __init__(self):
        pass

    @staticmethod
    def parse_version(version_string: str) -> SemanticVersion:
        """
        Parse version string into SemanticVersion object

        Args:
            version_string: Version string (e.g., "1.0.0", "v1.2.3-alpha")

        Returns:
            SemanticVersion object

        Raises:
            VersionManagerError: If version string is invalid
        """
        return SemanticVersion(version_string)

    @staticmethod
    def compare_versions(
        version1: Union[str, SemanticVersion], version2: Union[str, SemanticVersion]
    ) -> int:
        """
        Compare two versions

        Args:
            version1: First version to compare
            version2: Second version to compare

        Returns:
            -1 if version1 < version2
             0 if version1 == version2
             1 if version1 > version2
        """
        if isinstance(version1, str):
            version1 = SemanticVersion(version1)
        if isinstance(version2, str):
            version2 = SemanticVersion(version2)

        # Compare major.minor.patch
        v1_tuple = (version1.major, version1.minor, version1.patch)
        v2_tuple = (version2.major, version2.minor, version2.patch)

        if v1_tuple < v2_tuple:
            return -1
        elif v1_tuple > v2_tuple:
            return 1

        # If base versions are equal, compare prerelease
        if version1.prerelease and version2.prerelease:
            if version1.prerelease < version2.prerelease:
                return -1
            elif version1.prerelease > version2.prerelease:
                return 1
            else:
                return 0
        elif version1.prerelease and not version2.prerelease:
            # Prerelease versions are less than normal versions
            return -1
        elif not version1.prerelease and version2.prerelease:
            # Normal versions are greater than prerelease versions
            return 1

        return 0

    @staticmethod
    def is_newer_version(
        current: Union[str, SemanticVersion], candidate: Union[str, SemanticVersion]
    ) -> bool:
        """
        Check if candidate version is newer than current version

        Args:
            current: Current version
            candidate: Candidate version to compare

        Returns:
            True if candidate is newer than current
        """
        return VersionComparator.compare_versions(candidate, current) > 0

    @staticmethod
    def is_compatible_version(
        version: Union[str, SemanticVersion],
        min_version: Union[str, SemanticVersion],
        max_version: Optional[Union[str, SemanticVersion]] = None,
    ) -> bool:
        """
        Check if version is within compatible range

        Args:
            version: Version to check
            min_version: Minimum compatible version
            max_version: Maximum compatible version (optional)

        Returns:
            True if version is compatible
        """
        # Check minimum version
        if VersionComparator.compare_versions(version, min_version) < 0:
            return False

        # Check maximum version if provided
        if max_version and VersionComparator.compare_versions(version, max_version) > 0:
            return False

        return True

    @staticmethod
    def get_version_series(version: Union[str, SemanticVersion]) -> str:
        """
        Get version series (major.minor) for compatibility checking

        Args:
            version: Version to get series for

        Returns:
            Version series string (e.g., "1.2")
        """
        if isinstance(version, str):
            version = SemanticVersion(version)

        return f"{version.major}.{version.minor}"

    @staticmethod
    def sort_versions(
        versions: List[Union[str, SemanticVersion]], reverse: bool = False
    ) -> List[SemanticVersion]:
        """
        Sort list of versions

        Args:
            versions: List of versions to sort
            reverse: Sort in descending order if True

        Returns:
            Sorted list of SemanticVersion objects
        """
        semantic_versions = []
        for v in versions:
            if isinstance(v, str):
                semantic_versions.append(SemanticVersion(v))
            else:
                semantic_versions.append(v)

        def version_sort_key(v):
            return (v.major, v.minor, v.patch, v.prerelease or "")

        return sorted(semantic_versions, key=version_sort_key, reverse=reverse)

    @staticmethod
    def filter_prereleases(
        versions: List[Union[str, SemanticVersion]], include_prereleases: bool = False
    ) -> List[SemanticVersion]:
        """
        Filter prerelease versions from list

        Args:
            versions: List of versions
            include_prereleases: Whether to include prerelease versions

        Returns:
            Filtered list of versions
        """
        semantic_versions = []
        for v in versions:
            if isinstance(v, str):
                v = SemanticVersion(v)

            if include_prereleases or not v.prerelease:
                semantic_versions.append(v)

        return semantic_versions

    @staticmethod
    def get_latest_version(
        versions: List[Union[str, SemanticVersion]], include_prereleases: bool = False
    ) -> Optional[SemanticVersion]:
        """
        Get latest version from list

        Args:
            versions: List of versions
            include_prereleases: Whether to consider prerelease versions

        Returns:
            Latest version or None if list is empty
        """
        if not versions:
            return None

        filtered_versions = VersionComparator.filter_prereleases(
            versions, include_prereleases
        )
        if not filtered_versions:
            return None

        sorted_versions = VersionComparator.sort_versions(
            filtered_versions, reverse=True
        )
        return sorted_versions[0]

    @staticmethod
    def check_breaking_change(
        old_version: Union[str, SemanticVersion],
        new_version: Union[str, SemanticVersion],
    ) -> bool:
        """
        Check if upgrade involves a breaking change (major version bump)

        Args:
            old_version: Current version
            new_version: Target version

        Returns:
            True if major version changed
        """
        if isinstance(old_version, str):
            old_version = SemanticVersion(old_version)
        if isinstance(new_version, str):
            new_version = SemanticVersion(new_version)

        return old_version.major != new_version.major

    @staticmethod
    def get_update_type(
        old_version: Union[str, SemanticVersion],
        new_version: Union[str, SemanticVersion],
    ) -> str:
        """
        Determine the type of version update

        Args:
            old_version: Current version
            new_version: Target version

        Returns:
            Update type: "major", "minor", "patch", "prerelease", or "none"
        """
        if isinstance(old_version, str):
            old_version = SemanticVersion(old_version)
        if isinstance(new_version, str):
            new_version = SemanticVersion(new_version)

        comparison = VersionComparator.compare_versions(old_version, new_version)

        if comparison == 0:
            return "none"
        elif comparison > 0:
            # Downgrade - treat as the type of change
            old_version, new_version = new_version, old_version

        if old_version.major < new_version.major:
            return "major"
        elif old_version.minor < new_version.minor:
            return "minor"
        elif old_version.patch < new_version.patch:
            return "patch"
        elif (not old_version.prerelease and new_version.prerelease) or (
            old_version.prerelease and new_version.prerelease
        ):
            return "prerelease"

        return "patch"  # Default fallback


class ComponentVersionManager:
    """Manages versions of individual components"""

    def __init__(self, version_file: Optional[Path] = None):
        self.version_manager = VersionManager()
        self.version_file = version_file or Path.cwd() / "version.json"

    def get_component_versions(self) -> Dict[str, str]:
        """Get current versions of all components"""
        try:
            version_data = self.version_manager.load_version_data()
            return version_data.get("components", {})
        except Exception:
            return {}

    def get_component_version(self, component: str) -> Optional[str]:
        """Get version of specific component"""
        components = self.get_component_versions()
        return components.get(component)

    def update_component_version(self, component: str, version: str) -> None:
        """Update version of specific component"""
        try:
            version_data = self.version_manager.load_version_data()
            if "components" not in version_data:
                version_data["components"] = {}

            version_data["components"][component] = version
            self.version_manager.save_version_data(version_data)
        except Exception as e:
            raise VersionManagerError(f"Failed to update component version: {e}")

    def check_component_updates(
        self, available_versions: Dict[str, List[str]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Check for component updates

        Args:
            available_versions: Dict mapping component names to lists of available versions

        Returns:
            Dict with update information for each component
        """
        current_versions = self.get_component_versions()
        update_info = {}

        for component, current_version in current_versions.items():
            if component not in available_versions:
                update_info[component] = {
                    "current": current_version,
                    "latest": None,
                    "available": [],
                    "update_available": False,
                    "update_type": None,
                }
                continue

            available = available_versions[component]
            latest = VersionComparator.get_latest_version(available)

            if latest is None:
                update_info[component] = {
                    "current": current_version,
                    "latest": None,
                    "available": available,
                    "update_available": False,
                    "update_type": None,
                }
                continue

            try:
                current_sem = SemanticVersion(current_version)
                update_available = VersionComparator.is_newer_version(
                    current_sem, latest
                )
                update_type = (
                    VersionComparator.get_update_type(current_sem, latest)
                    if update_available
                    else None
                )

                update_info[component] = {
                    "current": current_version,
                    "latest": str(latest),
                    "available": [
                        str(v)
                        for v in VersionComparator.sort_versions(
                            available, reverse=True
                        )
                    ],
                    "update_available": update_available,
                    "update_type": update_type,
                    "breaking_change": (
                        VersionComparator.check_breaking_change(current_sem, latest)
                        if update_available
                        else False
                    ),
                }
            except VersionManagerError:
                # Handle invalid version formats
                update_info[component] = {
                    "current": current_version,
                    "latest": str(latest),
                    "available": available,
                    "update_available": True,  # Assume update needed if version parsing fails
                    "update_type": "unknown",
                    "breaking_change": False,
                }

        return update_info

    def get_compatibility_info(self) -> Dict[str, Any]:
        """Get compatibility information from version file"""
        try:
            version_data = self.version_manager.load_version_data()
            return version_data.get("compatibility", {})
        except Exception:
            return {}

    def check_system_compatibility(self) -> Dict[str, bool]:
        """Check if current system meets compatibility requirements"""
        compatibility = self.get_compatibility_info()
        results = {}

        # Check minimum Ubuntu version
        min_ubuntu = compatibility.get("min_ubuntu")
        if min_ubuntu:
            try:
                import subprocess

                # Try to get Ubuntu version
                result = subprocess.run(
                    ["lsb_release", "-rs"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    current_ubuntu = result.stdout.strip()
                    results["ubuntu_version"] = VersionComparator.is_compatible_version(
                        current_ubuntu, min_ubuntu
                    )
                else:
                    results["ubuntu_version"] = None  # Can't determine
            except (subprocess.TimeoutExpired, FileNotFoundError):
                results["ubuntu_version"] = None

        # Check WSL version
        supported_wsl = compatibility.get("wsl_versions", [])
        if supported_wsl:
            try:
                wsl_version = os.environ.get("WSL_DISTRO_NAME", "")
                results["wsl_support"] = bool(wsl_version)  # Basic WSL detection
            except Exception:
                results["wsl_support"] = None

        # Check supported shells
        supported_shells = compatibility.get("supported_shells", [])
        if supported_shells:
            try:
                current_shell = Path(os.environ.get("SHELL", "")).name
                results["shell_support"] = current_shell in supported_shells
            except Exception:
                results["shell_support"] = None

        return results


def parse_version(version_string: str) -> SemanticVersion:
    """Convenience function for parsing version strings"""
    return VersionComparator.parse_version(version_string)


def compare_versions(version1: str, version2: str) -> int:
    """Convenience function for comparing version strings"""
    return VersionComparator.compare_versions(version1, version2)


if __name__ == "__main__":
    # CLI for testing version utilities
    import json

    import click

    @click.group()
    def cli():
        """Version utilities for testing"""

    @cli.command()
    @click.argument("version1")
    @click.argument("version2")
    def compare(version1, version2):
        """Compare two versions"""
        try:
            result = VersionComparator.compare_versions(version1, version2)

            if result < 0:
                click.echo(f"{version1} < {version2}")
            elif result > 0:
                click.echo(f"{version1} > {version2}")
            else:
                click.echo(f"{version1} == {version2}")

        except VersionManagerError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    @cli.command()
    @click.argument("versions", nargs=-1, required=True)
    @click.option(
        "--include-prereleases", is_flag=True, help="Include prerelease versions"
    )
    def sort(versions, include_prereleases):
        """Sort versions"""
        try:
            sorted_versions = VersionComparator.sort_versions(versions, reverse=True)
            filtered_versions = VersionComparator.filter_prereleases(
                sorted_versions, include_prereleases
            )

            for version in filtered_versions:
                click.echo(str(version))

        except VersionManagerError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    @cli.command()
    @click.argument("versions", nargs=-1, required=True)
    @click.option(
        "--include-prereleases", is_flag=True, help="Include prerelease versions"
    )
    def latest(versions, include_prereleases):
        """Get latest version from list"""
        try:
            latest_version = VersionComparator.get_latest_version(
                versions, include_prereleases
            )

            if latest_version:
                click.echo(str(latest_version))
            else:
                click.echo("No valid versions found")

        except VersionManagerError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    @cli.command()
    @click.option("--version-file", type=click.Path(), help="Path to version.json file")
    def components(version_file):
        """Show component versions"""
        try:
            manager = ComponentVersionManager(
                Path(version_file) if version_file else None
            )
            components = manager.get_component_versions()

            click.echo(json.dumps(components, indent=2))

        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    cli()
