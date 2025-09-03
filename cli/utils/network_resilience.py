#!/usr/bin/env python3
"""
Network Resilience System for WSM CLI

Provides robust network operations with retries, mirrors, offline mode, and caching.
"""

import hashlib
import json
import sys
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry
    from rich.console import Console
    from rich.progress import (
        DownloadColumn,
        Progress,
        TimeRemainingColumn,
        TransferSpeedColumn,
    )
except ImportError as e:
    print(f"Error: Required packages not found: {e}", file=sys.stderr)
    sys.exit(1)


class NetworkMode(Enum):
    """Network operation modes"""

    ONLINE = "online"
    OFFLINE = "offline"
    AUTO = "auto"


class MirrorStatus(Enum):
    """Mirror health status"""

    HEALTHY = "healthy"
    SLOW = "slow"
    UNREACHABLE = "unreachable"
    UNKNOWN = "unknown"


@dataclass
class Mirror:
    """Mirror configuration"""

    name: str
    base_url: str
    priority: int = 1
    status: MirrorStatus = MirrorStatus.UNKNOWN
    response_time: float = 0.0
    last_checked: Optional[datetime] = None
    success_rate: float = 0.0
    total_requests: int = 0
    successful_requests: int = 0


@dataclass
class CacheEntry:
    """Cache entry metadata"""

    url: str
    file_path: Path
    content_type: str
    size: int
    etag: Optional[str] = None
    last_modified: Optional[datetime] = None
    cached_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)


@dataclass
class DownloadTask:
    """Download task configuration"""

    url: str
    destination: Path
    expected_size: Optional[int] = None
    expected_hash: Optional[str] = None
    hash_algorithm: str = "sha256"
    max_retries: int = 3
    timeout: int = 30
    chunk_size: int = 8192
    resumable: bool = True
    mirrors: List[str] = field(default_factory=list)
    priority: int = 1


class NetworkResilientDownloader:
    """Network resilient download manager"""

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        max_cache_size: int = 1024 * 1024 * 1024,  # 1GB
        offline_mode: bool = False,
        console: Optional[Console] = None,
    ):

        self.console = console or Console()
        self.offline_mode = offline_mode
        self.max_cache_size = max_cache_size

        # Setup cache directory
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "wsl-tmux-nvim-setup"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Cache management
        self.cache_index_file = self.cache_dir / "cache_index.json"
        self.cache_entries: Dict[str, CacheEntry] = {}
        self._load_cache_index()

        # Mirror management
        self.mirrors: Dict[str, Mirror] = {}
        self.default_mirrors = [
            Mirror("github", "https://github.com", priority=1),
            Mirror("github_api", "https://api.github.com", priority=1),
        ]
        self._initialize_mirrors()

        # Network session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set user agent
        self.session.headers.update(
            {
                "User-Agent": "WSL-Tmux-Nvim-Setup/1.0 (+https://github.com/albert-kw/wsl-tmux-nvim-setup)"
            }
        )

        # Statistics
        self.stats = {
            "downloads_attempted": 0,
            "downloads_successful": 0,
            "downloads_failed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "bytes_downloaded": 0,
            "bytes_cached": 0,
            "network_errors": 0,
            "retry_attempts": 0,
        }

    def _initialize_mirrors(self):
        """Initialize mirror configurations"""
        for mirror in self.default_mirrors:
            self.mirrors[mirror.name] = mirror

        # Load custom mirrors from config
        mirrors_config_file = self.cache_dir / "mirrors.json"
        if mirrors_config_file.exists():
            try:
                with open(mirrors_config_file, "r") as f:
                    mirrors_data = json.load(f)
                    for mirror_data in mirrors_data.get("mirrors", []):
                        mirror = Mirror(**mirror_data)
                        self.mirrors[mirror.name] = mirror
            except Exception as e:
                self.console.print(f"[yellow]Warning: Failed to load mirrors config: {e}[/yellow]")

    def _load_cache_index(self):
        """Load cache index from disk"""
        if not self.cache_index_file.exists():
            return

        try:
            with open(self.cache_index_file, "r") as f:
                cache_data = json.load(f)

                for url, entry_data in cache_data.get("entries", {}).items():
                    # Convert datetime strings back to datetime objects
                    for date_field in [
                        "last_modified",
                        "cached_at",
                        "expires_at",
                        "last_accessed",
                    ]:
                        if entry_data.get(date_field):
                            entry_data[date_field] = datetime.fromisoformat(entry_data[date_field])

                    entry_data["file_path"] = Path(entry_data["file_path"])
                    self.cache_entries[url] = CacheEntry(**entry_data)

        except Exception as e:
            self.console.print(f"[yellow]Warning: Failed to load cache index: {e}[/yellow]")

    def _save_cache_index(self):
        """Save cache index to disk"""
        try:
            cache_data = {
                "version": "1.0",
                "created": datetime.now().isoformat(),
                "entries": {},
            }

            for url, entry in self.cache_entries.items():
                # Convert datetime objects to strings for JSON serialization
                entry_data = {
                    "url": entry.url,
                    "file_path": str(entry.file_path),
                    "content_type": entry.content_type,
                    "size": entry.size,
                    "etag": entry.etag,
                    "cached_at": entry.cached_at.isoformat(),
                    "access_count": entry.access_count,
                    "last_accessed": entry.last_accessed.isoformat(),
                }

                if entry.last_modified:
                    entry_data["last_modified"] = entry.last_modified.isoformat()
                if entry.expires_at:
                    entry_data["expires_at"] = entry.expires_at.isoformat()

                cache_data["entries"][url] = entry_data

            with open(self.cache_index_file, "w") as f:
                json.dump(cache_data, f, indent=2)

        except Exception as e:
            self.console.print(f"[yellow]Warning: Failed to save cache index: {e}[/yellow]")

    def add_mirror(self, name: str, base_url: str, priority: int = 1):
        """Add a new mirror"""
        mirror = Mirror(name=name, base_url=base_url, priority=priority)
        self.mirrors[name] = mirror
        self.check_mirror_health(mirror)

    def check_mirror_health(self, mirror: Mirror) -> bool:
        """Check mirror health and update status"""
        try:
            start_time = time.time()
            response = self.session.head(mirror.base_url, timeout=10, allow_redirects=True)
            response_time = time.time() - start_time

            mirror.response_time = response_time
            mirror.last_checked = datetime.now()
            mirror.total_requests += 1

            if response.status_code < 400:
                mirror.successful_requests += 1

                if response_time < 2.0:
                    mirror.status = MirrorStatus.HEALTHY
                else:
                    mirror.status = MirrorStatus.SLOW

                mirror.success_rate = mirror.successful_requests / mirror.total_requests
                return True
            else:
                mirror.status = MirrorStatus.UNREACHABLE

        except Exception as e:
            self.console.print(f"[dim]Mirror {mirror.name} check failed: {e}[/dim]")
            mirror.status = MirrorStatus.UNREACHABLE

        mirror.success_rate = (
            mirror.successful_requests / mirror.total_requests if mirror.total_requests > 0 else 0.0
        )
        return False

    def get_best_mirrors(self, count: int = 3) -> List[Mirror]:
        """Get best available mirrors sorted by priority and health"""
        available_mirrors = [
            mirror
            for mirror in self.mirrors.values()
            if mirror.status in [MirrorStatus.HEALTHY, MirrorStatus.SLOW, MirrorStatus.UNKNOWN]
        ]

        # Sort by priority (higher is better) and success rate
        available_mirrors.sort(
            key=lambda m: (m.priority, m.success_rate, -m.response_time), reverse=True
        )

        return available_mirrors[:count]

    def _get_cache_key(self, url: str) -> str:
        """Generate cache key for URL"""
        return hashlib.sha256(url.encode()).hexdigest()

    def _get_cached_file_path(self, url: str) -> Path:
        """Get cached file path for URL"""
        cache_key = self._get_cache_key(url)
        return self.cache_dir / "files" / cache_key[:2] / cache_key[2:4] / cache_key

    def is_cached(self, url: str, max_age: Optional[timedelta] = None) -> bool:
        """Check if URL is cached and valid"""
        if url not in self.cache_entries:
            return False

        entry = self.cache_entries[url]

        # Check if file exists
        if not entry.file_path.exists():
            del self.cache_entries[url]
            return False

        # Check expiration
        if entry.expires_at and datetime.now() > entry.expires_at:
            return False

        # Check max age
        if max_age and datetime.now() - entry.cached_at > max_age:
            return False

        return True

    def get_cached_file(self, url: str) -> Optional[Path]:
        """Get cached file path if available"""
        if self.is_cached(url):
            entry = self.cache_entries[url]
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            self.stats["cache_hits"] += 1
            return entry.file_path

        self.stats["cache_misses"] += 1
        return None

    def cache_cleanup(self, max_size: Optional[int] = None):
        """Clean up cache to reduce size"""
        if max_size is None:
            max_size = self.max_cache_size

        # Calculate current cache size
        total_size = 0
        valid_entries = {}

        for url, entry in self.cache_entries.items():
            if entry.file_path.exists():
                entry.size = entry.file_path.stat().st_size
                total_size += entry.size
                valid_entries[url] = entry
            # Remove invalid entries

        self.cache_entries = valid_entries

        if total_size <= max_size:
            return

        # Sort entries by priority (least recently used, lowest access count)
        sorted_entries = sorted(
            self.cache_entries.items(),
            key=lambda x: (x[1].access_count, x[1].last_accessed),
        )

        # Remove entries until under size limit
        for url, entry in sorted_entries:
            try:
                entry.file_path.unlink()
                total_size -= entry.size
                del self.cache_entries[url]

                if total_size <= max_size:
                    break
            except Exception:
                pass

        self._save_cache_index()

    def _try_mirrors(self, url: str, task: DownloadTask) -> Optional[requests.Response]:
        """Try downloading from mirrors"""
        mirrors_to_try = self.get_best_mirrors()

        # Add specific mirrors from task
        if task.mirrors:
            for mirror_name in task.mirrors:
                if mirror_name in self.mirrors:
                    mirrors_to_try.insert(0, self.mirrors[mirror_name])

        # Try original URL first
        for attempt in range(task.max_retries):
            try:
                response = self.session.get(
                    url, timeout=task.timeout, stream=True, allow_redirects=True
                )

                if response.status_code == 200:
                    return response
                elif response.status_code == 404:
                    break  # Don't retry 404s

            except Exception as e:
                self.stats["network_errors"] += 1
                if attempt < task.max_retries - 1:
                    self.stats["retry_attempts"] += 1
                    wait_time = 2**attempt
                    self.console.print(
                        f"[yellow]Network error, retrying in {wait_time}s: {e}[/yellow]"
                    )
                    time.sleep(wait_time)

        # Try mirrors if original URL failed
        for mirror in mirrors_to_try:
            if mirror.status == MirrorStatus.UNREACHABLE:
                continue

            try:
                # Replace base URL with mirror URL
                parsed_url = urllib.parse.urlparse(url)
                parsed_mirror = urllib.parse.urlparse(mirror.base_url)

                mirror_url = urllib.parse.urlunparse(
                    (
                        parsed_mirror.scheme,
                        parsed_mirror.netloc,
                        parsed_url.path,
                        parsed_url.params,
                        parsed_url.query,
                        parsed_url.fragment,
                    )
                )

                response = self.session.get(
                    mirror_url, timeout=task.timeout, stream=True, allow_redirects=True
                )

                if response.status_code == 200:
                    mirror.successful_requests += 1
                    return response

            except Exception:
                mirror.total_requests += 1
                self.stats["network_errors"] += 1
                continue

        return None

    def download_file(self, task: DownloadTask, show_progress: bool = True) -> bool:
        """Download file with resilience features"""

        self.stats["downloads_attempted"] += 1

        # Check offline mode
        if self.offline_mode:
            cached_file = self.get_cached_file(task.url)
            if cached_file:
                if cached_file != task.destination:
                    # Copy from cache to destination
                    import shutil

                    task.destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(cached_file, task.destination)
                return True
            else:
                self.console.print(f"[red]Offline mode: {task.url} not in cache[/red]")
                return False

        # Check cache first
        cached_file = self.get_cached_file(task.url)
        if cached_file and not task.expected_hash:
            # Use cached file if no hash verification required
            if cached_file != task.destination:
                import shutil

                task.destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(cached_file, task.destination)
            return True

        # Prepare destination
        task.destination.parent.mkdir(parents=True, exist_ok=True)

        # Check for partial download (resume support)
        resume_pos = 0
        if task.resumable and task.destination.exists():
            resume_pos = task.destination.stat().st_size

        # Try download
        response = self._try_mirrors(task.url, task)
        if not response:
            self.stats["downloads_failed"] += 1
            return False

        # Setup resume headers
        if resume_pos > 0:
            resume_headers = {"Range": f"bytes={resume_pos}-"}
            try:
                response = self.session.get(
                    task.url, headers=resume_headers, timeout=task.timeout, stream=True
                )
                if response.status_code not in [
                    206,
                    416,
                ]:  # Partial content or range not satisfiable
                    resume_pos = 0  # Start fresh
                    response = self.session.get(task.url, timeout=task.timeout, stream=True)
            except Exception:
                resume_pos = 0
                response = self.session.get(task.url, timeout=task.timeout, stream=True)

        # Get content information
        total_size = task.expected_size
        if not total_size:
            content_length = response.headers.get("content-length")
            if content_length:
                total_size = int(content_length)
                if resume_pos > 0:
                    total_size += resume_pos

        # Download with progress
        try:
            mode = "ab" if resume_pos > 0 else "wb"

            with open(task.destination, mode) as f:
                if show_progress and total_size:
                    with Progress(
                        "[progress.description]{task.description}",
                        "[progress.percentage]{task.percentage:>3.0f}%",
                        DownloadColumn(),
                        TransferSpeedColumn(),
                        TimeRemainingColumn(),
                        console=self.console,
                    ) as progress:

                        download_task = progress.add_task(
                            f"Downloading {task.destination.name}",
                            total=total_size,
                            completed=resume_pos,
                        )

                        for chunk in response.iter_content(chunk_size=task.chunk_size):
                            if chunk:
                                f.write(chunk)
                                progress.update(download_task, advance=len(chunk))
                                self.stats["bytes_downloaded"] += len(chunk)
                else:
                    # Download without progress
                    for chunk in response.iter_content(chunk_size=task.chunk_size):
                        if chunk:
                            f.write(chunk)
                            self.stats["bytes_downloaded"] += len(chunk)

            # Verify hash if provided
            if task.expected_hash:
                if not self._verify_hash(task.destination, task.expected_hash, task.hash_algorithm):
                    task.destination.unlink()
                    self.stats["downloads_failed"] += 1
                    return False

            # Cache the downloaded file
            self._cache_file(task.url, task.destination, response.headers)

            self.stats["downloads_successful"] += 1
            return True

        except Exception as e:
            self.console.print(f"[red]Download failed: {e}[/red]")
            if task.destination.exists():
                task.destination.unlink()
            self.stats["downloads_failed"] += 1
            return False

    def _verify_hash(self, file_path: Path, expected_hash: str, algorithm: str) -> bool:
        """Verify file hash"""
        try:
            hasher = hashlib.new(algorithm)

            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)

            calculated_hash = hasher.hexdigest()
            return calculated_hash.lower() == expected_hash.lower()

        except Exception:
            return False

    def _cache_file(self, url: str, file_path: Path, headers: Dict[str, str]):
        """Cache downloaded file"""
        try:
            # Create cache entry
            cache_file_path = self._get_cached_file_path(url)
            cache_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file to cache
            import shutil

            shutil.copy2(file_path, cache_file_path)

            # Create cache entry
            entry = CacheEntry(
                url=url,
                file_path=cache_file_path,
                content_type=headers.get("content-type", "application/octet-stream"),
                size=cache_file_path.stat().st_size,
                etag=headers.get("etag"),
            )

            # Parse last-modified header
            if "last-modified" in headers:
                try:
                    from email.utils import parsedate_to_datetime

                    entry.last_modified = parsedate_to_datetime(headers["last-modified"])
                except Exception:
                    pass

            # Set expiration based on cache-control
            cache_control = headers.get("cache-control", "")
            if "max-age=" in cache_control:
                try:
                    max_age = int(cache_control.split("max-age=")[1].split(",")[0])
                    entry.expires_at = datetime.now() + timedelta(seconds=max_age)
                except Exception:
                    pass

            self.cache_entries[url] = entry
            self.stats["bytes_cached"] += entry.size

            # Clean up cache if needed
            if len(self.cache_entries) % 10 == 0:  # Periodic cleanup
                self.cache_cleanup()

            self._save_cache_index()

        except Exception as e:
            self.console.print(f"[yellow]Failed to cache file: {e}[/yellow]")

    def download_multiple(self, tasks: List[DownloadTask], max_concurrent: int = 3) -> List[bool]:
        """Download multiple files concurrently"""

        if max_concurrent == 1:
            # Sequential download
            return [self.download_file(task) for task in tasks]

        # Concurrent download
        import concurrent.futures

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = [executor.submit(self.download_file, task) for task in tasks]

            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.console.print(f"[red]Download task failed: {e}[/red]")
                    results.append(False)

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get download statistics"""
        stats = self.stats.copy()
        stats["cache_size"] = sum(entry.size for entry in self.cache_entries.values())
        stats["cache_entries"] = len(self.cache_entries)
        stats["mirror_count"] = len(self.mirrors)
        stats["healthy_mirrors"] = len(
            [m for m in self.mirrors.values() if m.status == MirrorStatus.HEALTHY]
        )

        return stats

    def display_statistics(self):
        """Display download statistics"""
        from rich.table import Table

        stats = self.get_statistics()

        table = Table(title="Network & Download Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Downloads Attempted", str(stats["downloads_attempted"]))
        table.add_row("Downloads Successful", str(stats["downloads_successful"]))
        table.add_row("Downloads Failed", str(stats["downloads_failed"]))
        table.add_row("Cache Hits", str(stats["cache_hits"]))
        table.add_row("Cache Misses", str(stats["cache_misses"]))
        table.add_row("Bytes Downloaded", f"{stats['bytes_downloaded'] / 1024 / 1024:.1f} MB")
        table.add_row("Cache Size", f"{stats['cache_size'] / 1024 / 1024:.1f} MB")
        table.add_row("Cache Entries", str(stats["cache_entries"]))
        table.add_row("Network Errors", str(stats["network_errors"]))
        table.add_row("Retry Attempts", str(stats["retry_attempts"]))

        self.console.print(table)

    def cleanup(self):
        """Cleanup resources"""
        self._save_cache_index()
        self.session.close()


def create_network_downloader(
    cache_dir: Optional[Path] = None,
    offline_mode: bool = False,
    console: Optional[Console] = None,
) -> NetworkResilientDownloader:
    """Factory function to create network resilient downloader"""
    return NetworkResilientDownloader(
        cache_dir=cache_dir, offline_mode=offline_mode, console=console
    )


if __name__ == "__main__":
    # Test the network resilience system
    console = Console()
    downloader = create_network_downloader(console=console)

    # Test download
    task = DownloadTask(
        url="https://httpbin.org/json",
        destination=Path("test_download.json"),
        max_retries=3,
    )

    success = downloader.download_file(task)
    console.print(f"Download {'successful' if success else 'failed'}")

    # Display statistics
    downloader.display_statistics()

    # Cleanup
    downloader.cleanup()
