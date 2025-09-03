#!/usr/bin/env python3
"""
Backup Manager for WSL-Tmux-Nvim-Setup CLI

Handles backup and restore operations with compression and retention policies.
"""

import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from rich.console import Console
    from rich.progress import Progress
    from rich.table import Table
except ImportError as e:
    print(f"Error: Required package not found: {e}", file=sys.stderr)
    print("Install with: pip install rich", file=sys.stderr)
    sys.exit(1)

from .extract import ExtractionError, ExtractManager


class BackupError(Exception):
    """Backup-related errors"""


class BackupManager:
    """Manages backup and restore operations"""

    def __init__(
        self, backup_dir: Path, retention_count: int = 5, show_progress: bool = True
    ):
        self.backup_dir = Path(backup_dir)
        self.retention_count = retention_count
        self.show_progress = show_progress
        self.console = Console()
        self.extract_manager = ExtractManager(show_progress=show_progress)

        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Backup metadata file
        self.metadata_file = self.backup_dir / "backups.json"

    def create_backup(
        self,
        source_paths: List[Path],
        backup_name: str,
        description: str = "",
        exclude_patterns: Optional[List[str]] = None,
    ) -> Path:
        """
        Create a backup of specified paths

        Args:
            source_paths: List of paths to backup
            backup_name: Name for the backup
            description: Optional description
            exclude_patterns: Patterns to exclude from backup

        Returns:
            Path to created backup archive
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{backup_name}_{timestamp}.tar.gz"
        backup_path = self.backup_dir / backup_filename

        if self.show_progress:
            self.console.print(f"[blue]Creating backup: {backup_name}[/blue]")

        try:
            # Create temporary staging directory
            staging_dir = self.backup_dir / f"staging_{timestamp}"
            staging_dir.mkdir(exist_ok=True)

            try:
                # Copy source paths to staging area
                self._copy_to_staging(source_paths, staging_dir, exclude_patterns)

                # Create compressed archive from staging area
                archive_path = self.extract_manager.create_archive(
                    staging_dir, backup_path, "tar.gz"
                )

                # Record backup metadata
                self._record_backup_metadata(
                    backup_name, archive_path, source_paths, description
                )

                # Clean up old backups if needed
                self._cleanup_old_backups(backup_name)

                if self.show_progress:
                    size = archive_path.stat().st_size
                    size_str = self._format_size(size)
                    self.console.print(
                        f"[green]✓ Backup created: {backup_filename} ({size_str})[/green]"
                    )

                return archive_path

            finally:
                # Clean up staging directory
                if staging_dir.exists():
                    shutil.rmtree(staging_dir)

        except Exception as e:
            if backup_path.exists():
                backup_path.unlink()  # Clean up partial backup
            raise BackupError(f"Failed to create backup: {e}")

    def restore_backup(
        self,
        backup_name: str,
        restore_to: Optional[Path] = None,
        backup_timestamp: Optional[str] = None,
    ) -> Path:
        """
        Restore from backup

        Args:
            backup_name: Name of backup to restore
            restore_to: Directory to restore to (default: original locations)
            backup_timestamp: Specific backup timestamp (default: latest)

        Returns:
            Path where backup was restored
        """
        # Find backup file
        backup_info = self._find_backup(backup_name, backup_timestamp)
        if not backup_info:
            available = self.list_backups()
            available_names = [b["name"] for b in available]
            raise BackupError(
                f"Backup '{backup_name}' not found. Available: {available_names}"
            )

        backup_path = Path(backup_info["path"])
        if not backup_path.exists():
            raise BackupError(f"Backup file not found: {backup_path}")

        # Determine restore location
        if restore_to is None:
            restore_to = (
                Path.home() / "restored_backups" / f"{backup_name}_{int(time.time())}"
            )
        else:
            restore_to = Path(restore_to)

        restore_to.mkdir(parents=True, exist_ok=True)

        if self.show_progress:
            self.console.print(f"[blue]Restoring backup: {backup_name}[/blue]")

        try:
            # Extract backup
            extracted_path = self.extract_manager.extract_archive(
                backup_path, restore_to
            )

            if self.show_progress:
                self.console.print(
                    f"[green]✓ Backup restored to: {extracted_path}[/green]"
                )

            return extracted_path

        except ExtractionError as e:
            raise BackupError(f"Failed to restore backup: {e}")

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups"""
        metadata = self._load_backup_metadata()
        backups = []

        for backup_name, backup_data in metadata.items():
            for backup in backup_data["backups"]:
                backup_info = {
                    "name": backup_name,
                    "timestamp": backup["timestamp"],
                    "date": backup["date"],
                    "path": backup["path"],
                    "size": self._get_file_size(backup["path"]),
                    "description": backup.get("description", ""),
                    "source_paths": backup.get("source_paths", []),
                }
                backups.append(backup_info)

        # Sort by date (newest first)
        backups.sort(key=lambda x: x["timestamp"], reverse=True)
        return backups

    def delete_backup(
        self,
        backup_name: str,
        backup_timestamp: Optional[str] = None,
        confirm: bool = True,
    ) -> bool:
        """
        Delete a backup

        Args:
            backup_name: Name of backup to delete
            backup_timestamp: Specific timestamp (default: all backups for name)
            confirm: Whether to confirm deletion

        Returns:
            True if deleted, False if cancelled
        """
        backups_to_delete = []

        if backup_timestamp:
            # Delete specific backup
            backup_info = self._find_backup(backup_name, backup_timestamp)
            if backup_info:
                backups_to_delete.append(backup_info)
        else:
            # Delete all backups for name
            metadata = self._load_backup_metadata()
            if backup_name in metadata:
                backups_to_delete = metadata[backup_name]["backups"]

        if not backups_to_delete:
            raise BackupError(f"No backups found for: {backup_name}")

        # Confirm deletion
        if confirm and self.show_progress:
            count = len(backups_to_delete)
            self.console.print(
                f"[yellow]About to delete {count} backup(s) for '{backup_name}'[/yellow]"
            )

            import click

            if not click.confirm("Are you sure?"):
                return False

        # Delete backup files and update metadata
        try:
            deleted_count = 0
            metadata = self._load_backup_metadata()

            for backup_info in backups_to_delete:
                backup_path = Path(backup_info["path"])
                if backup_path.exists():
                    backup_path.unlink()
                    deleted_count += 1

            # Update metadata
            if backup_timestamp:
                # Remove specific backup
                if backup_name in metadata:
                    metadata[backup_name]["backups"] = [
                        b
                        for b in metadata[backup_name]["backups"]
                        if b["timestamp"] != backup_timestamp
                    ]
                    # Remove backup name if no backups left
                    if not metadata[backup_name]["backups"]:
                        del metadata[backup_name]
            else:
                # Remove all backups for name
                if backup_name in metadata:
                    del metadata[backup_name]

            self._save_backup_metadata(metadata)

            if self.show_progress:
                self.console.print(
                    f"[green]✓ Deleted {deleted_count} backup(s)[/green]"
                )

            return True

        except Exception as e:
            raise BackupError(f"Failed to delete backup: {e}")

    def get_backup_info(
        self, backup_name: str, backup_timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get detailed information about a backup"""
        backup_info = self._find_backup(backup_name, backup_timestamp)
        if not backup_info:
            raise BackupError(f"Backup not found: {backup_name}")

        backup_path = Path(backup_info["path"])

        # Get file information
        info = {
            "name": backup_name,
            "timestamp": backup_info["timestamp"],
            "date": backup_info["date"],
            "path": str(backup_path),
            "exists": backup_path.exists(),
            "description": backup_info.get("description", ""),
            "source_paths": backup_info.get("source_paths", []),
        }

        if backup_path.exists():
            stat = backup_path.stat()
            info.update(
                {
                    "size": stat.st_size,
                    "size_human": self._format_size(stat.st_size),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )

            # Get archive information
            try:
                archive_info = self.extract_manager.get_archive_info(backup_path)
                info.update(
                    {
                        "archive_format": archive_info["format"],
                        "member_count": archive_info["member_count"],
                        "uncompressed_size": archive_info["uncompressed_size"],
                        "uncompressed_size_human": self._format_size(
                            archive_info["uncompressed_size"]
                        ),
                    }
                )
            except Exception:
                pass  # Archive info is optional

        return info

    def cleanup_orphaned_backups(self) -> int:
        """Remove backup files that have no metadata entry"""
        metadata = self._load_backup_metadata()
        known_paths = set()

        # Collect all known backup paths
        for backup_data in metadata.values():
            for backup in backup_data["backups"]:
                known_paths.add(Path(backup["path"]))

        # Find orphaned backup files
        orphaned = []
        for backup_file in self.backup_dir.glob("*.tar.gz"):
            if backup_file not in known_paths:
                orphaned.append(backup_file)

        # Delete orphaned files
        deleted_count = 0
        for orphaned_file in orphaned:
            try:
                orphaned_file.unlink()
                deleted_count += 1
                if self.show_progress:
                    self.console.print(
                        f"[yellow]Deleted orphaned backup: {orphaned_file.name}[/yellow]"
                    )
            except Exception as e:
                if self.show_progress:
                    self.console.print(
                        f"[red]Failed to delete {orphaned_file.name}: {e}[/red]"
                    )

        return deleted_count

    def _copy_to_staging(
        self,
        source_paths: List[Path],
        staging_dir: Path,
        exclude_patterns: Optional[List[str]] = None,
    ) -> None:
        """Copy source paths to staging directory"""
        import fnmatch

        exclude_patterns = exclude_patterns or []

        progress = None
        if self.show_progress:
            progress = Progress(console=self.console)
            task = progress.add_task("Copying files...", total=len(source_paths))
            progress.start()

        try:
            for i, source_path in enumerate(source_paths):
                source_path = Path(source_path)

                if not source_path.exists():
                    if self.show_progress:
                        self.console.print(
                            f"[yellow]Warning: {source_path} does not exist[/yellow]"
                        )
                    continue

                # Determine destination in staging area
                if source_path.is_absolute():
                    # Create a relative path based on the source
                    rel_path = source_path.name
                else:
                    rel_path = str(source_path)

                dest_path = staging_dir / rel_path

                # Check if path should be excluded
                if any(
                    fnmatch.fnmatch(str(source_path), pattern)
                    for pattern in exclude_patterns
                ):
                    continue

                # Copy file or directory
                if source_path.is_file():
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, dest_path)
                elif source_path.is_dir():
                    self._copy_tree_with_excludes(
                        source_path, dest_path, exclude_patterns
                    )

                if progress:
                    progress.update(task, completed=i + 1)

        finally:
            if progress:
                progress.stop()

    def _copy_tree_with_excludes(
        self, source_dir: Path, dest_dir: Path, exclude_patterns: List[str]
    ) -> None:
        """Copy directory tree with exclusion patterns"""
        import fnmatch

        for root, dirs, files in os.walk(source_dir):
            root_path = Path(root)
            rel_root = root_path.relative_to(source_dir)
            dest_root = dest_dir / rel_root

            # Filter out excluded directories
            dirs[:] = [
                d
                for d in dirs
                if not any(fnmatch.fnmatch(d, pattern) for pattern in exclude_patterns)
            ]

            # Create destination directory
            dest_root.mkdir(parents=True, exist_ok=True)

            # Copy files
            for file in files:
                file_path = root_path / file
                if not any(
                    fnmatch.fnmatch(str(file_path), pattern)
                    for pattern in exclude_patterns
                ):
                    dest_file = dest_root / file
                    shutil.copy2(file_path, dest_file)

    def _record_backup_metadata(
        self,
        backup_name: str,
        backup_path: Path,
        source_paths: List[Path],
        description: str,
    ) -> None:
        """Record backup metadata"""
        metadata = self._load_backup_metadata()

        timestamp = datetime.now().isoformat()
        backup_info = {
            "timestamp": timestamp,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "path": str(backup_path),
            "source_paths": [str(p) for p in source_paths],
            "description": description,
        }

        if backup_name not in metadata:
            metadata[backup_name] = {"backups": []}

        metadata[backup_name]["backups"].append(backup_info)

        self._save_backup_metadata(metadata)

    def _load_backup_metadata(self) -> Dict[str, Any]:
        """Load backup metadata from file"""
        if not self.metadata_file.exists():
            return {}

        try:
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_backup_metadata(self, metadata: Dict[str, Any]) -> None:
        """Save backup metadata to file"""
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
            f.write("\n")

    def _find_backup(
        self, backup_name: str, timestamp: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Find a specific backup by name and optional timestamp"""
        metadata = self._load_backup_metadata()

        if backup_name not in metadata:
            return None

        backups = metadata[backup_name]["backups"]

        if timestamp:
            # Find specific timestamp
            for backup in backups:
                if backup["timestamp"] == timestamp:
                    return backup
            return None
        else:
            # Return latest backup
            return max(backups, key=lambda x: x["timestamp"]) if backups else None

    def _cleanup_old_backups(self, backup_name: str) -> None:
        """Clean up old backups based on retention policy"""
        if self.retention_count <= 0:
            return

        metadata = self._load_backup_metadata()
        if backup_name not in metadata:
            return

        backups = metadata[backup_name]["backups"]

        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x["timestamp"], reverse=True)

        # Keep only the specified number of backups
        if len(backups) > self.retention_count:
            backups_to_delete = backups[self.retention_count :]

            for backup in backups_to_delete:
                backup_path = Path(backup["path"])
                if backup_path.exists():
                    backup_path.unlink()
                    if self.show_progress:
                        self.console.print(
                            f"[dim]Cleaned up old backup: {backup_path.name}[/dim]"
                        )

            # Update metadata
            metadata[backup_name]["backups"] = backups[: self.retention_count]
            self._save_backup_metadata(metadata)

    def _get_file_size(self, file_path: str) -> int:
        """Get file size safely"""
        try:
            return Path(file_path).stat().st_size
        except (FileNotFoundError, OSError):
            return 0

    def _format_size(self, size: int) -> str:
        """Format file size in human readable format"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}PB"

    def print_backup_list(self) -> None:
        """Print formatted list of backups"""
        backups = self.list_backups()

        if not backups:
            self.console.print("[yellow]No backups found[/yellow]")
            return

        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Name", style="cyan")
        table.add_column("Date", style="green")
        table.add_column("Size", style="yellow")
        table.add_column("Description", style="dim")

        for backup in backups:
            size_str = self._format_size(backup["size"])
            table.add_row(
                backup["name"], backup["date"], size_str, backup["description"]
            )

        self.console.print(table)


if __name__ == "__main__":
    # CLI for testing backup functionality
    import click

    @click.group()
    @click.option("--backup-dir", default="./backups", help="Backup directory")
    @click.option("--retention", default=5, help="Number of backups to retain")
    @click.pass_context
    def cli(ctx, backup_dir, retention):
        """Backup management utilities"""
        ctx.ensure_object(dict)
        ctx.obj["manager"] = BackupManager(Path(backup_dir), retention)

    @cli.command()
    @click.argument("paths", nargs=-1, required=True)
    @click.argument("backup_name")
    @click.option("--description", default="", help="Backup description")
    @click.pass_context
    def create(ctx, paths, backup_name, description):
        """Create a backup"""
        try:
            manager = ctx.obj["manager"]
            source_paths = [Path(p) for p in paths]
            result = manager.create_backup(source_paths, backup_name, description)
            click.echo(f"Backup created: {result}")
        except BackupError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    @cli.command()
    @click.pass_context
    def list(ctx):
        """List all backups"""
        manager = ctx.obj["manager"]
        manager.print_backup_list()

    @cli.command()
    @click.argument("backup_name")
    @click.option("--restore-to", help="Directory to restore to")
    @click.pass_context
    def restore(ctx, backup_name, restore_to):
        """Restore a backup"""
        try:
            manager = ctx.obj["manager"]
            restore_path = Path(restore_to) if restore_to else None
            result = manager.restore_backup(backup_name, restore_path)
            click.echo(f"Backup restored to: {result}")
        except BackupError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    cli()
