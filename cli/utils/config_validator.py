#!/usr/bin/env python3
"""
Configuration Validation and Enhancement System

Provides comprehensive configuration validation, migration, and optimization.
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
import socket
import subprocess

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Confirm, Prompt
    from rich.text import Text
    import requests
    from pydantic import BaseModel, Field, validator, ValidationError
except ImportError as e:
    print(f"Error: Required packages not found: {e}", file=sys.stderr)
    sys.exit(1)


class ValidationLevel(Enum):
    """Validation strictness levels"""
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"
    PARANOID = "paranoid"


class ConfigIssueType(Enum):
    """Types of configuration issues"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUGGESTION = "suggestion"


@dataclass
class ConfigIssue:
    """Configuration validation issue"""
    type: ConfigIssueType
    field: str
    message: str
    current_value: Any = None
    suggested_value: Any = None
    auto_fixable: bool = False
    
    def __str__(self) -> str:
        prefix = {
            ConfigIssueType.ERROR: "❌",
            ConfigIssueType.WARNING: "⚠️",
            ConfigIssueType.INFO: "ℹ️",
            ConfigIssueType.SUGGESTION: "💡"
        }[self.type]
        
        return f"{prefix} {self.field}: {self.message}"


class EnhancedConfigModel(BaseModel):
    """Enhanced configuration model with validation"""
    
    # Installation settings
    installation_path: str = Field(default="~/.local/share/wsl-tmux-nvim-setup")
    backup_retention: int = Field(default=5, ge=0, le=50)
    auto_update: bool = Field(default=False)
    check_updates_interval: int = Field(default=24, ge=1, le=168)  # 1-168 hours
    
    # Network settings
    github_token: Optional[str] = Field(default=None)
    network_timeout: int = Field(default=30, ge=5, le=300)
    max_retries: int = Field(default=3, ge=1, le=10)
    parallel_downloads: bool = Field(default=True)
    max_concurrent_downloads: int = Field(default=3, ge=1, le=10)
    verify_checksums: bool = Field(default=True)
    offline_mode: bool = Field(default=False)
    
    # UI settings
    show_progress: bool = Field(default=True)
    verbose: bool = Field(default=False)
    color_output: bool = Field(default=True)
    interactive_mode: bool = Field(default=True)
    ui_mode: str = Field(default="auto", regex="^(auto|rich|curses|textual)$")
    
    # Performance settings
    cache_enabled: bool = Field(default=True)
    cache_size_mb: int = Field(default=256, ge=10, le=2048)
    performance_profile: str = Field(default="auto", regex="^(auto|low_resource|standard|high_performance)$")
    max_workers: int = Field(default=0, ge=0, le=32)  # 0 = auto-detect
    
    # Component preferences
    preferred_components: List[str] = Field(default_factory=lambda: [
        "dependencies", "tmux", "neovim", "yazi", "lazygit"
    ])
    excluded_components: List[str] = Field(default_factory=list)
    
    # Shell integration
    shell_integration: bool = Field(default=True)
    modify_shell_config: bool = Field(default=True)
    backup_shell_config: bool = Field(default=True)
    
    # Advanced settings
    debug_mode: bool = Field(default=False)
    log_level: str = Field(default="INFO", regex="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    log_file_retention: int = Field(default=7, ge=1, le=365)
    enable_telemetry: bool = Field(default=False)
    
    @validator('installation_path')
    def validate_installation_path(cls, v):
        """Validate installation path"""
        if not v or not isinstance(v, str):
            raise ValueError("Installation path must be a non-empty string")
        
        # Expand path
        expanded = Path(v).expanduser().resolve()
        
        # Check if parent directory is writable
        parent = expanded.parent
        if parent.exists() and not os.access(parent, os.W_OK):
            raise ValueError(f"Parent directory is not writable: {parent}")
        
        return str(expanded)
    
    @validator('github_token')
    def validate_github_token(cls, v):
        """Validate GitHub token format"""
        if v is None:
            return None
        
        if not isinstance(v, str):
            raise ValueError("GitHub token must be a string")
        
        # Basic token format validation
        if not (v.startswith('ghp_') or v.startswith('github_pat_')):
            raise ValueError("GitHub token should start with 'ghp_' or 'github_pat_'")
        
        if len(v) < 20:
            raise ValueError("GitHub token seems too short")
        
        return v
    
    @validator('preferred_components', 'excluded_components')
    def validate_component_lists(cls, v):
        """Validate component lists"""
        if not isinstance(v, list):
            raise ValueError("Component lists must be arrays")
        
        valid_components = {
            'dependencies', 'tmux', 'neovim', 'yazi', 'lazygit', 
            'nerdfonts', 'synth-shell', 'kitty', 'git'
        }
        
        for component in v:
            if component.lower() not in valid_components:
                raise ValueError(f"Unknown component: {component}")
        
        return [c.lower() for c in v]


class ConfigValidator:
    """Comprehensive configuration validator"""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD,
                 console: Optional[Console] = None):
        self.validation_level = validation_level
        self.console = console or Console()
        self.issues: List[ConfigIssue] = []
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[ConfigIssue]]:
        """Validate configuration comprehensively"""
        self.issues.clear()
        
        # Basic structure validation
        self._validate_structure(config)
        
        # Pydantic model validation
        self._validate_with_pydantic(config)
        
        # System compatibility validation
        self._validate_system_compatibility(config)
        
        # Network connectivity validation
        self._validate_network_settings(config)
        
        # Performance optimization validation
        self._validate_performance_settings(config)
        
        # Security validation
        self._validate_security_settings(config)
        
        # Component compatibility validation
        self._validate_component_compatibility(config)
        
        # Calculate validation result
        has_errors = any(issue.type == ConfigIssueType.ERROR for issue in self.issues)
        return not has_errors, self.issues.copy()
    
    def _validate_structure(self, config: Dict[str, Any]):
        """Validate basic configuration structure"""
        required_sections = ['installation_path']
        
        for section in required_sections:
            if section not in config:
                self.issues.append(ConfigIssue(
                    type=ConfigIssueType.ERROR,
                    field=section,
                    message=f"Required configuration field missing",
                    suggested_value="~/.local/share/wsl-tmux-nvim-setup" if section == "installation_path" else None,
                    auto_fixable=True
                ))
    
    def _validate_with_pydantic(self, config: Dict[str, Any]):
        """Validate using Pydantic model"""
        try:
            EnhancedConfigModel(**config)
        except ValidationError as e:
            for error in e.errors():
                field_path = '.'.join(str(x) for x in error['loc'])
                self.issues.append(ConfigIssue(
                    type=ConfigIssueType.ERROR,
                    field=field_path,
                    message=error['msg'],
                    current_value=error.get('input'),
                    auto_fixable=False
                ))
    
    def _validate_system_compatibility(self, config: Dict[str, Any]):
        """Validate system compatibility"""
        
        # Check installation path accessibility
        install_path = config.get('installation_path', '')
        if install_path:
            try:
                expanded_path = Path(install_path).expanduser()
                parent = expanded_path.parent
                
                if not parent.exists():
                    self.issues.append(ConfigIssue(
                        type=ConfigIssueType.WARNING,
                        field="installation_path",
                        message=f"Installation directory parent does not exist: {parent}",
                        auto_fixable=True
                    ))
                elif not os.access(parent, os.W_OK):
                    self.issues.append(ConfigIssue(
                        type=ConfigIssueType.ERROR,
                        field="installation_path", 
                        message=f"No write permission to installation directory: {parent}"
                    ))
                
                # Check available disk space
                if parent.exists():
                    import shutil
                    total, used, free = shutil.disk_usage(parent)
                    free_gb = free / (1024**3)
                    
                    if free_gb < 1.0:
                        self.issues.append(ConfigIssue(
                            type=ConfigIssueType.ERROR,
                            field="installation_path",
                            message=f"Insufficient disk space: {free_gb:.1f}GB available"
                        ))
                    elif free_gb < 2.0:
                        self.issues.append(ConfigIssue(
                            type=ConfigIssueType.WARNING,
                            field="installation_path",
                            message=f"Low disk space: {free_gb:.1f}GB available"
                        ))
                        
            except Exception as e:
                self.issues.append(ConfigIssue(
                    type=ConfigIssueType.WARNING,
                    field="installation_path",
                    message=f"Cannot validate installation path: {e}"
                ))
        
        # Check WSL environment
        try:
            with open('/proc/version', 'r') as f:
                version_info = f.read()
                if 'microsoft' not in version_info.lower() and 'wsl' not in version_info.lower():
                    self.issues.append(ConfigIssue(
                        type=ConfigIssueType.INFO,
                        field="system",
                        message="Not running in WSL environment - some features may not be available"
                    ))
        except:
            pass
        
        # Check required system commands
        required_commands = ['curl', 'wget', 'tar', 'unzip']
        missing_commands = []
        
        for cmd in required_commands:
            try:
                result = subprocess.run(['which', cmd], capture_output=True, timeout=5)
                if result.returncode != 0:
                    missing_commands.append(cmd)
            except:
                missing_commands.append(cmd)
        
        if missing_commands:
            self.issues.append(ConfigIssue(
                type=ConfigIssueType.WARNING,
                field="system",
                message=f"Missing system commands: {', '.join(missing_commands)}",
                suggested_value="Install missing commands with package manager"
            ))
    
    def _validate_network_settings(self, config: Dict[str, Any]):
        """Validate network configuration"""
        
        # Test GitHub connectivity
        github_token = config.get('github_token')
        if github_token and self.validation_level in [ValidationLevel.STRICT, ValidationLevel.PARANOID]:
            if self._test_github_token(github_token):
                self.issues.append(ConfigIssue(
                    type=ConfigIssueType.INFO,
                    field="github_token",
                    message="GitHub token validated successfully"
                ))
            else:
                self.issues.append(ConfigIssue(
                    type=ConfigIssueType.WARNING,
                    field="github_token",
                    message="GitHub token validation failed - check token validity"
                ))
        
        # Test general network connectivity
        if not config.get('offline_mode', False):
            if not self._test_network_connectivity():
                self.issues.append(ConfigIssue(
                    type=ConfigIssueType.WARNING,
                    field="network",
                    message="No internet connectivity detected",
                    suggested_value="Enable offline mode or check network connection"
                ))
        
        # Validate timeout settings
        timeout = config.get('network_timeout', 30)
        if timeout < 10:
            self.issues.append(ConfigIssue(
                type=ConfigIssueType.SUGGESTION,
                field="network_timeout",
                message="Network timeout is quite low, may cause failures on slow connections",
                current_value=timeout,
                suggested_value=30
            ))
        elif timeout > 120:
            self.issues.append(ConfigIssue(
                type=ConfigIssueType.SUGGESTION,
                field="network_timeout",
                message="Network timeout is very high, may slow down error detection",
                current_value=timeout,
                suggested_value=60
            ))
    
    def _validate_performance_settings(self, config: Dict[str, Any]):
        """Validate performance configuration"""
        
        # Check system resources for performance settings
        try:
            import psutil
            
            # Memory validation
            memory = psutil.virtual_memory()
            cache_size_mb = config.get('cache_size_mb', 256)
            
            if cache_size_mb > memory.available / (1024*1024) * 0.5:
                self.issues.append(ConfigIssue(
                    type=ConfigIssueType.WARNING,
                    field="cache_size_mb",
                    message=f"Cache size ({cache_size_mb}MB) is large relative to available memory ({memory.available // (1024*1024)}MB)",
                    suggested_value=min(256, memory.available // (1024*1024) // 4)
                ))
            
            # CPU validation
            cpu_count = psutil.cpu_count()
            max_workers = config.get('max_workers', 0)
            max_concurrent = config.get('max_concurrent_downloads', 3)
            
            if max_workers > cpu_count * 2:
                self.issues.append(ConfigIssue(
                    type=ConfigIssueType.SUGGESTION,
                    field="max_workers",
                    message=f"Worker count ({max_workers}) exceeds recommended limit for {cpu_count} CPU cores",
                    suggested_value=cpu_count
                ))
            
            if max_concurrent > cpu_count:
                self.issues.append(ConfigIssue(
                    type=ConfigIssueType.SUGGESTION,
                    field="max_concurrent_downloads",
                    message=f"Concurrent downloads ({max_concurrent}) may overwhelm system with {cpu_count} CPU cores",
                    suggested_value=min(cpu_count, 6)
                ))
                
        except ImportError:
            self.issues.append(ConfigIssue(
                type=ConfigIssueType.INFO,
                field="performance",
                message="Cannot validate performance settings - psutil not available"
            ))
    
    def _validate_security_settings(self, config: Dict[str, Any]):
        """Validate security configuration"""
        
        # Check if GitHub token is exposed
        github_token = config.get('github_token')
        if github_token and self.validation_level in [ValidationLevel.STRICT, ValidationLevel.PARANOID]:
            # Check if token appears in environment variables (potential exposure)
            for key, value in os.environ.items():
                if github_token in str(value):
                    self.issues.append(ConfigIssue(
                        type=ConfigIssueType.WARNING,
                        field="github_token",
                        message=f"GitHub token found in environment variable {key} - potential security risk"
                    ))
                    break
        
        # Validate backup settings for security
        if not config.get('backup_enabled', True):
            self.issues.append(ConfigIssue(
                type=ConfigIssueType.SUGGESTION,
                field="backup_retention",
                message="Backups are disabled - consider enabling for safety",
                suggested_value=5
            ))
        
        # Check telemetry setting
        if config.get('enable_telemetry', False):
            self.issues.append(ConfigIssue(
                type=ConfigIssueType.INFO,
                field="enable_telemetry",
                message="Telemetry is enabled - data will be collected for improvement"
            ))
    
    def _validate_component_compatibility(self, config: Dict[str, Any]):
        """Validate component compatibility"""
        
        preferred = set(config.get('preferred_components', []))
        excluded = set(config.get('excluded_components', []))
        
        # Check for conflicts
        conflicts = preferred & excluded
        if conflicts:
            self.issues.append(ConfigIssue(
                type=ConfigIssueType.ERROR,
                field="components",
                message=f"Components cannot be both preferred and excluded: {', '.join(conflicts)}",
                auto_fixable=True
            ))
        
        # Check dependencies
        if 'dependencies' in excluded:
            self.issues.append(ConfigIssue(
                type=ConfigIssueType.ERROR,
                field="excluded_components",
                message="Dependencies component cannot be excluded - it's required for other components"
            ))
        
        # Check for essential components
        essential_components = {'tmux', 'neovim'}
        excluded_essential = essential_components & excluded
        if excluded_essential:
            self.issues.append(ConfigIssue(
                type=ConfigIssueType.WARNING,
                field="excluded_components",
                message=f"Excluding essential components may limit functionality: {', '.join(excluded_essential)}"
            ))
    
    def _test_github_token(self, token: str) -> bool:
        """Test GitHub token validity"""
        try:
            headers = {'Authorization': f'token {token}'}
            response = requests.get('https://api.github.com/user', headers=headers, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def _test_network_connectivity(self) -> bool:
        """Test basic network connectivity"""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            return True
        except:
            return False
    
    def generate_fixes(self) -> Dict[str, Any]:
        """Generate automatic fixes for issues"""
        fixes = {}
        
        for issue in self.issues:
            if issue.auto_fixable and issue.suggested_value is not None:
                fixes[issue.field] = issue.suggested_value
        
        return fixes
    
    def display_issues(self):
        """Display validation issues in a formatted way"""
        if not self.issues:
            self.console.print("[green]✅ Configuration validation passed![/green]")
            return
        
        # Group issues by type
        errors = [i for i in self.issues if i.type == ConfigIssueType.ERROR]
        warnings = [i for i in self.issues if i.type == ConfigIssueType.WARNING]
        info = [i for i in self.issues if i.type == ConfigIssueType.INFO]
        suggestions = [i for i in self.issues if i.type == ConfigIssueType.SUGGESTION]
        
        # Create summary table
        summary_table = Table(title="Configuration Validation Summary")
        summary_table.add_column("Type", style="bold")
        summary_table.add_column("Count", style="cyan")
        
        if errors:
            summary_table.add_row("Errors", str(len(errors)), style="red")
        if warnings:
            summary_table.add_row("Warnings", str(len(warnings)), style="yellow")
        if info:
            summary_table.add_row("Info", str(len(info)), style="blue")
        if suggestions:
            summary_table.add_row("Suggestions", str(len(suggestions)), style="green")
        
        self.console.print(summary_table)
        
        # Display detailed issues
        for issue_type, issues_list, style in [
            ("Errors", errors, "red"),
            ("Warnings", warnings, "yellow"),
            ("Information", info, "blue"),
            ("Suggestions", suggestions, "green")
        ]:
            if issues_list:
                self.console.print(f"\n[bold {style}]{issue_type}:[/bold {style}]")
                for issue in issues_list:
                    self.console.print(f"  {issue}")
                    if issue.suggested_value is not None:
                        self.console.print(f"    💡 Suggested: {issue.suggested_value}")


class ConfigMigrator:
    """Configuration migration and upgrade system"""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.migration_history = []
    
    def migrate_config(self, old_config: Dict[str, Any], target_version: str = "latest") -> Dict[str, Any]:
        """Migrate configuration to newer format"""
        
        # Detect current version
        current_version = old_config.get('config_version', '1.0')
        
        self.console.print(f"[blue]Migrating configuration from version {current_version} to {target_version}[/blue]")
        
        migrated_config = old_config.copy()
        
        # Apply version-specific migrations
        if current_version == '1.0':
            migrated_config = self._migrate_v1_to_v2(migrated_config)
            current_version = '2.0'
        
        if current_version == '2.0':
            migrated_config = self._migrate_v2_to_v3(migrated_config)
            current_version = '3.0'
        
        # Set final version
        migrated_config['config_version'] = target_version
        
        self.console.print("[green]✅ Configuration migration completed[/green]")
        return migrated_config
    
    def _migrate_v1_to_v2(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from v1.0 to v2.0"""
        self.migration_history.append("v1.0 -> v2.0: Added performance settings")
        
        # Add new performance settings
        if 'performance' not in config:
            config['cache_enabled'] = True
            config['cache_size_mb'] = 256
            config['performance_profile'] = 'auto'
        
        # Rename old settings
        if 'timeout' in config:
            config['network_timeout'] = config.pop('timeout')
        
        return config
    
    def _migrate_v2_to_v3(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from v2.0 to v3.0"""
        self.migration_history.append("v2.0 -> v3.0: Added component preferences")
        
        # Add component preference settings
        if 'preferred_components' not in config:
            config['preferred_components'] = ['dependencies', 'tmux', 'neovim', 'yazi', 'lazygit']
        
        if 'excluded_components' not in config:
            config['excluded_components'] = []
        
        return config


def create_config_validator(validation_level: ValidationLevel = ValidationLevel.STANDARD,
                          console: Optional[Console] = None) -> ConfigValidator:
    """Factory function to create configuration validator"""
    return ConfigValidator(validation_level, console)


def create_config_migrator(console: Optional[Console] = None) -> ConfigMigrator:
    """Factory function to create configuration migrator"""
    return ConfigMigrator(console)


if __name__ == "__main__":
    # Test the configuration validation system
    console = Console()
    
    # Sample configuration
    test_config = {
        'installation_path': '~/.local/share/wsl-tmux-nvim-setup',
        'backup_retention': 5,
        'github_token': 'ghp_test_token_123456789',
        'network_timeout': 30,
        'cache_size_mb': 256,
        'preferred_components': ['tmux', 'neovim', 'yazi'],
        'excluded_components': []
    }
    
    # Validate configuration
    validator = create_config_validator(ValidationLevel.STANDARD, console)
    is_valid, issues = validator.validate_config(test_config)
    
    console.print(f"Configuration valid: {is_valid}")
    validator.display_issues()
    
    # Test migration
    old_config = {'timeout': 30, 'config_version': '1.0'}
    migrator = create_config_migrator(console)
    new_config = migrator.migrate_config(old_config)
    
    console.print(f"Migrated config: {new_config}")