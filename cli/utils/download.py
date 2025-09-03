#!/usr/bin/env python3
"""
Download Manager for WSL-Tmux-Nvim-Setup CLI

Handles file downloads with progress bars, resume capability, and error handling.
"""

import hashlib
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlparse

try:
    import click
    import requests
    from requests.adapters import HTTPAdapter
    from rich.console import Console
    from rich.progress import (
        DownloadColumn,
        Progress,
        TimeRemainingColumn,
        TransferSpeedColumn,
    )
    from urllib3.util.retry import Retry
except ImportError as e:
    print(f"Error: Required package not found: {e}", file=sys.stderr)
    print("Install with: pip install requests rich click", file=sys.stderr)
    sys.exit(1)


class DownloadError(Exception):
    """Download-related errors"""


class DownloadManager:
    """Enhanced download manager with network resilience"""

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        chunk_size: int = 8192,
        show_progress: bool = True,
        cache_enabled: bool = True,
        offline_mode: bool = False,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.chunk_size = chunk_size
        self.show_progress = show_progress
        self.console = Console()

        # Enhanced network resilience
        if cache_enabled:
            try:
                from .network_resilience import create_network_downloader

                self.network_downloader = create_network_downloader(
                    offline_mode=offline_mode, console=self.console
                )
                self.use_enhanced_network = True
            except ImportError:
                self.use_enhanced_network = False
        else:
            self.use_enhanced_network = False

        # Fallback to original session setup
        if not self.use_enhanced_network:
            self.session = requests.Session()
            retry_strategy = Retry(
                total=max_retries,
                status_forcelist=[429, 500, 502, 503, 504],
                method_whitelist=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"],
                backoff_factor=1,
                respect_retry_after_header=True,
            )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set user agent
        self.session.headers.update(
            {
                "User-Agent": "wsl-tmux-nvim-setup-cli/1.0 (https://github.com/albertodall/wsl-tmux-nvim-setup)"
            }
        )

    def download_file(
        self,
        url: str,
        output_path: Path,
        expected_hash: Optional[str] = None,
        hash_algorithm: str = "sha256",
        resume: bool = True,
        progress_callback: Optional[Callable] = None,
    ) -> Path:
        """
        Download a file from URL to output path

        Args:
            url: Download URL
            output_path: Path where file should be saved
            expected_hash: Expected file hash for verification
            hash_algorithm: Hash algorithm to use (sha256, md5, etc.)
            resume: Whether to resume partial downloads
            progress_callback: Optional callback for progress updates

        Returns:
            Path to downloaded file

        Raises:
            DownloadError: If download fails
        """
        output_path = Path(output_path)

        # Use enhanced network downloader if available
        if self.use_enhanced_network:
            from .network_resilience import DownloadTask

            task = DownloadTask(
                url=url,
                destination=output_path,
                expected_hash=expected_hash,
                hash_algorithm=hash_algorithm,
                max_retries=self.max_retries,
                timeout=self.timeout,
                chunk_size=self.chunk_size,
                resumable=resume,
            )

            success = self.network_downloader.download_file(task, self.show_progress)
            if success:
                return output_path
            else:
                raise DownloadError(f"Enhanced download failed for {url}")

        # Create directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if we should resume download
        resume_byte_pos = 0
        if resume and output_path.exists():
            resume_byte_pos = output_path.stat().st_size
            if self.show_progress:
                self.console.print(
                    f"[yellow]Resuming download from byte {resume_byte_pos}[/yellow]"
                )

        try:
            # Make HEAD request to get file info
            head_response = self.session.head(url, timeout=self.timeout)
            head_response.raise_for_status()

            total_size = int(head_response.headers.get("content-length", 0))
            supports_range = head_response.headers.get("accept-ranges") == "bytes"

            # Setup headers for resume
            headers = {}
            if resume and resume_byte_pos > 0 and supports_range:
                headers["Range"] = f"bytes={resume_byte_pos}-"
                if total_size > 0:
                    total_size -= resume_byte_pos
            elif resume_byte_pos > 0:
                # Server doesn't support range requests, start over
                resume_byte_pos = 0
                if output_path.exists():
                    output_path.unlink()

            # Make download request
            response = self.session.get(
                url, headers=headers, stream=True, timeout=self.timeout
            )
            response.raise_for_status()

            # Update total size if we got content-length from GET request
            if not total_size and "content-length" in response.headers:
                total_size = int(response.headers["content-length"])

            # Open file for writing (append if resuming)
            file_mode = "ab" if resume_byte_pos > 0 else "wb"

            downloaded = resume_byte_pos
            hash_obj = None
            if expected_hash:
                hash_obj = getattr(hashlib, hash_algorithm.lower())()

                # If resuming, we need to rehash the existing content
                if resume_byte_pos > 0 and output_path.exists():
                    with open(output_path, "rb") as existing_file:
                        while True:
                            chunk = existing_file.read(self.chunk_size)
                            if not chunk:
                                break
                            hash_obj.update(chunk)

            # Setup progress bar
            progress = None
            task = None
            if self.show_progress:
                progress = Progress(
                    "[progress.description]{task.description}",
                    "[progress.percentage]{task.percentage:>3.0f}%",
                    DownloadColumn(),
                    TransferSpeedColumn(),
                    TimeRemainingColumn(),
                    console=self.console,
                )
                filename = output_path.name
                total_display = total_size + resume_byte_pos if total_size else None
                task = progress.add_task(f"Downloading {filename}", total=total_display)
                progress.start()

                if resume_byte_pos > 0:
                    progress.update(task, completed=resume_byte_pos)

            try:
                with open(output_path, file_mode) as f:
                    for chunk in response.iter_content(chunk_size=self.chunk_size):
                        if chunk:  # Filter out keep-alive chunks
                            f.write(chunk)
                            downloaded += len(chunk)

                            if hash_obj:
                                hash_obj.update(chunk)

                            if progress:
                                progress.update(task, completed=downloaded)

                            if progress_callback:
                                progress_callback(
                                    downloaded,
                                    (
                                        total_size + resume_byte_pos
                                        if total_size
                                        else None
                                    ),
                                )

            finally:
                if progress:
                    progress.stop()

            # Verify hash if provided
            if expected_hash and hash_obj:
                actual_hash = hash_obj.hexdigest()
                if actual_hash.lower() != expected_hash.lower():
                    output_path.unlink()  # Remove corrupted file
                    raise DownloadError(
                        f"Hash mismatch: expected {expected_hash}, got {actual_hash}"
                    )

                if self.show_progress:
                    self.console.print("[green]✓ Hash verification passed[/green]")

            if self.show_progress:
                self.console.print(f"[green]✓ Downloaded: {output_path.name}[/green]")

            return output_path

        except requests.exceptions.RequestException as e:
            if output_path.exists() and not resume:
                output_path.unlink()  # Clean up partial download if not resuming
            raise DownloadError(f"Download failed for {url}: {e}")

        except Exception as e:
            if output_path.exists() and not resume:
                output_path.unlink()
            raise DownloadError(f"Unexpected error downloading {url}: {e}")

    def download_multiple(
        self, downloads: Dict[str, Dict[str, Any]], max_concurrent: int = 4
    ) -> Dict[str, Path]:
        """
        Download multiple files concurrently

        Args:
            downloads: Dict mapping filenames to download configs
                      Each config should have 'url' and 'output_path' keys
            max_concurrent: Maximum concurrent downloads

        Returns:
            Dict mapping filenames to downloaded file paths
        """
        import concurrent.futures

        results = {}
        errors = {}

        def download_worker(name: str, config: Dict[str, Any]) -> tuple:
            try:
                output_path = self.download_file(**config)
                return name, output_path, None
            except Exception as e:
                return name, None, e

        # Use ThreadPoolExecutor for concurrent downloads
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=max_concurrent
        ) as executor:
            # Submit all download tasks
            future_to_name = {
                executor.submit(download_worker, name, config): name
                for name, config in downloads.items()
            }

            # Collect results
            for future in concurrent.futures.as_completed(future_to_name):
                name, output_path, error = future.result()

                if error:
                    errors[name] = error
                else:
                    results[name] = output_path

        # Report any errors
        if errors:
            error_msg = "Download errors:\n"
            for name, error in errors.items():
                error_msg += f"  {name}: {error}\n"
            raise DownloadError(error_msg.strip())

        return results

    def get_file_info(self, url: str) -> Dict[str, Any]:
        """
        Get information about a remote file without downloading

        Returns:
            Dict with file information (size, content-type, supports_range, etc.)
        """
        try:
            response = self.session.head(url, timeout=self.timeout)
            response.raise_for_status()

            return {
                "size": int(response.headers.get("content-length", 0)),
                "content_type": response.headers.get("content-type", "unknown"),
                "supports_range": response.headers.get("accept-ranges") == "bytes",
                "last_modified": response.headers.get("last-modified"),
                "etag": response.headers.get("etag"),
                "filename": self._extract_filename_from_headers(response.headers, url),
            }

        except requests.exceptions.RequestException as e:
            raise DownloadError(f"Failed to get file info for {url}: {e}")

    def _extract_filename_from_headers(self, headers: Dict[str, str], url: str) -> str:
        """Extract filename from response headers or URL"""
        # Try content-disposition header first
        content_disposition = headers.get("content-disposition", "")
        if "filename=" in content_disposition:
            import re

            match = re.search(r"filename[*]?=([^;]+)", content_disposition)
            if match:
                filename = match.group(1).strip("\"'")
                return filename

        # Fall back to URL path
        parsed_url = urlparse(url)
        return Path(parsed_url.path).name or "download"

    def verify_file_hash(
        self, file_path: Path, expected_hash: str, algorithm: str = "sha256"
    ) -> bool:
        """
        Verify file hash

        Args:
            file_path: Path to file to verify
            expected_hash: Expected hash value
            algorithm: Hash algorithm (sha256, md5, etc.)

        Returns:
            True if hash matches, False otherwise
        """
        if not file_path.exists():
            return False

        try:
            hash_obj = getattr(hashlib, algorithm.lower())()

            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    hash_obj.update(chunk)

            actual_hash = hash_obj.hexdigest()
            return actual_hash.lower() == expected_hash.lower()

        except Exception:
            return False


def download_with_progress(url: str, output_path: Path, **kwargs) -> Path:
    """Convenience function for downloading with progress"""
    manager = DownloadManager()
    return manager.download_file(url, output_path, **kwargs)


if __name__ == "__main__":
    # CLI for testing downloads
    @click.command()
    @click.argument("url")
    @click.argument("output", type=click.Path())
    @click.option("--hash", help="Expected file hash")
    @click.option("--algorithm", default="sha256", help="Hash algorithm")
    @click.option("--resume/--no-resume", default=True, help="Resume partial downloads")
    @click.option("--quiet", is_flag=True, help="Quiet mode")
    def cli(url, output, hash, algorithm, resume, quiet):
        """Download a file with progress tracking"""
        try:
            manager = DownloadManager(show_progress=not quiet)
            result = manager.download_file(
                url=url,
                output_path=Path(output),
                expected_hash=hash,
                hash_algorithm=algorithm,
                resume=resume,
            )

            if not quiet:
                click.echo(f"Downloaded: {result}")

        except DownloadError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    cli()
