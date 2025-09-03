#!/usr/bin/env python3
"""
WSL-Tmux-Nvim-Setup Automatic Changelog Generator

Generates changelog entries from git commits, following Keep a Changelog format
and integrating with the release system for automated documentation.
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ChangeType(Enum):
    """Changelog entry categories"""

    ADDED = "Added"
    CHANGED = "Changed"
    DEPRECATED = "Deprecated"
    REMOVED = "Removed"
    FIXED = "Fixed"
    SECURITY = "Security"


@dataclass
class ChangeEntry:
    """Individual changelog entry"""

    change_type: ChangeType
    description: str
    commit_hash: str
    author: str
    date: str

    def __str__(self) -> str:
        return f"- {self.description}"


@dataclass
class Release:
    """Release information container"""

    version: str
    date: str
    changes: Dict[ChangeType, List[ChangeEntry]]
    is_unreleased: bool = False

    def has_changes(self) -> bool:
        """Check if release has any changes"""
        return any(len(entries) > 0 for entries in self.changes.values())


class GitCommitParser:
    """Parse git commits for changelog generation"""

    # Conventional commit patterns
    COMMIT_PATTERNS = {
        ChangeType.ADDED: [
            r"^feat(\(.+\))?\s*:\s*(.+)",
            r"^add(\(.+\))?\s*:\s*(.+)",
            r"^implement(\(.+\))?\s*:\s*(.+)",
        ],
        ChangeType.CHANGED: [
            r"^change(\(.+\))?\s*:\s*(.+)",
            r"^update(\(.+\))?\s*:\s*(.+)",
            r"^modify(\(.+\))?\s*:\s*(.+)",
            r"^improve(\(.+\))?\s*:\s*(.+)",
        ],
        ChangeType.FIXED: [
            r"^fix(\(.+\))?\s*:\s*(.+)",
            r"^bugfix(\(.+\))?\s*(.+)",
            r"^resolve(\(.+\))?\s*:\s*(.+)",
        ],
        ChangeType.REMOVED: [
            r"^remove(\(.+\))?\s*:\s*(.+)",
            r"^delete(\(.+\))?\s*:\s*(.+)",
        ],
        ChangeType.SECURITY: [
            r"^security(\(.+\))?\s*:\s*(.+)",
            r"^sec(\(.+\))?\s*:\s*(.+)",
        ],
        ChangeType.DEPRECATED: [
            r"^deprecate(\(.+\))?\s*:\s*(.+)",
            r"^deprecated(\(.+\))?\s*:\s*(.+)",
        ],
    }

    # Keywords that indicate change types
    KEYWORD_PATTERNS = {
        ChangeType.ADDED: ["add", "new", "create", "implement", "introduce"],
        ChangeType.CHANGED: ["update", "change", "modify", "improve", "enhance"],
        ChangeType.FIXED: ["fix", "resolve", "correct", "patch", "repair"],
        ChangeType.REMOVED: ["remove", "delete", "drop"],
        ChangeType.SECURITY: ["security", "vulnerability", "cve"],
        ChangeType.DEPRECATED: ["deprecate", "obsolete"],
    }

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()

    def get_git_commits(self, since: str = None, until: str = "HEAD") -> List[Dict]:
        """Fetch git commits in specified range"""
        cmd = [
            "git",
            "log",
            "--pretty=format:%H|%an|%ae|%ad|%s|%b",
            "--date=iso",
            f"{since}..{until}" if since else until,
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=self.project_root, check=True
            )

            commits = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("|", 5)
                if len(parts) >= 5:
                    commits.append(
                        {
                            "hash": parts[0],
                            "author": parts[1],
                            "email": parts[2],
                            "date": parts[3],
                            "subject": parts[4],
                            "body": parts[5] if len(parts) > 5 else "",
                        }
                    )

            return commits

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git command failed: {e}")
        except Exception as e:
            raise RuntimeError(f"Error fetching git commits: {e}")

    def classify_commit(self, commit: Dict) -> Tuple[ChangeType, str]:
        """Classify commit into changelog category"""
        subject = commit["subject"].lower().strip()
        full_message = f"{subject} {commit['body']}".lower()

        # Try conventional commit patterns first
        for change_type, patterns in self.COMMIT_PATTERNS.items():
            for pattern in patterns:
                match = re.match(pattern, subject, re.IGNORECASE)
                if match:
                    # Extract description (usually the last group)
                    description = match.groups()[-1].strip()
                    return change_type, description.capitalize()

        # Fallback to keyword matching
        for change_type, keywords in self.KEYWORD_PATTERNS.items():
            for keyword in keywords:
                if keyword in full_message:
                    return change_type, commit["subject"]

        # Default to "Changed" for unclassified commits
        return ChangeType.CHANGED, commit["subject"]

    def parse_commits_to_entries(self, commits: List[Dict]) -> Dict[ChangeType, List[ChangeEntry]]:
        """Convert git commits to changelog entries"""
        entries = {change_type: [] for change_type in ChangeType}

        for commit in commits:
            # Skip merge commits
            if commit["subject"].lower().startswith("merge "):
                continue

            # Skip commits with specific patterns to ignore
            ignore_patterns = [
                r"bump version",
                r"release v?\d+\.\d+\.\d+",
                r"update changelog",
                r"^\d+\.\d+\.\d+$",  # Version number only
            ]

            if any(
                re.search(pattern, commit["subject"], re.IGNORECASE) for pattern in ignore_patterns
            ):
                continue

            change_type, description = self.classify_commit(commit)

            entry = ChangeEntry(
                change_type=change_type,
                description=description,
                commit_hash=commit["hash"][:8],
                author=commit["author"],
                date=commit["date"],
            )

            entries[change_type].append(entry)

        return entries

    def get_last_release_tag(self) -> Optional[str]:
        """Get the most recent release tag"""
        try:
            result = subprocess.run(
                ["git", "tag", "--sort=-version:refname", "--list", "v*"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                check=True,
            )

            tags = result.stdout.strip().split("\n")
            return tags[0] if tags and tags[0] else None

        except subprocess.CalledProcessError:
            return None


class ChangelogGenerator:
    """Main changelog generator class"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.changelog_path = self.project_root / "CHANGELOG.md"
        self.version_path = self.project_root / "version.json"
        self.parser = GitCommitParser(project_root)

    def load_current_version(self) -> str:
        """Load current version from version.json"""
        try:
            with open(self.version_path, "r") as f:
                data = json.load(f)
            return data["version"]
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            raise RuntimeError(f"Error loading version: {e}")

    def read_existing_changelog(self) -> str:
        """Read existing changelog content"""
        try:
            with open(self.changelog_path, "r") as f:
                return f.read()
        except FileNotFoundError:
            return ""

    def generate_release_entry(
        self,
        version: str,
        changes: Dict[ChangeType, List[ChangeEntry]],
        is_unreleased: bool = False,
    ) -> str:
        """Generate a single release entry"""
        if is_unreleased:
            header = "## [Unreleased]"
        else:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            header = f"## [{version}] - {date}"

        entry_lines = [header, ""]

        # Add entries for each change type
        for change_type in ChangeType:
            entries = changes.get(change_type, [])
            if entries:
                entry_lines.append(f"### {change_type.value}")
                for entry in entries:
                    entry_lines.append(str(entry))
                entry_lines.append("")

        return "\n".join(entry_lines)

    def update_unreleased_section(self, changes: Dict[ChangeType, List[ChangeEntry]]) -> str:
        """Update the unreleased section of changelog"""
        existing_content = self.read_existing_changelog()

        # Generate unreleased entry
        unreleased_entry = self.generate_release_entry("", changes, is_unreleased=True)

        # Pattern to match existing unreleased section
        unreleased_pattern = r"## \[Unreleased\].*?(?=## \[|\Z)"

        if re.search(unreleased_pattern, existing_content, re.DOTALL):
            # Replace existing unreleased section
            updated_content = re.sub(
                unreleased_pattern,
                unreleased_entry + "\n\n",
                existing_content,
                flags=re.DOTALL,
            )
        else:
            # Add unreleased section at the top (after the header)
            lines = existing_content.split("\n")
            insert_index = 0

            # Find the end of the header section
            for i, line in enumerate(lines):
                if line.startswith("## [") and "Unreleased" not in line:
                    insert_index = i
                    break

            lines.insert(insert_index, unreleased_entry)
            lines.insert(insert_index + 1, "")
            updated_content = "\n".join(lines)

        return updated_content

    def add_release_entry(self, version: str, changes: Dict[ChangeType, List[ChangeEntry]]) -> str:
        """Add a new release entry to changelog"""
        existing_content = self.read_existing_changelog()

        # Generate release entry
        release_entry = self.generate_release_entry(version, changes)

        # Find where to insert the release entry
        lines = existing_content.split("\n")
        insert_index = len(lines)  # Default to end of file

        # Look for the first existing release or end of unreleased section
        for i, line in enumerate(lines):
            if line.startswith("## [") and "Unreleased" not in line:
                insert_index = i
                break

        # Insert release entry
        lines.insert(insert_index, release_entry)
        lines.insert(insert_index + 1, "")

        return "\n".join(lines)

    def clear_unreleased_section(self) -> str:
        """Clear the unreleased section after creating a release"""
        existing_content = self.read_existing_changelog()

        # Create empty unreleased section
        empty_unreleased = """## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security

"""

        # Replace unreleased section
        unreleased_pattern = r"## \[Unreleased\].*?(?=## \[|\Z)"

        if re.search(unreleased_pattern, existing_content, re.DOTALL):
            updated_content = re.sub(
                unreleased_pattern, empty_unreleased, existing_content, flags=re.DOTALL
            )
        else:
            # Add empty unreleased section at the top
            lines = existing_content.split("\n")
            insert_index = 0

            for i, line in enumerate(lines):
                if line.startswith("## [") and "Unreleased" not in line:
                    insert_index = i
                    break

            lines.insert(insert_index, empty_unreleased.strip())
            lines.insert(insert_index + 1, "")
            updated_content = "\n".join(lines)

        return updated_content

    def write_changelog(self, content: str) -> None:
        """Write updated changelog to file"""
        with open(self.changelog_path, "w") as f:
            f.write(content)

    def generate_from_commits(self, since: str = None, mode: str = "unreleased") -> None:
        """Generate changelog from git commits"""
        # Get commits since last release or specified point
        if since is None:
            since = self.parser.get_last_release_tag()

        commits = self.parser.get_git_commits(since=since)

        if not commits:
            print("No commits found for changelog generation")
            return

        changes = self.parser.parse_commits_to_entries(commits)

        # Filter out empty categories for cleaner output
        non_empty_changes = {
            change_type: entries for change_type, entries in changes.items() if entries
        }

        if not non_empty_changes:
            print("No significant changes found for changelog")
            return

        # Update changelog based on mode
        if mode == "unreleased":
            updated_content = self.update_unreleased_section(non_empty_changes)
        elif mode == "release":
            version = self.load_current_version()
            updated_content = self.add_release_entry(version, non_empty_changes)
            updated_content = self.clear_unreleased_section()
        else:
            raise ValueError(f"Invalid mode: {mode}")

        self.write_changelog(updated_content)

        # Summary
        total_changes = sum(len(entries) for entries in non_empty_changes.values())
        print(f"Generated changelog with {total_changes} changes")
        for change_type, entries in non_empty_changes.items():
            print(f"  {change_type.value}: {len(entries)} entries")


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(
        description="Generate changelog from git commits",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Update unreleased section
  %(prog)s --mode release            # Create release entry from unreleased
  %(prog)s --since v1.0.0            # Generate from specific tag
  %(prog)s --since HEAD~10           # Generate from last 10 commits
        """,
    )

    parser.add_argument(
        "--project-root",
        "-p",
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "--since",
        "-s",
        help="Generate changes since this git reference (tag, commit, etc.)",
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["unreleased", "release"],
        default="unreleased",
        help="Generation mode (default: unreleased)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    try:
        generator = ChangelogGenerator(args.project_root)
        generator.generate_from_commits(since=args.since, mode=args.mode)

        print("\nChangelog updated successfully!")
        print(f"File: {generator.changelog_path}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
