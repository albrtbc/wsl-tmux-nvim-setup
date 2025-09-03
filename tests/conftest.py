"""
Pytest configuration and shared fixtures for WSL-Tmux-Nvim-Setup tests.
"""

import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import MagicMock, Mock, patch

import click.testing
import pytest
from rich.console import Console

# Add CLI to path for testing
CLI_DIR = Path(__file__).parent.parent / "cli"

if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Return path to test data directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test isolation."""
    with tempfile.TemporaryDirectory() as temp_path:
        yield Path(temp_path)


@pytest.fixture
def temp_config_dir(temp_dir: Path) -> Path:
    """Create a temporary config directory with default structure."""
    config_dir = temp_dir / "config"
    config_dir.mkdir(parents=True)

    # Create default config structure
    (config_dir / "backups").mkdir()
    (config_dir / "cache").mkdir()
    (config_dir / "logs").mkdir()

    return config_dir


@pytest.fixture
def mock_config_manager():
    """Mock ConfigManager for isolated testing."""
    from config import ConfigManager

    with patch("config.ConfigManager") as mock_manager_class:
        mock_manager = Mock(spec=ConfigManager)
        mock_manager_class.return_value = mock_manager

        # Default configuration
        mock_manager.config = Mock()
        mock_manager.config.installation_path = "/tmp/wsl-setup"
        mock_manager.config.auto_update = True
        mock_manager.config.backup_retention = 5
        mock_manager.config.github_token = None
        mock_manager.config.preferred_components = []
        mock_manager.config.verbose = False

        # Default status
        mock_manager.status = Mock()
        mock_manager.status.version = "1.0.0"
        mock_manager.status.installed_components = ["tmux", "neovim"]
        mock_manager.status.installation_date = "2025-09-01"
        mock_manager.status.last_update_check = None

        # Mock methods
        mock_manager.update_config = Mock()
        mock_manager.should_check_for_updates = Mock(return_value=False)
        mock_manager.save_config = Mock()
        mock_manager.load_config = Mock()

        yield mock_manager


@pytest.fixture
def mock_version_manager():
    """Mock ComponentVersionManager for testing."""
    with patch("cli.utils.version_utils.ComponentVersionManager") as mock_class:
        mock_manager = Mock()
        mock_class.return_value = mock_manager

        # Default version info
        mock_manager.version_manager = Mock()
        mock_manager.version_manager.get_current_version = Mock(return_value="1.0.0")
        mock_manager.version_manager.get_latest_release = Mock(
            return_value={
                "tag_name": "v1.1.0",
                "name": "Release v1.1.0",
                "published_at": "2025-09-01T00:00:00Z",
                "assets": [],
            }
        )

        # Component versions
        mock_manager.get_component_versions = Mock(
            return_value={"tmux": "3.3a", "neovim": "0.9.0", "git": "2.40.0"}
        )

        # System compatibility
        mock_manager.check_system_compatibility = Mock(
            return_value={
                "wsl_available": True,
                "python_version_ok": True,
                "dependencies_installed": True,
                "disk_space_sufficient": True,
            }
        )

        mock_manager.get_compatibility_info = Mock(
            return_value={
                "supported_platforms": ["linux", "wsl1", "wsl2"],
                "python_versions": ["3.7+"],
                "required_tools": ["git", "curl", "wget"],
            }
        )

        yield mock_manager


@pytest.fixture
def cli_runner():
    """Click test runner for CLI testing."""
    return click.testing.CliRunner()


@pytest.fixture
def mock_console():
    """Mock Rich Console for output testing."""
    with patch("rich.console.Console") as mock_console_class:
        mock_console = Mock(spec=Console)
        mock_console_class.return_value = mock_console

        # Mock console methods
        mock_console.print = Mock()
        mock_console.input = Mock(return_value="y")

        yield mock_console


@pytest.fixture
def mock_network():
    """Mock network operations for testing."""
    with patch("requests.get") as mock_get, patch("requests.Session") as mock_session_class:

        # Default successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"tag_name": "v1.1.0"}
        mock_response.content = b"test content"
        mock_response.headers = {"content-length": "12"}
        mock_response.raise_for_status = Mock()

        mock_get.return_value = mock_response

        # Mock session
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        yield {"get": mock_get, "session": mock_session, "response": mock_response}


@pytest.fixture
def mock_filesystem():
    """Mock filesystem operations for testing."""
    with patch("pathlib.Path.exists") as mock_exists, patch(
        "pathlib.Path.mkdir"
    ) as mock_mkdir, patch("pathlib.Path.unlink") as mock_unlink, patch(
        "shutil.copy2"
    ) as mock_copy, patch(
        "shutil.move"
    ) as mock_move, patch(
        "shutil.rmtree"
    ) as mock_rmtree:

        # Default filesystem state
        mock_exists.return_value = True
        mock_mkdir.return_value = None
        mock_unlink.return_value = None
        mock_copy.return_value = None
        mock_move.return_value = None
        mock_rmtree.return_value = None

        yield {
            "exists": mock_exists,
            "mkdir": mock_mkdir,
            "unlink": mock_unlink,
            "copy": mock_copy,
            "move": mock_move,
            "rmtree": mock_rmtree,
        }


@pytest.fixture
def sample_release_data():
    """Sample GitHub release data for testing."""
    return {
        "tag_name": "v1.1.0",
        "name": "WSL-Tmux-Nvim-Setup v1.1.0",
        "body": "Release notes for v1.1.0",
        "published_at": "2025-09-01T00:00:00Z",
        "prerelease": False,
        "draft": False,
        "assets": [
            {
                "name": "wsl-setup-v1.1.0.tar.gz",
                "browser_download_url": "https://example.com/releases/download/v1.1.0/wsl-setup-v1.1.0.tar.gz",
                "size": 1024000,
                "content_type": "application/gzip",
            }
        ],
    }


@pytest.fixture
def sample_config_data():
    """Sample configuration data for testing."""
    return {
        "installation_path": "/tmp/wsl-setup-test",
        "auto_update": True,
        "backup_retention": 3,
        "github_token": None,
        "preferred_components": ["tmux", "neovim", "git"],
        "verbose": False,
        "download_timeout": 300,
        "max_retries": 3,
        "parallel_downloads": True,
        "use_mirrors": True,
    }


@pytest.fixture
def sample_status_data():
    """Sample status data for testing."""
    return {
        "version": "1.0.0",
        "installed_components": ["tmux", "neovim", "git"],
        "installation_date": "2025-09-01T12:00:00Z",
        "last_update_check": "2025-09-02T12:00:00Z",
        "installation_path": "/tmp/wsl-setup-test",
        "backup_count": 2,
    }


@pytest.fixture
def performance_metrics():
    """Sample performance metrics for testing."""
    return {
        "installation_time": 180.5,  # seconds
        "download_speed": 5.2,  # MB/s
        "memory_peak": 85.3,  # MB
        "cpu_peak": 45.2,  # %
        "disk_usage": 256.8,  # MB
        "command_response_times": {
            "install": 1.2,
            "update": 0.8,
            "status": 0.3,
            "list": 0.5,
            "config": 0.4,
        },
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")
    config.addinivalue_line("markers", "performance: marks tests as performance tests")
    config.addinivalue_line("markers", "security: marks tests as security tests")


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Add markers based on test file location
        if "unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e/" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        elif "performance/" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
        elif "security/" in str(item.fspath):
            item.add_marker(pytest.mark.security)


# Test utilities
class TestHelper:
    """Helper utilities for testing."""

    @staticmethod
    def create_mock_release(version: str = "1.1.0", prerelease: bool = False) -> Dict[str, Any]:
        """Create a mock GitHub release object."""
        return {
            "tag_name": f"v{version}",
            "name": f"WSL-Tmux-Nvim-Setup v{version}",
            "body": f"Release notes for v{version}",
            "published_at": "2025-09-01T00:00:00Z",
            "prerelease": prerelease,
            "draft": False,
            "assets": [
                {
                    "name": f"wsl-setup-v{version}.tar.gz",
                    "browser_download_url": f"https://example.com/releases/download/v{version}/wsl-setup-v{version}.tar.gz",
                    "size": 1024000,
                    "content_type": "application/gzip",
                }
            ],
        }

    @staticmethod
    def create_test_file(path: Path, content: str = "test content") -> None:
        """Create a test file with specified content."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    @staticmethod
    def assert_file_contains(path: Path, expected_content: str) -> None:
        """Assert that a file contains expected content."""
        assert path.exists(), f"File {path} does not exist"
        content = path.read_text()
        assert expected_content in content, f"Expected content not found in {path}"


@pytest.fixture
def test_helper():
    """Test helper utilities."""
    return TestHelper


# Environment setup for different test scenarios
@pytest.fixture
def wsl1_environment():
    """Mock WSL1 environment for testing."""
    with patch("platform.system", return_value="Linux"), patch(
        "builtins.open",
        side_effect=lambda path, *args, **kwargs: (
            MagicMock(read=lambda: "microsoft-standard-WSL1")
            if path == "/proc/version"
            else MagicMock()
        ),
    ):
        yield


@pytest.fixture
def wsl2_environment():
    """Mock WSL2 environment for testing."""
    with patch("platform.system", return_value="Linux"), patch(
        "builtins.open",
        side_effect=lambda path, *args, **kwargs: (
            MagicMock(read=lambda: "microsoft-standard-WSL2")
            if path == "/proc/version"
            else MagicMock()
        ),
    ):
        yield


@pytest.fixture
def native_linux_environment():
    """Mock native Linux environment for testing."""
    with patch("platform.system", return_value="Linux"), patch(
        "builtins.open",
        side_effect=lambda path, *args, **kwargs: (
            MagicMock(read=lambda: "generic-linux-kernel")
            if path == "/proc/version"
            else MagicMock()
        ),
    ):
        yield
