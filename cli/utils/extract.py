#!/usr/bin/env python3
"""
Archive Extraction Manager for WSL-Tmux-Nvim-Setup CLI

Handles extraction of various archive formats with progress tracking.
"""

import os
import shutil
import tarfile
import zipfile
import sys
from pathlib import Path
from typing import Optional, List, Callable

try:
    from rich.progress import Progress, TaskID
    from rich.console import Console
except ImportError as e:
    print(f"Error: Required package not found: {e}", file=sys.stderr)
    print("Install with: pip install rich", file=sys.stderr)
    sys.exit(1)


class ExtractionError(Exception):
    """Archive extraction related errors"""
    pass


class ExtractManager:
    """Manages archive extraction with progress tracking"""
    
    def __init__(self, show_progress: bool = True):
        self.show_progress = show_progress
        self.console = Console()
        
        # Supported archive formats
        self.supported_formats = {
            '.tar.gz': self._extract_tar,
            '.tgz': self._extract_tar,
            '.tar.xz': self._extract_tar,
            '.tar.bz2': self._extract_tar,
            '.tar': self._extract_tar,
            '.zip': self._extract_zip,
        }
    
    def extract_archive(self, archive_path: Path, extract_to: Path,
                       strip_components: int = 0,
                       progress_callback: Optional[Callable] = None) -> Path:
        """
        Extract archive to specified directory
        
        Args:
            archive_path: Path to archive file
            extract_to: Directory to extract to
            strip_components: Number of leading path components to strip
            progress_callback: Optional callback for progress updates
        
        Returns:
            Path to extraction directory
        
        Raises:
            ExtractionError: If extraction fails
        """
        if not archive_path.exists():
            raise ExtractionError(f"Archive not found: {archive_path}")
        
        # Determine archive format
        archive_format = self._detect_format(archive_path)
        if not archive_format:
            raise ExtractionError(f"Unsupported archive format: {archive_path}")
        
        # Create extraction directory
        extract_to = Path(extract_to)
        extract_to.mkdir(parents=True, exist_ok=True)
        
        if self.show_progress:
            self.console.print(f"[blue]Extracting {archive_path.name}...[/blue]")
        
        try:
            # Extract using appropriate method
            extractor = self.supported_formats[archive_format]
            result_path = extractor(
                archive_path, extract_to, strip_components, progress_callback
            )
            
            if self.show_progress:
                self.console.print(f"[green]✓ Extracted to: {result_path}[/green]")
            
            return result_path
            
        except Exception as e:
            raise ExtractionError(f"Failed to extract {archive_path}: {e}")
    
    def _detect_format(self, archive_path: Path) -> Optional[str]:
        """Detect archive format from file extension"""
        path_str = str(archive_path).lower()
        
        # Check for compound extensions first
        for ext in ['.tar.gz', '.tar.xz', '.tar.bz2']:
            if path_str.endswith(ext):
                return ext
        
        # Check simple extensions
        suffix = archive_path.suffix.lower()
        if suffix in self.supported_formats:
            return suffix
        
        return None
    
    def _extract_tar(self, archive_path: Path, extract_to: Path, 
                    strip_components: int = 0,
                    progress_callback: Optional[Callable] = None) -> Path:
        """Extract tar archive"""
        
        with tarfile.open(archive_path, 'r:*') as tar:
            members = tar.getmembers()
            total_members = len(members)
            
            # Setup progress tracking
            progress = None
            task = None
            if self.show_progress:
                progress = Progress(console=self.console)
                task = progress.add_task(
                    f"Extracting {archive_path.name}", 
                    total=total_members
                )
                progress.start()
            
            try:
                extracted_count = 0
                for member in members:
                    # Strip path components if requested
                    if strip_components > 0:
                        path_parts = Path(member.name).parts
                        if len(path_parts) > strip_components:
                            # Reconstruct path without leading components
                            new_name = str(Path(*path_parts[strip_components:]))
                            member.name = new_name
                        else:
                            # Skip this member if stripping would remove everything
                            continue
                    
                    # Security check: ensure path is within extraction directory
                    full_path = extract_to / member.name
                    if not self._is_safe_path(extract_to, full_path):
                        if self.show_progress:
                            self.console.print(f"[yellow]Skipping unsafe path: {member.name}[/yellow]")
                        continue
                    
                    tar.extract(member, extract_to)
                    extracted_count += 1
                    
                    if progress:
                        progress.update(task, completed=extracted_count)
                    
                    if progress_callback:
                        progress_callback(extracted_count, total_members)
                        
            finally:
                if progress:
                    progress.stop()
        
        return extract_to
    
    def _extract_zip(self, archive_path: Path, extract_to: Path,
                    strip_components: int = 0,
                    progress_callback: Optional[Callable] = None) -> Path:
        """Extract zip archive"""
        
        with zipfile.ZipFile(archive_path, 'r') as zip_file:
            members = zip_file.namelist()
            total_members = len(members)
            
            # Setup progress tracking
            progress = None
            task = None
            if self.show_progress:
                progress = Progress(console=self.console)
                task = progress.add_task(
                    f"Extracting {archive_path.name}", 
                    total=total_members
                )
                progress.start()
            
            try:
                extracted_count = 0
                for member_name in members:
                    member_path = member_name
                    
                    # Strip path components if requested
                    if strip_components > 0:
                        path_parts = Path(member_name).parts
                        if len(path_parts) > strip_components:
                            member_path = str(Path(*path_parts[strip_components:]))
                        else:
                            continue  # Skip if stripping would remove everything
                    
                    # Security check
                    full_path = extract_to / member_path
                    if not self._is_safe_path(extract_to, full_path):
                        if self.show_progress:
                            self.console.print(f"[yellow]Skipping unsafe path: {member_name}[/yellow]")
                        continue
                    
                    # Extract member
                    source = zip_file.open(member_name)
                    target_path = extract_to / member_path
                    
                    # Create parent directories
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Extract file
                    if not member_name.endswith('/'):  # Not a directory
                        with open(target_path, 'wb') as target_file:
                            shutil.copyfileobj(source, target_file)
                    
                    source.close()
                    extracted_count += 1
                    
                    if progress:
                        progress.update(task, completed=extracted_count)
                    
                    if progress_callback:
                        progress_callback(extracted_count, total_members)
                        
            finally:
                if progress:
                    progress.stop()
        
        return extract_to
    
    def _is_safe_path(self, base_path: Path, target_path: Path) -> bool:
        """Check if extraction path is safe (prevents directory traversal)"""
        try:
            # Resolve both paths to absolute paths
            base_abs = base_path.resolve()
            target_abs = target_path.resolve()
            
            # Check if target is within base directory
            return base_abs in target_abs.parents or target_abs == base_abs
            
        except Exception:
            # If we can't resolve paths, err on the side of caution
            return False
    
    def list_archive_contents(self, archive_path: Path) -> List[str]:
        """List contents of archive without extracting"""
        if not archive_path.exists():
            raise ExtractionError(f"Archive not found: {archive_path}")
        
        archive_format = self._detect_format(archive_path)
        if not archive_format:
            raise ExtractionError(f"Unsupported archive format: {archive_path}")
        
        try:
            if archive_format in ['.tar.gz', '.tgz', '.tar.xz', '.tar.bz2', '.tar']:
                with tarfile.open(archive_path, 'r:*') as tar:
                    return [member.name for member in tar.getmembers()]
                    
            elif archive_format == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zip_file:
                    return zip_file.namelist()
                    
        except Exception as e:
            raise ExtractionError(f"Failed to list archive contents: {e}")
        
        return []
    
    def get_archive_info(self, archive_path: Path) -> dict:
        """Get information about archive"""
        if not archive_path.exists():
            raise ExtractionError(f"Archive not found: {archive_path}")
        
        info = {
            'path': archive_path,
            'size': archive_path.stat().st_size,
            'format': self._detect_format(archive_path),
            'member_count': 0,
            'uncompressed_size': 0
        }
        
        try:
            contents = self.list_archive_contents(archive_path)
            info['member_count'] = len(contents)
            
            # Try to get uncompressed size for supported formats
            if info['format'] in ['.tar.gz', '.tgz', '.tar.xz', '.tar.bz2', '.tar']:
                with tarfile.open(archive_path, 'r:*') as tar:
                    info['uncompressed_size'] = sum(
                        member.size for member in tar.getmembers() if member.isfile()
                    )
            elif info['format'] == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zip_file:
                    info['uncompressed_size'] = sum(
                        zip_info.file_size for zip_info in zip_file.filelist
                    )
                    
        except Exception:
            pass  # Not critical, just informational
        
        return info
    
    def create_archive(self, source_dir: Path, archive_path: Path,
                      archive_format: str = 'tar.gz',
                      exclude_patterns: Optional[List[str]] = None) -> Path:
        """
        Create archive from directory
        
        Args:
            source_dir: Directory to archive
            archive_path: Path for created archive
            archive_format: Archive format (tar.gz, zip, etc.)
            exclude_patterns: Patterns to exclude from archive
        
        Returns:
            Path to created archive
        """
        if not source_dir.exists() or not source_dir.is_dir():
            raise ExtractionError(f"Source directory not found: {source_dir}")
        
        # Ensure archive directory exists
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        
        exclude_patterns = exclude_patterns or []
        
        if self.show_progress:
            self.console.print(f"[blue]Creating archive: {archive_path.name}[/blue]")
        
        try:
            if archive_format in ['tar.gz', 'tgz']:
                mode = 'w:gz'
            elif archive_format in ['tar.xz']:
                mode = 'w:xz'
            elif archive_format in ['tar.bz2']:
                mode = 'w:bz2'
            elif archive_format == 'tar':
                mode = 'w'
            elif archive_format == 'zip':
                return self._create_zip_archive(source_dir, archive_path, exclude_patterns)
            else:
                raise ExtractionError(f"Unsupported archive format: {archive_format}")
            
            # Create tar archive
            with tarfile.open(archive_path, mode) as tar:
                for root, dirs, files in os.walk(source_dir):
                    # Filter out excluded directories
                    dirs[:] = [d for d in dirs if not self._should_exclude(d, exclude_patterns)]
                    
                    for file in files:
                        file_path = Path(root) / file
                        if not self._should_exclude(str(file_path), exclude_patterns):
                            # Calculate relative path
                            rel_path = file_path.relative_to(source_dir)
                            tar.add(file_path, arcname=rel_path)
            
            if self.show_progress:
                self.console.print(f"[green]✓ Created archive: {archive_path}[/green]")
            
            return archive_path
            
        except Exception as e:
            if archive_path.exists():
                archive_path.unlink()  # Clean up partial archive
            raise ExtractionError(f"Failed to create archive: {e}")
    
    def _create_zip_archive(self, source_dir: Path, archive_path: Path,
                           exclude_patterns: List[str]) -> Path:
        """Create ZIP archive"""
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for root, dirs, files in os.walk(source_dir):
                # Filter out excluded directories
                dirs[:] = [d for d in dirs if not self._should_exclude(d, exclude_patterns)]
                
                for file in files:
                    file_path = Path(root) / file
                    if not self._should_exclude(str(file_path), exclude_patterns):
                        # Calculate relative path
                        rel_path = file_path.relative_to(source_dir)
                        zip_file.write(file_path, arcname=rel_path)
        
        return archive_path
    
    def _should_exclude(self, path: str, patterns: List[str]) -> bool:
        """Check if path matches any exclude pattern"""
        import fnmatch
        
        for pattern in patterns:
            if fnmatch.fnmatch(path, pattern):
                return True
        
        return False


def extract_archive(archive_path: Path, extract_to: Path, **kwargs) -> Path:
    """Convenience function for extracting archives"""
    manager = ExtractManager()
    return manager.extract_archive(archive_path, extract_to, **kwargs)


if __name__ == '__main__':
    # CLI for testing extraction
    import click
    
    @click.group()
    def cli():
        """Archive extraction utilities"""
        pass
    
    @cli.command()
    @click.argument('archive_path', type=click.Path(exists=True))
    @click.argument('extract_to', type=click.Path())
    @click.option('--strip-components', default=0, help='Strip leading path components')
    def extract(archive_path, extract_to, strip_components):
        """Extract archive to directory"""
        try:
            manager = ExtractManager()
            result = manager.extract_archive(
                Path(archive_path), 
                Path(extract_to),
                strip_components=strip_components
            )
            click.echo(f"Extracted to: {result}")
            
        except ExtractionError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    @cli.command()
    @click.argument('archive_path', type=click.Path(exists=True))
    def list(archive_path):
        """List archive contents"""
        try:
            manager = ExtractManager(show_progress=False)
            contents = manager.list_archive_contents(Path(archive_path))
            
            for item in contents:
                click.echo(item)
                
        except ExtractionError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    @cli.command()
    @click.argument('archive_path', type=click.Path(exists=True))
    def info(archive_path):
        """Show archive information"""
        try:
            manager = ExtractManager(show_progress=False)
            info = manager.get_archive_info(Path(archive_path))
            
            click.echo(f"Archive: {info['path']}")
            click.echo(f"Format: {info['format']}")
            click.echo(f"Size: {info['size']} bytes")
            click.echo(f"Members: {info['member_count']}")
            if info['uncompressed_size']:
                click.echo(f"Uncompressed: {info['uncompressed_size']} bytes")
                
        except ExtractionError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    
    cli()