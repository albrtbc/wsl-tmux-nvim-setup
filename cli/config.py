#!/usr/bin/env python3
"""
WSL-Tmux-Nvim-Setup CLI Configuration Management

Handles user configuration, settings persistence, and default values.
"""

import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

try:
    from pydantic import BaseModel, Field, validator
except ImportError:
    print("Error: pydantic not found. Install with: pip install pydantic>=1.10.0", file=sys.stderr)
    sys.exit(1)


class UserConfig(BaseModel):
    """User configuration schema with validation"""

    # Update settings
    auto_update: bool = Field(False, description="Enable automatic updates")
    update_frequency: str = Field("weekly", description="Update check frequency")
    backup_retention: int = Field(5, description="Number of backups to keep")

    # Installation settings
    installation_path: str = Field("~/.config/wsl-setup", description="Installation directory")
    preferred_components: List[str] = Field(
        default_factory=list, description="Preferred components to install"
    )

    # API and network settings
    github_token: Optional[str] = Field(None, description="GitHub token for higher API limits")
    network_timeout: int = Field(30, description="Network timeout in seconds")
    max_retries: int = Field(3, description="Maximum retry attempts")

    # UI preferences
    show_progress: bool = Field(True, description="Show progress bars")
    verbose: bool = Field(False, description="Enable verbose output")
    color_output: bool = Field(True, description="Enable colored output")

    # Advanced settings
    verify_checksums: bool = Field(True, description="Verify downloaded file checksums")
    parallel_downloads: bool = Field(True, description="Enable parallel downloads")
    max_concurrent_downloads: int = Field(4, description="Maximum concurrent downloads")

    @validator("update_frequency")
    def validate_update_frequency(cls, v):
        valid_frequencies = ["daily", "weekly", "monthly", "never"]
        if v not in valid_frequencies:
            raise ValueError(f"update_frequency must be one of: {valid_frequencies}")
        return v

    @validator("backup_retention")
    def validate_backup_retention(cls, v):
        if v < 0:
            raise ValueError("backup_retention must be non-negative")
        return v

    @validator("installation_path")
    def validate_installation_path(cls, v):
        # Expand user path
        expanded_path = os.path.expanduser(v)
        return expanded_path

    @validator("network_timeout")
    def validate_network_timeout(cls, v):
        if v <= 0:
            raise ValueError("network_timeout must be positive")
        return v


@dataclass
class InstallationStatus:
    """Track installation status and metadata"""

    version: str = "unknown"
    installed_components: List[str] = None
    installation_date: Optional[str] = None
    last_update_check: Optional[str] = None
    last_update: Optional[str] = None

    def __post_init__(self):
        if self.installed_components is None:
            self.installed_components = []

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InstallationStatus":
        return cls(**data)


class ConfigManager:
    """Manages configuration files and user settings"""

    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir or os.path.expanduser("~/.config/wsl-setup"))
        self.config_file = self.config_dir / "config.yml"
        self.status_file = self.config_dir / "status.json"

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Initialize configuration
        self._config = self._load_config()
        self._status = self._load_status()

    def _load_config(self) -> UserConfig:
        """Load user configuration from file"""
        if not self.config_file.exists():
            # Create default config
            config = UserConfig()
            self._save_config(config)
            return config

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data is None:
                data = {}

            return UserConfig(**data)

        except (yaml.YAMLError, FileNotFoundError, TypeError) as e:
            print(f"Warning: Error loading config file: {e}")
            print("Using default configuration.")
            return UserConfig()
        except Exception as e:
            print(f"Warning: Unexpected error loading config: {e}")
            return UserConfig()

    def _save_config(self, config: UserConfig) -> None:
        """Save user configuration to file"""
        try:
            config_dict = config.dict()

            with open(self.config_file, "w", encoding="utf-8") as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)

        except Exception as e:
            raise RuntimeError(f"Failed to save configuration: {e}")

    def _load_status(self) -> InstallationStatus:
        """Load installation status from file"""
        if not self.status_file.exists():
            return InstallationStatus()

        try:
            with open(self.status_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            return InstallationStatus.from_dict(data)

        except (json.JSONDecodeError, FileNotFoundError, TypeError) as e:
            print(f"Warning: Error loading status file: {e}")
            return InstallationStatus()
        except Exception as e:
            print(f"Warning: Unexpected error loading status: {e}")
            return InstallationStatus()

    def _save_status(self, status: InstallationStatus) -> None:
        """Save installation status to file"""
        try:
            with open(self.status_file, "w", encoding="utf-8") as f:
                json.dump(status.to_dict(), f, indent=2, ensure_ascii=False)
                f.write("\n")

        except Exception as e:
            raise RuntimeError(f"Failed to save status: {e}")

    @property
    def config(self) -> UserConfig:
        """Get current configuration"""
        return self._config

    @property
    def status(self) -> InstallationStatus:
        """Get current installation status"""
        return self._status

    def update_config(self, **kwargs) -> None:
        """Update configuration with new values"""
        config_dict = self._config.dict()
        config_dict.update(kwargs)

        try:
            new_config = UserConfig(**config_dict)
            self._config = new_config
            self._save_config(new_config)

        except Exception as e:
            raise ValueError(f"Invalid configuration update: {e}")

    def update_status(self, **kwargs) -> None:
        """Update installation status"""
        status_dict = self._status.to_dict()
        status_dict.update(kwargs)

        # Update timestamp for certain operations
        if any(key in kwargs for key in ["version", "installed_components"]):
            status_dict["last_update"] = datetime.now().isoformat()

        self._status = InstallationStatus.from_dict(status_dict)
        self._save_status(self._status)

    def get_expanded_installation_path(self) -> Path:
        """Get expanded installation path"""
        return Path(os.path.expanduser(self._config.installation_path))

    def reset_config(self) -> None:
        """Reset configuration to defaults"""
        self._config = UserConfig()
        self._save_config(self._config)

    def reset_status(self) -> None:
        """Reset installation status"""
        self._status = InstallationStatus()
        self._save_status(self._status)

    def export_config(self, output_file: Path) -> None:
        """Export configuration to file"""
        config_data = {
            "config": self._config.dict(),
            "status": self._status.to_dict(),
            "export_date": datetime.now().isoformat(),
        }

        with open(output_file, "w", encoding="utf-8") as f:
            if output_file.suffix.lower() == ".json":
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            else:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)

    def import_config(self, input_file: Path) -> None:
        """Import configuration from file"""
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                if input_file.suffix.lower() == ".json":
                    data = json.load(f)
                else:
                    data = yaml.safe_load(f)

            if "config" in data:
                self._config = UserConfig(**data["config"])
                self._save_config(self._config)

            if "status" in data:
                self._status = InstallationStatus.from_dict(data["status"])
                self._save_status(self._status)

        except Exception as e:
            raise RuntimeError(f"Failed to import configuration: {e}")

    def get_backup_directory(self) -> Path:
        """Get backup directory path"""
        backup_dir = self.get_expanded_installation_path() / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir

    def should_check_for_updates(self) -> bool:
        """Determine if it's time to check for updates"""
        if not self._config.auto_update:
            return False

        if self._config.update_frequency == "never":
            return False

        last_check = self._status.last_update_check
        if not last_check:
            return True

        try:
            from datetime import datetime

            last_check_date = datetime.fromisoformat(last_check.replace("Z", "+00:00"))
            now = datetime.now()

            if self._config.update_frequency == "daily":
                return (now - last_check_date).days >= 1
            elif self._config.update_frequency == "weekly":
                return (now - last_check_date).days >= 7
            elif self._config.update_frequency == "monthly":
                return (now - last_check_date).days >= 30

        except (ValueError, TypeError):
            return True

        return False

    def mark_update_check(self) -> None:
        """Mark that an update check was performed"""
        self.update_status(last_update_check=datetime.now().isoformat())


def get_default_config_manager() -> ConfigManager:
    """Get default configuration manager instance"""
    return ConfigManager()


if __name__ == "__main__":
    # CLI for configuration management
    import argparse

    parser = argparse.ArgumentParser(description="WSL-Tmux-Nvim-Setup Configuration Manager")
    parser.add_argument("--show", action="store_true", help="Show current configuration")
    parser.add_argument("--reset", action="store_true", help="Reset configuration to defaults")
    parser.add_argument("--export", type=str, help="Export configuration to file")
    parser.add_argument(
        "--import", type=str, dest="import_file", help="Import configuration from file"
    )

    args = parser.parse_args()

    try:
        config_manager = get_default_config_manager()

        if args.show:
            print("Current Configuration:")
            print("=" * 40)
            config_dict = config_manager.config.dict()
            for key, value in config_dict.items():
                print(f"{key}: {value}")

            print("\nInstallation Status:")
            print("=" * 40)
            status_dict = config_manager.status.to_dict()
            for key, value in status_dict.items():
                print(f"{key}: {value}")

        elif args.reset:
            config_manager.reset_config()
            config_manager.reset_status()
            print("Configuration reset to defaults.")

        elif args.export:
            config_manager.export_config(Path(args.export))
            print(f"Configuration exported to: {args.export}")

        elif args.import_file:
            config_manager.import_config(Path(args.import_file))
            print(f"Configuration imported from: {args.import_file}")

        else:
            parser.print_help()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
