#!/usr/bin/env python3
"""
WSL-Tmux-Nvim-Setup Version Manager

A utility for managing semantic versioning, changelog generation,
and version bumping operations for the release system.
"""

import json
import sys
import argparse
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple, Optional

# POSIX-compliant error handling


class VersionManagerError(Exception):
    """Custom exception for version manager errors"""

    pass


class SemanticVersion:
    """Semantic version parser and manipulator"""

    def __init__(self, version_string: str):
        self.original = version_string
        parts = self._parse(version_string)
        self.major, self.minor, self.patch, self.prerelease = parts

    def _parse(self, version: str) -> Tuple[int, int, int, Optional[str]]:
        """Parse semantic version string"""
        # Remove 'v' prefix if present
        version = version.lstrip("v")

        # Pattern for semantic versioning
        pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9\-\.]+))?$"
        match = re.match(pattern, version)

        if not match:
            raise VersionManagerError(f"Invalid semantic version: {version}")

        major, minor, patch = map(int, match.groups()[:3])
        prerelease = match.group(4)

        return major, minor, patch, prerelease

    def bump(self, version_type: str) -> "SemanticVersion":
        """Bump version according to type"""
        if version_type == "major":
            return SemanticVersion(f"{self.major + 1}.0.0")
        elif version_type == "minor":
            return SemanticVersion(f"{self.major}.{self.minor + 1}.0")
        elif version_type == "patch":
            return SemanticVersion(f"{self.major}.{self.minor}.{self.patch + 1}")
        else:
            raise VersionManagerError(f"Invalid version type: {version_type}")

    def __str__(self) -> str:
        """String representation of version"""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        return version

    def with_v_prefix(self) -> str:
        """Return version with 'v' prefix for git tags"""
        return f"v{str(self)}"


class VersionManager:
    """Main version management class"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.version_file = self.project_root / "version.json"

        if not self.version_file.exists():
            raise VersionManagerError(f"Version file not found: {self.version_file}")

    def load_version_data(self) -> Dict:
        """Load version data from version.json"""
        try:
            with open(self.version_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise VersionManagerError(f"Error reading version file: {e}")

    def save_version_data(self, data: Dict) -> None:
        """Save version data to version.json"""
        try:
            with open(self.version_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")  # Add trailing newline
        except IOError as e:
            raise VersionManagerError(f"Error writing version file: {e}")

    def get_current_version(self) -> SemanticVersion:
        """Get current version from version.json"""
        data = self.load_version_data()
        return SemanticVersion(data["version"])

    def bump_version(self, version_type: str) -> SemanticVersion:
        """Bump version and update version.json"""
        data = self.load_version_data()
        current_version = SemanticVersion(data["version"])
        new_version = current_version.bump(version_type)

        # Update version data
        data["version"] = str(new_version)
        data["release_date"] = datetime.now(timezone.utc).isoformat()

        # Save updated data
        self.save_version_data(data)

        print(f"Version bumped: {current_version} -> {new_version}")
        return new_version

    def validate_version_format(self, version: str) -> bool:
        """Validate semantic version format"""
        try:
            SemanticVersion(version)
            return True
        except VersionManagerError:
            return False

    def get_next_version(self, version_type: str) -> SemanticVersion:
        """Get next version without updating files"""
        current_version = self.get_current_version()
        return current_version.bump(version_type)

    def set_version(self, version: str) -> None:
        """Manually set version (for hotfixes or corrections)"""
        if not self.validate_version_format(version):
            raise VersionManagerError(f"Invalid version format: {version}")

        data = self.load_version_data()
        old_version = data["version"]

        data["version"] = version
        data["release_date"] = datetime.now(timezone.utc).isoformat()

        self.save_version_data(data)
        print(f"Version set: {old_version} -> {version}")


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="WSL-Tmux-Nvim-Setup Version Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s current                    # Show current version
  %(prog)s bump patch                 # Bump patch version
  %(prog)s bump minor                 # Bump minor version
  %(prog)s bump major                 # Bump major version
  %(prog)s next minor                 # Show next minor version
  %(prog)s set 1.2.3                  # Set specific version
  %(prog)s validate v1.2.3-alpha      # Validate version format
        """,
    )

    parser.add_argument("--project-root", "-p", help="Project root dir (default: current)")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Current version command
    subparsers.add_parser("current", help="Show current version")

    # Bump version command
    bump_parser = subparsers.add_parser("bump", help="Bump version")
    bump_parser.add_argument(
        "type", choices=["major", "minor", "patch"], help="Version component to bump"
    )

    # Next version command (preview)
    next_parser = subparsers.add_parser("next", help="Show next version (preview)")
    next_parser.add_argument(
        "type", choices=["major", "minor", "patch"], help="Version component to preview"
    )

    # Set version command
    set_parser = subparsers.add_parser("set", help="Set specific version")
    set_parser.add_argument("version", help="Version to set (e.g., 1.2.3)")

    # Validate version command
    validate_parser = subparsers.add_parser("validate", help="Validate version format")
    validate_parser.add_argument("version", help="Version to validate")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        # Initialize version manager
        if args.command != "validate":
            vm = VersionManager(args.project_root)

        # Execute commands
        if args.command == "current":
            version = vm.get_current_version()
            print(f"Current version: {version}")

        elif args.command == "bump":
            new_version = vm.bump_version(args.type)
            print(f"Git tag: {new_version.with_v_prefix()}")

        elif args.command == "next":
            next_version = vm.get_next_version(args.type)
            print(f"Next {args.type} version: {next_version}")

        elif args.command == "set":
            vm.set_version(args.version)

        elif args.command == "validate":
            # Validate version format directly
            try:
                SemanticVersion(args.version)
                print(f"Version '{args.version}' is valid")
                return 0
            except VersionManagerError as e:
                print(f"Version '{args.version}' is invalid: {e}")
                return 1

        return 0

    except VersionManagerError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
